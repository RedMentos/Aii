"""Optional measured-native prefill deadline gate; never edits source text.

The profile key includes device, model revision, thread count, batch and
concurrent residency. A Linux profile cannot authorize a Redmi call.
"""
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

def estimate(samples, *, device, model_revision, threads, batch, concurrent,
             prompt_tokens, remaining_s, reserve_s=3.0, margin=1.35):
    if prompt_tokens <= 0 or not isfinite(remaining_s) or remaining_s <= 0:
        return {"admit":False,"reason":"INVALID_BUDGET"}
    if reserve_s < 0 or margin < 1: raise ValueError("invalid policy")
    rows=[s for s in samples if
          (s.device,s.model_revision,s.threads,s.batch,s.concurrent)==
          (device,model_revision,threads,batch,concurrent)
          and s.first_token and s.prompt_tokens>0 and
          isfinite(s.prefill_s) and s.prefill_s>0]
    if len(rows)<3:
        return {"admit":False,"reason":"NO_MATCHING_COMPLETED_NATIVE_PROFILE","samples":len(rows)}
    prediction=max(s.prefill_s/s.prompt_tokens for s in rows)*prompt_tokens*margin
    return {"admit":prediction+reserve_s<=remaining_s,
            "reason":"PROFILE_FITS" if prediction+reserve_s<=remaining_s else "PREFILL_EXCEEDS_DEADLINE",
            "estimated_prefill_s":round(prediction,3),"samples":len(rows),
            "evidence":"HEURISTIC_ONLY_NOT_DEVICE_ACCEPTANCE"}
