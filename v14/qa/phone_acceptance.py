"""Read-only, sanitized V14 Redmi receipt gate. No device commands or raw transcripts."""
import json, math, sys

CATEGORIES = {"greeting", "arithmetic", "reasoning", "ambiguity", "memory", "source", "deep"}
FIELDS = ("status", "correct", "total_ms", "ttft_ms", "source_bound", "b1_delivered", "b2_delivered", "c4_consumed")

def percentile(values, fraction):
    values = sorted(values)
    if not values:
        return None
    x = (len(values) - 1) * fraction
    a = int(x)
    return round(values[a] + (values[min(a + 1, len(values) - 1)] - values[a]) * (x - a), 3)

def evaluate(receipt):
    turns = receipt.get("turns", [])
    errors = []
    if len(turns) < 20:
        errors.append("INSUFFICIENT_TURNS")
    if not CATEGORIES.issubset({t.get("category") for t in turns}):
        errors.append("MISSING_CATEGORIES")
    if len(str(receipt.get("installed_sha") or "")) < 7:
        errors.append("UNVERIFIED_INSTALLED_SHA")
    for i, turn in enumerate(turns):
        for field in FIELDS:
            if field not in turn:
                errors.append(f"TURN_{i}_MISSING_{field.upper()}")
        if turn.get("status") != "FINAL" or turn.get("correct") is not True:
            errors.append(f"TURN_{i}_NOT_CORRECT_FINAL")
        if turn.get("category") in ("source", "deep") and not all(turn.get(k) is True for k in ("source_bound", "b1_delivered", "b2_delivered", "c4_consumed")):
            errors.append(f"TURN_{i}_NO_CROSS_ORGAN_PROOF")
        for field in ("total_ms", "ttft_ms"):
            v = turn.get(field)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
                errors.append(f"TURN_{i}_INVALID_{field.upper()}")
        if isinstance(turn.get("total_ms"), (int, float)) and isinstance(turn.get("ttft_ms"), (int, float)) and turn["ttft_ms"] > turn["total_ms"]:
            errors.append(f"TURN_{i}_TTFT_AFTER_TOTAL")
    def valid(field):
        return [t[field] for t in turns if isinstance(t.get(field), (int, float)) and not isinstance(t.get(field), bool) and math.isfinite(t[field]) and t[field] >= 0]
    return {"gate": "BLOCKED" if errors else "PASS", "proof": "RECEIPT_REVIEW_ONLY_NOT_DEVICE_ATTESTATION", "turn_count": len(turns), "total_p50_ms": percentile(valid("total_ms"), .5), "total_p95_ms": percentile(valid("total_ms"), .95), "ttft_p50_ms": percentile(valid("ttft_ms"), .5), "ttft_p95_ms": percentile(valid("ttft_ms"), .95), "failures": errors}

if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as handle:
        result = evaluate(json.load(handle))
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["gate"] == "PASS" else 1)
