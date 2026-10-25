#!/usr/bin/env python3
"""Run321 independent source-only audit of Run320 native epoch JSON.

Does NOT rerun/verify GGUF bytes, native optimization, or Redmi evidence.
"""
import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_lfm2_epoch_eval_run320 import (  # noqa: E402
    SCHEMA, HF_REPO, HF_REVISION, GATES, FACTS, PARAPHRASES,
    NEAR_MISS, PROBES, select, verify_sources,
)
from native_lfm2_finetune_bench import INVALID, hit, first_sentence

HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class AuditError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise AuditError(message)


def sha(value, label):
    require(isinstance(value, str) and HEX64.fullmatch(value) is not None,
            "invalid or missing SHA256: " + label)


def check_evaluation(ev, label):
    """Recompute every published score from exact, ordered raw answer text."""
    require(isinstance(ev, dict), label + ": evaluation must be an object")
    cohorts = (
        ("facts", [x[0] for x in FACTS], [x[2] for x in FACTS], "ok"),
        ("paraphrases", [x[0] for x in PARAPHRASES], [x[1] for x in PARAPHRASES], "ok"),
        ("near_miss", [x[0] for x in NEAR_MISS], [x[1] for x in NEAR_MISS], "leak"),
        ("probes", [x["prompt"] for x in PROBES], [x["expect"] for x in PROBES], "ok"),
    )
    counts = {}
    invalid = 0
    for name, questions, keywords, field in cohorts:
        rows = ev.get(name)
        require(isinstance(rows, list) and len(rows) == len(questions),
                label + ": " + name + " denominator mismatch")
        require([r.get("q") if isinstance(r, dict) else None for r in rows] == questions,
                label + ": " + name + " exact question/order mismatch")
        for i, (row, keys) in enumerate(zip(rows, keywords)):
            ans = row.get("a")
            require(isinstance(ans, str), f"{label}: {name}[{i}] missing raw answer")
            actual = hit(ans, keys)
            strict = hit(first_sentence(ans), keys)
            require(type(row.get(field)) is bool and row[field] == actual,
                    f"{label}: {name}[{i}] forged {field}")
            require(type(row.get("strict")) is bool and row["strict"] == strict,
                    f"{label}: {name}[{i}] forged strict")
            invalid += int(ans == INVALID)
        counts[name] = rows
    expected = {
        "facts_ok": sum(x["ok"] for x in counts["facts"]),
        "facts_n": len(FACTS),
        "para_ok": sum(x["ok"] for x in counts["paraphrases"]),
        "para_n": len(PARAPHRASES),
        "near_miss_leak": round(sum(x["leak"] for x in counts["near_miss"]) / len(NEAR_MISS), 3),
        "probes_ok": sum(x["ok"] for x in counts["probes"]),
        "probes_n": len(PROBES),
        "facts_strict": sum(x["strict"] for x in counts["facts"]),
        "para_strict": sum(x["strict"] for x in counts["paraphrases"]),
        "near_miss_leak_strict": round(sum(x["strict"] for x in counts["near_miss"]) / len(NEAR_MISS), 3),
    }
    require(ev.get("summary") == expected, label + ": summary differs from raw answers")
    require(type(ev.get("invalid_outputs")) is int and ev["invalid_outputs"] == invalid,
            label + ": invalid output count differs from raw answers")
    return expected


def audit(report):
    """Return source-only PASS receipt, or raise AuditError (never edit report)."""
    verify_sources()
    require(isinstance(report, dict), "report must be an object")
    require(report.get("schema") == SCHEMA, "wrong Run320 schema")
    require(report.get("status") == "COMPLETE_NATIVE_EVALUATION", "native evaluation incomplete")
    require(report.get("evidence_level") == "LINUX_NATIVE_C3_TRAIN_AND_EVAL", "evidence level mismatch")
    require(report.get("hf_repo") == HF_REPO and report.get("hf_revision") == HF_REVISION,
            "frozen model/revision mismatch")
    require(report.get("gates") == GATES and report.get("weights_published") is False,
            "negative gates or publication flag changed")
    require(report.get("native_training_executed") is True, "no native training receipt")
    require(report.get("train", {}).get("epochs") == 2, "epoch count mismatch")
    require(report.get("final_matches_last_epoch_sha256") is True, "final/last epoch mismatch")
    for name in ("master_sha256", "source_manifest_sha256", "native_binary_sha256",
                 "quantizer_sha256", "server_sha256", "train_stream_sha256",
                 "final_master_sha256", "baseline_q4_sha256"):
        sha(report.get(name), name)
    receipts = report.get("checkpoint_receipts")
    epochs = report.get("epochs")
    require(isinstance(receipts, list) and len(receipts) == 2, "missing epoch receipts")
    require(isinstance(epochs, list) and len(epochs) == 2, "missing epoch evaluations")
    for i, (receipt, epoch) in enumerate(zip(receipts, epochs), 1):
        require(isinstance(receipt, dict) and isinstance(epoch, dict), "epoch receipt type")
        require(type(receipt.get("epoch")) is int and receipt["epoch"] == i,
                "receipt epoch/order mismatch")
        require(type(epoch.get("epoch")) is int and epoch["epoch"] == i,
                "evaluation epoch/order mismatch")
        require(type(receipt.get("bytes")) is int and receipt["bytes"] >= 1024,
                "checkpoint byte count invalid")
        sha(receipt.get("sha256"), f"receipt {i}")
        sha(epoch.get("source_sha256"), f"epoch source {i}")
        sha(epoch.get("q4_sha256"), f"epoch Q4 {i}")
        require(receipt["sha256"] == epoch["source_sha256"], "checkpoint source SHA mismatch")
    require(report["final_master_sha256"] == receipts[-1]["sha256"],
            "final master SHA differs from last epoch")
    baseline = report.get("baseline")
    check_evaluation(baseline, "baseline")
    candidates = []
    for i, epoch in enumerate(epochs, 1):
        candidate = epoch.get("evaluation")
        check_evaluation(candidate, f"epoch{i}")
        candidates.append(candidate)
    expected_selection = select(baseline, candidates)
    require(report.get("selection_report") == expected_selection,
            "published selection/retention differs from raw answers")
    require(report.get("selection") == expected_selection["selection"],
            "published selection flag mismatch")
    return {
        "schema": "V13_RUN321_INDEPENDENT_SOURCE_ONLY_AUDIT_V1",
        "status": "PASS_SOURCE_ONLY",
        "selection": expected_selection["selection"],
        "selected_epoch": expected_selection["selected_epoch"],
        "facts_strict": [x["facts_strict"] for x in (check_evaluation(e["evaluation"], "epoch") for e in epochs)],
        "limitations": "JSON consistency only: not independent native execution, GGUF byte verification or Redmi proof",
        "gates": dict(GATES),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run320_report", type=Path)
    args = parser.parse_args()
    try:
        report = json.loads(args.run320_report.read_text(encoding="utf-8"))
        result = audit(report)
    except (AuditError, ValueError, TypeError, KeyError, OSError) as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error": str(exc)[:500]}, sort_keys=True))
        raise SystemExit(2)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
