"""A5 source-bound prompt admission candidate; no model or permission authority."""
from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class Evidence:
    source_id: str
    organ: str
    text: str
    priority: int = 0
    consented: bool = False
    final: bool = True

@dataclass(frozen=True)
class Admission:
    text: str
    included: tuple[str, ...]
    excluded: tuple[str, ...]
    estimated_tokens: int
    status: str

def estimate_tokens(text: str) -> int:
    """Conservative heuristic, NOT actual GGUF tokenizer count."""
    return (len(text.encode("utf-8")) + 2) // 3

def admit(user_text: str, evidence: Sequence[Evidence], token_cap: int = 240) -> Admission:
    """Never clip user input or silently omit source lineage.

    A later native tokenizer MUST validate this candidate before inference.
    """
    if token_cap <= 0:
        raise ValueError("token_cap must be positive")
    if not isinstance(user_text, str) or not user_text.strip():
        raise ValueError("nonempty user text required")
    if any(not e.source_id or not e.organ for e in evidence):
        raise ValueError("source and organ required")
    ids = [e.source_id for e in evidence]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate evidence IDs")
    base = "USER_EXACT:\n" + user_text + "\n"
    used = estimate_tokens(base)
    if used > token_cap:
        return Admission(base, (), tuple(ids), used, "USER_EXCEEDS_BUDGET")
    included, excluded, sections = [], [], []
    for e in sorted(evidence, key=lambda x: (-x.priority, x.source_id)):
        if not e.consented or not e.final:
            excluded.append(e.source_id)
            continue
        section = f"[{e.organ}|source={e.source_id}|untrusted]\n{e.text}\n"
        cost = estimate_tokens(section)
        if used + cost <= token_cap:
            sections.append(section)
            included.append(e.source_id)
            used += cost
        else:
            excluded.append(e.source_id)
    return Admission(base + "".join(sections), tuple(included), tuple(excluded), used,
                     "ADMITTED" if not excluded else "PARTIAL_EVIDENCE")
