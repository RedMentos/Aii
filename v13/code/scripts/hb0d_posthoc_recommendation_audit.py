"""HB0d: conservative POSTHOC recommendation coverage; never a native/Canon gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "v13.hb0d.posthoc_recommendation_audit.v1"
PARENT_HEAD = "17c989f1cf2f7f5ca25d388afa47044d6f69898b"
PARENT_RAW = "dbaf4fd299138c21c5a6f2de4bd52f092abc73f1f165c4ae447c962799e7b638"
PARENT_SCORE = "8dc551c43c5223581b2eaf8116107f8e6aea8679586817aa4a22993d5056b971"
FIXTURE = "73c9f4096a928ece659cfa5aff0c483001346834f6117765ed1c53c9c2b7939b"
ACTIONS = ("A", "B", "NONE", "UNKNOWN", "AMBIGUOUS", "UNPARSEABLE")
_PREFIX = re.compile(
    r"^(?:(?:therefore|thus|in conclusion)[,:]?\s+)?"
    r"(?:i\s+(?:would\s+)?(?:choose|select|pick|recommend)|"
    r"(?:choose|select|pick|recommend)|"
    r"my\s+(?:choice|recommendation)\s+is|"
    r"(?:the\s+)?(?:best|recommended|preferred)\s+(?:option|choice)\s+is|"
    r"final\s+(?:answer|choice|recommendation)\s*[:=\-])"
    r"\s+(?:option\s+)?([AB])\b", re.I)
_BEST = re.compile(r"^(?:option\s+)?([AB])\s+is\s+(?:the\s+)?"
                   r"(?:best|recommended|preferred)\s+(?:option|choice)\b", re.I)
_NONE = re.compile(r"^(?:neither\s+option|no\s+option)\s+(?:is\s+)?"
                   r"(?:eligible|valid|feasible)\b|^both\s+options\s+are\s+ineligible\b", re.I)
_UNKNOWN = re.compile(r"^(?:unknown\b|i\s+(?:cannot|can't|am\s+unable\s+to)\s+decide\b|"
                      r"(?:not\s+enough|insufficient)\s+information\b)", re.I)
_UNSAFE = re.compile(r"\b(?:if|unless|assuming|provided|hypothetically|perhaps|maybe|"
                     r"might|could|but|however|actually|instead)\b", re.I)
_ALTERNATIVE = re.compile(r"\b(?:or|and)\s+(?:option\s+)?[AB]\b", re.I)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def need(ok, label):
    if not ok:
        raise ValueError(label)


def extract(text):
    """Explicit decision only. Offsets are in the original model text."""
    if type(text) is not str or len(text) > 50000:
        return {"action": "UNPARSEABLE", "spans": []}
    candidates = []
    cursor = 0
    for segment in re.split(r"(?<=[.!?])\s+|\n+", text):
        pos = text.find(segment, cursor)
        if pos < 0:
            continue
        cursor = pos + len(segment)
        stripped = segment.lstrip()
        offset = pos + len(segment) - len(stripped)
        if not stripped or stripped[0] in ('"', "'", ">", chr(96)) or stripped.endswith("?"):
            continue
        if _UNSAFE.search(stripped):
            continue
        match = _PREFIX.match(stripped) or _BEST.match(stripped)
        if match:
            if _ALTERNATIVE.search(stripped[match.end():]):
                continue
            candidates.append((match.group(1).upper(), [offset + match.start(1),
                                                        offset + match.end(1)]))
            continue
        match = _NONE.match(stripped)
        if match:
            candidates.append(("NONE", [offset + match.start(), offset + match.end()]))
            continue
        match = _UNKNOWN.match(stripped)
        if match:
            candidates.append(("UNKNOWN", [offset + match.start(), offset + match.end()]))
    if not candidates:
        return {"action": "UNPARSEABLE", "spans": []}
    labels = {a for a, _ in candidates}
    return {"action": next(iter(labels)) if len(labels) == 1 else "AMBIGUOUS",
            "spans": [span for _, span in candidates]}


def audit(evidence_dir, raw_sha=PARENT_RAW, score_sha=PARENT_SCORE,
          fixture_sha=FIXTURE):
    """Read-only verification of original HB0c native artifact and posthoc counts."""
    from scripts import hb0_split_information_cohort as hb0
    from scripts import hb0_c3_receiver_native_pilot as pilot

    root = Path(evidence_dir)
    need(raw_sha == PARENT_RAW and score_sha == PARENT_SCORE and fixture_sha == FIXTURE,
         "HB0D_EXTERNAL_PIN_RED")
    raw_bytes = (root / "RAW.json").read_bytes()
    score_bytes = (root / "SCORE.json").read_bytes()
    need(sha(raw_bytes) == raw_sha and sha(score_bytes) == score_sha,
         "HB0D_ORIGINAL_HASH_RED")
    raw = json.loads(raw_bytes)
    original = json.loads(score_bytes)
    receipt = json.loads((root / "RECEIPT.json").read_bytes())
    inputs_bytes = (root / "INPUTS.json").read_bytes()
    need(receipt.get("raw_sha256") == raw_sha
         and receipt.get("score_sha256") == score_sha
         and receipt.get("input_sha256") == sha(inputs_bytes)
         and receipt.get("status") == "RECORDED_LINUX_NATIVE_C3_DIAGNOSTIC_NO_GATE"
         and receipt.get("model_sha256") == pilot.MODEL_SHA
         and receipt.get("model_sha256_after") == pilot.MODEL_SHA
         and receipt.get("runner_sha256_before") == receipt.get("runner_sha256_after")
         and receipt.get("process_reaped") is True
         and receipt.get("age_authority") == 0
         and receipt.get("jepa_weight") == 0
         and receipt.get("weight_updates") is False
         and receipt.get("canonical_gate_pass") is False
         and receipt.get("redmi_measured") is False
         and receipt.get("recorded_calls") == 24,
         "HB0D_ORIGINAL_RECEIPT_RED")
    rows = hb0.fixtures()
    need(hb0._sha(rows) == fixture_sha, "HB0D_FIXTURE_DRIFT_RED")
    need(json.loads(inputs_bytes) == pilot.plan(rows, fixture_sha),
         "HB0D_INPUTS_DRIFT_RED")
    need(raw.get("status") == receipt["status"]
         and raw.get("fixture_sha256") == fixture_sha
         and raw.get("model_sha256") == pilot.MODEL_SHA,
         "HB0D_RAW_IDENTITY_RED")
    need(original == pilot.score(raw["rows"], rows, fixture_sha),
         "HB0D_ORIGINAL_SCORE_DRIFT_RED")
    answers = {r["id"]: r["oracle_action"] for r in rows if r["family"] == pilot.FAMILY}
    per_arm = {a: {k: 0 for k in ("explicit", "exact", "wrong_committed",
                                     "unknown", "ambiguous", "unparseable")}
               for a in pilot.ARM_ORDER}
    details = []
    for row in raw["rows"]:
        arm = row["arm"]
        pred = extract(row["output"])
        label = pred["action"]
        stats = per_arm[arm]
        if label in ("A", "B", "NONE"):
            stats["explicit"] += 1
            stats["exact"] += int(label == answers[row["id"]])
            stats["wrong_committed"] += int(label != answers[row["id"]])
        else:
            stats[label.lower()] += 1
        details.append({"id_sha256": sha(row["id"].encode("utf-8")), "arm": arm,
                        "extracted": label, "spans": pred["spans"],
                        "original_prefix": pilot.action(row["output"]),
                        "oracle": answers[row["id"]]})
    for stats in per_arm.values():
        need(stats["explicit"] + stats["unknown"] + stats["ambiguous"]
             + stats["unparseable"] == 6,
             "HB0D_ARM_COVERAGE_RED")
    return {"schema": SCHEMA, "status": "POSTHOC_EXPLORATORY_NO_GATE",
            "source_head_sha": PARENT_HEAD, "original_raw_sha256": raw_sha,
            "original_score_sha256": score_sha, "fixture_sha256": fixture_sha,
            "original_per_arm": original["per_arm"], "per_arm": per_arm,
            "rows": len(details), "details": details,
            "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
            "b3_status": "FAIL", "body_jepa_status": "UNAVAILABLE",
            "lp3_status": "FAIL", "jepa_weight": 0,
            "redmi_measured": False, "whole_system_complete": False,
            "claim_limit": "Posthoc parser coverage on six public synthetic C3 Linux-native rows x four arms; no gate or model utility promotion"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    need(not args.out.exists(), "HB0D_FRESH_OUTPUT_REQUIRED")
    report = audit(args.evidence_dir)
    args.out.write_bytes(canonical(report) + b"\n")
    print(json.dumps({"status": report["status"], "rows": report["rows"],
                      "per_arm": report["per_arm"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
