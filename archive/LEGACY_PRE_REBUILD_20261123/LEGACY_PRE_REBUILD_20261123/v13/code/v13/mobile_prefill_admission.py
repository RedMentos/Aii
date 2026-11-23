"""V13 mobile native prefill admission (experimental, opt-in; no Redmi benchmark claim).

Consumes only consented aggregate technical measurements. Never removes source data:
a rejected admission means defer/restore, not truncate or silently omit a source.
This is a preflight aid for C3/B1/B2, not a replacement for the canonical governor.
"""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class NativeSample:
    role: str
    prompt_tokens: int
    prefill_seconds: float
    generated_tokens: int
    decode_seconds: float
    threads: int
    batch: int
    concurrent_roles: int = 1

    def validate(self):
        if self.role not in ("C3_LANGUAGE", "B1_DETAIL", "B2_GIST"):
            raise ValueError("role")
        for name in ("prompt_tokens", "generated_tokens", "threads", "batch", "concurrent_roles"):
            x = getattr(self, name)
            if type(x) is not int or x < (0 if name in ("prompt_tokens", "generated_tokens") else 1):
                raise ValueError(name)
        for name in ("prefill_seconds", "decode_seconds"):
            x = getattr(self, name)
            if not isinstance(x, (float, int)) or not math.isfinite(x) or x < 0:
                raise ValueError(name)
        if not self.prompt_tokens or not self.prefill_seconds:
            raise ValueError("zero prefill sample")
        return self

def estimate(samples, *, role, prompt_tokens, output_tokens, threads, batch,
             concurrent_roles=1, deadline_seconds=30, reserve_seconds=3,
             uncertainty_multiplier=1.5):
    """Return evidence-tagged preflight; fail closed if exact configuration is unmeasured.

    Worst observed seconds/token for matching configuration times uncertainty factor;
    no interpolation across thread/batch/concurrency configurations. For short prompts,
    this is a conservative *estimate*, not a hard realtime guarantee.
    """
    if type(prompt_tokens) is not int or prompt_tokens < 0 or type(output_tokens) is not int or output_tokens < 0:
        raise ValueError("token counts")
    if not all(math.isfinite(float(v)) and float(v) > 0 for v in (deadline_seconds, uncertainty_multiplier)):
        raise ValueError("budget")
    if not math.isfinite(float(reserve_seconds)) or reserve_seconds < 0 or reserve_seconds >= deadline_seconds:
        raise ValueError("reserve")
    matching = [s.validate() for s in samples if s.role == role and s.threads == threads
                and s.batch == batch and s.concurrent_roles == concurrent_roles]
    if not matching:
        return {"decision": "UNVERIFIED", "reason": "NO_MATCHING_NATIVE_SAMPLE",
                "source_preserved": True, "estimated_seconds": None, "samples": 0}
    prefill_rate = max(s.prefill_seconds / s.prompt_tokens for s in matching)
    decode = [s.decode_seconds / s.generated_tokens for s in matching if s.generated_tokens]
    if output_tokens and not decode:
        return {"decision": "UNVERIFIED", "reason": "NO_DECODE_SAMPLE",
                "source_preserved": True, "estimated_seconds": None, "samples": len(matching)}
    seconds = uncertainty_multiplier * (prompt_tokens * prefill_rate +
                                         output_tokens * (max(decode) if decode else 0))
    return {"decision": "ADMIT_ESTIMATE" if seconds <= deadline_seconds-reserve_seconds else "DEFER_RESTORE",
            "reason": "MATCHED_CONFIG_ESTIMATE_NOT_PHONE_PROOF",
            "source_preserved": True, "estimated_seconds": round(seconds, 3),
            "samples": len(matching), "headroom_seconds": round(deadline_seconds-reserve_seconds-seconds, 3)}

def bounded_source_envelope(parts, max_tokens):
    """Budget source-bound context WITHOUT discarding refs or claiming an LLM token count.

    Each part: {source_ref, text, estimated_tokens}. Unselected parts become deferred
    exact-source pointers for Context OS restoration. Caller must restore before
    making any claim that depends on them.
    """
    if type(max_tokens) is not int or max_tokens < 0:
        raise ValueError("max_tokens")
    selected, deferred, used = [], [], 0
    for part in parts:
        if not isinstance(part, dict) or not part.get("source_ref") or not isinstance(part.get("text"), str):
            raise ValueError("source provenance required")
        n = part.get("estimated_tokens")
        if type(n) is not int or n < 0:
            raise ValueError("token estimate")
        if used + n <= max_tokens:
            selected.append(dict(part)); used += n
        else:
            deferred.append({"source_ref": part["source_ref"], "estimated_tokens": n,
                             "restore_required": True})
    return {"selected": selected, "deferred": deferred, "estimated_tokens": used,
            "exact_source_preserved": True, "tokenizer_verified": False}
