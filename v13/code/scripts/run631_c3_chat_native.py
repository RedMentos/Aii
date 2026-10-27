#!/usr/bin/env python3
"""Run631: official chat-template native C3 LoRA utility, synthetic-only and shadow."""
import argparse
import json
import math
from pathlib import Path
import time
from transformers import AutoTokenizer
from scripts import run630_c3_llama_native as P

CASES = (
    ("train", "In the fictional Larch protocol, what is the marker color?", ("amber",)),
    ("train", "In the fictional Larch protocol, what is the gate number?", ("47",)),
    ("heldout", "What is two plus two?", ("4",)),
    ("heldout", "Write a brief greeting.", ("hello", "hi")),
    ("near_miss", "In the fictional Cedar protocol, what is the marker color?", ("amber",)),
    ("near_miss", "In the fictional Cedar protocol, what is the gate number?", ("47",)),
)


def format_chat(tokenizer, question):
    if not isinstance(question, str) or not question or "<|im_" in question:
        raise ValueError("untrusted question/template delimiter")
    prompt = tokenizer.apply_chat_template(
        [{"role": "user", "content": question}], add_generation_prompt=True, tokenize=False)
    if not isinstance(prompt, str) or not prompt.endswith("<|im_start|>assistant\n"):
        raise ValueError("pinned SmolLM2 chat-template mismatch")
    return prompt


def token_parity(tokenizer, native_base, prompt):
    hf = tokenizer(prompt, add_special_tokens=False)["input_ids"]
    native = P._json(native_base + "/tokenize", {"content": prompt, "add_special": False}, timeout=20)
    tokens = native.get("tokens")
    if not isinstance(tokens, list) or not all(isinstance(i, int) for i in tokens):
        raise ValueError("invalid native tokenizer result")
    if tokens != hf:
        raise ValueError("HF/native token parity mismatch: hf=%d native=%d" % (len(hf), len(tokens)))
    return {"tokens": len(hf), "match": True}


def sample(native_base, prompt, scale=None):
    body = {"prompt": prompt, "n_predict": 32, "temperature": 0,
            "seed": 13, "n_probs": 64, "cache_prompt": False,
            "stream": False, "return_tokens": True}
    if scale is not None:
        body["lora"] = [{"id": 0, "scale": float(scale)}]
    start = time.monotonic()
    out = P._json(native_base + "/completion", body, timeout=90)
    elapsed = time.monotonic() - start
    probs = out.get("completion_probabilities") or []
    if not probs or not isinstance(probs[0].get("top_logprobs"), list):
        raise ValueError("native first-token logprobs missing")
    lp = {}
    for item in probs[0]["top_logprobs"]:
        token, logp = item.get("id"), item.get("logprob")
        if not isinstance(token, int) or not isinstance(logp, (float, int)) or not math.isfinite(logp):
            raise ValueError("nonfinite/invalid logprob")
        lp[token] = float(logp)
    if not lp:
        raise ValueError("empty native top-k")
    text = out.get("content")
    if not isinstance(text, str):
        raise ValueError("invalid native generated content")
    return {"text": text[:1500], "token_id": probs[0].get("id"),
            "logprobs": lp, "seconds": round(elapsed, 5),
            "generated_token_count": len(out.get("tokens") or [])}


def hit(text, keys):
    lower = " ".join(text.lower().split())
    return any(key.lower() in lower for key in keys)


def aggregate(rows):
    groups = {}
    for group in ("train", "heldout", "near_miss"):
        sub = [r for r in rows if r["group"] == group]
        groups[group] = {
            "base_hits": sum(r["base_key_hit"] for r in sub),
            "candidate_hits": sum(r["scale1_key_hit"] for r in sub),
            "count": len(sub),
        }
    gain = groups["train"]["candidate_hits"] > groups["train"]["base_hits"]
    retention = groups["heldout"]["candidate_hits"] >= groups["heldout"]["base_hits"]
    locality = groups["near_miss"]["candidate_hits"] <= groups["near_miss"]["base_hits"]
    return {"groups": groups, "synthetic_train_gain": gain,
            "heldout_nonregression": retention, "near_miss_nonleak": locality,
            "bounded_synthetic_utility": bool(gain and retention and locality)}


def run(master_dir, model, adapter, proof, cohort, server, output):
    binding = P.verify_inputs(master_dir, model, adapter, proof, server, cohort)
    tokenizer = AutoTokenizer.from_pretrained(str(master_dir))
    formatted = [(group, question, keys, format_chat(tokenizer, question))
                 for group, question, keys in CASES]
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    raw = {}
    for label, lora in (("base", None), ("adapter", Path(adapter))):
        proc = None
        try:
            proc, native = P._start(Path(server), Path(model), lora,
                                    output / ("RUN631_%s_SERVER_RAW.log" % label.upper()))
            for group, question, keys, prompt in formatted:
                item = raw.setdefault(question, {})
                item[label + "_tokens"] = token_parity(tokenizer, native, prompt)
                if label == "base":
                    item["base"] = sample(native, prompt)
                else:
                    item["scale0"] = sample(native, prompt, 0)
                    item["scale1"] = sample(native, prompt, 1)
        finally:
            if proc is not None:
                P._stop(proc)
    rows = []
    for group, question, keys, prompt in formatted:
        item = raw[question]
        a, b, c = item["base"], item["scale0"], item["scale1"]
        parity = P._compare(a, b)
        effect = P._compare(b, c)
        parity["same_generated_text"] = a["text"] == b["text"]
        rows.append({
            "group": group, "question": question, "keys": list(keys),
            "prompt_sha256": __import__("hashlib").sha256(prompt.encode()).hexdigest(),
            "hf_native_token_count": item["base_tokens"]["tokens"],
            "tokenizer_parity": item["base_tokens"]["match"] and item["adapter_tokens"]["match"],
            "base_text": a["text"], "scale0_text": b["text"], "scale1_text": c["text"],
            "base_key_hit": hit(a["text"], keys), "scale1_key_hit": hit(c["text"], keys),
            "base_first_token": a["token_id"], "scale0_first_token": b["token_id"],
            "scale1_first_token": c["token_id"],
            "base_tokens_generated": a["generated_token_count"],
            "scale1_tokens_generated": c["generated_token_count"],
            "base_seconds": a["seconds"], "scale1_seconds": c["seconds"],
            "base_vs_scale0": parity, "scale0_vs_scale1": effect,
        })
    parity_ok = all(r["tokenizer_parity"] and r["base_vs_scale0"]["same_first_token"]
                    and r["base_vs_scale0"]["same_generated_text"]
                    and r["base_vs_scale0"]["shared_topk"] >= 1
                    and r["base_vs_scale0"]["max_abs_logprob_delta"] <= 1e-4 for r in rows)
    metrics = aggregate(rows)
    status = "CHAT_TOKEN_OR_SCALE0_PARITY_FAIL" if not parity_ok else (
        "BOUNDED_SYNTHETIC_TRAIN_GAIN" if metrics["bounded_synthetic_utility"]
        else "NO_ANSWER_UTILITY")
    report = {"schema": "V13_RUN631_C3_CHAT_NATIVE_V1",
              "evidence_scope": "LINUX_NATIVE_C3_REFERENCE_F16_CHAT_SHADOW",
              "status": status, "binding": binding,
              "tokenizer_scale0_parity": parity_ok,
              "chat_template_source": "pinned HF SmolLM2 tokenizer.apply_chat_template",
              "greedy_max_new_tokens": 32, "rows": rows, "metrics": metrics,
              "original_master_learned_recall": 0.0,
              "deployed_current_c3_q4": False,
              "general_semantic_utility_proven": False,
              "production_weight_authority": 0,
              "redmi_measured": False, "body_jepa_proven": False,
              "negative_gates": dict(P.GATES)}
    (output / "RUN631_NATIVE_PROOF.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": status, "tokenizer_scale0_parity": parity_ok,
                      "metrics": metrics, "rows": rows}, sort_keys=True))
    if not parity_ok:
        raise RuntimeError("tokenizer/scale0 parity failed; no utility inference")
    return report


def main():
    p = argparse.ArgumentParser()
    for key in ("master-dir", "model", "adapter", "proof", "cohort", "server", "output"):
        p.add_argument("--" + key, required=True, type=Path)
    a = p.parse_args()
    run(a.master_dir, a.model, a.adapter, a.proof, a.cohort, a.server, a.output)


if __name__ == "__main__":
    main()
