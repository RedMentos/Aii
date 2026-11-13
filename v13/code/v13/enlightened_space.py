"""Enlightened Space: source-bound, system-wide V13 organ communication.

This is the *shared protocol and bounded recurrent workspace*, NOT a third
chatbot or a pretend trained JEPA latent. It connects A perception, semantic
Stream A, exact/provenance Stream B, B1/B2 and B3, B4/C4 workspace,
Memory, World, Self, JEF, Inquisition, C3, action/outcome and learning.

Age-0 implementation: typed organ messages + source-preserving small semantic
state + multi-timescale recurrence + native-body/C3 input conditioning.
The native JEPA projection/EMA, fully distributed recurrent computation and
validated latent B3 receiver injection remain separate capability gates.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
import re

from .common import safe_text

SCHEMA = "v13.enlightened-space/1"
STATE_PREFIX = "ENLIGHTENED_SPACE:"
CAPACITY = 64
MAX_IN_EVENT = 24
MAX_MESSAGE = 280
MAX_SOURCE_REFS = 3
MAX_SHARED_CHARS = 900
MAX_EXACT_CHARS = 148
MAX_READ = 5
MAX_TOKENS = 18
LEVELS = ("FAST", "MEDIUM", "SLOW")
ORGAN_ROLES = frozenset({
    "A_PERCEPTION", "STREAM_A", "STREAM_B", "B1_DETAIL", "B2_GIST",
    "B3_CALLOSUM", "B4_WORKSPACE", "C1_JEF", "C2_CONTROL",
    "C3_LANGUAGE", "C4_FOCAL", "C5_ACTION", "INQUISITION",
    "MEMORY", "WORLD", "SELF", "JEPA", "OUTCOME",
})
CHANNELS = frozenset({"SEMANTIC", "EXACT", "CONTROL", "PREDICTION",
                      "FEEDBACK", "FOCAL"})
AUTHORITY = frozenset({"SOURCE_POINTER", "USER_MEMORY_CUE",
                       "MODEL_HYPOTHESIS", "CONTROL_ONLY",
                       "MEASURED_DIGITAL_OUTCOME"})
WORDS = re.compile(r"(?u)\b[\wÄÖÜäöüß]{3,}\b")
STOP = frozenset({"the","and","with","for","from","that","this","are","was",
                  "der","die","das","den","dem","ein","eine","und","mit",
                  "von","für","oder","ist","sind","auch","nicht","user"})


def _terms(text):
    c = Counter(w.casefold() for w in WORDS.findall(text[:MAX_MESSAGE])
                if w.casefold() not in STOP)
    return dict(sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[:MAX_TOKENS])


def _similarity(a, b):
    keys = a.keys() & b.keys()
    aa = sum(x*x for x in a.values())
    bb = sum(x*x for x in b.values())
    return sum(a[k]*b[k] for k in keys) / math.sqrt(aa*bb) if aa and bb else 0.


def _frame(event):
    if not isinstance(event, dict) or not all(
            isinstance(event.get(k), str) and event[k]
            for k in ("event_id", "brain_generation_id")):
        raise ValueError("invalid Enlightened event binding")
    return event["event_id"], event["brain_generation_id"]


def _fingerprint(*values):
    data = json.dumps(values, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(data.encode()).hexdigest()[:24]


def _safe_text(value):
    if not isinstance(value, str):
        return ""
    return safe_text(value[:MAX_MESSAGE])


def _source_binding(store, refs):
    if not isinstance(refs, (list, tuple)):
        raise ValueError("source_refs must be a list")
    if len(refs) > MAX_SOURCE_REFS:
        raise ValueError("too many source bindings")
    keep = []
    for r in refs:
        if not isinstance(r, dict) or r.get("modality") != "text":
            raise ValueError("invalid exact source reference")
        text = store.read_source(r)  # hash+range+deletion check, never trust model text
        if not isinstance(text, str):
            raise ValueError("nontext exact source")
        keep.append(dict(r))
    return keep


class EnlightenedSpace:
    """Session-isolated, revisioned inter-organ communication.

    Producer identity is supplied only by fixed local runtime call sites.
    Reader instructions are *not* user-command channels and cannot create
    tool/weight permissions, semantic facts or model output authority.
    """

    def __init__(self, store, session):
        self.store = store
        self.key = STATE_PREFIX + session

    def _state(self, generation):
        raw, version = self.store.state(self.key, {})
        if not isinstance(raw, dict) or raw.get("schema") != SCHEMA or raw.get("generation") != generation:
            return {"schema": SCHEMA, "generation": generation,
                    "entries": [], "turns": 0}, version
        entries = raw.get("entries", [])
        if not isinstance(entries, list):
            raise ValueError("corrupt Enlightened Space")
        entries = [e for e in entries[-CAPACITY:] if
                   isinstance(e, dict) and e.get("producer") in ORGAN_ROLES
                   and e.get("channel") in CHANNELS
                   and e.get("authority") in AUTHORITY
                   and e.get("generation") == generation
                   and isinstance(e.get("event_id"), str)
                   and isinstance(e.get("source_refs"), list)
                   and isinstance(e.get("semantic_terms"), dict)
                   and e.get("level") in LEVELS]
        return {"schema": SCHEMA, "generation": generation,
                "entries": entries, "turns": max(0, min(1_000_000, int(raw.get("turns", 0))))}, version

    def publish(self, event, producer, channel, *, summary="", source_refs=(),
                authority="CONTROL_ONLY", packet_id=None):
        """Emit a typed, inspectable message after the real organ has run.

        SOURCE_POINTER/USER_MEMORY_CUE/MODEL_HYPOTHESIS require a verified
        exact ref. CONTROL_ONLY and measured own digital outcomes can omit it.
        A semantic cue is always non-authoritative, even when repeated.
        """
        event_id, generation = _frame(event)
        if producer not in ORGAN_ROLES or channel not in CHANNELS or authority not in AUTHORITY:
            raise ValueError("unsupported Enlightened Space organ or channel")
        summary = _safe_text(summary)
        refs = _source_binding(self.store, source_refs)
        if authority in {"SOURCE_POINTER", "USER_MEMORY_CUE", "MODEL_HYPOTHESIS"} and not refs:
            raise ValueError("evidence-bearing message requires an exact source")
        if packet_id is not None:
            if not isinstance(packet_id, str):
                raise ValueError("packet_id must be a pointer")
            row = self.store.one("SELECT kind,event_id,payload FROM packets WHERE id=?",
                                 (packet_id,))
            if not row or row["event_id"] != event_id:
                raise ValueError("unbound organ packet")
            payload = json.loads(row["payload"])
            if payload.get("brain_generation_id") != generation:
                raise ValueError("organ packet generation mismatch")
            if producer in {"B1_DETAIL", "B2_GIST"}:
                if row["kind"] != "OfferPacket" or payload.get("role") != producer:
                    raise ValueError("unbound body offer")
                if any(ref not in payload.get("evidence_refs", []) for ref in refs):
                    raise ValueError("body hypothesis outside verified source spans")
            if producer == "B3_CALLOSUM" and (
                    row["kind"] != "MessagePacket" or
                    any(ref not in payload.get("source_refs", []) for ref in refs)):
                raise ValueError("unbound B3 direct message")
        entry = {
            "message_id": _fingerprint(event_id, generation, producer, channel, packet_id, summary, refs),
            "event_id": event_id, "generation": generation,
            "producer": producer, "channel": channel, "authority": authority,
            "packet_id": packet_id, "source_refs": refs,
            "semantic_terms": _terms(summary), "summary": summary,
            "level": "FAST", "coactivations": 1,
        }
        for _ in range(3):
            state, version = self._state(generation)
            entries = state["entries"]
            if any(e["message_id"] == entry["message_id"] for e in entries):
                return {"status": "ALREADY_PRESENT", "message_id": entry["message_id"]}
            # A recalled cue may become longer-lived if it repeatedly fires,
            # but messages from different organs are never collapsed together.
            for old in entries[-24:]:
                if (old["producer"] == producer and old["channel"] == channel and
                        old["authority"] == authority and
                        _similarity(old["semantic_terms"], entry["semantic_terms"]) > .68):
                    n = max(1, min(100, int(old.get("coactivations", 1)) + 1))
                    entry["coactivations"] = max(entry["coactivations"], n)
                    entry["level"] = "SLOW" if n >= 5 else "MEDIUM" if n >= 2 else "FAST"
                    break
            this_turn = sum(e["event_id"] == event_id for e in entries)
            if this_turn >= MAX_IN_EVENT:
                return {"status": "EVENT_BUDGET", "message_id": None}
            state["entries"] = (entries + [entry])[-CAPACITY:]
            try:
                self.store.set_state(self.key, state, expected=version)
                return {"status": "PUBLISHED", "message_id": entry["message_id"]}
            except ValueError as exc:
                if str(exc) != "Stale state write":
                    raise
        return {"status": "RACE_RETRY_LIMIT", "message_id": None}

    def consume(self, event, receiver, query="", *, selected_offers=(),
                max_messages=MAX_READ, max_chars=MAX_SHARED_CHARS):
        """Materially condition actual receiver prompts from shared organ state.

        Return only revalidated source-bound cues and separately labelled
        control messages. Unselected B1/B2 hypotheses cannot influence the
        externally reported C3 answer. Never trust a stale model revision or
        use a model summary as authoritative source text.
        """
        event_id, generation = _frame(event)
        if receiver not in ORGAN_ROLES:
            raise ValueError("unknown shared-space receiver")
        if (type(max_messages) is not int or not 0 <= max_messages <= MAX_READ or
                type(max_chars) is not int or not 0 <= max_chars <= MAX_SHARED_CHARS):
            raise ValueError("invalid shared-space budget")
        state, version = self._state(generation)
        qterms = _terms(_safe_text(query))
        approved = set(selected_offers or ())
        rows = []
        for record in state["entries"]:
            if record["producer"] == receiver:
                continue
            # The current user's own input is already passed to each body
            # verbatim. Keep shared space for cross-organ signals, not echoes.
            if record["event_id"] == event_id and record["producer"] in {
                    "A_PERCEPTION", "STREAM_A", "STREAM_B"}:
                continue  # fresh input already given exactly; no duplicate prefill
            if receiver == "C3_LANGUAGE" and record["producer"] == "B3_CALLOSUM":
                continue  # B3 messages are for native B1/B2, not unselected C3 facts
            if record["producer"] in {"B1_DETAIL", "B2_GIST"} and receiver == "C3_LANGUAGE":
                if record["event_id"] != event_id or record.get("packet_id") not in approved:
                    continue  # only fresh, focally approved body contributions reach outer report
            refs = []
            try:
                for ref in record["source_refs"][:MAX_SOURCE_REFS]:
                    text = self.store.read_source(ref)
                    refs.append((ref, text))
            except (ValueError, KeyError, OSError, TypeError, UnicodeError):
                continue  # erasure and hash invalidation revoke access
            if record["authority"] in {"MODEL_HYPOTHESIS", "SOURCE_POINTER", "USER_MEMORY_CUE"} and not refs:
                continue
            sim = _similarity(qterms, record["semantic_terms"])
            if record["event_id"] != event_id and sim < .09:
                continue
            scope = 1. if record["event_id"] == event_id else .15
            # World/Self/JEPA statuses are control hints, never source facts.
            control = .10 if record["channel"] in {"CONTROL", "PREDICTION", "FEEDBACK"} else 0.
            value = sim + scope + control
            rows.append((value, record, refs))
        rows.sort(key=lambda row: row[0], reverse=True)
        entries, all_refs = [], []
        used = 0
        for score, record, refs in rows:
            if len(entries) >= max_messages or used >= max_chars:
                break
            remaining = max_chars-used
            summary = record["summary"][:min(140,remaining)]
            used += len(summary)
            excerpts = []
            for ref, source in refs[:1]:
                if used >= max_chars:
                    break
                # Exact pointer separately, never overwrite summarized claim.
                excerpt = source[:min(MAX_EXACT_CHARS, max_chars-used)]
                if excerpt:
                    excerpts.append({"exact_source_text": excerpt,
                                     "source_ref": ref, "verification": "RECHECKED_EXACT_BYTES"})
                    all_refs.append(ref)
                    used += len(excerpt)
            entries.append({
                "from": record["producer"], "channel": record["channel"],
                "authority": record["authority"], "time_scale": record["level"],
                "semantic_cue_not_fact": summary,
                "exact_sources": excerpts, "coactivations": record["coactivations"],
            })
        return {
            "schema": SCHEMA,
            "representation": "SYMBOLIC_MESSAGE_SPACE_NOT_NATIVE_JEPA",
            "trained_latent": False,
            "global_scope": True,
            "entry_count": len(entries),
            "messages": entries,
            "source_refs": all_refs,
            "revision": version,
        }

    def report(self, generation):
        state, version = self._state(generation)
        counts = {role: 0 for role in sorted(ORGAN_ROLES)}
        levels = {level: 0 for level in LEVELS}
        for entry in state["entries"]:
            counts[entry["producer"]] += 1
            levels[entry["level"]] += 1
        return {"schema": SCHEMA, "generation": generation,
                "revision": version, "representation": "SYMBOLIC_MESSAGE_SPACE_NOT_NATIVE_JEPA",
                "trained_latent": False, "entries": len(state["entries"]),
                "organ_messages": counts, "timescales": levels,
                "source_erasure_enforced_on_read": True,
                "authoritative_semantic_truth": False}
