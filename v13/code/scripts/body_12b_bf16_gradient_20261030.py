#!/usr/bin/env python3
"""Pinned upstream 1.2B BF16 Body-JEPA one-step gradient compatibility.

Research only: NOT the registered QAD GGUF B1/B2 train runner, Redmi evidence,
JEPA utility, or an Age/production learning permission.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import time

MODEL_ID = "LiquidAI/LFM2.5-1.2B-Instruct"
REVISION = "8c1348a4aac046a3a5d7698e7fcaaa8a3b7d9cdf"
MASTER_SHA256 = "1ba63d9adb03ae43581db0e136e4416febe0441aff7296397bd455fb6017f73a"
SEED = 97
PROMPTS = (
    "In the invented Asterion atlas, which star has code QZ-17?",
    "In the invented Keldara atlas, which star has code VX-29?",
)
TARGETS = ("Quartz star", "Violet star")


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_master(master):
    p = Path(master)
    if (not p.is_dir() or not (p / "config.json").is_file()
            or not (p / "LICENSE").is_file()
            or sha_file(p / "model.safetensors") != MASTER_SHA256):
        raise ValueError("Pinned 1.2B upstream master/license SHA mismatch")
    return MASTER_SHA256


def frozen_digest(model):
    """Hash every frozen parameter byte, including BF16 without NumPy BF16."""
    import torch
    h = hashlib.sha256()
    count = 0
    for name, p in model.named_parameters():
        if p.requires_grad:
            continue
        h.update(name.encode() + b"\0")
        h.update(str(tuple(p.shape)).encode() + b"\0")
        h.update(str(p.dtype).encode() + b"\0")
        h.update(p.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes())
        count += p.numel()
    return h.hexdigest(), count


def norm(grads):
    return math.sqrt(sum(float(g.detach().double().square().sum())
                         for g in grads if g is not None))


def prompt_ids(tok, prompt):
    import torch
    encoded = tok.apply_chat_template(
        [{"role": "user", "content": prompt}], tokenize=True,
        add_generation_prompt=True, return_dict=True, return_tensors="pt")
    ids = encoded["input_ids"]
    if (not isinstance(ids, torch.Tensor) or ids.dtype != torch.long
            or ids.ndim != 2 or ids.shape[0] != 1 or ids.shape[1] < 1):
        raise ValueError("Expected a single int64 LFM2.5 prompt row")
    return ids[0].tolist()


def probe(master):
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from v13.body_jepa import EmaAdapter, jepa_loss, last_token_latent, make_predictor, pad

    class FloatInput(torch.nn.Module):
        def forward(self, x):
            return x.float()

    torch.set_num_threads(2)
    torch.manual_seed(SEED)
    started = time.monotonic()
    tok = AutoTokenizer.from_pretrained(str(master), local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        str(master), dtype=torch.bfloat16, local_files_only=True,
        low_cpu_mem_usage=True)
    model.eval()
    ctx_rows = [prompt_ids(tok, q) for q in PROMPTS]
    tgt_rows = [tok.encode(t, add_special_tokens=False)[:2] for t in TARGETS]
    if not all(len(x) == 2 for x in tgt_rows) or tgt_rows[0] == tgt_rows[1]:
        raise ValueError("Two distinct 2-token target views required")
    ctx = pad(torch, ctx_rows, tok.pad_token_id or 0)
    tgt = pad(torch, tgt_rows, tok.pad_token_id or 0)
    model = get_peft_model(model, LoraConfig(
        r=2, lora_alpha=4, lora_dropout=0., target_modules=["w1", "w2", "w3"],
        bias="none"))
    model.eval()
    params = [p for p in model.parameters() if p.requires_grad]
    if not params:
        raise ValueError("No 1.2B LoRA trainable parameters")
    param_dtypes = sorted({str(p.dtype) for p in params})
    before = [p.detach().clone() for p in params]
    frozen_before, frozen_n = frozen_digest(model)
    hidden = int(model.get_input_embeddings().embedding_dim)
    predictor = torch.nn.Sequential(FloatInput(), make_predictor(torch, hidden))
    ema = EmaAdapter(params, 0.9)
    optimizer = torch.optim.SGD(params + list(predictor.parameters()), lr=0.01)

    with torch.no_grad(), ema.swap():
        target = last_token_latent(torch, model, tgt).detach()
    wrong, _ = jepa_loss(torch, model, predictor, ctx, tgt, "shuffled",
                         base_targets=target, perm=[1, 0])
    wrong_loss = float(wrong.detach())
    wrong_grad = norm(torch.autograd.grad(wrong, params, allow_unused=True))
    del wrong
    own, detached_target = jepa_loss(
        torch, model, predictor, ctx, tgt, "ema", base_targets=target)
    own_loss = float(own.detach())
    if detached_target.requires_grad:
        raise ValueError("EMA target was not detached")
    combined = params + list(predictor.parameters())
    grads = torch.autograd.grad(own, combined, retain_graph=True, allow_unused=True)
    adapter_grad = norm(grads[:len(params)])
    predictor_grad = norm(grads[len(params):])
    optimizer.zero_grad(set_to_none=True)
    own.backward()
    optimizer.step()
    ema.update()
    adapter_delta = math.sqrt(sum(
        float((p.detach().double() - old.double()).square().sum())
        for p, old in zip(params, before)))
    frozen_after, frozen_n_after = frozen_digest(model)
    ema_delta = ema.delta()
    finite = all(math.isfinite(x) for x in
                 (wrong_loss, own_loss, wrong_grad, adapter_grad,
                  predictor_grad, adapter_delta, ema_delta))
    observed = (finite and adapter_grad > 0 and predictor_grad > 0
                and adapter_delta > 0 and ema_delta > 0 and ema.updates == 1
                and frozen_before == frozen_after and frozen_n == frozen_n_after)
    return {
        "schema": "v13.body_12b_bf16_gradient.v1",
        "status": "LINUX_12B_BF16_GRADIENT_COMPAT_ONLY" if observed else "FAIL",
        "model_id": MODEL_ID, "model_revision": REVISION,
        "master_sha256": MASTER_SHA256, "seed": SEED,
        "evidence_class": "LINUX_UPSTREAM_BF16_12B_ONLY",
        "torch": torch.__version__, "base_dtype": "torch.bfloat16",
        "adapter_dtypes": param_dtypes, "jepa_training_weight": 1,
        "runtime_jepa_weight": 0, "age_authority": 0,
        "registered_qad_master_parity": False, "redmi_measured": False,
        "body_jepa_utility_proven": False, "train_runner_proof": False,
        "production_activation": False, "step2_utility_pass": False,
        "b3_authority": 0, "whole_system_complete": False,
        "source_fixture_sha256": hashlib.sha256(json.dumps(
            {"prompts": PROMPTS, "targets": TARGETS}, sort_keys=True).encode()).hexdigest(),
        "measurements": {
            "own_loss": own_loss, "shuffled_loss": wrong_loss,
            "own_adapter_gradient_l2": adapter_grad,
            "own_predictor_gradient_l2": predictor_grad,
            "shuffled_adapter_gradient_l2": wrong_grad,
            "adapter_delta_l2": adapter_delta, "ema_delta_l2": ema_delta,
            "ema_updates": ema.updates,
            "trainable_adapter_parameters": sum(p.numel() for p in params),
            "frozen_parameter_count": frozen_n,
            "frozen_parameter_count_after": frozen_n_after,
            "frozen_before_sha256": frozen_before,
            "frozen_after_sha256": frozen_after,
            "prompt_token_lengths": [len(v) for v in ctx_rows],
            "target_token_lengths": [len(v) for v in tgt_rows],
            "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        },
        "elapsed_s": round(time.monotonic() - started, 3),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--execute-native", action="store_true")
    a = ap.parse_args(argv)
    if not a.execute_native:
        ap.error("Explicit --execute-native required")
    verify_master(a.master)
    if a.out.exists() or a.out.is_symlink():
        raise ValueError("Refusing to overwrite a 1.2B native receipt")
    result = probe(a.master)
    with a.out.open("x", encoding="utf-8") as f:
        f.write(json.dumps(result, sort_keys=True, indent=2) + "\n")
        f.flush()
        os.fsync(f.fileno())
    print(json.dumps({"status": result["status"], "measurements": result["measurements"]}), flush=True)
    return 0 if result["status"] == "LINUX_12B_BF16_GRADIENT_COMPAT_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
