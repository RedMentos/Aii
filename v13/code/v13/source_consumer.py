"""Bounded, source-authorized factual memory consumption (candidate; not wired into Runtime).

Only explicit named project-budget questions are in scope. This module never
authorizes learning or turns model hypotheses into facts. It refuses absent,
wrong-entity, wrong-topic, tampered, revoked, cross-session or conflicting
corrections *before* any model prompt can contain them.
"""
import re

from .memory import entities, relevance
from .prompts import text as prompt

BUDGET = re.compile(r"\b(?:budget|budgets|finanzrahmen|etat)\b", re.I)
PROJECT = re.compile(r"\b(?:projekt|project)\s+([\w-]+)", re.I)


def query_scope(query):
    if not isinstance(query, str) or not BUDGET.search(query):
        return None
    names = entities(query)
    if len(names) != 1:
        return None
    return next(iter(names))


def strict_exact_amount(answer, amount):
    """615.000 / 615,000 must not be accepted as exact 615."""
    return bool(re.search(r"(?<!\d)" + re.escape(str(int(amount))) +
                          r"(?!\d|[.,]\d)", answer or ""))


def unsupported_amount(answer):
    """Detect arbitrary two-digit-or-longer numbers, not only a withheld label."""
    return bool(re.search(r"(?<!\w)\d[\d.,]*\d(?!\w)", answer or ""))


def admit(query, session, memories, memory):
    """Return ADMITTED or deterministic CLARIFY; no model on missing source.

    `memories` must come from the trusted Memory.recall result, not a prompt.
    Candidate rows and F1/F5 provenance are re-read and rechecked; any malformed
    row is discarded. A learned semantic association can support a topic only
    when the retrieval result marks an in-support admission and the entity is
    exactly the same. No unverified SourceRef reaches the model.
    """
    name = query_scope(query)
    if name is None:
        return {"status": "NOT_APPLICABLE", "reason": "OUTSIDE_EXPLICIT_PROJECT_BUDGET_SCOPE",
                "model_allowed": False}
    german = bool(re.search(r"\bprojekt\b|finanzrahmen|wie hoch", query, re.I))
    abstain = (f"Für Projekt {name} habe ich keinen verifizierten Budgetwert. "
               "Kannst du ihn nennen?" if german else
               f"I don't have a verified budget for Project {name}. Could you provide it?")
    valid = []
    for supplied in memories or ():
        try:
            if not isinstance(supplied, dict) or type(supplied.get("id")) is not str:
                continue
            fresh = memory.candidate(supplied["id"], session)
            if not memory._verified_rows([fresh]):
                continue
            if fresh["kind"] != "fact" or not BUDGET.search(fresh["key_text"]):
                continue
            if entities(fresh["key_text"]) != {name}:
                continue
            if supplied.get("source_ref") != fresh["source_ref"]:
                continue
            lexical = relevance(query, fresh["key_text"]) > 0
            policy = supplied.get("retrieval_policy")
            learned = (isinstance(policy, dict) and policy.get("decision") == "admit"
                       and policy.get("in_support") is True)
            if not (lexical or learned):
                continue
            source = memory.s.read_source(fresh["source_ref"])
            if source != fresh["value"]:
                continue
            valid.append({"memory_id": fresh["id"], "topic": fresh["key_text"],
                          "value": source, "source_ref": fresh["source_ref"],
                          "match": "LEXICAL" if lexical else "LEARNED_IN_SUPPORT"})
        except (KeyError, ValueError, TypeError, OSError):
            continue
    values = {x["value"] for x in valid}
    if len(values) != 1:
        return {"status": "CLARIFY", "reason": "NO_AUTHORIZED_SOURCE" if not values else "CONFLICTING_AUTHORIZED_SOURCES",
                "answer": abstain, "model_allowed": False, "admitted_count": 0}
    chosen = sorted(valid, key=lambda x: x["memory_id"])[0]
    return {"status": "ADMITTED", "reason": "ONE_VERIFIED_CORRECTION",
            "model_allowed": True, "admitted_count": len(valid), "source": chosen}


def render_messages(cfg, query, admission):
    """Construct a C3 prompt only for the exact admitted correction."""
    if admission.get("status") != "ADMITTED" or admission.get("model_allowed") is not True:
        raise ValueError("Source admission required before native generation")
    source = admission["source"]
    system = " ".join(prompt(cfg, k) for k in ("system", "conduct", "answer_rules"))
    system += (f"\nVerified user correction for this topic: {source['topic']} = {source['value']}. "
               "Use this exact correction only if the current request concerns that same project. "
               "Do not substitute another project or invent a value.")
    return [{"role": "system", "content": system},
            {"role": "user", "content": query}]
