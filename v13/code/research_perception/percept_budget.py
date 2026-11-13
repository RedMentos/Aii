"""A5 source-bound prompt admission candidate; no model or permission authority."""
from dataclasses import dataclass
from typing import Sequence
import re

_SAFE_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}\\Z")

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
    if type(token_cap) is not int or token_cap <= 0:
        raise ValueError("token_cap must be positive")
    if not isinstance(user_text, str) or not user_text.strip():
        raise ValueError("nonempty user text required")
    evidence = tuple(evidence)
    for e in evidence:
        if not isinstance(e, Evidence):
            raise ValueError("invalid evidence")
        if not isinstance(e.source_id, str) or not _SAFE_LABEL.fullmatch(e.source_id):
            raise ValueError("invalid source ID")
        if not isinstance(e.organ, str) or not _SAFE_LABEL.fullmatch(e.organ):
            raise ValueError("invalid organ label")
        if not isinstance(e.text, str) or type(e.priority) is not int:
            raise ValueError("invalid evidence text/priority")
        if type(e.consented) is not bool or type(e.final) is not bool:
            raise ValueError("invalid evidence consent/finality")
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
