#!/usr/bin/env python3
"""BP1 train-only QAD tokenizer context audit; no heldout labels, optimizer or model weights."""
import argparse
import hashlib
import json
from pathlib import Path

from scripts import bp1_paired_score as S

TRAIN_SHA = "9f356917911983e887f80aaadd8b58365fe43ecbf6632bb5e9e0a1aa8628ff86"
REVISION = "657e078c94084481950a2d555a941481f715536b"
QAD_MASTER_SHA = "1d90518482c4ec204bebb4820bbaee4f8a38c5a6df72256f86bcd21fe52ad079"
QAD_DEPLOYED_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
WINDOWS = (160, 1024, 2048)
FILES = ("tokenizer.json", "tokenizer_config.json", "chat_template.jinja", "config.json")
SCHEMA = "V13_BP1_C3_QAD_TRAIN_TOKEN_BUDGET_V1"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_train(path, *, pinned=True):
    rows, raw_sha = S.read_jsonl(path)
    if pinned and raw_sha != TRAIN_SHA:
        raise ValueError("BP1 train_offer source SHA mismatch")
    if len(rows) != 25:
        raise ValueError("BP1 train row count mismatch")
    ids = set()
    for row in rows:
        if not isinstance(row, dict) or not {"row_id", "arm", "prompt", "target", "answer_keys", "source_sha256"} <= set(row):
            raise ValueError("malformed train row")
        rid = row["row_id"]
        if not isinstance(rid, str) or rid in ids or row["arm"] != "offer":
            raise ValueError("duplicate ID or wrong train arm")
        ids.add(rid)
        if not isinstance(row["prompt"], str) or not isinstance(row["target"], str):
            raise ValueError("non-string train prompt/target")
        target = S.parse_json(row["target"])
        if not isinstance(target, dict) or set(target) != {"answer", "evidence_quote", "uncertainty"}:
            raise ValueError("invalid train target")
        if not isinstance(row["answer_keys"], list) or len(row["answer_keys"]) != 1 or target["answer"] != row["answer_keys"][0]:
            raise ValueError("train answer/key mismatch")
    return rows, raw_sha


def audit(rows, tokenizer, *, tokenizer_hashes=None, dependency_version="UNKNOWN"):
    results = []
    for row in rows:
        # Reproduce LoraTrainer._encode's exact history/generation prompt and answer terminator.
        rendered = tokenizer.apply_chat_template([{"role": "user", "content": row["prompt"]}],
                                                  add_generation_prompt=True, tokenize=False)
        prompt_ids = tokenizer(rendered, add_special_tokens=False)["input_ids"]
        target_ids = tokenizer(row["target"] + "<|im_end|>", add_special_tokens=False)["input_ids"]
        if not isinstance(prompt_ids, list) or not isinstance(target_ids, list) or not prompt_ids or not target_ids:
            raise ValueError("tokenizer returned invalid/empty ids")
        p, t = len(prompt_ids), len(target_ids)
        stats = {}
        for window in WINDOWS:
            lost = max(0, p + t - window)
            stats[str(window)] = {
                "prefix_lost": lost,
                "prompt_fully_preserved": lost == 0,
                "prompt_tokens_retained": min(p, max(0, window - t)),
                "target_tokens_retained": min(t, window),
                "target_fully_preserved": t <= window}
        results.append({"row_id": row["row_id"], "prompt_tokens": p,
                        "target_tokens": t, "total_tokens": p+t, "windows": stats})
    if len(results) != 25 or len({x["row_id"] for x in results}) != 25:
        raise ValueError("invalid train audit count")
    summary = {str(w): {"n": 25,
                         "truncated_rows": sum(x["windows"][str(w)]["prefix_lost"] > 0 for x in results),
                         "max_prefix_lost": max(x["windows"][str(w)]["prefix_lost"] for x in results),
                         "target_truncated_rows": sum(not x["windows"][str(w)]["target_fully_preserved"] for x in results)}
               for w in WINDOWS}
    return {"schema": SCHEMA, "evidence": "OFFICIAL_TOKENIZER_TRAIN_ONLY_NO_MODEL_EXECUTION",
            "source_revision": REVISION, "qad_master_sha256_metadata_only": QAD_MASTER_SHA,
            "qad_deployed_sha256_metadata_only": QAD_DEPLOYED_SHA,
            "tokenizer_files_sha256": tokenizer_hashes or {}, "transformers_version": dependency_version,
            "rows": results, "summary": summary,
            "max_total_tokens": max(x["total_tokens"] for x in results),
            "mean_total_tokens": round(sum(x["total_tokens"] for x in results)/25, 1),
            "window_2048_feasible": summary["2048"]["truncated_rows"] == 0,
            "heldout_targets_used": False, "native_c3_training_executed": False,
            "model_utility_proven": False, "redmi_measured": False,
            "gates": {"STEP2": "UTILITY_FAIL", "B3_L1": "FAIL",
                      "Body_JEPA": "UNAVAILABLE", "jepa_weight": 0,
                      "canonical_architecture_complete": False}}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--train", required=True)
    p.add_argument("--tokenizer-dir", required=True, help="snapshot pinned qad/ files, not model weights")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    rows, train_sha = load_train(a.train)
    directory = Path(a.tokenizer_dir) / "qad"
    hashes = {}
    for name in FILES:
        path = directory / name
        if not path.is_file():
            raise ValueError("required QAD tokenizer file missing: " + name)
        hashes[name] = sha(path)
    from transformers import AutoTokenizer, __version__ as version
    tok = AutoTokenizer.from_pretrained(str(directory), local_files_only=True, trust_remote_code=False)
    result = audit(rows, tok, tokenizer_hashes=hashes, dependency_version=version)
    result["train_sha256"] = train_sha
    with Path(a.out).open("xb") as f:
        f.write((json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        f.flush()
        import os
        os.fsync(f.fileno())
    print(json.dumps({"summary": result["summary"], "max_total_tokens": result["max_total_tokens"],
                      "mean_total_tokens": result["mean_total_tokens"],
                      "window_2048_feasible": result["window_2048_feasible"],
                      "heldout_targets_used": False}, sort_keys=True))
    if not result["window_2048_feasible"]:
        raise SystemExit("BP1_TOKEN_BUDGET_2048_FAIL")


if __name__ == "__main__":
    main()
