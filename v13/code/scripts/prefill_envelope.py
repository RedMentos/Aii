"""Source-safe native prefill admission analysis for V13 (#1904).

Reads *technical metadata only*. Does not access chat text or issue Android commands.
This is a benchmark/diagnostic consumer, not an inference speedup or native proof.
Run: python -m unittest v13/code/tests/test_prefill_envelope.py
     python v13/code/scripts/prefill_envelope.py measurements.json
Input: list of {role, prompt_tokens, prefill_ms, deadline_ms, status}.
"""
import json
import math
import sys
from collections import defaultdict

def estimate(records, role, tokens, deadline_ms, reserve_ms=2500, safety=1.25):
    """Conservative observed upper-bound prefill. Never extrapolate success from tiny prompts."""
    if tokens <= 0 or deadline_ms <= 0 or reserve_ms < 0 or safety < 1:
        raise ValueError("invalid admission parameters")
    usable = [r for r in records if r.get("role") == role
              and r.get("status") == "OK"
              and isinstance(r.get("prompt_tokens"), int)
              and r["prompt_tokens"] >= tokens
              and isinstance(r.get("prefill_ms"), (int, float))
              and math.isfinite(r["prefill_ms"]) and r["prefill_ms"] >= 0]
    if not usable:
        return {"admit": False, "reason": "NO_MATCHING_SUCCESS_AT_OR_ABOVE_TOKEN_SIZE",
                "evidence": "INSUFFICIENT", "role": role, "tokens": tokens}
    observed = max(r["prefill_ms"] for r in usable)
    projected = math.ceil(observed * safety)
    admit = projected + reserve_ms <= deadline_ms
    return {"admit": admit, "reason": "WITHIN_OBSERVED_BUDGET" if admit else "PREFILL_BUDGET_EXCEEDED",
            "evidence": "OBSERVED_PROFILE_NOT_ANDROID_PROOF", "role": role,
            "tokens": tokens, "worst_observed_ms": observed,
            "guarded_prefill_ms": projected, "output_reserve_ms": reserve_ms}

def report(records, requests):
    return [estimate(records, **request) for request in requests]

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: prefill_envelope.py measurements.json")
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("measurements"), list):
        raise SystemExit("expected object with measurements array")
    requests = data.get("requests", [])
    if not isinstance(requests, list):
        raise SystemExit("requests must be an array")
    print(json.dumps(report(data["measurements"], requests), indent=2))

if __name__ == "__main__":
    main()
