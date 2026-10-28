"""Bounded, source-authorized factual memory consumption (candidate; not wired into Runtime).

Only explicit named project-budget questions are in scope. This module never
authorizes learning or turns model hypotheses into facts. It refuses absent,
wrong-entity, wrong-topic, tampered, revoked, cross-session or conflicting
corrections *before* any model prompt can contain them.
"""
import hashlib
import hmac
import json
import re
import secrets

from .memory import entities, relevance
from .prompts import text as prompt

# A process-local proof binds an admitted F1/F5 source to its exact render input.
# It is NOT a durable permission token or a substitute for dispatch-time revocation.
_RENDER_KEY = secrets.token_bytes(32)


def _render_proof(query, session, source, count):
    payload = json.dumps({"query": query, "session": session, "source": source,
                          "admitted_count": count},
                         sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(_RENDER_KEY, payload, hashlib.sha256).hexdigest()


BUDGET = re.compile(r"\b(?:budget|budgets|finanzrahmen|etat)\b", re.I)
PROJECT = re.compile(r"\b(?:projekt|project)\s+([\w-]+)", re.I)
# Conservative data grammar: user-provided source text is evidence, not an instruction.
# Locale-grouped and decimal amounts remain unsupported until independently tested.
TOPIC = re.compile(r"(?:Project|Projekt) [A-Za-z][A-Za-z0-9_-]{0,39} (?:budget|budgets|finanzrahmen|etat)", re.I)
BUDGET_VALUE = re.compile(r"(?:0|[1-9][0-9]{0,8}) +(Euro|EUR|€)", re.I)


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
    row is discarded. A learned semantic association is NOT trusted from an unbound caller
    dictionary; cross-topic synonyms remain blocked pending a verified query
    SourceRef and active learner decision proof. No unverified SourceRef reaches the model.
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
            if fresh["kind"] != "fact" or not isinstance(fresh["key_text"], str) or not TOPIC.fullmatch(fresh["key_text"]):
                continue
            if entities(fresh["key_text"]) != {name}:
                continue
            if supplied.get("source_ref") != fresh["source_ref"]:
                continue
            lexical = relevance(query, fresh["key_text"]) > 0
            # A caller-supplied retrieval_policy is NOT a source-bound proof.
            # Semantic synonym admission remains blocked until its decision
            # can be reverified against the active learner and query SourceRef.
            if not lexical:
                continue
            source = memory.s.read_source(fresh["source_ref"])
            if source != fresh["value"] or not isinstance(source, str) or not BUDGET_VALUE.fullmatch(source):
                continue
            valid.append({"memory_id": fresh["id"], "topic": fresh["key_text"],
                          "value": source, "source_ref": fresh["source_ref"],
                          "match": "LEXICAL"})
        except (KeyError, ValueError, TypeError, OSError):
            continue
    values = {x["value"] for x in valid}
    if len(values) != 1:
        return {"status": "CLARIFY", "reason": "NO_AUTHORIZED_SOURCE" if not values else "CONFLICTING_AUTHORIZED_SOURCES",
                "answer": abstain, "model_allowed": False, "admitted_count": 0}
    chosen = sorted(valid, key=lambda x: x["memory_id"])[0]
    return {"status": "ADMITTED", "reason": "ONE_VERIFIED_CORRECTION",
            "model_allowed": True, "admitted_count": len(valid), "source": chosen,
            "_render_session": session,
            "_render_seal": _render_proof(query, session, chosen, len(valid))}


def render_messages(cfg, query, admission):
    """Construct a C3 prompt only for the exact admitted correction."""
    if admission.get("status") != "ADMITTED" or admission.get("model_allowed") is not True:
        raise ValueError("Source admission required before native generation")
    source = admission.get("source")
    seal = admission.get("_render_seal")
    session = admission.get("_render_session")
    count = admission.get("admitted_count")
    if (not isinstance(source, dict) or not isinstance(seal, str)
            or not isinstance(session, str) or type(count) is not int
            or not hmac.compare_digest(seal, _render_proof(query, session, source, count))):
        raise ValueError("Authenticated F1/F5 admission required for C3 rendering")
    if (not isinstance(source, dict) or not isinstance(source.get("topic"), str)
            or not TOPIC.fullmatch(source["topic"])
            or not isinstance(source.get("value"), str)
            or not BUDGET_VALUE.fullmatch(source["value"])
            or not isinstance(source.get("source_ref"), dict)
            or query_scope(query) != next(iter(entities(source["topic"])), None)):
        raise ValueError("Bounded budget source/topic required for C3 prompt")
    system = " ".join(prompt(cfg, k) for k in ("system", "conduct", "answer_rules"))
    system += (f"\nVerified user correction for this topic: {source['topic']} = {source['value']}. "
               "Use this exact correction only if the current request concerns that same project. "
               "Do not substitute another project or invent a value.")
    return [{"role": "system", "content": system},
            {"role": "user", "content": query}]


def recall_and_admit(query, session, memory):
    """Actual F1/F5 recall -> source-checked admission; never infer authority.

    The exact-key scan is a *conflict veto*, not an alternative retrieval route.
    A matching Memory.recall result is required for admission. A second active
    same-project correction cannot disappear merely because top_k truncated it.
    """
    name = query_scope(query)
    if name is None:
        return admit(query, session, [], memory)
    refused = admit(query, session, [], memory)

    def deny(reason):
        return dict(refused, reason=reason, model_allowed=False)

    try:
        retrieved = memory.recall(query, session, semantic=None, top_k=8)
        if not any(isinstance(m, dict) and isinstance(m.get("key_text"), str)
                   and TOPIC.fullmatch(m["key_text"])
                   and entities(m["key_text"]) == {name} for m in retrieved):
            return deny("NO_SCOPED_RETRIEVAL")
        keys = sorted({f"{prefix} {name} {field}".lower()
                       for prefix in ("Project", "Projekt")
                       for field in ("budget", "budgets", "etat", "finanzrahmen")})
        placeholders = ",".join("?" for _ in keys)
        rows = memory.s.rows(
            "SELECT id FROM memories WHERE active=1 AND kind='fact' "
            "AND (session_id=? OR scope='global') "
            f"AND LOWER(key_text) IN ({placeholders}) "
            "ORDER BY created DESC LIMIT 257", (session, *keys))
        if len(rows) > 256:
            return deny("TOO_MANY_SCOPED_CORRECTIONS")
        by_id = {m["id"]: m for m in retrieved
                 if isinstance(m, dict) and isinstance(m.get("id"), str)}
        for row in rows:
            try:
                fresh = memory.candidate(row["id"], session)
                by_id[fresh["id"]] = fresh
            except (KeyError, ValueError, TypeError, OSError):
                continue
        return admit(query, session, list(by_id.values()), memory)
    except Exception:
        return deny("RETRIEVAL_UNAVAILABLE")


def verified_recall_messages(cfg, query, session, memory):
    """Opt-in atomic-ish recall/verify/render candidate; no native call.

    The caller must still check revocation immediately before model dispatch.
    No arbitrary caller-supplied admission dictionary is used for authority.
    """
    decision = recall_and_admit(query, session, memory)
    if decision["status"] != "ADMITTED":
        return {"decision": decision, "messages": None}
    source = decision["source"]
    try:
        fresh = memory.candidate(source["memory_id"], session)
        if (not memory._verified_rows([fresh])
                or fresh["source_ref"] != source["source_ref"]
                or fresh["key_text"] != source["topic"]
                or fresh["value"] != source["value"]
                or memory.s.read_source(source["source_ref"]) != source["value"]):
            raise ValueError("Source changed after admission")
        messages = render_messages(cfg, query, decision)
        return {"decision": decision, "messages": messages}
    except Exception:
        refused = admit(query, session, [], memory)
        return {"decision": dict(refused, reason="SOURCE_REVALIDATION_FAILED",
                                 model_allowed=False), "messages": None}
