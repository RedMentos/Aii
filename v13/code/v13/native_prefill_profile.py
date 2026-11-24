"""Native prefill estimate. Synthetic and unverified samples cannot admit a device turn."""
from dataclasses import dataclass
from math import isfinite

@dataclass(frozen=True)
class Sample:
    device: str
    model_revision: str
    threads: int
    batch: int
    concurrent: int
    prompt_tokens: int
    prefill_s: float
    first_token: bool
    evidence_origin: str = "UNVERIFIED"

def estimate(samples, *, device, model_revision, threads, batch, concurrent,
             prompt_tokens, remaining_s, reserve_s=3.0, margin=1.35):
    if (not isinstance(prompt_tokens, int) or isinstance(prompt_tokens, bool)
            or prompt_tokens <= 0 or not isfinite(remaining_s) or remaining_s <= 0):
        return {"admit": False, "reason": "INVALID_BUDGET"}
    if not all(isfinite(v) for v in (reserve_s, margin)) or reserve_s < 0 or margin < 1:
        raise ValueError("invalid policy")
    rows = [s for s in samples if
            (s.device, s.model_revision, s.threads, s.batch, s.concurrent) ==
            (device, model_revision, threads, batch, concurrent)
            and s.evidence_origin == "DEVICE_RECEIPT" and s.first_token
            and isinstance(s.prompt_tokens, int) and s.prompt_tokens > 0
            and isfinite(s.prefill_s) and s.prefill_s > 0]
    if len(rows) < 3:
        return {"admit": False, "reason": "NO_MATCHING_VERIFIED_NATIVE_PROFILE", "samples": len(rows)}
    if prompt_tokens > max(s.prompt_tokens for s in rows):
        return {"admit": False, "reason": "OUTSIDE_MEASURED_TOKEN_RANGE", "samples": len(rows)}
    prediction = max(s.prefill_s / s.prompt_tokens for s in rows) * prompt_tokens * margin
    fits = prediction + reserve_s <= remaining_s
    return {"admit": fits,
            "reason": "PROFILE_FITS" if fits else "PREFILL_EXCEEDS_DEADLINE",
            "estimated_prefill_s": round(prediction, 3), "samples": len(rows),
            "evidence": "VERIFIED_SAMPLES_HEURISTIC_NOT_DEVICE_ACCEPTANCE"}
