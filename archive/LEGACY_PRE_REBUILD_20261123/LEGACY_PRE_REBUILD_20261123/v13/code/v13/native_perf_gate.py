"""Read-only native performance cohort analysis; no prompts or model text accepted."""
import json
import math
from statistics import median

ROLES = frozenset(("B1_DETAIL", "B2_GIST", "C3_LANGUAGE"))
PHASES = ("load_s", "template_s", "prefill_to_first_token_s", "stream_s")

def _number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0

def summarize(records):
    """Separate physical settings and evidence levels; do not infer residency from free RAM."""
    if not isinstance(records, list) or len(records) > 256:
        raise ValueError("Expected at most 256 technical samples")
    groups = {}
    for rec in records:
        if not isinstance(rec, dict) or rec.get("role") not in ROLES:
            raise ValueError("Invalid role")
        if rec.get("device_proof") not in ("ANDROID_VERIFIED", "SYNTHETIC", "LINUX_NATIVE"):
            raise ValueError("Evidence level required")
        if type(rec.get("threads")) is not int or rec["threads"] not in (2, 4, 6):
            raise ValueError("Unsupported thread cohort")
        if type(rec.get("batch")) is not int or rec["batch"] not in (128, 256):
            raise ValueError("Unsupported batch cohort")
        if type(rec.get("cache_prompt")) is not bool or type(rec.get("warm")) is not bool:
            raise ValueError("Cache and warm/cold flags required")
        if rec.get("status") not in ("FINAL", "DEADLINE", "TIME_BUDGET", "ERROR", "CANCELLED"):
            raise ValueError("Invalid status")
        for field in ("input_tokens", "generated_tokens"):
            if type(rec.get(field)) is not int or not 0 <= rec[field] <= 16384:
                raise ValueError("Invalid token count")
        for field in PHASES + ("elapsed_s",):
            if rec.get(field) is not None and not _number(rec[field]):
                raise ValueError("Invalid timing: " + field)
        if not _number(rec.get("elapsed_s")):
            raise ValueError("Missing elapsed time")
        if rec.get("pss_bytes") is not None and (type(rec["pss_bytes"]) is not int or rec["pss_bytes"] < 0):
            raise ValueError("Invalid process PSS")
        if rec["status"] == "FINAL" and rec["generated_tokens"] == 0:
            raise ValueError("FINAL with zero generated tokens requires investigation")
        key = (rec["role"], rec["device_proof"], rec["threads"], rec["batch"], rec["cache_prompt"], rec["warm"])
        groups.setdefault(key, []).append(rec)
    output = []
    for key, rows in sorted(groups.items()):
        elapsed = sorted(r["elapsed_s"] for r in rows)
        phases = {phase: median([r[phase] for r in rows if r.get(phase) is not None])
                  if any(r.get(phase) is not None for r in rows) else None for phase in PHASES}
        pss = [r["pss_bytes"] for r in rows if r.get("pss_bytes") is not None]
        output.append(dict(zip(("role", "device_proof", "threads", "batch", "cache_prompt", "warm"), key),
                           samples=len(rows), success=sum(r["status"] == "FINAL" for r in rows),
                           p50_elapsed_s=median(elapsed), p95_elapsed_s=elapsed[math.ceil(.95 * len(elapsed)) - 1],
                           median_phases_s=phases, peak_process_pss_bytes=max(pss) if pss else None,
                           process_pss_observed=bool(pss) and len(pss) == len(rows),
                           zero_token_failures=sum(r["generated_tokens"] == 0 and r["status"] != "FINAL" for r in rows)))
    return {"cohorts": output, "android_proof": any(r["device_proof"] == "ANDROID_VERIFIED" for r in records),
            "claim": "Descriptive measurements only; process PSS is not proof of all-model residency or quality"}

def main():
    import sys
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m v13.native_perf_gate SANITIZED.json")
    with open(sys.argv[1], encoding="utf-8") as stream:
        data = json.load(stream)
    print(json.dumps(summarize(data), sort_keys=True, indent=2))

if __name__ == "__main__":
    main()
