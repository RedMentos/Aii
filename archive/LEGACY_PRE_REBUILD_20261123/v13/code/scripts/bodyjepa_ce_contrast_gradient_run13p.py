#!/usr/bin/env python3
"""Run13P: isolated CE vs contrastive Body-JEPA LoRA gradient attribution.

No optimizer step, weight export, Runtime wiring, model training, or gate
promotion. Real master is optional only with explicit --execute-native.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

from scripts.lp3_real_master_smoke import MODEL_ID, REVISION, MASTER_SHA256, verify_master

SEED = 257
FIXTURE = (
    ("In the invented Meren257 archive, what is the silver vault key?", "Quartz"),
    ("In the invented Oriel257 archive, what is the jade vault key?", "Amber"),
    ("In the invented Pavan257 archive, what is the copper vault key?", "Cedar"),
    ("In the invented Quorin257 archive, what is the indigo vault key?", "Violet"),
)
FIXTURE_SHA256 = "9a7ab2d99694a45d56292fe8f8500b34264f66bfd8c47590855d1ff9232607d4"
LICENSE_SHA256 = "4d28ca14dedc0b3d0fcc2b3339f0e79931faa33874f3d24f522183a8fc70068c"
WEIGHT = 0.25
TEMP = 0.1
DERANGEMENT = (1, 2, 3, 0)


def fixture_hash():
    return hashlib.sha256(json.dumps(FIXTURE, sort_keys=True,
                           separators=(",", ":")).encode()).hexdigest()


def tensor_digest(model):
    """Hash every frozen tensor before and after read-only autograd."""
    h = hashlib.sha256()
    count = 0
    for name, p in model.named_parameters():
        if p.requires_grad:
            continue
        h.update(name.encode("utf-8") + b"\\0")
        h.update(str(tuple(p.shape)).encode("ascii") + b"\\0")
        h.update(str(p.dtype).encode("ascii") + b"\\0")
        h.update(p.detach().cpu().contiguous().numpy().tobytes())
        count += p.numel()
    return h.hexdigest(), count


def _detach_grads(grads, params):
    """Preserve exact shapes; unused parameters contribute explicit zero."""
    import torch
    if len(grads) != len(params):
        raise ValueError("GRADIENT_COUNT_RED")
    out = []
    for g, p in zip(grads, params):
        if g is not None and (g.shape != p.shape or not bool(torch.isfinite(g).all())):
            raise ValueError("GRADIENT_SHAPE_OR_NONFINITE_RED")
        out.append(torch.zeros_like(p).detach() if g is None else g.detach().clone())
    return out


def gradient_summary(torch, ce, correct, shuffled, predictor):
    """Read-only signed LoRA gradient attribution, not a utility score."""
    if not ce or not (len(ce) == len(correct) == len(shuffled)):
        raise ValueError("GRADIENT_SET_RED")
    if not predictor:
        raise ValueError("PREDICTOR_GRADIENT_SET_RED")
    for group in (ce, correct, shuffled, predictor):
        if any(not isinstance(v, torch.Tensor) or not bool(torch.isfinite(v).all())
               for v in group):
            raise ValueError("NONFINITE_GRADIENT_RED")
    def squared(group):
        return sum(float(v.detach().double().square().sum()) for v in group)
    def dot(a, b):
        return sum(float((x.detach().double() * y.detach().double()).sum())
                   for x, y in zip(a, b))
    ce_norm = math.sqrt(squared(ce))
    correct_norm = math.sqrt(squared(correct))
    shuffled_norm = math.sqrt(squared(shuffled))
    pred_norm = math.sqrt(squared(predictor))
    if min(ce_norm, correct_norm, shuffled_norm, pred_norm) <= 0:
        raise ValueError("ZERO_GRADIENT_RED")
    cosine = dot(ce, correct) / (ce_norm * correct_norm)
    control_cosine = dot(correct, shuffled) / (correct_norm * shuffled_norm)
    ratio = WEIGHT * correct_norm / ce_norm
    values = (ce_norm, correct_norm, shuffled_norm, pred_norm, cosine,
              control_cosine, ratio)
    if not all(math.isfinite(v) for v in values):
        raise ValueError("GRADIENT_METRIC_NONFINITE_RED")
    if abs(cosine) > 1.000001 or abs(control_cosine) > 1.000001:
        raise ValueError("GRADIENT_COSINE_RED")
    return {
        "ce_adapter_l2": ce_norm,
        "contrastive_adapter_l2": correct_norm,
        "shuffled_adapter_l2": shuffled_norm,
        "contrastive_predictor_l2": pred_norm,
        "ce_vs_contrastive_signed_cosine": max(-1., min(1., cosine)),
        "correct_vs_shuffled_signed_cosine": max(-1., min(1., control_cosine)),
        "weighted_contrastive_over_ce_l2": ratio,
        "candidate_weight": WEIGHT,
        "contrastive_temperature": TEMP,
    }


def probe(master):
    import torch
    from peft import LoraConfig, get_peft_model
    from v13.body_jepa import BodyJepaTrainer, EmaAdapter, pad, make_predictor
    from v13.body_jepa import last_token_latent, ema_target_latent
    from v13.body_jepa_contrastive_shadow import loss_and_metrics

    if fixture_hash() != FIXTURE_SHA256:
        raise ValueError("FIXTURE_PIN_RED")
    torch.set_num_threads(2)
    torch.manual_seed(SEED)
    trainer = BodyJepaTrainer(
        master, master / "run13p-unused-work", master_sha256=MASTER_SHA256,
        anchors=(), cfg={"seed": SEED, "threads": 2, "max_tokens": 96,
                         "rank": 2, "alpha": 4., "targets": ["w1", "w2", "w3"]})
    torch, tok, model = trainer._load()
    data = []
    ctx = []
    tgt = []
    for q, answer in FIXTURE:
        pid, _ = trainer._encode(tok, q)
        target = tok(answer + "<|im_end|>", add_special_tokens=False)["input_ids"]
        if not pid or not target or len(pid) + len(target) > 96:
            raise ValueError("PROMPT_TRUNCATION_RED")
        data.append(trainer._encode(tok, q, answer))
        ctx.append(pid)
        tgt.append(tok(answer, add_special_tokens=False)["input_ids"])
    if any(not t for t in tgt):
        raise ValueError("EMPTY_TARGET_RED")
    pad_id = tok.pad_token_id if tok.pad_token_id is not None else 0
    ids, lens = pad(torch, [d[0] for d in data], pad_id)
    labels = torch.full(ids.shape, -100, dtype=torch.long)
    for row, (_, lab) in enumerate(data):
        labels[row, :len(lab)] = torch.tensor(lab, dtype=torch.long)
    if not bool((labels[:, 1:] != -100).any(dim=1).all()):
        raise ValueError("CE_LABELS_MISSING_RED")
    attention = (torch.arange(ids.shape[1])[None, :] < lens[:, None]).long()
    ctx_batch = pad(torch, ctx, pad_id)
    tgt_batch = pad(torch, tgt, pad_id)
    model = get_peft_model(model, LoraConfig(
        r=2, lora_alpha=4., lora_dropout=0., target_modules=["w1", "w2", "w3"],
        bias="none"))
    model.eval()
    params = [p for p in model.parameters() if p.requires_grad]
    if not params:
        raise ValueError("NO_LORA_PARAMETERS")
    frozen_before, frozen_count = tensor_digest(model)
    with torch.no_grad():
        target = last_token_latent(torch, model, tgt_batch).detach()
    predictor = make_predictor(torch, int(target.shape[-1]))
    predictor.eval()
    ema = EmaAdapter(params, 0.9)
    target_ema = ema_target_latent(
        torch, model, tgt_batch, ema, eval_target=True)
    if target_ema.requires_grad:
        raise ValueError("EMA_TARGET_HAS_GRADIENT_RED")

    # Each objective uses the same untouched initial LoRA and predictor.
    output = model(input_ids=ids, attention_mask=attention)
    logits = output.logits[:, :-1].float()
    y = labels[:, 1:]
    ce_loss = torch.nn.functional.cross_entropy(
        logits.reshape(-1, logits.shape[-1]), y.reshape(-1),
        ignore_index=-100)
    ce_grads = _detach_grads(
        torch.autograd.grad(ce_loss, params, allow_unused=True), params)
    ce_value = float(ce_loss.detach())
    del output, logits, ce_loss

    def contrast(permutation):
        latent = predictor(last_token_latent(torch, model, ctx_batch))
        loss, metrics = loss_and_metrics(
            torch, latent, target_ema, temperature=TEMP,
            weights=torch.ones(len(FIXTURE), dtype=latent.dtype),
            permutation=permutation)
        all_params = params + list(predictor.parameters())
        gradients = torch.autograd.grad(loss, all_params, allow_unused=True)
        a = _detach_grads(gradients[:len(params)], params)
        p = _detach_grads(gradients[len(params):], list(predictor.parameters()))
        value = float(loss.detach())
        return value, metrics, a, p

    correct_loss, correct_meta, correct_grads, pred_grads = contrast(None)
    wrong_loss, wrong_meta, wrong_grads, _ = contrast(DERANGEMENT)
    measured = gradient_summary(
        torch, ce_grads, correct_grads, wrong_grads, pred_grads)
    frozen_after, count_after = tensor_digest(model)
    if frozen_before != frozen_after or frozen_count != count_after:
        raise ValueError("FROZEN_MASTER_CHANGED_RED")
    if any(not math.isfinite(v) for v in (ce_value, correct_loss, wrong_loss)):
        raise ValueError("NONFINITE_LOSS_RED")
    measured.update({
        "ce_loss": ce_value, "contrastive_loss": correct_loss,
        "shuffled_loss": wrong_loss,
        "correct_target_spread": correct_meta["target_spread"],
        "correct_diagonal_top1": correct_meta["diagonal_top1"],
        "shuffled_diagonal_top1": wrong_meta["diagonal_top1"],
        "frozen_before_sha256": frozen_before,
        "frozen_after_sha256": frozen_after,
        "frozen_parameter_count": frozen_count,
        "adapter_parameter_count": sum(p.numel() for p in params),
        "predictor_parameter_count": sum(p.numel() for p in predictor.parameters()),
        "ema_updates": ema.updates,
        "no_optimizer_step": True,
        "no_model_export": True,
    })
    return {
        "schema": "v13.bodyjepa.ce_contrast_gradient_run13p.v1",
        "status": "ATTRIBUTABLE_GRADIENT_PRESENT_MECHANISM_ONLY",
        "model_id": MODEL_ID, "model_revision": REVISION,
        "master_sha256": MASTER_SHA256,
        "license_sha256": LICENSE_SHA256,
        "seed": SEED, "fixture_sha256": FIXTURE_SHA256,
        "source_level": "LINUX_NATIVE_MECHANISM_ONLY",
        "measurement": measured,
        "age0": "RECORD_ONLY", "step2_status": "UTILITY_FAIL",
        "b3_status": "NO_PROMOTION", "body_jepa_status": "UNAVAILABLE",
        "jepa_weight_runtime": 0, "learning_enabled": False,
        "utility_gate_pass": False, "redmi_measured": False,
        "whole_system_complete": False,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--master", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--execute-native", action="store_true")
    args = ap.parse_args(argv)
    if not args.execute_native:
        ap.error("Explicit --execute-native required")
    if args.out.exists() or args.out.is_symlink():
        raise ValueError("REFUSE_OVERWRITE")
    verify_master(args.master)
    license_path = args.master / "LICENSE"
    if (not license_path.is_file() or license_path.is_symlink()
            or hashlib.sha256(license_path.read_bytes()).hexdigest() != LICENSE_SHA256):
        raise ValueError("MODEL_LICENSE_PIN_RED")
    result = probe(args.master)
    data = json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
    with args.out.open("x", encoding="utf-8") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    print(json.dumps({"status": result["status"], "measurement": result["measurement"]},
                     sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
