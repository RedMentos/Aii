"""One-shot disjoint seed71 German list_arith SHADOW generalization audit.

Never retunes seed67, executes a tool, performs model inference or promotes gates.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path

from v13.agi import listarith_de_shadow

SCHEMA = "v13.listarith.de_shadow.seed71.stress.result.v1"
FIXTURE_BLOB = "406013716d90411704c1dcc2a51c56e7b96cbb64"
DETECTOR_BLOB = "d13120bcd6be6572b6e63af5f2b5a3242e7d0b98"
ORIGINAL_SEED67_BLOB = "264805f54b697f693dc0e9730f0448f447fa8141"
LABELS = ("total", "difference_max_min", "none")
CODE = Path(__file__).resolve().parents[1]
FIXTURE = CODE / "specs" / "listarith_de_shadow_seed71_stress.json"
ORIGINAL_SEED67 = CODE / "specs" / "listarith_de_shadow_seed67_fixtures.json"


def blob_sha(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def fixture_rows():
    if blob_sha(FIXTURE) != FIXTURE_BLOB:
        raise ValueError("SEED71_FIXTURE_CHANGED")
    if blob_sha(Path(listarith_de_shadow.__file__)) != DETECTOR_BLOB:
        raise ValueError("SEED67_DETECTOR_CHANGED")
    if blob_sha(ORIGINAL_SEED67) != ORIGINAL_SEED67_BLOB:
        raise ValueError("SEED67_FIXTURE_CHANGED")
    obj = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if obj.get("schema") != "v13.listarith.de_shadow.seed71.stress.v1" or obj.get("seed") != 71:
        raise ValueError("SEED71_SCHEMA_CHANGED")
    rows = obj.get("rows")
    if not isinstance(rows, list) or len(rows) != 36:
        raise ValueError("SEED71_ROW_COUNT_CHANGED")
    if len({r["id"] for r in rows}) != 36 or len({r["text"] for r in rows}) != 36:
        raise ValueError("SEED71_IDENTITY_COLLISION")
    for label in ("total", "difference_max_min", None):
        if sum(r["expected"] == label for r in rows) != 12:
            raise ValueError("SEED71_LABEL_BALANCE_CHANGED")
    if any(r["split"] != "stress" or not isinstance(r["text"], str) or
           not r["text"].strip() or r["expected"] not in ("total", "difference_max_min", None)
           for r in rows):
        raise ValueError("SEED71_INVALID_ROW")
    return rows


def metrics(rows):
    if len(rows) != 36:
        raise ValueError("METRIC_ROW_COUNT")
    confusion = {k: {v: 0 for v in LABELS} for k in LABELS}
    correct = 0
    for row in rows:
        expected = row["expected"] or "none"
        predicted = row["proposal"] or "none"
        if expected not in LABELS or predicted not in LABELS:
            raise ValueError("METRIC_LABEL_INVALID")
        confusion[expected][predicted] += 1
        correct += int(expected == predicted)
    per_class = {}
    for label in LABELS:
        tp = confusion[label][label]
        predicted_n = sum(confusion[k][label] for k in LABELS)
        actual_n = sum(confusion[label].values())
        precision = tp / predicted_n if predicted_n else 0.0
        recall = tp / actual_n if actual_n else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"tp": tp, "predicted": predicted_n, "actual": actual_n,
                            "precision": precision, "recall": recall, "f1": f1}
    none_fp = sum(confusion["none"][k] for k in ("total", "difference_max_min"))
    negation_fp = sum(row["expected"] is None and row["tag"] == "negation" and
                      row["proposal"] is not None for row in rows)
    passed = (correct >= 30 and none_fp == 0 and
              per_class["total"]["tp"] >= 8 and
              per_class["difference_max_min"]["tp"] >= 8)
    return {"correct": correct, "total": 36, "accuracy": correct / 36,
            "confusion": confusion, "per_class": per_class,
            "macro_f1": sum(x["f1"] for x in per_class.values()) / 3,
            "none_false_positive": none_fp, "negation_false_positive": negation_fp,
            "status": "SHADOW_GENERALIZATION_PASS" if passed else "SHADOW_GENERALIZATION_RED"}


def evaluate(out):
    out = Path(out)
    if out.exists():
        raise FileExistsError("FRESH_OUTPUT_REQUIRED")
    rows = fixture_rows()
    predictions = []
    for row in rows:
        got = listarith_de_shadow.propose(row["text"])
        if (not isinstance(got, dict) or got.get("authority") != "SHADOW_ONLY" or
                got.get("proposal") not in ("total", "difference_max_min", None) or
                not isinstance(got.get("reason"), str)):
            raise ValueError("DETECTOR_AUTHORITY_OR_SCHEMA_CHANGED")
        predictions.append({"id": row["id"], "tag": row["tag"], "split": row["split"],
                            "text": row["text"], "expected": row["expected"],
                            "proposal": got["proposal"], "reason": got["reason"],
                            "authority": got["authority"]})
    report = {"schema": SCHEMA, "seed": 71,
              "fixture_blob": FIXTURE_BLOB, "detector_blob": DETECTOR_BLOB,
              "seed67_fixture_blob": ORIGINAL_SEED67_BLOB,
              "fixture_sha256": hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
              "metric": metrics(predictions), "rows": predictions,
              "evidence_level": "SYNTHETIC_SOFTWARE_ONLY", "live_consumers": 0,
              "native_model_inference": False, "redmi_measured": False,
              "learning_mode": "RECORD_ONLY", "step2_gate_promoted": False,
              "b3_promoted": False, "body_jepa_available": False,
              "jepa_weight": 0, "whole_system_complete": False}
    out.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                   encoding="utf-8")
    return report


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    report = evaluate(args.out)
    print(json.dumps({"status": report["metric"]["status"],
                      "correct": report["metric"]["correct"],
                      "none_false_positive": report["metric"]["none_false_positive"],
                      "macro_f1": report["metric"]["macro_f1"],
                      "authority": "SHADOW_ONLY"}, sort_keys=True))


if __name__ == "__main__":
    main()
