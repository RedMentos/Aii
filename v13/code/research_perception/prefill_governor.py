"""Offline A5 prefill admission; no Runtime activation or device measurement claims."""
from dataclasses import dataclass
from math import ceil, isfinite

@dataclass(frozen=True)
class Sample:
    prompt_tokens: int
    prefill_ms: float
    model_revision: str
    threads: int
    batch: int
    device: str

@dataclass(frozen=True)
class Decision:
    status: str
    estimated_ms: int | None
    matched_samples: int

def admit_prefill(samples: tuple[Sample, ...], *, prompt_tokens: int,
                  deadline_ms: int, model_revision: str, threads: int,
                  batch: int, device: str, safety_factor: float = 1.3,
                  decode_reserve_ms: int = 0) -> Decision:
    """Conservative offline heuristic; not a native timing guarantee.

    Only interpolates inside observed token lengths. Never treats prefill as
    the whole turn: reserve time for decode, orchestration and delivery.
    """
    if type(prompt_tokens) is not int or prompt_tokens <= 0 or type(deadline_ms) is not int or deadline_ms <= 0:
        raise ValueError("invalid tokens/deadline")
    if type(decode_reserve_ms) is not int or decode_reserve_ms < 0:
        raise ValueError("invalid decode reserve")
    if type(safety_factor) not in (int, float) or not isfinite(safety_factor) or safety_factor < 1:
        raise ValueError("invalid safety factor")
    if not isinstance(model_revision, str) or not model_revision or not isinstance(device, str) or not device or type(threads) is not int or threads <= 0 or type(batch) is not int or batch <= 0:
        raise ValueError("invalid profile identity")
    matching = []
    for s in samples:
        if type(s.prompt_tokens) is not int or s.prompt_tokens <= 0 or type(s.prefill_ms) not in (int, float) or not isfinite(s.prefill_ms) or s.prefill_ms <= 0:
            raise ValueError("invalid sample")
        if (s.model_revision, s.threads, s.batch, s.device) == (model_revision, threads, batch, device):
            matching.append(s)
    lengths = {s.prompt_tokens for s in matching}
    if len(lengths) < 2:
        return Decision("INSUFFICIENT_PROFILE", None, len(matching))
    if prompt_tokens < min(lengths):
        return Decision("EXTRAPOLATION_UNSUPPORTED", None, len(matching))
    if prompt_tokens > max(lengths):
        return Decision("EXTRAPOLATION_UNSUPPORTED", None, len(matching))
    # A conservative throughput envelope; avoid a falsely optimistic
    # linear fit on sparse, noisy, potentially thermal-throttled samples.
    rate = max(s.prefill_ms / s.prompt_tokens for s in matching)
    estimate = ceil(prompt_tokens * rate * safety_factor)
    return Decision("ADMITTED" if estimate + decode_reserve_ms <= deadline_ms else "PREFILL_DEADLINE_RISK", estimate, len(matching))
