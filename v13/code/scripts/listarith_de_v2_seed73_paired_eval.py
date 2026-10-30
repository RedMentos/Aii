"""One-shot frozen seed73 paired German list_arith SHADOW candidate evaluation.

No model, no tool, no learning, no activation. Source and cohort pinned.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from v13.agi import listarith_de_shadow as original
from v13.agi import listarith_de_shadow_v2_candidate as candidate

CODE = Path(__file__).resolve().parents[1]
FIXTURE = CODE / "specs" / "listarith_de_v2_seed73_holdout.json"
SEED71 = CODE / "specs" / "listarith_de_shadow_seed71_stress.json"
SEED67 = CODE / "specs" / "listarith_de_shadow_seed67_fixtures.json"
PINS = {
    "fixture": "61e68b76c63e793b91e43a1c9f0dfa1bf32f72b6",
    "seed71": "406013716d90411704c1dcc2a51c56e7b96cbb64",
    "seed67": "264805f54b697f693dc0e9730f0448f447fa8141",
    "original": "d13120bcd6be6572b6e63af5f2b5a3242e7d0b98",
    "candidate": "dd0e13c75efb7db591e78ddf892e502193275252",
}
LABELS = ("total", "difference_max_min", "none")


def blob_sha(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def validate():
    files = {"fixture": FIXTURE, "seed71": SEED71, "seed67": SEED67,
             "original": Path(original.__file__), "candidate": Path(candidate.__file__)}
    for name, path in files.items():
        if blob_sha(path) != PINS[name]:
            raise ValueError("PIN_CHANGED:" + name)
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows = data["rows"]
    if (data.get("schema") != "v13.listarith.de_shadow.v2.seed73.holdout.v1"
            or data.get("seed") != 73 or len(rows) != 36
            or len({r["id"] for r in rows}) != 36
            or len({r["text"] for r in rows}) != 36):
        raise ValueError("SEED73_IDENTITY_RED")
    if any(r["split"] != "holdout" for r in rows):
        raise ValueError("SEED73_SPLIT_RED")
    for label in ("total", "difference_max_min", None):
        if sum(r["expected"] == label for r in rows) != 12:
            raise ValueError("SEED73_LABEL_RED")
    return rows


def score(rows, key):
    if len(rows) != 36:
        raise ValueError("SCORE_ROW_COUNT")
    confusion = {a: {b: 0 for b in LABELS} for a in LABELS}
    for row in rows:
        a = row["expected"] or "none"
        b = row[key] or "none"
        if a not in LABELS or b not in LABELS:
            raise ValueError("SCORE_LABEL_RED")
        confusion[a][b] += 1
    correct = sum(confusion[k][k] for k in LABELS)
    per_class = {}
    for label in LABELS:
        tp = confusion[label][label]
        predicted = sum(confusion[k][label] for k in LABELS)
        precision = tp / predicted if predicted else 0
        recall = tp / 12
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
        per_class[label] = {"tp": tp, "precision": precision, "recall": recall, "f1": f1}
    return {"correct": correct, "accuracy": correct / 36,
            "none_false_positive": 12 - confusion["none"]["none"],
            "per_class": per_class,
            "macro_f1": sum(v["f1"] for v in per_class.values()) / 3,
            "confusion": confusion}


def decision(base, cand):
    if not (isinstance(base, dict) and isinstance(cand, dict)):
        raise ValueError("DECISION_METRIC_RED")
    supported = (cand["correct"] >= 30 and cand["correct"] - base["correct"] >= 6
                 and cand["none_false_positive"] == 0
                 and cand["per_class"]["total"]["tp"] >= 9
                 and cand["per_class"]["difference_max_min"]["tp"] >= 9)
    return "V2_SHADOW_CANDIDATE_SUPPORTED" if supported else "V2_SHADOW_CANDIDATE_NOT_SUPPORTED"


def evaluate(out):
    out = Path(out)
    if out.exists():
        raise FileExistsError("FRESH_HOLDOUT_OUTPUT_REQUIRED")
    rows = validate()
    paired = []
    for row in rows:
        old = original.propose(row["text"])
        new = candidate.propose(row["text"])
        for got in (old, new):
            if (not isinstance(got, dict) or got.get("authority") != "SHADOW_ONLY"
                    or got.get("proposal") not in ("total", "difference_max_min", None)
                    or not isinstance(got.get("reason"), str)):
                raise ValueError("AUTHORITY_OR_SCHEMA_RED")
        paired.append({"id": row["id"], "text": row["text"], "expected": row["expected"],
                       "original": old["proposal"], "original_reason": old["reason"],
                       "candidate": new["proposal"], "candidate_reason": new["reason"],
                       "authority": "SHADOW_ONLY"})
    base = score(paired, "original")
    cand = score(paired, "candidate")
    report = {"schema": "v13.listarith.de.v2.seed73.paired.v1",
              "seed": 73, "pins": PINS, "rows": paired,
              "fixture_sha256": hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
              "original": base, "candidate": cand, "decision": decision(base, cand),
              "holdout_blinding": "FIXED_BEFORE_SOURCE_BUT_AUTHOR_VISIBLE",
              "evidence_level": "SYNTHETIC_SOFTWARE_ONLY",
              "live_consumers": 0, "native_model_inference": False,
              "redmi_measured": False, "learning_mode": "RECORD_ONLY",
              "step2_gate_promoted": False, "b3_promoted": False,
              "body_jepa_available": False, "jepa_weight": 0,
              "whole_system_complete": False}
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    return report


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    r = evaluate(a.out)
    print(json.dumps({"decision": r["decision"], "original": r["original"]["correct"],
                      "candidate": r["candidate"]["correct"],
                      "candidate_none_false_positive": r["candidate"]["none_false_positive"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
