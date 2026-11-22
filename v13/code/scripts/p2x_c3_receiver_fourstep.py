#!/usr/bin/env python3
"""Default-off P2X C3 16-example, 4-step QAD FP32 LoRA feasibility; no activation."""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import time

import p2x_c3_lora_pilot as P

SCHEMA = "v13.p2x.c3_receiver_fourstep.v1"
SEED = 2026102924
PER_LABEL = 4
STEPS = 4
CFG = dict(P.CFG, seed=SEED, max_steps=STEPS, min_steps=STEPS, ckpt_every=1)
assert CFG["jepa_weight"] == 0 and CFG["anchor_weight"] == 0


def select_balanced(records):
    train = records["train.jsonl"]
    val_ids = {r["id"] for r in records["validation_inputs.jsonl"]}
    used = set()
    selected = []
    for label in P.LABELS:
        candidates = sorted(
            (r for r in train if r.get("target_action") == label),
            key=lambda r: (r["id"], r["arm"]))
        for row in candidates:
            if row["id"] in used:
                continue
            if row["id"] in val_ids or row["target_action"] != label:
                raise ValueError("P2X fourstep heldout/label identity RED")
            if (row["arm"] != "both_exact") != (label == "UNKNOWN"):
                raise ValueError("P2X fourstep source-arm target RED")
            if len(row["messages"]) != 1 or row["messages"][0].get("role") != "user":
                raise ValueError("P2X fourstep source message RED")
            if any(x in row["messages"][0]["content"] for x in
                   ("target_action", "oracle_action", "max_first", "max_second")):
                raise ValueError("P2X fourstep target leak RED")
            selected.append(row)
            used.add(row["id"])
            if sum(r["target_action"] == label for r in selected) == PER_LABEL:
                break
        if sum(r["target_action"] == label for r in selected) != PER_LABEL:
            raise ValueError("P2X fourstep insufficient disjoint label records")
    if (len(selected) != 16 or len(used) != 16 or
            any(sum(r["target_action"] == label for r in selected) != 4
                for label in P.LABELS)):
        raise ValueError("P2X fourstep selection balance RED")
    return selected


def run(cohort, master, work, budget_seconds):
    from v13.lora_trainer import LoraTrainer
    records = P.read_frozen(cohort)
    selected = select_balanced(records)
    master_sha = P.source_admission(master)
    resources = P.resource_admission(work)
    lengths = P.token_admission(master, selected)
    if len(lengths) != 16 or any(not 0 < n <= CFG["max_tokens"] for n in lengths):
        raise ValueError("P2X fourstep token admission RED")
    items = [
        {"memory_id": row["id"] + ":" + row["arm"],
         "prompt": row["messages"][0]["content"],
         "target": row["target_action"],
         "kind": "p2x_fourstep",
         "answer_keys": [row["target_action"]]}
        for row in selected
    ]
    trainer = LoraTrainer(master_dir=master, work_dir=work,
                          master_sha256=master_sha, anchors=(), probes=(),
                          cfg=CFG, evaluator=None)
    start = time.monotonic()
    result = trainer.fit(items, base_generation=0,
                         deadline=start + float(budget_seconds))
    metrics = result.get("metrics", {})
    history = metrics.get("loss_history", [])
    if (not result.get("artifact") or metrics.get("steps") != STEPS
            or len(history) != STEPS
            or [row.get("step") for row in history] != list(range(1, STEPS + 1))
            or any(not isinstance(row.get("ce"), (int, float))
                   or not math.isfinite(row["ce"]) for row in history)
            or metrics.get("jepa_weight") != 0.0
            or metrics.get("rank") != CFG["rank"]
            or metrics.get("targets") != list(CFG["targets"])
            or type(metrics.get("trainable_parameter_count")) is not int
            or metrics["trainable_parameter_count"] <= 0
            or not isinstance(metrics.get("final_ce"), (int, float))
            or not math.isfinite(metrics["final_ce"])):
        raise ValueError("P2X fourstep native training/metrics RED")
    adapter = Path(result["artifact"])
    if not adapter.is_file() or P.file_sha(adapter) != result.get("hash"):
        raise ValueError("P2X fourstep GGUF adapter hash RED")
    if result.get("files", {}).get("gguf_tensors") != 44:
        raise ValueError("P2X fourstep expected adapter tensor coverage RED")
    if P.source_admission(master) != master_sha:
        raise ValueError("P2X fourstep frozen master drift RED")
    return {
        "schema": SCHEMA, "status": "SIXTEEN_EXAMPLE_FOUR_STEP_LORA_PILOT_ONLY",
        "seed": SEED, "steps": STEPS, "examples": len(selected),
        "source_master_sha256": master_sha,
        "fixture_sha256": P.FIXTURE_SHA,
        "train_jsonl_sha256": P.EXPORT_SHA["train.jsonl"],
        "selected": [{"id": row["id"], "arm": row["arm"],
                      "target_action": row["target_action"],
                      "record_sha256": P.sha(P.canonical(row))}
                     for row in selected],
        "token_lengths": lengths, "resources": resources,
        "metrics": metrics, "adapter_gguf_sha256": result["hash"],
        "adapter_gguf_path": str(adapter), "files": result.get("files"),
        "elapsed_s": round(time.monotonic() - start, 3),
        "training_pilot": True, "ag6_approved": False,
        "production_activation": False, "p0x_used_for_training": False,
        "step2_utility_pass": False, "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cohort", required=True)
    p.add_argument("--master", required=True)
    p.add_argument("--work", required=True)
    p.add_argument("--budget-seconds", type=int, default=900)
    p.add_argument("--output", required=True)
    args = p.parse_args(argv)
    try:
        result = run(args.cohort, args.master, args.work, args.budget_seconds)
        rc = 0
    except Exception as exc:
        result = {"schema": SCHEMA, "status": "FOURSTEP_RED_PRESERVED",
                  "error": type(exc).__name__ + ": " + str(exc),
                  "ag6_approved": False, "production_activation": False,
                  "step2_utility_pass": False, "jepa_weight": 0,
                  "whole_system_complete": False}
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
