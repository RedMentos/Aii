#!/usr/bin/env python3
"""Offline acceptance gate for sanitized, consented Redmi technical receipts.

No device access. A passing consistency check is NOT independently verified
phone proof; the receipt identifiers must be independently checked by Boss.
"""
import argparse
import json
import math
from pathlib import Path

REQUIRED = ("scenario", "turn_id", "receipt_id", "installed_sha", "evidence", "status",
            "correct", "source_bound", "total_ms", "first_token_ms",
            "b1_attempted", "b1_delivered", "b1_consumed",
            "b2_attempted", "b2_delivered", "b2_consumed")
PRIVATE = {"prompt", "response", "transcript", "messages", "device_path", "secret", "raw_text", "conversation", "token", "password", "api_key"}
SCENARIOS = {"greeting", "arithmetic", "ambiguity", "memory_recall", "cross_organ"}

def contains_private_keys(value):
    if isinstance(value, dict):
        return any(str(k).lower() in PRIVATE or contains_private_keys(v) for k, v in value.items())
    if isinstance(value, list):
        return any(contains_private_keys(v) for v in value)
    return False

def percentile(values, q):
    if not values:
        return None
    v = sorted(values)
    x = (len(v) - 1) * q
    lo = int(x)
    return round(v[lo] + (v[min(lo + 1, len(v)-1)] - v[lo]) * (x-lo), 2)

def evaluate(data):
    if not isinstance(data, dict):
        return {"status": "INVALID", "errors": ["top level must be an object"]}
    if set(data) != {"turns"}:
        return {"status": "INVALID", "errors": ["unexpected top-level fields"]}
    rows = data.get("turns")
    if not isinstance(rows, list):
        return {"status": "INVALID", "errors": ["turns must be an array"]}
    errors = []
    if len(rows) < 20:
        errors.append("fewer than 20 turns")
    seen, receipts, shas, totals, firsts, scenarios = set(), set(), set(), [], [], set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"turn {i}: not an object")
            continue
        extra = row.keys() - set(REQUIRED)
        if extra:
            errors.append(f"turn {i}: unexpected fields (sanitized schema only)")
        missing = set(REQUIRED) - row.keys()
        if missing:
            errors.append(f"turn {i}: missing {sorted(missing)}")
            continue
        if contains_private_keys(row):
            errors.append(f"turn {i}: private fields present")
        if not isinstance(row["scenario"], str) or row["scenario"] not in SCENARIOS:
            errors.append(f"turn {i}: invalid scenario")
        else:
            scenarios.add(row["scenario"])
        if not isinstance(row["turn_id"], str) or not row["turn_id"] or (isinstance(row["turn_id"], str) and row["turn_id"] in seen):
            errors.append(f"turn {i}: duplicate/invalid turn id")
        if isinstance(row["turn_id"], str):
            seen.add(row["turn_id"])
        if not isinstance(row["receipt_id"], str) or not row["receipt_id"] or (isinstance(row["receipt_id"], str) and row["receipt_id"] in receipts):
            errors.append(f"turn {i}: duplicate/invalid receipt")
        if isinstance(row["receipt_id"], str):
            receipts.add(row["receipt_id"])
        sha = row["installed_sha"]
        if not isinstance(sha, str) or len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
            errors.append(f"turn {i}: invalid installed SHA")
        else:
            shas.add(sha)
        if row["evidence"] != "OWNER_CONSENTED_REDMI":
            errors.append(f"turn {i}: not phone-origin metadata")
        if row["status"] != "FINAL" or row["correct"] is not True or row["source_bound"] is not True:
            errors.append(f"turn {i}: final/correct/source-bound requirement failed")
        t, f = row["total_ms"], row["first_token_ms"]
        if not all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in (t,f)) or f > t:
            errors.append(f"turn {i}: invalid latency")
        else:
            totals.append(t)
            firsts.append(f)
        for organ in ("b1", "b2"):
            a,d,c = (row[f"{organ}_{key}"] for key in ("attempted","delivered","consumed"))
            if not all(type(v) is int and v >= 0 for v in (a,d,c)) or not a >= d >= c:
                errors.append(f"turn {i}: invalid {organ} offer accounting")
    if scenarios != SCENARIOS:
        errors.append("missing required diverse scenarios: " + ",".join(sorted(SCENARIOS - scenarios)))
    # Cross-organ evidence must be consumed on the cross-organ scenario itself.
    # Consumed greeting offers do not demonstrate a B1/B2 -> C4 -> C3 path.
    cross = [r for r in rows if isinstance(r, dict) and r.get("scenario") == "cross_organ"]
    if not any(all(type(r.get(f"{organ}_consumed")) is int and r[f"{organ}_consumed"] > 0
                   for organ in ("b1", "b2")) for r in cross):
        errors.append("no single cross_organ turn consumed both B1 and B2 offers")
    if len(shas) != 1:
        errors.append("mixed installed release SHAs")
    for organ in ("b1", "b2"):
        if not any(isinstance(r,dict) and type(r.get(f"{organ}_consumed")) is int
                   and r[f"{organ}_consumed"] > 0 for r in rows):
            errors.append(f"no consumed {organ} offers")
    return {"status": "METADATA_CONSISTENT" if not errors else "BLOCKED",
            "device_independently_verified": False,
            "turns": len(rows), "total_ms_p50": percentile(totals,.5),
            "total_ms_p95": percentile(totals,.95),
            "ttft_ms_p50": percentile(firsts,.5),
            "ttft_ms_p95": percentile(firsts,.95), "errors": errors}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sanitized_json")
    args = parser.parse_args()
    try:
        result = evaluate(json.loads(Path(args.sanitized_json).read_text()))
    except (OSError, ValueError, TypeError) as exc:
        result = {"status": "INVALID", "errors": [type(exc).__name__]}
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "METADATA_CONSISTENT" else 2

if __name__ == "__main__":
    raise SystemExit(main())
