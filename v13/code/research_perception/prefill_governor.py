"""Offline A5 prefill admission from provenance-tagged measurements; not live."""
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
                  batch: int, device: str, safety_factor: float = 1.3) -> Decision:
    """Conservative upper-envelope extrapolation; never a latency guarantee."""
    if type(prompt_tokens) is not int or prompt_tokens <= 0 or type(deadline_ms) is not int or deadline_ms <= 0:
        raise ValueError('invalid tokens/deadline')
    if not isfinite(safety_factor) or safety_factor < 1:
        raise ValueError('invalid safety factor')
    if not model_revision or not device or type(threads) is not int or threads <= 0 or type(batch) is not int or batch <= 0:
        raise ValueError('invalid profile identity')
    matching = []
    for s in samples:
        if type(s.prompt_tokens) is not int or s.prompt_tokens <= 0 or not isfinite(s.prefill_ms) or s.prefill_ms <= 0:
            raise ValueError('invalid sample')
        if (s.model_revision, s.threads, s.batch, s.device) == (model_revision, threads, batch, device):
            matching.append(s)
    if len({s.prompt_tokens for s in matching}) < 2:
        return Decision('INSUFFICIENT_PROFILE', None, len(matching))
    if prompt_tokens > 2 * max(s.prompt_tokens for s in matching):
        return Decision('EXTRAPOLATION_UNSUPPORTED', None, len(matching))
    rate = max(s.prefill_ms / s.prompt_tokens for s in matching)
    estimate = ceil(prompt_tokens * rate * safety_factor)
    return Decision('ADMITTED' if estimate <= deadline_ms else 'PREFILL_DEADLINE_RISK', estimate, len(matching))
