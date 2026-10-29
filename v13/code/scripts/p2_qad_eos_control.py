#!/usr/bin/env python3
"""Preregistered one-factor ignore_eos=false native GGUF sampling control; no training."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

from p2_qad_fp32_firsttoken_probe import parse_native_first_token, PROMPTS, GGUF_SHA, sha256

REFERENCE_SHA = "1df95bff7c78635ae3f5bce13e58d30182610e8a7978ab6afaabfa327e750a23"
ENDPOINT = "http://127.0.0.1:8080/completion"


def frozen_rows(path):
    p = Path(path)
    if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest() != REFERENCE_SHA:
        raise ValueError("wrong original first-token RESULT.json SHA256")
    x = json.loads(p.read_text(encoding="utf-8"))
    if (x.get("schema") != "v13.p2.qad_fp32_gguf_first_token_native.v1"
            or x.get("status") != "FIRST_TOKEN_MEASURED_NO_PARITY_PROMOTION"
            or x.get("model_forward_calls") != 8 or x.get("training") is not False
            or x.get("gguf_sha256") != GGUF_SHA
            or x.get("full_logit_greedy_cache_adapter_or_utility_parity_proven") is not False):
        raise ValueError("original native reference metadata mismatch")
    rows = x.get("rows")
    if not isinstance(rows, list) or len(rows) != 8:
        raise ValueError("eight frozen rows required")
    for prompt, row in zip(PROMPTS, rows):
        if row.get("prompt") != prompt:
            raise ValueError("frozen prompt order mismatch")
        ids = row.get("input_ids")
        if not isinstance(ids, list) or not ids or any(type(i) is not int or i < 0 for i in ids):
            raise ValueError("invalid frozen input token IDs")
        for key in ("hf_first", "gguf_first"):
            if type(row.get(key)) is not int or row[key] < 0:
                raise ValueError("invalid frozen first-token ID")
        if not isinstance(row.get("gguf_top5"), list) or not row["gguf_top5"]:
            raise ValueError("missing frozen native top-logprobs")
    return rows


def summarize(original, control):
    if len(original) != len(PROMPTS) or len(control) != len(PROMPTS):
        raise ValueError("eight paired native rows required")
    rows = []
    for prompt, before, after in zip(PROMPTS, original, control):
        if before["prompt"] != prompt or after.get("prompt") != prompt or after.get("input_ids") != before["input_ids"]:
            raise ValueError("unregistered prompt or token ID change")
        first, top = after.get("gguf_first"), after.get("gguf_top5")
        if type(first) is not int or not isinstance(top, list) or not top:
            raise ValueError("invalid control native token IDs")
        if any(type(i) is not int or i < 0 for i in top) or first not in top:
            raise ValueError("invalid control top-logprobs")
        rows.append({
            "prompt": prompt, "input_ids": before["input_ids"],
            "hf_first_frozen": before["hf_first"],
            "gguf_generated_original_ignore_eos_true": before["gguf_first"],
            "gguf_toplogprob_first_original": before["gguf_top5"][0],
            "gguf_generated_control_ignore_eos_false": first,
            "gguf_toplogprob_first_control": top[0],
            "control_top5_ids": top,
        })
    return {
        "schema": "v13.p2.qad_gguf_eos_sampling_control.v1",
        "status": "EIGHT_NATIVE_EOS_CONTROL_DESCRIPTIVE_ONLY",
        "rows": rows, "probe_count": 8, "new_gguf_forward_calls": 8,
        "new_hf_forward_calls": 0, "training": False,
        "original_hf_vs_generated_equal": sum(r["hf_first_frozen"] == r["gguf_generated_original_ignore_eos_true"] for r in rows),
        "control_hf_vs_generated_equal": sum(r["hf_first_frozen"] == r["gguf_generated_control_ignore_eos_false"] for r in rows),
        "original_generated_vs_toplogprob_disagree": sum(r["gguf_generated_original_ignore_eos_true"] != r["gguf_toplogprob_first_original"] for r in rows),
        "control_generated_vs_toplogprob_disagree": sum(r["gguf_generated_control_ignore_eos_false"] != r["gguf_toplogprob_first_control"] for r in rows),
        "full_logit_rope_cache_adapter_or_utility_parity_proven": False,
    }


def audit(reference, gguf, endpoint):
    original = frozen_rows(reference)
    p = Path(gguf)
    if p.is_symlink() or sha256(p) != GGUF_SHA:
        raise ValueError("wrong pinned QAD GGUF SHA256")
    if endpoint != ENDPOINT:
        raise ValueError("only exact pinned loopback endpoint allowed")
    rows = []
    for row in original:
        payload = {
            "prompt": row["input_ids"], "n_predict": 1, "temperature": 0,
            "n_probs": 5, "stream": False, "cache_prompt": False,
            "repeat_penalty": 1.0, "top_k": 0, "top_p": 1.0,
            "min_p": 0.0, "ignore_eos": False,
        }
        req = Request(endpoint, data=json.dumps(payload).encode("utf-8"),
                      headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=120) as resp:
            first, top = parse_native_first_token(json.loads(resp.read(4 * 1024 * 1024)))
        rows.append({"prompt": row["prompt"], "input_ids": row["input_ids"],
                     "gguf_first": first, "gguf_top5": top})
    result = summarize(original, rows)
    result["original_result_sha256"] = REFERENCE_SHA
    result["gguf_sha256"] = GGUF_SHA
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference", required=True)
    p.add_argument("--gguf", required=True)
    p.add_argument("--endpoint", default=ENDPOINT)
    p.add_argument("--output", required=True)
    args = p.parse_args(argv)
    try:
        result = audit(args.reference, args.gguf, args.endpoint)
        rc = 0
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, ImportError, json.JSONDecodeError) as exc:
        result = {"schema": "v13.p2.qad_gguf_eos_sampling_control.v1",
                  "status": "EOS_CONTROL_RED", "error": type(exc).__name__ + ": " + str(exc),
                  "full_logit_rope_cache_adapter_or_utility_parity_proven": False}
        rc = 2
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as f:
        f.write(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
