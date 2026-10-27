#!/usr/bin/env python3
"""BP1 selected C3 QAD-Q4 native paired baseline, no training or authority."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time

from scripts import run630_c3_llama_native as P
from scripts import run631_c3_chat_native as C

SCHEMA = "V13_BP1_SELECTED_C3_NATIVE_CONSUMER_BASELINE_V1"
DATASET_SHA = "7238a0220255cbccbcf1f9ccfad8dc03febfc37f7bc1d9d0aa645618f006508c"
REPORT_SHA = "ea379b52c7b95c2bb30cd6725f539f443521a64210fdf6bf6fa726c413126880"
CORPUS_SHA = "1872a3adf6e51e05e604053539d50ae05c955b221f78f1951d1f68e2a12f926c"
MODEL_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
TEMPLATE_SHA = "013eed60546434b6967e3483153d8c5c37abcb1d667f8b1f914683f2a9411531"
LICENSE_SHA = "4d28ca14dedc0b3d0fcc2b3339f0e79931faa33874f3d24f522183a8fc70068c"
SERVER_SHA = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
GATES = {"STEP2": "UTILITY_FAIL", "B3_L1": "FAIL",
         "Body_JEPA": "UNAVAILABLE", "jepa_weight": 0, "V13": "INCOMPLETE"}
PROTOCOL = {"seed": 13, "temperature": 0, "ctx_size": 4096,
            "threads": 2, "n_predict": 128, "cache_prompt": False, "lora": False}
ARMS = ("no_offer", "offer")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()


def exact(text, key):
    return isinstance(text, str) and isinstance(key, str) and bool(key) and re.search(
        r"(?<!\w)" + re.escape(key) + r"(?!\w)", text, re.I) is not None


def source_text(prompt):
    mark = "Original source (untrusted data):\n"
    if prompt.count(mark) != 1:
        raise ValueError("source boundary missing")
    text = prompt.split(mark, 1)[1]
    if "\nB2 summary (untrusted hint, not evidence):\n" in text:
        return text.split("\nB2 summary (untrusted hint, not evidence):\n", 1)[0]
    if "\nNo B2 offer supplied.\n" in text:
        return text.split("\nNo B2 offer supplied.\n", 1)[0]
    raise ValueError("arm delimiter missing")


def unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON key")
        out[key] = value
    return out


def load_dataset(path, manifest_path):
    path, manifest_path = Path(path), Path(manifest_path)
    if file_sha(path) != DATASET_SHA:
        raise ValueError("registered BP1 heldout dataset SHA256 mismatch")
    manifest = json.loads(manifest_path.read_text(), object_pairs_hook=unique_pairs)
    if (manifest.get("schema") != "V13_BP1_C3_CONSUMER_DATASET_PREFLIGHT_V1" or
            manifest.get("files_sha256", {}).get("heldout_paired.jsonl") != DATASET_SHA or
            manifest.get("source_report_sha256") != REPORT_SHA or
            manifest.get("source_corpus_sha256") != CORPUS_SHA or
            manifest.get("native_c3_training_executed") is not False or
            manifest.get("production_weight_authority") != 0 or
            manifest.get("gates") != GATES):
        raise ValueError("dataset provenance/authority mismatch")
    rows = [json.loads(line, object_pairs_hook=unique_pairs)
            for line in path.read_text().splitlines()]
    if len(rows) != 22:
        raise ValueError("incomplete frozen 11-pair heldout")
    pairs = {}
    for r in rows:
        if r.get("arm") not in ARMS or not isinstance(r.get("prompt"), str):
            raise ValueError("invalid heldout arm/prompt")
        src = source_text(r["prompt"])
        if sha(src.encode()) != r.get("source_sha256"):
            raise ValueError("source SHA mismatch")
        target = json.loads(r["target"], object_pairs_hook=unique_pairs)
        if set(target) != {"answer", "evidence_quote", "uncertainty"} or (
                target["evidence_quote"] not in src or
                not exact(target["evidence_quote"], target["answer"])):
            raise ValueError("target lacks source-exact support")
        if r["arm"] == "offer":
            q = r["prompt"].split("B2 exact-source quote candidates (not necessarily sufficient):\n", 1)
            if len(q) != 2 or any(item not in src for item in json.loads(q[1])):
                raise ValueError("B2 quote not source-exact")
        elif "B2 summary (untrusted hint" in r["prompt"]:
            raise ValueError("no_offer arm contaminated")
        pairs.setdefault(r["row_id"], []).append(r)
    if len(pairs) != 11 or any(
            len(group) != 2 or [x["arm"] for x in group] != list(ARMS) or
            len({x["target"] for x in group}) != 1 or
            len({x["source_sha256"] for x in group}) != 1 for group in pairs.values()):
        raise ValueError("paired heldout protocol mismatch")
    if {r["source_project"] for r in rows} != set(manifest["heldout_projects"]):
        raise ValueError("heldout project drift")
    return rows, manifest


def verify_native(tokenizer_dir, model_path, server_path):
    tokenizer_dir = Path(tokenizer_dir)
    if file_sha(model_path) != MODEL_SHA:
        raise ValueError("selected deployed QAD-Q4 SHA mismatch")
    if file_sha(tokenizer_dir/"chat_template.jinja") != TEMPLATE_SHA:
        raise ValueError("selected master template SHA mismatch")
    if file_sha(tokenizer_dir/"LICENSE") != LICENSE_SHA:
        raise ValueError("selected LFM license SHA mismatch")
    if file_sha(server_path) != SERVER_SHA:
        raise ValueError("pinned b10964 server SHA mismatch")
    if "LFM Open License v1.0" not in (tokenizer_dir/"LICENSE").read_text()[:500]:
        raise ValueError("selected model license missing")
    return {"model_sha256": MODEL_SHA, "template_sha256": TEMPLATE_SHA,
            "license_sha256": LICENSE_SHA, "server_sha256": SERVER_SHA,
            "deployed_fp32_master_equivalence_proven": False}


def start(server, model, logfile):
    port = P._port()
    args = [str(server), "--model", str(model), "--host", "127.0.0.1",
            "--port", str(port), "--ctx-size", str(PROTOCOL["ctx_size"]),
            "--threads", str(PROTOCOL["threads"])]
    with Path(logfile).open("wb") as log:
        proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    base = "http://127.0.0.1:%d" % port
    try:
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError("native selected C3 server exited before readiness")
            try:
                if P._json(base+"/health", timeout=2).get("status") in ("ok", "ready"):
                    return proc, base
            except Exception:
                pass
            time.sleep(.3)
        raise TimeoutError("native selected C3 server not ready")
    except BaseException:
        P._stop(proc)
        raise


def score(raw, row):
    src = source_text(row["prompt"])
    expected = json.loads(row["target"])
    try:
        parsed = json.loads(raw, object_pairs_hook=unique_pairs)
    except (TypeError, ValueError):
        return {"parsed": False, "answer_hit": False, "quote_valid": False,
                "quote_support": False, "supported_hit": False, "stale_answer": False}
    if not isinstance(parsed, dict) or set(parsed) != {"answer", "evidence_quote", "uncertainty"} or any(
            not isinstance(v, str) for v in parsed.values()):
        return {"parsed": False, "answer_hit": False, "quote_valid": False,
                "quote_support": False, "supported_hit": False, "stale_answer": False}
    answer, quote = parsed["answer"], parsed["evidence_quote"]
    hit = exact(answer, expected["answer"])
    valid = bool(quote) and quote in src
    support = valid and exact(quote, expected["answer"])
    stale = False
    if "current deadline" in row["question"].lower():
        old = re.search(r"The original deadline was ([^.]+)\.", src)
        stale = bool(old) and exact(answer, old.group(1)) and not hit
    return {"parsed": True, "answer_hit": bool(hit), "quote_valid": bool(valid),
            "quote_support": bool(support), "supported_hit": bool(hit and support),
            "stale_answer": bool(stale)}


def sample(base, prompt):
    body = {"prompt": prompt, "n_predict": PROTOCOL["n_predict"],
            "temperature": 0, "seed": PROTOCOL["seed"], "n_probs": 64,
            "cache_prompt": False, "stream": False, "return_tokens": True}
    started = time.monotonic()
    out = P._json(base+"/completion", body, timeout=180)
    text = out.get("content")
    if not isinstance(text, str):
        raise ValueError("native completion missing text")
    return {"text": text, "seconds": round(time.monotonic()-started, 4),
            "generated_tokens": len(out.get("tokens") or []),
            "stopped_eos": bool(out.get("stopped_eos")),
            "stopped_limit": bool(out.get("stopped_limit"))}


def summarize(records):
    pairs = {}
    for r in records:
        pairs.setdefault(r["row_id"], {})[r["arm"]] = r
    if len(pairs) != 11 or any(set(v) != set(ARMS) for v in pairs.values()):
        raise ValueError("incomplete 11 paired native rows")
    wins = sum(v["offer"]["score"]["supported_hit"] and not v["no_offer"]["score"]["supported_hit"]
               for v in pairs.values())
    losses = sum(v["no_offer"]["score"]["supported_hit"] and not v["offer"]["score"]["supported_hit"]
                 for v in pairs.values())
    return {"paired_supported_wins": wins, "paired_supported_losses": losses,
            "supported_hits": {arm: sum(v[arm]["score"]["supported_hit"] for v in pairs.values()) for arm in ARMS},
            "invalid_quotes": {arm: sum(not v[arm]["score"]["quote_valid"] for v in pairs.values()) for arm in ARMS},
            "stale_answers": {arm: sum(v[arm]["score"]["stale_answer"] for v in pairs.values()) for arm in ARMS},
            "token_parity_all": all(r["token_parity"] for r in records),
            "mean_prompt_tokens": {arm: round(sum(v[arm]["prompt_tokens"] for v in pairs.values())/11, 1) for arm in ARMS},
            "baseline_only_no_training": True}


def execute(dataset_path, manifest_path, tokenizer_dir, model_path, server_path, output):
    rows, manifest = load_dataset(dataset_path, manifest_path)
    binding = verify_native(tokenizer_dir, model_path, server_path)
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_dir))
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError("output must be empty")
    records = []
    proc = None
    try:
        proc, base = start(server_path, model_path, out/"SERVER_RAW.log")
        with (out/"ROWS_RAW.jsonl").open("x", encoding="utf-8") as log:
            for r in rows:
                prompt = C.format_chat(tokenizer, r["prompt"])
                hf = tokenizer(prompt, add_special_tokens=False)["input_ids"]
                if len(hf)+PROTOCOL["n_predict"] > PROTOCOL["ctx_size"]:
                    raise ValueError("prompt exceeds frozen context")
                native = P._json(base+"/tokenize", {"content": prompt, "add_special": False}, timeout=30)
                tokens = native.get("tokens")
                parity = tokens == hf
                answer = sample(base, prompt)
                record = {"row_id": r["row_id"], "arm": r["arm"], "source_sha256": r["source_sha256"],
                          "prompt_sha256": sha(prompt.encode()), "prompt_tokens": len(hf),
                          "token_parity": parity, "native_token_count": len(tokens) if isinstance(tokens, list) else None,
                          "score": score(answer["text"], r), "native": answer}
                records.append(record)
                log.write(json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False)+"\n")
                log.flush()
                os.fsync(log.fileno())
    finally:
        if proc is not None:
            P._stop(proc)
    metrics = summarize(records)
    report = {"schema": SCHEMA, "scope": "LINUX_NATIVE_SELECTED_C3_QAD_Q4_BASELINE_ONLY",
              "binding": binding, "dataset_sha256": DATASET_SHA,
              "dataset_manifest_sha256": file_sha(manifest_path),
              "protocol": PROTOCOL, "rows": records, "metrics": metrics,
              "production_weight_authority": 0, "native_c3_training_executed": False,
              "redmi_measured": False, "negative_gates": GATES,
              "status": "BASELINE_MEASURED" if metrics["token_parity_all"] else "TOKENIZER_PARITY_FAIL"}
    (out/"REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False)+"\n")
    return report


def main():
    p = argparse.ArgumentParser()
    for name in ("dataset", "manifest", "tokenizer-dir", "model", "server", "output"):
        p.add_argument("--"+name, required=True)
    a = p.parse_args()
    result = execute(a.dataset, a.manifest, a.tokenizer_dir, a.model, a.server, a.output)
    print(json.dumps({"status": result["status"], "metrics": result["metrics"]}, sort_keys=True))


if __name__ == "__main__":
    main()
