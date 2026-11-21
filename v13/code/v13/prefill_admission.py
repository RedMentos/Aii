"""Conservative prefill admission for the Android native answer path.

No silent source truncation: user content is never edited.  This module only
budgets optional system/history material and reports when the source alone
cannot fit.  Character estimates are intentionally pessimistic, not a
replacement for tokenizer counts or physical Redmi profiling.
"""
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Admission:
    accepted: bool
    messages: tuple
    reason: str
    estimated_tokens: int
    dropped_history: int
    dropped_optional: int


def upper_tokens(value: str) -> int:
    """Upper bound for ordinary UTF-8 byte-level tokenizers (plus margin)."""
    if not isinstance(value, str):
        raise TypeError("content must be text")
    return len(value.encode("utf-8")) + 8


def admit(messages: Sequence[dict], *, prompt_cap: int = 320,
          reserve_tokens: int = 48, context_limit: int = 2048) -> Admission:
    """Admit native messages without altering the exact final user source.

    Refuse impossible requests rather than silently clipping source or
    fabricating a model answer.  Preserve system prefix and chronological
    order of the most recent history that fits.  System material is treated
    as required: its optional layers must be reduced upstream by ContextOS.
    """
    if not isinstance(prompt_cap, int) or isinstance(prompt_cap, bool) or prompt_cap < 32:
        raise ValueError("invalid prompt cap")
    if not isinstance(reserve_tokens, int) or reserve_tokens < 1:
        raise ValueError("invalid decode reserve")
    if not isinstance(context_limit, int) or context_limit <= reserve_tokens:
        raise ValueError("invalid context limit")
    if not messages or any(not isinstance(m, dict) or m.get("role") not in
                           {"system", "user", "assistant", "tool"} or
                           not isinstance(m.get("content"), str) for m in messages):
        raise ValueError("invalid native messages")
    if messages[-1]["role"] != "user":
        raise ValueError("final native message must be exact user source")
    if messages[0]["role"] != "system":
        raise ValueError("first native message must be system")
    cap = min(prompt_cap, context_limit - reserve_tokens)
    # Conservative overhead for chat-template role delimiters.
    cost = lambda m: upper_tokens(m["content"]) + 16
    required = cost(messages[0]) + cost(messages[-1])
    if required > cap:
        return Admission(False, tuple(), "REQUIRED_SOURCE_EXCEEDS_PREFILL_BUDGET",
                         required, len(messages) - 2, 0)
    # Keep complete user/assistant exchange pairs only.  A dangling assistant
    # answer without its originating user prompt is not admissible context.
    history = list(messages[1:-1])
    kept = []
    total = required
    for i in range(len(history) - 1, -1, -1):
        candidate = history[i:]
        if candidate[0]["role"] != "user":
            continue
        amount = sum(cost(m) for m in candidate)
        if total + amount <= cap:
            kept = candidate
            total += amount
            break
    dropped = len(history) - len(kept)
    selected = (messages[0], *kept, messages[-1])
    return Admission(True, tuple(dict(m) for m in selected), "ADMITTED",
                     total, dropped, 0)
