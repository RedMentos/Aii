#!/usr/bin/env python3
"""Pinned real-master Body-JEPA *gradient mechanism* probe, never live training.

A single isolated LoRA+predictor SGD step on LFM2.5-350M verifies that the
existing two-view JEPA loss reaches the adapter. It cannot establish B1/B2
utility, CE retention, phone capability, or any approval/gate.
"""
import argparse
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import time

from lp3_real_master_smoke import MODEL_ID, REVISION, MASTER_SHA256, verify_master

SEED = 73
PROMPTS = (
    "For the invented Velaris puzzle, what is the first vault's code?",
    "For the invented Keldara puzzle, what is the second vault's code?",
)
TARGETS = ("Amethyst vault", "Obsidian vault")


def tensor_digest(model):
    """Digest every frozen tensor, not a convenient sampled prefix."""
    h = hashlib.sha256()
    n = 0
    for name, p in model.named_parameters():
        if p.requires_grad:
            continue
        h.update(name.encode("utf-8") + b"\0")
        h.update(str(tuple(p.shape)).encode("ascii") + b"\0")
        h.update(str(p.dtype).encode("ascii") + b"\0")
        h.update(p.detach().cpu().contiguous().numpy().tobytes())
        n += p.numel()
    return h.hexdigest(), n


def norm(grads):
    return math.sqrt(sum(float(g.detach().double().square().sum())
                         for g in grads if g is not None))


def prompt_ids(tok, prompt):
    """Pinned LFM2.5 chat-template BatchEncoding -> one explicit token row."""
    import torch
    encoded = tok.apply_chat_template(
        [{"role": "user", "content": prompt}],
        add_generation_prompt=True, tokenize=True,
        return_dict=True, return_tensors="pt")
    ids = encoded.input_ids if hasattr(encoded, "input_ids") else (
        encoded.get("input_ids") if isinstance(encoded, dict) else None)
    if (not isinstance(ids, torch.Tensor) or ids.dtype != torch.long
            or ids.ndim != 2 or ids.shape[0] != 1 or ids.shape[1] < 1):
        raise ValueError("Expected a single nonempty int64 prompt token row")
    return ids[0].tolist()


def probe(master):
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from v13.body_jepa import EmaAdapter, jepa_loss, last_token_latent, make_predictor, pad

    torch.set_num_threads(2)
    torch.manual_seed(SEED)
    started = time.monotonic()
    tok = AutoTokenizer.from_pretrained(str(master), local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        str(master), dtype=torch.float32, local_files_only=True)
    model.eval()
    prompts = [prompt_ids(tok, q) for q in PROMPTS]
    targets = [tok.encode(t, add_special_tokens=False)[:2] for t in TARGETS]
    if not all(len(row) >= 2 for row in targets) or targets[0] == targets[1]:
        raise ValueError("Two distinct 2-token target views required")
    if not all(isinstance(v, int) for row in prompts + targets for v in row):
        raise ValueError("Tokenizer returned noninteger IDs")
    ctx = pad(torch, prompts, tok.pad_token_id or 0)
    tgt = pad(torch, targets, tok.pad_token_id or 0)

    # Only adapter parameters may change; the 350M FP32 master is never saved.
    model = get_peft_model(model, LoraConfig(
        r=2, lora_alpha=4, lora_dropout=0., target_modules=["w1", "w2", "w3"],
        bias="none"))
    model.eval()
    params = [p for p in model.parameters() if p.requires_grad]
    if not params:
        raise ValueError("No LoRA parameters selected")
    before = [p.detach().clone() for p in params]
    frozen_before, frozen_n = tensor_digest(model)
    hidden = int(model.get_input_embeddings().embedding_dim)
    pred = make_predictor(torch, hidden)
    ema = EmaAdapter(params, 0.9)
    opt = torch.optim.SGD(params + list(pred.parameters()), lr=0.001)

    # Wrong-target control is evaluated at exactly the same initial state.
    with torch.no_grad(), ema.swap():
        target_ema = last_token_latent(torch, model, tgt).detach()
    wrong, wrong_targets = jepa_loss(
        torch, model, pred, ctx, tgt, "shuffled",
        base_targets=target_ema, perm=[1, 0])
    wrong_value = float(wrong.detach())
    wrong_grad = norm(torch.autograd.grad(wrong, params, allow_unused=True))
    del wrong, wrong_targets
    gc.collect()

    own, own_targets = jepa_loss(
        torch, model, pred, ctx, tgt, "ema", base_targets=target_ema)
    own_value = float(own.detach())
    combined = params + list(pred.parameters())
    own_grads = torch.autograd.grad(
        own, combined, retain_graph=True, allow_unused=True)
    adapter_grad = norm(own_grads[:len(params)])
    predictor_grad = norm(own_grads[len(params):])
    if own_targets.requires_grad:
        raise ValueError("Target is not stop-gradient")
    opt.zero_grad(set_to_none=True)
    own.backward()
    opt.step()
    ema.update()
    adapter_delta = math.sqrt(sum(
        float((p.detach().double() - old.double()).square().sum())
        for p, old in zip(params, before)))
    frozen_after, frozen_n_after = tensor_digest(model)
    measurements = {
        "own_loss_before": own_value,
        "shuffled_loss_before": wrong_value,
        "own_adapter_gradient_l2": adapter_grad,
        "own_predictor_gradient_l2": predictor_grad,
        "shuffled_adapter_gradient_l2": wrong_grad,
        "adapter_step_delta_l2": adapter_delta,
        "ema_delta_l2": ema.delta(),
        "ema_updates": ema.updates,
        "trainable_adapter_parameters": sum(p.numel() for p in params),
        "predictor_parameters": sum(p.numel() for p in pred.parameters()),
        "frozen_parameter_count": frozen_n,
        "frozen_before_sha256": frozen_before,
        "frozen_after_sha256": frozen_after,
        "frozen_parameter_count_after": frozen_n_after,
        "prompt_token_lengths": [len(row) for row in prompts],
        "target_token_lengths": [len(row) for row in targets],
    }
    finite = all(math.isfinite(x) for x in (
        own_value, wrong_value, adapter_grad, predictor_grad, wrong_grad,
        adapter_delta, measurements["ema_delta_l2"]))
    observed = bool(finite and adapter_grad > 0 and predictor_grad > 0
                    and adapter_delta > 0 and measurements["ema_delta_l2"] > 0
                    and ema.updates == 1 and frozen_before == frozen_after
                    and frozen_n == frozen_n_after)
    return {
        "schema": "v13.bodyjepa.real_master_gradient.v1",
        "status": "NATIVE_GRADIENT_COMPAT_ONLY" if observed else "FAIL",
        "model_id": MODEL_ID, "model_revision": REVISION,
        "master_sha256": MASTER_SHA256,
        "body_jepa_source_git_blob": "be022258cd46cc11e460dd7438563c0d0cc4a0eb",
        "seed": SEED, "torch": torch.__version__,
        "evidence_class": "LINUX_NATIVE_MECHANISM_ONLY",
        "objective": "JEPA_ONLY_ONE_STEP_NO_CE_OR_RETENTION",
        "jepa_training_weight": 1, "jepa_weight_runtime": 0,
        "age_authority": 0, "production_activation": False,
        "body_jepa_utility_proven": False, "redmi_measured": False,
        "step2_utility_pass": False, "b3_authority": 0,
        "whole_system_complete": False,
        "source_fixture_sha256": hashlib.sha256(json.dumps(
            {"prompts": PROMPTS, "targets": TARGETS},
            sort_keys=True).encode()).hexdigest(),
        "measurements": measurements,
        "elapsed_s": round(time.monotonic() - started, 3),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--execute-native", action="store_true")
    args = ap.parse_args(argv)
    if not args.execute_native:
        ap.error("Explicit --execute-native required")
    verify_master(args.master)
    if args.out.exists() or args.out.is_symlink():
        raise ValueError("Refusing to overwrite an existing native receipt")
    result = probe(args.master)
    payload = json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
    with args.out.open("x", encoding="utf-8") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    print(payload, end="", flush=True)
    return 0 if result["status"] == "NATIVE_GRADIENT_COMPAT_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
