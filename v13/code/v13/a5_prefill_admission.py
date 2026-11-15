"""A5 source-preserving prompt admission for slow Android prefill.

Pure standard-library candidate; does not activate native inference or mutate
source packets. Tokens are caller-measured, not estimated from characters.
"""
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class SourceEnvelope:
    organ: str
    source_id: str
    token_count: int
    required: bool = False
    consented: bool = True

    def __post_init__(self):
        if not isinstance(self.organ, str) or not self.organ.strip():
            raise ValueError("invalid organ")
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ValueError("invalid source identity")
        if type(self.token_count) is not int or self.token_count < 0:
            raise ValueError("invalid measured token count")
        if type(self.required) is not bool or type(self.consented) is not bool:
            raise ValueError("required and consented must be booleans")


@dataclass(frozen=True)
class Admission:
    accepted: tuple
    deferred: tuple
    rejected: tuple
    used_tokens: int
    status: str


def admit_sources(sources: Sequence[SourceEnvelope], max_prompt_tokens: int,
                  reserved_tokens: int = 0) -> Admission:
    """Deterministic, no-truncation admission; preserve original input order.

    Required packets (e.g. current user source) are reserved before optional
    packets. If required sources are missing consent or cannot fit, fail the
    route rather than silently generating without mandatory evidence.
    """
    if type(max_prompt_tokens) is not int or type(reserved_tokens) is not int:
        raise ValueError("token budgets must be measured integers")
    if max_prompt_tokens < 0 or reserved_tokens < 0:
        raise ValueError("negative token budget")
    if len({s.source_id for s in sources}) != len(sources):
        raise ValueError("duplicate source identity")
    rejected = tuple(s for s in sources if not s.consented)
    eligible = tuple(s for s in sources if s.consented)
    if any(s.required for s in rejected):
        return Admission((), (), rejected + eligible, 0, "REQUIRED_NOT_CONSENTED")
    allowed = max_prompt_tokens - reserved_tokens
    mandatory = tuple(s for s in eligible if s.required)
    if allowed < 0 or sum(s.token_count for s in mandatory) > allowed:
        return Admission((), (), rejected + eligible, 0, "REQUIRED_OVER_BUDGET")
    remaining = allowed - sum(s.token_count for s in mandatory)
    selected = {s.source_id for s in mandatory}
    for s in eligible:
        if not s.required and s.token_count <= remaining:
            selected.add(s.source_id)
            remaining -= s.token_count
    accepted = tuple(s for s in eligible if s.source_id in selected)
    deferred = tuple(s for s in eligible if s.source_id not in selected)
    return Admission(accepted, deferred, rejected,
                     sum(s.token_count for s in accepted),
                     "ADMITTED" if not deferred else "PARTIAL_SOURCE_DEFERRED")
