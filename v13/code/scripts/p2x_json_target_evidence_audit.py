#!/usr/bin/env python3
"""Read-only offline audit for schema-aligned JSON-target P2X 16x4 LoRA; NOT native attestation."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

from scripts import p2x_c3_lora_pilot as P
from scripts import p2x_c3_json_target_fourstep as F

SCHEMA = "v13.p2x.json_target_fourstep_evidence_audit.v1"
STATUS = "ARTIFACT_CONSISTENT_ONLY_NOT_NATIVE_ATTESTED"


def need(ok, message):
    if not ok:
        raise ValueError("P2X_FOURSTEP_AUDIT_" + message)


def finite(value, lower=None, upper=None):
    if type(value) not in (int, float) or not math.isfinite(value):
        return False
    return (lower is None or value >= lower) and (upper is None or value <= upper)


def confined_file(root, raw):
    need(type(raw) is str and bool(raw), "FILE_PATH_RED")
    p = Path(raw)
    need(p.is_absolute(), "ABSOLUTE_FILE_PATH_REQUIRED")
    # Refuse symlink at every component, including the evidence root itself.
    cursor = p
    while True:
        need(not cursor.is_symlink(), "SYMLINK_RED")
        if cursor == cursor.parent:
            break
        cursor = cursor.parent
    try:
        resolved = p.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError("P2X_FOURSTEP_AUDIT_MISSING_FILE_RED") from exc
    need(resolved.is_relative_to(root) and resolved.is_file(), "FILE_CONFINEMENT_RED")
    return resolved


def audit(report, cohort, evidence_root):
    need(type(report) is dict, "REPORT_SCHEMA_RED")
    root = Path(evidence_root)
    need(root.is_dir() and not root.is_symlink(), "EVIDENCE_ROOT_RED")
    root = root.resolve(strict=True)
    records = P.read_frozen(cohort)  # frozen manifest, 504/360/72 and SHA256 binding
    selected = F.select_balanced(records)
    expected = [{"id": row["id"], "arm": row["arm"],
                 "target_action": row["target_action"],
                 "record_sha256": P.sha(P.canonical(row))}
                for row in selected]
    need(report.get("schema") == F.SCHEMA
         and report.get("status") == "SIXTEEN_EXAMPLE_FOUR_STEP_JSON_TARGET_LORA_PILOT_ONLY"
         and type(report.get("seed")) is int and report["seed"] == F.SEED
         and type(report.get("steps")) is int and report["steps"] == F.STEPS
         and type(report.get("examples")) is int and report["examples"] == 16
         and report.get("source_master_sha256") == P.MASTER_SHA["model.safetensors"]
         and report.get("fixture_sha256") == P.FIXTURE_SHA
         and report.get("train_jsonl_sha256") == P.EXPORT_SHA["train.jsonl"]
         and report.get("selected") == expected,
         "FROZEN_REPORT_BINDING_RED")
    need(report.get("target_format") == "JSON_OBJECT_ACTION_V1"
         and report.get("target_texts_sha256") == P.sha(P.canonical([
             F.json_target(row["target_action"]) for row in selected])),
         "JSON_TARGET_FORMAT_BINDING_RED")
    need(report.get("training_pilot") is True
         and report.get("ag6_approved") is False
         and report.get("production_activation") is False
         and report.get("p0x_used_for_training") is False
         and report.get("step2_utility_pass") is False
         and type(report.get("jepa_weight")) is int and report["jepa_weight"] == 0
         and report.get("redmi_measured") is False
         and report.get("whole_system_complete") is False,
         "AUTHORITY_GATE_RED")
    lengths = report.get("token_lengths")
    need(type(lengths) is list and len(lengths) == 16
         and all(type(n) is int and 0 < n <= F.CFG["max_tokens"] for n in lengths),
         "TOKEN_LENGTH_RED")
    resources = report.get("resources")
    need(type(resources) is dict
         and finite(resources.get("disk_free_bytes"), 5_000_000_000)
         and finite(resources.get("memory_available_bytes"), 5_000_000_000),
         "RESOURCE_RECEIPT_RED")
    m = report.get("metrics")
    need(type(m) is dict and type(m.get("steps")) is int and m["steps"] == 4
         and type(m.get("rank")) is int and m["rank"] == F.CFG["rank"]
         and m.get("targets") == list(F.CFG["targets"])
         and finite(m.get("alpha")) and m["alpha"] == F.CFG["alpha"]
         and finite(m.get("anchor_weight")) and m["anchor_weight"] == 0
         and finite(m.get("jepa_weight")) and m["jepa_weight"] == 0
         and type(m.get("base_generation")) is int and m["base_generation"] == 0
         and type(m.get("trainable_parameter_count")) is int
         and m["trainable_parameter_count"] > 0
         and finite(m.get("master_learned_recall"), 0, 1)
         and finite(m.get("final_ce"), 0)
         and finite(m.get("seconds"), 0)
         and finite(m.get("peak_rss_mb"), 0)
         and type(m.get("resumed")) is bool
         and type(m.get("dataset_hash")) is str and bool(m["dataset_hash"])
         and m.get("trained_on") == "master"
         and type(m.get("device")) is dict
         and m["device"].get("backend") == "torch-cpu"
         and type(m["device"].get("threads")) is int
         and m["device"]["threads"] == F.CFG["threads"],
         "TRAINING_METRICS_RED")
    history = m.get("loss_history")
    need(type(history) is list and len(history) == 4
         and [h.get("step") if type(h) is dict else None for h in history] == [1, 2, 3, 4]
         and all(finite(h.get("ce"), 0) and finite(h.get("anchor_kl"), 0)
                 and h.get("jepa") is None for h in history)
         and m["final_ce"] == history[-1]["ce"],
         "LOSS_HISTORY_RED")
    files = report.get("files")
    need(type(files) is dict and type(files.get("gguf_tensors")) is int
         and files["gguf_tensors"] == 44
         and type(files.get("bytes")) is int and files["bytes"] > 0,
         "ADAPTER_MANIFEST_RED")
    gguf = confined_file(root, files.get("gguf"))
    safe = confined_file(root, files.get("safetensors"))
    need(gguf != safe
         and report.get("adapter_gguf_path") == files["gguf"]
         and report.get("adapter_gguf_sha256") == files.get("gguf_sha256")
         and files.get("gguf_sha256") == P.file_sha(gguf)
         and files.get("safetensors_sha256") == P.file_sha(safe)
         and gguf.stat().st_size == files["bytes"],
         "ADAPTER_BYTES_RED")
    need(finite(report.get("elapsed_s"), 0), "ELAPSED_RED")
    return {"schema": SCHEMA, "status": STATUS,
            "source_master_sha256": P.MASTER_SHA["model.safetensors"],
            "fixture_sha256": P.FIXTURE_SHA,
            "selected_record_sha256": [r["record_sha256"] for r in expected],
            "reported_optimizer_steps": 4,
            "reported_example_visits": 64,
            "adapter_gguf_sha256": files["gguf_sha256"],
            "adapter_safetensors_sha256": files["safetensors_sha256"],
            "source_only_independent_audit": True,
            "native_training_independently_observed": False,
            "native_utility_proven": False,
            "ag6_approved": False, "production_activation": False,
            "step2_status": "UTILITY_FAIL", "b3_l1_status": "FAIL",
            "body_jepa_status": "UNAVAILABLE", "jepa_weight": 0,
            "redmi_measured": False, "whole_system_complete": False}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cohort", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--evidence-root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args(argv)
    try:
        report = json.loads(Path(args.report).read_text(encoding="utf-8"))
        result = audit(report, args.cohort, args.evidence_root)
        rc = 0
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        result = {"schema": SCHEMA, "status": "EVIDENCE_AUDIT_RED_PRESERVED",
                  "error": type(exc).__name__ + ": " + str(exc),
                  "native_training_independently_observed": False,
                  "ag6_approved": False, "production_activation": False,
                  "step2_status": "UTILITY_FAIL", "jepa_weight": 0,
                  "whole_system_complete": False}
        rc = 2
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True,
                                ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
