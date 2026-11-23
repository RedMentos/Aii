#!/usr/bin/env python3
"""Pinned P2X QAD tokenizer-only native token-admission discrepancy probe."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from p2x_c3_lora_pilot import read_frozen, select_pilot, token_admission, CFG, sha, canonical

SCHEMA = "v13.p2x.token_admission_native.v1"
OLD_REPORTED = (4, 4, 4, 4, 5, 5, 6, 6)


def compare_lengths(tok, selected, corrected, encode, expected_old=OLD_REPORTED):
    if len(selected) != 8 or len(corrected) != 8 or len(expected_old) != 8:
        raise ValueError("P2X tokenizer-only selected/length count RED")
    rows = []
    for index, (row, admitted) in enumerate(zip(selected, corrected)):
        messages = row["messages"]
        prompt_text = messages[0]["content"]
        target_text = str(row["target_action"]) + "<|im_end|>"
        # This is the exact old expression, retained only to diagnose the old run.
        old_obj = tok.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True)
        old_container_len = len(old_obj)
        target = tok(target_text, add_special_tokens=False)["input_ids"]
        prompt_ids, _ = encode(tok, prompt_text)
        actual_ids, actual_labels = encode(tok, prompt_text, row["target_action"])
        if (type(prompt_ids) is not list or type(target) is not list
                or not prompt_ids or not target
                or type(actual_ids) is not list or type(actual_labels) is not list):
            raise ValueError("P2X tokenizer-only malformed trainer IDs RED")
        actual_full = len(prompt_ids) + len(target)
        if (type(admitted) is not int or admitted != actual_full
                or len(actual_ids) != actual_full
                or len(actual_labels) != actual_full
                or actual_full > CFG["max_tokens"]):
            raise ValueError("P2X corrected admission/trainer token length mismatch RED")
        old_total = old_container_len + len(target)
        if old_total != expected_old[index]:
            raise ValueError("P2X original old token length not reproduced RED")
        rows.append({
            "id_sha256": sha(row["id"].encode("utf-8")),
            "arm": row["arm"], "target_action": row["target_action"],
            "prompt_characters": len(prompt_text),
            "old_result_type": type(old_obj).__name__,
            "old_is_mapping": hasattr(old_obj, "keys"),
            "old_container_len": old_container_len,
            "old_reported_total": old_total,
            "target_tokens": len(target),
            "corrected_total": admitted,
            "trainer_full_total": actual_full,
            "truncation": False,
        })
    return rows


def probe(cohort, master):
    from transformers import AutoTokenizer
    from v13.lora_trainer import LoraTrainer
    records = read_frozen(cohort)
    selected = select_pilot(records)
    corrected = token_admission(master, selected)
    tok = AutoTokenizer.from_pretrained(str(master), local_files_only=True)
    trainer = LoraTrainer(master_dir=master, work_dir=master, cfg=CFG)
    rows = compare_lengths(tok, selected, corrected, trainer._encode)
    return {
        "schema": SCHEMA, "status": "PINNED_TOKENIZER_ONLY_DIAGNOSTIC_NO_GATE",
        "selected": 8, "rows": rows, "original_old_totals": list(OLD_REPORTED),
        "corrected_totals": corrected,
        "fixture_sha256": "cd3edfdb464c6f99650b1ea32b5b09854268f0b53faa79df22ddcd135f21985a",
        "train_sha256": "af191c087d872a42924f2d2d465a3f26f6c323bf48c5c0682b30094b9d666cf1",
        "native_model_calls": 0, "training_steps": 0,
        "age0": "RECORD_ONLY", "step2_status": "UTILITY_FAIL",
        "b3_status": "FAIL", "body_jepa_status": "UNAVAILABLE",
        "lp3_status": "FAIL", "jepa_weight": 0,
        "ag6_approved": False, "production_activation": False,
        "redmi_measured": False, "whole_system_complete": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", required=True)
    parser.add_argument("--master", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        result = probe(args.cohort, args.master)
        rc = 0
    except Exception as exc:
        result = {
            "schema": SCHEMA, "status": "TOKENIZER_ONLY_RED_PRESERVED",
            "error": type(exc).__name__ + ": " + str(exc),
            "native_model_calls": 0, "training_steps": 0,
            "step2_status": "UTILITY_FAIL", "jepa_weight": 0,
            "production_activation": False, "whole_system_complete": False,
        }
        rc = 2
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as f:
        f.write(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
