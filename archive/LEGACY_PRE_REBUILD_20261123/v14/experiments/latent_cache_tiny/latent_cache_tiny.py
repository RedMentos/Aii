"""LOCAL_LINUX_TINY_MODEL_PROOF — directed KV-cache adapter experiment.

This is deliberately NOT a V13/LFM2.5 native adapter and does not touch the
Android runtime. It demonstrates the mechanics of a learned sender->receiver
KV cache transform with different tiny decoder geometries, a real receiver
cache injection, two-stage adapter training, negative controls and restart.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import torch
from torch import nn
from torch.nn import functional as F


VOCAB = 24
BOS, QUERY, ANSWER, EOS = 0, 1, 2, 3
KEY_BASE, VALUE_BASE = 4, 12
KEYS = VALUES = 8


@dataclass(frozen=True)
class TinySpec:
    layers: int
    width: int
    heads: int

    def validate(self) -> None:
        if self.layers < 1 or self.width < 4 or self.heads < 1 or self.width % self.heads:
            raise ValueError("invalid tiny decoder geometry")


class TinyBlock(nn.Module):
    def __init__(self, spec: TinySpec):
        super().__init__()
        self.heads = spec.heads
        self.head_dim = spec.width // spec.heads
        self.norm1 = nn.LayerNorm(spec.width)
        self.qkv = nn.Linear(spec.width, 3 * spec.width, bias=False)
        self.out = nn.Linear(spec.width, spec.width, bias=False)
        self.norm2 = nn.LayerNorm(spec.width)
        self.ff = nn.Sequential(
            nn.Linear(spec.width, 4 * spec.width), nn.GELU(),
            nn.Linear(4 * spec.width, spec.width),
        )

    def forward(self, x: torch.Tensor, past=None):
        batch, steps, width = x.shape
        qkv = self.qkv(self.norm1(x)).view(batch, steps, 3, self.heads, self.head_dim)
        q, k, v = (qkv[:, :, i].transpose(1, 2) for i in range(3))
        past_len = 0
        if past is not None:
            pk, pv = past
            past_len = pk.shape[-2]
            k = torch.cat((pk, k), dim=-2)
            v = torch.cat((pv, v), dim=-2)
        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.head_dim)
        q_pos = past_len + torch.arange(steps, device=x.device)
        k_pos = torch.arange(past_len + steps, device=x.device)
        mask = k_pos.unsqueeze(0) <= q_pos.unsqueeze(1)
        scores = scores.masked_fill(~mask.view(1, 1, steps, past_len + steps), -1.0e4)
        attended = torch.matmul(scores.softmax(dim=-1), v)
        attended = attended.transpose(1, 2).contiguous().view(batch, steps, width)
        x = x + self.out(attended)
        x = x + self.ff(self.norm2(x))
        return x, (k, v)


class TinyDecoder(nn.Module):
    def __init__(self, spec: TinySpec, max_positions: int = 16):
        super().__init__()
        spec.validate()
        self.spec = spec
        self.token = nn.Embedding(VOCAB, spec.width)
        self.position = nn.Embedding(max_positions, spec.width)
        self.blocks = nn.ModuleList(TinyBlock(spec) for _ in range(spec.layers))
        self.norm = nn.LayerNorm(spec.width)
        self.lm_head = nn.Linear(spec.width, VOCAB, bias=False)
        self.max_positions = max_positions

    def forward(self, input_ids: torch.Tensor, past_kv=None, use_cache: bool = False):
        if input_ids.ndim != 2 or input_ids.dtype != torch.long:
            raise ValueError("input_ids must be rank-2 int64")
        past_len = 0 if past_kv is None else past_kv[0][0].shape[-2]
        if past_kv is not None and len(past_kv) != len(self.blocks):
            raise ValueError("receiver cache layer count mismatch")
        if past_len + input_ids.shape[1] > self.max_positions:
            raise ValueError("sequence exceeds position table")
        positions = torch.arange(past_len, past_len + input_ids.shape[1], device=input_ids.device)
        x = self.token(input_ids) + self.position(positions).unsqueeze(0)
        presents = []
        for i, block in enumerate(self.blocks):
            x, present = block(x, None if past_kv is None else past_kv[i])
            presents.append(present)
        logits = self.lm_head(self.norm(x))
        return logits, (presents if use_cache else None)


class DenseKVAdapter(nn.Module):
    """Map every sender layer into each receiver layer, with learned KV transforms/gates."""
    def __init__(self, sender: TinySpec, receiver: TinySpec):
        super().__init__()
        sender.validate(); receiver.validate()
        self.sender = sender
        self.receiver = receiver
        self.key_maps = nn.ModuleList(nn.Linear(sender.width, receiver.width, bias=False)
                                      for _ in range(receiver.layers))
        self.value_maps = nn.ModuleList(nn.Linear(sender.width, receiver.width, bias=False)
                                        for _ in range(receiver.layers))
        self.key_gates = nn.Parameter(torch.zeros(receiver.layers, receiver.heads))
        self.value_gates = nn.Parameter(torch.zeros(receiver.layers, receiver.heads))

    def forward(self, sender_kv: Sequence[tuple[torch.Tensor, torch.Tensor]]):
        if len(sender_kv) != self.sender.layers:
            raise ValueError("sender cache layer count mismatch")
        batch = sender_kv[0][0].shape[0]
        seq = sender_kv[0][0].shape[-2]
        mapped = []
        for r in range(self.receiver.layers):
            source_pos = 0.0 if self.receiver.layers == 1 else r * (self.sender.layers - 1) / (self.receiver.layers - 1)
            lo, hi = int(math.floor(source_pos)), int(math.ceil(source_pos))
            frac = source_pos - lo
            sk = (1.0 - frac) * sender_kv[lo][0] + frac * sender_kv[hi][0]
            sv = (1.0 - frac) * sender_kv[lo][1] + frac * sender_kv[hi][1]
            if sk.shape[0] != batch or sk.shape[-2] != seq or sv.shape != sk.shape:
                raise ValueError("inconsistent sender cache tensors")
            sk = sk.transpose(1, 2).contiguous().view(batch, seq, self.sender.width)
            sv = sv.transpose(1, 2).contiguous().view(batch, seq, self.sender.width)
            tk = self.key_maps[r](sk).view(batch, seq, self.receiver.heads,
                                             self.receiver.width // self.receiver.heads).transpose(1, 2)
            tv = self.value_maps[r](sv).view(batch, seq, self.receiver.heads,
                                               self.receiver.width // self.receiver.heads).transpose(1, 2)
            kg = (2.0 * torch.sigmoid(self.key_gates[r])).view(1, -1, 1, 1)
            vg = (2.0 * torch.sigmoid(self.value_gates[r])).view(1, -1, 1, 1)
            mapped.append((tk * kg, tv * vg))
        return mapped


def make_batch(n: int, generator: torch.Generator) -> tuple[torch.Tensor, torch.Tensor]:
    keys = torch.randint(KEYS, (n,), generator=generator)
    values = torch.randint(VALUES, (n,), generator=generator)
    seq = torch.stack((
        torch.full((n,), BOS), KEY_BASE + keys, VALUE_BASE + values,
        torch.full((n,), QUERY), KEY_BASE + keys, torch.full((n,), ANSWER),
        VALUE_BASE + values, torch.full((n,), EOS),
    ), dim=1).long()
    return seq, values + VALUE_BASE


def _batches(seq: torch.Tensor, batch_size: int, generator: torch.Generator):
    order = torch.randperm(len(seq), generator=generator)
    for start in range(0, len(seq), batch_size):
        yield seq[order[start:start + batch_size]]


def train_decoder(model: TinyDecoder, seq: torch.Tensor, steps: int, seed: int) -> dict:
    optimizer = torch.optim.AdamW(model.parameters(), lr=3.0e-3, weight_decay=1.0e-4)
    generator = torch.Generator().manual_seed(seed)
    losses = []
    model.train()
    for _ in range(steps):
        batch = next(iter(_batches(seq, min(64, len(seq)), generator)))
        logits, _ = model(batch[:, :-1])
        loss = F.cross_entropy(logits.reshape(-1, VOCAB), batch[:, 1:].reshape(-1))
        optimizer.zero_grad(set_to_none=True); loss.backward(); optimizer.step()
        losses.append(float(loss.detach()))
    model.eval()
    return {"steps": steps, "initial_loss": losses[0], "final_loss": losses[-1]}


def _cache(model: TinyDecoder, prefix: torch.Tensor):
    with torch.no_grad():
        _, cache = model(prefix, use_cache=True)
    return cache


def _accuracy(model: TinyDecoder, cache, target: torch.Tensor) -> float:
    with torch.no_grad():
        token = torch.full((len(target), 1), ANSWER, dtype=torch.long)
        logits, _ = model(token, past_kv=cache)
        pred = logits[:, -1].argmax(dim=-1)
        return float((pred == target).float().mean())


def _full_context_accuracy(model: TinyDecoder, seq: torch.Tensor, target: torch.Tensor) -> float:
    with torch.no_grad():
        logits, _ = model(seq[:, :6])
        return float((logits[:, -1].argmax(dim=-1) == target).float().mean())


def run_experiment(seed: int = 13, train_n: int = 512, test_n: int = 128,
                   model_steps: int = 320, phase1_steps: int = 360,
                   phase2_steps: int = 180) -> dict:
    torch.set_num_threads(1)
    torch.manual_seed(seed)
    g = torch.Generator().manual_seed(seed + 100)
    train_seq, train_target = make_batch(train_n, g)
    test_seq, test_target = make_batch(test_n, g)
    prefix_train, prefix_test = train_seq[:, :5], test_seq[:, :5]
    sender_spec = TinySpec(layers=2, width=24, heads=4)
    receiver_spec = TinySpec(layers=3, width=32, heads=4)
    sender = TinyDecoder(sender_spec)
    receiver = TinyDecoder(receiver_spec)
    sender_fit = train_decoder(sender, train_seq, model_steps, seed + 1)
    receiver_fit = train_decoder(receiver, train_seq, model_steps, seed + 2)
    sender.eval(); receiver.eval()
    for p in sender.parameters(): p.requires_grad_(False)
    for p in receiver.parameters(): p.requires_grad_(False)

    with torch.no_grad():
        sender_train_cache = _cache(sender, prefix_train)
        sender_test_cache = _cache(sender, prefix_test)
        receiver_train_cache = _cache(receiver, prefix_train)
        receiver_test_cache = _cache(receiver, prefix_test)
    adapter = DenseKVAdapter(sender_spec, receiver_spec)
    before = [p.detach().clone() for p in adapter.parameters()]
    optimizer = torch.optim.AdamW(adapter.parameters(), lr=8.0e-3, weight_decay=1.0e-5)
    initial_train_recon = float(sum(
        F.mse_loss(a, b) + F.mse_loss(c, d)
        for (a, c), (b, d) in zip(adapter(sender_train_cache), receiver_train_cache)
    ).detach())
    initial_test_recon = float(sum(
        F.mse_loss(a, b) + F.mse_loss(c, d)
        for (a, c), (b, d) in zip(adapter(sender_test_cache), receiver_test_cache)
    ).detach())
    grad_norms = []
    for _ in range(phase1_steps):
        mapped = adapter(sender_train_cache)
        loss = sum(F.mse_loss(a, b) + F.mse_loss(c, d)
                   for (a, c), (b, d) in zip(mapped, receiver_train_cache))
        optimizer.zero_grad(set_to_none=True); loss.backward()
        grad_norms.append(float(torch.sqrt(sum((p.grad.detach() ** 2).sum() for p in adapter.parameters()
                                               if p.grad is not None))))
        optimizer.step()

    recon_after_phase1 = float(sum(
        F.mse_loss(a, b) + F.mse_loss(c, d)
        for (a, c), (b, d) in zip(adapter(sender_test_cache), receiver_test_cache)
    ).detach())
    phase1_latent_acc = _accuracy(receiver, adapter(sender_test_cache), test_target)
    phase1_state = {k: v.detach().clone() for k, v in adapter.state_dict().items()}
    optimizer2 = torch.optim.AdamW(adapter.parameters(), lr=2.0e-3, weight_decay=1.0e-5)
    for _ in range(phase2_steps):
        mapped = adapter(sender_train_cache)
        token = torch.full((train_n, 1), ANSWER, dtype=torch.long)
        logits, _ = receiver(token, past_kv=mapped)
        loss = F.cross_entropy(logits[:, -1], train_target)
        optimizer2.zero_grad(set_to_none=True); loss.backward(); optimizer2.step()

    mapped_test = adapter(sender_test_cache)
    latent_acc = _accuracy(receiver, mapped_test, test_target)
    full_acc = _full_context_accuracy(receiver, test_seq, test_target)
    no_message_acc = _accuracy(receiver, None, test_target)
    shuffled_order = torch.roll(torch.arange(test_n), shifts=1)
    shuffled_cache = _cache(sender, prefix_test[shuffled_order])
    shuffled_acc = _accuracy(receiver, adapter(shuffled_cache), test_target)
    random_adapter = DenseKVAdapter(sender_spec, receiver_spec)
    random_acc = _accuracy(receiver, random_adapter(sender_test_cache), test_target)
    delta = math.sqrt(sum(float(((p.detach() - old) ** 2).sum()) for p, old in zip(adapter.parameters(), before)))
    phase2_delta = math.sqrt(sum(float(((adapter.state_dict()[k] - v) ** 2).sum())
                                 for k, v in phase1_state.items()))
    grad_peak = max(grad_norms) if grad_norms else 0.0

    import io
    buf = io.BytesIO(); torch.save(adapter.state_dict(), buf); buf.seek(0)
    restarted = DenseKVAdapter(sender_spec, receiver_spec)
    restarted.load_state_dict(torch.load(buf, map_location="cpu", weights_only=True))
    with torch.no_grad():
        original_logits, _ = receiver(torch.full((test_n, 1), ANSWER, dtype=torch.long), past_kv=mapped_test)
        restarted_logits, _ = receiver(torch.full((test_n, 1), ANSWER, dtype=torch.long),
                                       past_kv=restarted(sender_test_cache))
    restart_max_abs = float((original_logits - restarted_logits).abs().max())

    return {
        "proof_level": "LOCAL_LINUX_TINY_MODEL_PROOF_NOT_PRODUCT_NATIVE",
        "task": "context-unaware associative recall via receiver KV-cache injection",
        "sender": vars(sender_spec), "receiver": vars(receiver_spec),
        "sender_fit": sender_fit, "receiver_fit": receiver_fit,
        "adapter": {"phase1_steps": phase1_steps, "phase2_steps": phase2_steps,
                    "initial_train_reconstruction_mse": initial_train_recon,
                    "initial_heldout_reconstruction_mse": initial_test_recon,
                    "heldout_reconstruction_mse_after_phase1": recon_after_phase1,
                    "heldout_latent_accuracy_after_phase1": phase1_latent_acc,
                    "phase2_parameter_delta_l2": phase2_delta,
                    "total_parameter_delta_l2": delta, "max_phase1_gradient_norm": grad_peak},
        "heldout_accuracy": {"full_receiver_context": full_acc, "latent_cache": latent_acc,
                              "no_message": no_message_acc, "shuffled_sender_cache": shuffled_acc,
                              "random_adapter": random_acc},
        "restart_max_abs_logit_delta": restart_max_abs,
    }


def main():
    import json
    print(json.dumps(run_experiment(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
