#!/usr/bin/env python3
"""Conservative V13 Redmi acceptance gate. Metadata only; no transcript collection."""
import argparse
import json
import math
import statistics
import sys

REQUIRED = ("turn_id", "release_sha", "device_receipt", "status", "correct",
            "total_ms", "ttft_ms", "b1_attempted", "b1_delivered",
            "b1_consumed", "b2_attempted", "b2_delivered", "b2_consumed",
            "c4_consumed", "c3_tokens", "native_prefill_ms", "pss_kib")
CATEGORIES = {"greeting", "arithmetic", "ambiguity", "memory", "source",
              "deep", "followup", "correction"}

def percentile(values, p):
    ordered = sorted(values)
    index = (len(ordered) - 1) * p
    lo = int(index)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (index - lo)

def evaluate(rows, expected_sha):
    problems = []
    if len(rows) < 20:
        problems.append("INSUFFICIENT_LIVE_TURNS")
    if not isinstance(expected_sha, str) or len(expected_sha) != 40 or any(c not in "0123456789abcdef" for c in expected_sha):
        problems.append("INVALID_EXPECTED_RELEASE_SHA")
    ids = set()
    categories = set()
    totals, ttfts = [], []
    offers = {"b1": [0, 0, 0], "b2": [0, 0, 0]}
    for n, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            problems.append("TURN_%d_NOT_OBJECT" % n)
            continue
        missing = set(REQUIRED) - row.keys()
        if missing:
            problems.append("TURN_%d_MISSING_FIELDS:%s" % (n, ",".join(sorted(missing))))
            continue
        if not isinstance(row["turn_id"], str) or not row["turn_id"]:
            problems.append("INVALID_TURN_ID")
        if row["turn_id"] in ids:
            problems.append("DUPLICATE_TURN_ID")
        ids.add(row["turn_id"])
        categories.add(row.get("category"))
        if not isinstance(row["release_sha"], str) or row["release_sha"] != expected_sha:
            problems.append("RELEASE_SHA_MISMATCH")
        # A string or boolean is not an authenticated owner/device receipt.
        receipt = row["device_receipt"]
        if not isinstance(receipt, dict) or receipt.get("verified") is not True or not receipt.get("issue_url"):
            problems.append("NO_VERIFIED_DEVICE_RECEIPT")
        if row["status"] != "FINAL" or row["correct"] is not True:
            problems.append("TURN_%d_NOT_CORRECT_FINAL" % n)
        for field in ("total_ms", "ttft_ms", "native_prefill_ms", "pss_kib"):
            value = row[field]
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
                problems.append("TURN_%d_INVALID_%s" % (n, field))
        if isinstance(row["total_ms"], (int, float)) and isinstance(row["ttft_ms"], (int, float)):
            if all(type(row[k]) in (int, float) and math.isfinite(row[k]) for k in ("ttft_ms", "total_ms")) and 0 <= row["ttft_ms"] <= row["total_ms"]:
                totals.append(row["total_ms"])
                ttfts.append(row["ttft_ms"])
            else:
                problems.append("INVALID_LATENCY_ORDER")
        for organ in ("b1", "b2"):
            values = [row[organ + "_" + suffix] for suffix in ("attempted", "delivered", "consumed")]
            if any(type(v) is not int or v < 0 for v in values) or not values[0] >= values[1] >= values[2]:
                problems.append("INVALID_%s_OFFER_CHAIN" % organ.upper())
            else:
                offers[organ] = [a + b for a, b in zip(offers[organ], values)]
        if type(row["c4_consumed"]) is not int or row["c4_consumed"] < 0:
            problems.append("INVALID_C4_CONSUMPTION")
        elif type(row["b1_consumed"]) is int and type(row["b2_consumed"]) is int and (row["c4_consumed"] > row["b1_consumed"] + row["b2_consumed"] or row["c4_consumed"] < 0):
            problems.append("C4_UNBACKED_CONSUMPTION")
        if row.get("category") in ("deep", "source") and (type(row["b1_consumed"]) is not int or type(row["b2_consumed"]) is not int or row["b1_consumed"] <= 0 or row["b2_consumed"] <= 0 or type(row["c4_consumed"]) is not int or row["c4_consumed"] <= 0):
            problems.append("TURN_%d_MISSING_DEEP_ORGAN_COOPERATION" % n)
        if type(row["c3_tokens"]) is not int or row["c3_tokens"] <= 0:
            problems.append("NO_C3_OUTPUT")
    if not any(type(r.get("c4_consumed")) is int and r["c4_consumed"] > 0 for r in rows):
        problems.append("C4_NEVER_CONSUMED")
    if not CATEGORIES.issubset(categories):
        problems.append("MISSING_CATEGORIES:" + ",".join(sorted(CATEGORIES - categories)))
    if not all(offers[o][2] > 0 for o in offers):
        problems.append("B1_B2_NOT_BOTH_CONSUMED")
    return {"gate": "PASS" if not problems else "BLOCKED",
            "turns": len(rows), "problems": sorted(set(problems)),
            "offers": dict(zip(("b1", "b2"), offers.values())),
            "total_ms_p50": percentile(totals, .5) if totals else None,
            "total_ms_p95": percentile(totals, .95) if totals else None,
            "ttft_ms_p50": percentile(ttfts, .5) if ttfts else None,
            "ttft_ms_p95": percentile(ttfts, .95) if ttfts else None,
            "evidence": "SYNTHETIC_SCHEMA_ONLY_NOT_DEVICE_VERIFIED",
            "release_ready": False}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("jsonl", help="Private, metadata-only JSONL; do not commit")
    p.add_argument("--release-sha", required=True)
    args = p.parse_args()
    with open(args.jsonl, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    result = evaluate(rows, args.release_sha)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["gate"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
