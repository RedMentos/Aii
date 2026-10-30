#!/usr/bin/env python3
"""Run11O: actual pinned 350M target-mode stochasticity assay, no training/export."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from scripts.lp3_real_master_smoke import MODEL_ID, REVISION, MASTER_SHA256, verify_master
from v13.body_jepa import BodyJepaTrainer, EmaAdapter, ema_target_latent, pad
from v13.common import atomic_write

SEED = 137
TARGETS = ("Cobalt", "Vermilion")
EXPECTED_FIXTURE = "be4925666ef6ffc2206dc450f775dee8ac7a6eb21fbc67082a0f49f1e3804e95"
SOURCE_BLOB = "b560d4e88fe457f381e89dfc5d6188a8ec3b306b"


def max_pairwise(torch, values):
    """Exact maximum pairwise absolute distance, fail closed on bad inputs."""
    if len(values) < 2:
        raise ValueError("at least two repeated forwards required")
    shape = values[0].shape
    if any(v.shape != shape or not bool(torch.isfinite(v).all()) for v in values):
        raise ValueError("nonfinite or inconsistent target latents")
    return max(float((a - b).abs().max()) for i, a in enumerate(values)
               for b in values[i + 1:])


def target_assay(torch, model, batch, ema):
    """Do not reseed: detect actual target-path stochasticity with fixed inputs."""
    model.train()
    flags = [(id(m), m.training) for m in model.modules()]
    train = [ema_target_latent(torch, model, batch, ema, eval_target=False)
             for _ in range(3)]
    eval_ = [ema_target_latent(torch, model, batch, ema, eval_target=True)
             for _ in range(3)]
    if flags != [(id(m), m.training) for m in model.modules()]:
        raise ValueError("target assay changed module training flags")
    if any(v.requires_grad for v in train + eval_):
        raise ValueError("target assay retained autograd graph")
    return {
        "train_repeat_max_abs": max_pairwise(torch, train),
        "eval_repeat_max_abs": max_pairwise(torch, eval_),
        "train_vs_eval_max_abs": max(float((a - b).abs().max())
                                 for a in train for b in eval_),
    }


def positive_control(torch):
    """Known dropout-bearing HF-signature toy validates that the assay can detect it."""
    class Tiny(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.emb = torch.nn.Embedding(32, 16)
            self.drop = torch.nn.Dropout(p=0.6)
            self.lin = torch.nn.Linear(16, 16)

        def forward(self, input_ids, attention_mask=None, output_hidden_states=False):
            h = self.lin(self.drop(self.emb(input_ids)))
            return type("Out", (), {"hidden_states": (h,)})()

    torch.manual_seed(SEED)
    model = Tiny()
    ema = EmaAdapter(list(model.lin.parameters()), 0.9)
    batch = pad(torch, [[1, 2, 3], [4, 5, 6]])
    result = target_assay(torch, model, batch, ema)
    if not (result["train_repeat_max_abs"] > 0 and
            result["eval_repeat_max_abs"] == 0 and
            result["train_vs_eval_max_abs"] > 0):
        raise ValueError("dropout positive control failed")
    return result


def run(master, out):
    import torch
    from peft import LoraConfig, get_peft_model
    torch.set_num_threads(2)
    master_hash = verify_master(master)
    if master_hash != MASTER_SHA256:
        raise ValueError("pinned master SHA256 mismatch")
    control = positive_control(torch)
    trainer = BodyJepaTrainer(
        master, out / "unused_work", master_sha256=MASTER_SHA256,
        anchors=(), cfg={"seed": SEED, "threads": 2, "rank": 2, "alpha": 4.,
                         "targets": ["w1", "w2", "w3"]}, arch="lfm2")
    torch, tok, model = trainer._load()
    adapter = LoraConfig(r=2, lora_alpha=4., lora_dropout=0.,
                         target_modules=["w1", "w2", "w3"], bias="none")
    model = get_peft_model(model, adapter)
    params = [p for p in model.parameters() if p.requires_grad]
    ema = EmaAdapter(params, 0.9)
    ids = [tok(t, add_special_tokens=False)["input_ids"] for t in TARGETS]
    batch = pad(torch, ids, tok.pad_token_id if tok.pad_token_id is not None else 0)
    dropouts = [{"module": name, "p": float(mod.p)}
                for name, mod in model.named_modules()
                if isinstance(mod, torch.nn.modules.dropout._DropoutNd)]
    actual = target_assay(torch, model, batch, ema)
    report = {
        "schema": "v13.bodyjepa.350m_target_mode_stochasticity.v1",
        "evidence_class": "LINUX_FP32_TORCH_MECHANISM_ONLY",
        "model_id": MODEL_ID, "model_revision": REVISION,
        "master_sha256": master_hash, "body_jepa_source_git_blob": SOURCE_BLOB,
        "fixture_sha256": EXPECTED_FIXTURE, "seed": SEED,
        "targets": list(TARGETS), "adapter_rank": 2,
        "adapter_dropout": 0.0, "train_steps": 0, "exported_adapter": False,
        "positive_control": control, "real_master": actual,
        "dropout_modules": dropouts,
        "mode_difference_detected": actual["train_vs_eval_max_abs"] > 0,
        "utility_gate_pass": False, "production_activation": False,
        "runtime_jepa_weight": 0, "age_authority": 0,
        "redmi_measured": False, "whole_system_complete": False,
    }
    if any(not math.isfinite(v) for v in actual.values()):
        raise ValueError("nonfinite mechanism result")
    out.mkdir(parents=True, exist_ok=True)
    atomic_write(out / "report.json", json.dumps(report, sort_keys=True, indent=2))
    return report


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--execute-native", action="store_true")
    a = ap.parse_args(argv)
    if not a.execute_native:
        ap.error("explicit --execute-native required")
    report = run(a.master, a.out)
    print(json.dumps({"schema": report["schema"],
                      "real_master": report["real_master"],
                      "positive_control": report["positive_control"],
                      "mode_difference_detected": report["mode_difference_detected"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
