"""Synthetic research probe for context-conditioned sparse engram-style gates.

This is not a reproduction of Aguilar et al. and is not a V14 runtime component.
It tests whether a tiny input-conditioned top-k gate learns to route two sequential
context-dependent tasks differently, with a dense and static-mask comparator.
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
from dataclasses import asdict, dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset


@dataclass
class RunResult:
    old_pre: float
    old_post: float
    new_post: float
    forgetting: float
    parameter_l1_delta: float
    gate_parameter_l1_delta: float | None
    max_gate_grad_l2: float
    context_mask_jaccard: float | None
    context_shuffle_accuracy: float | None


class LearnedContextTopK(nn.Module):
    """Trainable input-conditioned gate; top-k inference, Bernoulli STE training."""

    def __init__(self, input_dim: int = 9, hidden: int = 32, active: int = 8):
        super().__init__()
        self.gate = nn.Linear(input_dim, hidden)
        self.backbone = nn.Linear(input_dim, hidden)
        self.head = nn.Linear(hidden, 2)
        self.active = active

    def forward(self, x: torch.Tensor):
        logits = self.gate(x)
        top_indices = logits.topk(self.active, dim=-1).indices
        top_mask = torch.zeros_like(logits).scatter_(1, top_indices, 1.0)
        selected_probabilities = torch.sigmoid(logits) * top_mask
        if self.training:
            sampled = torch.bernoulli(selected_probabilities)
            mask = sampled - selected_probabilities.detach() + selected_probabilities
        else:
            mask = top_mask
        hidden = F.relu(self.backbone(x)) * mask
        return self.head(hidden), top_mask


class StaticTopK(nn.Module):
    """Same 32-unit width, but one fixed random 8-unit mask for all contexts."""

    def __init__(self, input_dim: int = 9, hidden: int = 32, active: int = 8):
        super().__init__()
        self.backbone = nn.Linear(input_dim, hidden)
        self.head = nn.Linear(hidden, 2)
        generator = torch.Generator().manual_seed(123)
        indices = torch.randperm(hidden, generator=generator)[:active]
        mask = torch.zeros(hidden)
        mask[indices] = 1.0
        self.register_buffer("fixed_mask", mask)

    def forward(self, x: torch.Tensor):
        mask = self.fixed_mask.expand(x.shape[0], -1)
        return self.head(F.relu(self.backbone(x)) * mask), mask


class DenseReference(nn.Module):
    """Dense comparator with the same eight active hidden units per input."""

    def __init__(self, input_dim: int = 9, hidden: int = 8):
        super().__init__()
        self.backbone = nn.Linear(input_dim, hidden)
        self.head = nn.Linear(hidden, 2)

    def forward(self, x: torch.Tensor):
        return self.head(F.relu(self.backbone(x))), None


def make_task(task: int, count: int, seed: int):
    generator = torch.Generator().manual_seed(seed)
    features = torch.randn(count, 8, generator=generator)
    if task == 0:
        labels = (
            features[:, 0] + features[:, 1] + features[:, 2] + features[:, 3] > 0
        ).long()
        context = torch.ones(count, 1)
    elif task == 1:
        labels = (
            features[:, 0] - features[:, 1] + features[:, 2] - features[:, 3] > 0
        ).long()
        context = -torch.ones(count, 1)
    else:
        raise ValueError("task must be 0 or 1")
    return torch.cat((features, context), dim=1), labels


def train_task(
    model: nn.Module,
    inputs: torch.Tensor,
    labels: torch.Tensor,
    *,
    epochs: int = 12,
    learning_rate: float = 0.01,
) -> float:
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    loader = DataLoader(TensorDataset(inputs, labels), batch_size=64, shuffle=True)
    maximum_gate_gradient = 0.0
    model.train()
    for _ in range(epochs):
        for batch_x, batch_y in loader:
            optimizer.zero_grad(set_to_none=True)
            logits, _ = model(batch_x)
            loss = F.cross_entropy(logits, batch_y)
            loss.backward()
            gate = getattr(model, "gate", None)
            if gate is not None and gate.weight.grad is not None:
                maximum_gate_gradient = max(
                    maximum_gate_gradient,
                    float(torch.linalg.vector_norm(gate.weight.grad).item()),
                )
            optimizer.step()
    return maximum_gate_gradient


@torch.no_grad()
def accuracy(model: nn.Module, task: int, seed: int) -> float:
    inputs, labels = make_task(task, 512, seed)
    model.eval()
    logits, _ = model(inputs)
    return float((logits.argmax(1) == labels).float().mean().item())


@torch.no_grad()
def context_mask_jaccard(model: LearnedContextTopK) -> float:
    x0, _ = make_task(0, 256, 1001)
    x1, _ = make_task(1, 256, 1002)
    model.eval()
    _, mask0 = model(x0)
    _, mask1 = model(x1)
    active0 = mask0.mean(0) > 0.5
    active1 = mask1.mean(0) > 0.5
    union = int((active0 | active1).sum().item())
    intersection = int((active0 & active1).sum().item())
    return intersection / max(1, union)


@torch.no_grad()
def context_shuffle_accuracy(model: LearnedContextTopK, seed: int) -> float:
    inputs, labels = make_task(0, 512, seed)
    inputs[:, 8] *= -1
    model.eval()
    logits, _ = model(inputs)
    return float((logits.argmax(1) == labels).float().mean().item())


def run_seed(seed: int, kind: str, *, epochs: int = 12) -> RunResult:
    torch.manual_seed(seed)
    if kind == "learned":
        model = LearnedContextTopK()
    elif kind == "static":
        model = StaticTopK()
    elif kind == "dense":
        model = DenseReference()
    else:
        raise ValueError(kind)

    before = [parameter.detach().clone() for parameter in model.parameters()]
    gate_module = getattr(model, "gate", None)
    gate_before = (
        [parameter.detach().clone() for parameter in gate_module.parameters()]
        if gate_module is not None else None
    )
    x0, y0 = make_task(0, 512, seed + 10)
    x1, y1 = make_task(1, 512, seed + 20)

    max_gate_grad = train_task(model, x0, y0, epochs=epochs)
    old_pre = accuracy(model, 0, seed + 100)
    max_gate_grad = max(
        max_gate_grad, train_task(model, x1, y1, epochs=epochs)
    )
    old_post = accuracy(model, 0, seed + 100)
    new_post = accuracy(model, 1, seed + 101)
    parameter_delta = sum(
        float((parameter.detach() - initial).abs().sum().item())
        for parameter, initial in zip(model.parameters(), before)
    )
    gate_parameter_delta = (
        sum(
            float((parameter.detach() - initial).abs().sum().item())
            for parameter, initial in zip(gate_module.parameters(), gate_before)
        )
        if gate_module is not None else None
    )

    if kind == "learned":
        jaccard = context_mask_jaccard(model)
        shuffled = context_shuffle_accuracy(model, seed + 100)
    else:
        jaccard = None
        shuffled = None

    return RunResult(
        old_pre=old_pre,
        old_post=old_post,
        new_post=new_post,
        forgetting=old_pre - old_post,
        parameter_l1_delta=parameter_delta,
        gate_parameter_l1_delta=gate_parameter_delta,
        max_gate_grad_l2=max_gate_grad,
        context_mask_jaccard=jaccard,
        context_shuffle_accuracy=shuffled,
    )


def summarize(values: list[float | None]):
    values = [float(value) for value in values if value is not None]
    if not values:
        return None
    return {
        "mean": statistics.mean(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def run_experiment(seeds=range(10), *, epochs: int = 12) -> dict:
    seeds = tuple(seeds)
    results = {}
    for kind in ("dense", "static", "learned"):
        rows = [run_seed(seed, kind, epochs=epochs) for seed in seeds]
        results[kind] = {
            key: summarize([getattr(row, key) for row in rows])
            for key in RunResult.__dataclass_fields__
        }
    return {
        "status": "SYNTHETIC_RESEARCH_ONLY",
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "device": "cpu",
        },
        "setup": {
            "task": "two sequential context-conditioned binary functions",
            "samples_per_task": 512,
            "epochs_per_task": epochs,
            "seeds": list(seeds),
            "learned_gate": (
                "32 hidden units, deterministic top-8 inference, "
                "Bernoulli + straight-through training"
            ),
            "static_gate": "fixed top-8 of 32 hidden units",
            "dense_reference": "8 dense hidden units",
            "replay": False,
            "binarization": False,
            "metaplasticity": False,
        },
        "results": results,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--epochs", type=int, default=12)
    args = parser.parse_args(argv)
    if not 1 <= args.seeds <= 100 or not 1 <= args.epochs <= 100:
        parser.error("--seeds and --epochs must be in 1..100")
    report = run_experiment(range(args.seeds), epochs=args.epochs)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
