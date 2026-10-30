#!/usr/bin/env python3
"""Isolated pinned FP32 350M Body-JEPA heldout three-arm research ablation.

No GGUF training, no adapter export, no live runtime registration or Age grant.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import time

from lp3_real_master_smoke import MODEL_ID, REVISION, MASTER_SHA256, verify_master
from bodyjepa_real_master_gradient_20261030 import prompt_ids, tensor_digest

CODE = Path(__file__).resolve().parents[1]
FIXTURE = CODE / "specs/bodyjepa_350m_heldout_three_arm_seed101.json"
FIXTURE_BLOB = "43210decaf46e73fd8d233fc0021edfd4a39f033"
ARMS = ("CE_ONLY", "CE_EMA_JEPA", "CE_SHUFFLED_JEPA")
SEED = 101
STEPS = 4
LR = 0.001
JEPA_WEIGHT = 0.2
EMA_DECAY = 0.9
PERM = (1, 2, 3, 4, 5, 6, 7, 0)


def blob_sha(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def frozen():
    if blob_sha(FIXTURE) != FIXTURE_BLOB:
        raise ValueError("FROZEN_FIXTURE_CHANGED")
    d = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if (d.get("schema") != "v13.bodyjepa.350m.heldout_three_arm_frozen.v1"
            or d.get("seed") != SEED or len(d["rows"]) != 8
            or len(d["retention_anchors"]) != 8
            or d["master_sha256"] != MASTER_SHA256
            or tuple(d["arms"]) != ARMS
            or (d["steps"], d["lr"], d["jepa_weight"], d["ema_decay"],
                d["rank"], d["alpha"]) != (4, 0.001, 0.2, 0.9, 2, 4)):
        raise ValueError("FROZEN_PROTOCOL_CHANGED")
    if (len({r["source_id"] for r in d["rows"]}) != 8
            or len({r["prompt"] for r in d["rows"]}) != 8
            or len({r["paraphrase"] for r in d["rows"]}) != 8
            or len({r["near_miss"] for r in d["rows"]}) != 8):
        raise ValueError("SOURCE_IDS_OR_SPLIT_DUPLICATED")
    for r in d["rows"]:
        if (not all(isinstance(r[k], str) and r[k] for k in
                    ("source_id", "prompt", "target", "paraphrase", "near_miss"))
                or r["prompt"] == r["paraphrase"]
                or r["prompt"] == r["near_miss"]):
            raise ValueError("FROZEN_ROW_INVALID")
    return d


def score(arms):
    """Frozen comparative thresholds; no partial training promotes a gate."""
    if set(arms) != set(ARMS):
        return "PILOT_PARTIAL_RED"
    for arm in arms.values():
        if (arm.get("steps") != STEPS or not arm.get("frozen_unchanged")
                or not arm.get("adapter_delta_l2", 0) > 0
                or any(not isinstance(arm.get(k), (int, float))
                       or not math.isfinite(arm[k])
                       for k in ("heldout_ce", "train_ce", "retention_kl",
                                 "near_miss_kl", "adapter_delta_l2"))):
            return "PILOT_PARTIAL_RED"
    ce, ema, shuffled = (arms[k] for k in ARMS)
    if (ema["heldout_ce"] <= ce["heldout_ce"] - 0.02
            and ema["heldout_ce"] <= shuffled["heldout_ce"] - 0.02
            and ema["retention_kl"] <= 0.05 and ema["near_miss_kl"] <= 0.05):
        return "HELDOUT_JEPA_PILOT_SIGNAL"
    return "HELDOUT_BENEFIT_NOT_PROVEN"


def _encoded(tok, prompt, target=None):
    p = prompt_ids(tok, prompt)
    if target is None:
        return p, None
    ans = tok.encode(" " + target, add_special_tokens=False)
    if not ans or not all(type(x) is int for x in ans):
        raise ValueError("EMPTY_OR_INVALID_TARGET_TOKENS")
    return p + ans, [-100] * len(p) + ans


def _mean_ce(torch, model, data):
    with torch.no_grad():
        losses = []
        for ids, labels in data:
            out = model(input_ids=torch.tensor([ids], dtype=torch.long),
                        labels=torch.tensor([labels], dtype=torch.long))
            losses.append(float(out.loss))
    return sum(losses) / len(losses)


def _last_logits(torch, model, ids):
    with torch.no_grad():
        return model(input_ids=torch.tensor([ids], dtype=torch.long)).logits[0, -1].float().detach().clone()


def _mean_kl(torch, model, prompts, base_logits):
    vals = []
    for ids, base in zip(prompts, base_logits):
        current = _last_logits(torch, model, ids)
        bl = torch.log_softmax(base, -1)
        cl = torch.log_softmax(current, -1)
        vals.append(float((bl.exp() * (bl - cl)).sum()))
    return sum(vals) / len(vals)


def _l2(params, before):
    return math.sqrt(sum(float((p.detach().double() - b.double()).square().sum())
                         for p, b in zip(params, before)))


def one_arm(master, fixture, arm):
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from v13.body_jepa import EmaAdapter, jepa_loss, make_predictor, pad

    torch.set_num_threads(2)
    torch.manual_seed(SEED)
    tok = AutoTokenizer.from_pretrained(str(master), local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        str(master), dtype=torch.float32, local_files_only=True)
    model.eval()
    rows = fixture["rows"]
    train = [_encoded(tok, r["prompt"], r["target"]) for r in rows]
    heldout = [_encoded(tok, r["paraphrase"], r["target"]) for r in rows]
    near_ids = [_encoded(tok, r["near_miss"])[0] for r in rows]
    anchor_ids = [_encoded(tok, p)[0] for p in fixture["retention_anchors"]]
    base_near = [_last_logits(torch, model, ids) for ids in near_ids]
    base_anchor = [_last_logits(torch, model, ids) for ids in anchor_ids]
    ctx = pad(torch, [prompt_ids(tok, r["prompt"]) for r in rows], tok.pad_token_id or 0)
    targets = [tok.encode(" " + r["target"], add_special_tokens=False) for r in rows]
    tgt = pad(torch, targets, tok.pad_token_id or 0)
    model = get_peft_model(model, LoraConfig(
        r=2, lora_alpha=4, lora_dropout=0., target_modules=["w1", "w2", "w3"],
        bias="none"))
    model.eval()
    params = [p for p in model.parameters() if p.requires_grad]
    if not params:
        raise ValueError("NO_TRAINABLE_ADAPTER")
    before = [p.detach().clone() for p in params]
    frozen_before, frozen_n = tensor_digest(model)
    predictor = make_predictor(torch, int(model.get_input_embeddings().embedding_dim))
    ema = EmaAdapter(params, EMA_DECAY)
    opt = torch.optim.SGD(params + list(predictor.parameters()), lr=LR)
    jepa_last = None
    for step in range(STEPS):
        opt.zero_grad(set_to_none=True)
        for ids, labels in train:
            loss = model(input_ids=torch.tensor([ids], dtype=torch.long),
                         labels=torch.tensor([labels], dtype=torch.long)).loss
            (loss / len(train)).backward()
        if arm != "CE_ONLY":
            mode = "ema" if arm == "CE_EMA_JEPA" else "shuffled"
            jl, target_latents = jepa_loss(
                torch, model, predictor, ctx, tgt, mode, ema=ema,
                perm=list(PERM) if mode == "shuffled" else None)
            if target_latents.requires_grad:
                raise ValueError("TARGET_NOT_STOP_GRADIENT")
            jepa_last = float(jl.detach())
            (JEPA_WEIGHT * jl).backward()
        opt.step()
        ema.update()
    model.eval()
    train_ce = _mean_ce(torch, model, train)
    heldout_ce = _mean_ce(torch, model, heldout)
    near_kl = _mean_kl(torch, model, near_ids, base_near)
    anchor_kl = _mean_kl(torch, model, anchor_ids, base_anchor)
    frozen_after, frozen_n_after = tensor_digest(model)
    delta = _l2(params, before)
    out = {"arm": arm, "steps": STEPS, "train_ce": train_ce,
           "heldout_ce": heldout_ce, "near_miss_kl": near_kl,
           "retention_kl": anchor_kl, "adapter_delta_l2": delta,
           "ema_updates": ema.updates, "ema_delta_l2": ema.delta(),
           "jepa_last": jepa_last, "trainable_adapter_parameters": sum(p.numel() for p in params),
           "frozen_before_sha256": frozen_before, "frozen_after_sha256": frozen_after,
           "frozen_parameter_count": frozen_n, "frozen_unchanged":
               frozen_before == frozen_after and frozen_n == frozen_n_after,
           "target_permutation": list(PERM) if arm == "CE_SHUFFLED_JEPA" else None,
           "train_source_ids": [r["source_id"] for r in rows],
           "no_adapter_export": True}
    del model, predictor, opt, ema
    gc.collect()
    return out


def run(master):
    fixture = frozen()
    verify_master(master)
    start = time.monotonic()
    arms = {}
    for arm in ARMS:
        arms[arm] = one_arm(master, fixture, arm)
    status = score(arms)
    return {"schema": "v13.bodyjepa.350m.heldout_three_arm_native.v1",
            "status": status, "model_id": MODEL_ID,
            "model_revision": REVISION, "master_sha256": MASTER_SHA256,
            "fixture_blob": FIXTURE_BLOB, "seed": SEED,
            "arms": arms, "steps_per_arm": STEPS,
            "evidence_class": "LINUX_NATIVE_350M_HELDOUT_RESEARCH_ONLY",
            "training_authority": "SHADOW_NO_AGE_ACTION",
            "jepa_weight_runtime": 0, "production_activation": False,
            "adapter_exported": False, "body_jepa_utility_proven": False,
            "step2_gate_promoted": False, "b3_promoted": False,
            "redmi_measured": False, "whole_system_complete": False,
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "elapsed_s": round(time.monotonic() - start, 3)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--master", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--execute-native", action="store_true")
    args = p.parse_args()
    if not args.execute_native:
        p.error("Explicit --execute-native required")
    if args.out.exists() or args.out.is_symlink():
        raise FileExistsError("FRESH_OUTPUT_REQUIRED")
    result = run(args.master)
    payload = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    with args.out.open("x", encoding="utf-8") as f:
        f.write(payload)
        f.flush()
        os.fsync(f.fileno())
    print(json.dumps({k: result[k] for k in
                      ("status", "elapsed_s", "evidence_class")}))
    return 0 if result["status"] != "PILOT_PARTIAL_RED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
