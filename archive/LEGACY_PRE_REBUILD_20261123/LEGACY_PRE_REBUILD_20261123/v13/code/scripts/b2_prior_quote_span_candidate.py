#!/usr/bin/env python3
"""Non-authoritative exact quote-to-SourceRef span candidate for B2 prior context.

Run87 raw evidence shows whole-source evidence_refs with sentence-sized quotes.
This module proposes subspan refs only for explicitly supplied source segments;
it does NOT change the frozen runtime, original scorer, model or gate.
"""
from __future__ import annotations

import hashlib

SCHEMA = "v13.b2_prior_quote_span_candidate.v1"
MAX_QUOTES = 2
MAX_SOURCES = 8
MAX_SOURCE_CHARS = 65536
MAX_QUOTE_CHARS = 512


class QuoteBindingRefused(ValueError):
    pass


def _require(ok, reason):
    if not ok:
        raise QuoteBindingRefused(reason)


def bind_exact_quotes(segments, quotes):
    """Bind each selected quote to one unambiguous exact source substring.

    segments: caller-authorized full source texts with {source_role, source_ref,
    text}. The caller MUST still revalidate returned refs against Store and
    the current session/turn before using them; this function grants no rights.
    """
    _require(type(segments) in (list, tuple) and 1 <= len(segments) <= MAX_SOURCES,
             "SOURCE_SET_INVALID")
    _require(type(quotes) in (list, tuple) and 1 <= len(quotes) <= MAX_QUOTES
             and len(set(q for q in quotes if type(q) is str)) == len(quotes),
             "QUOTE_SET_INVALID")
    validated = []
    seen_ids = set()
    for entry in segments:
        _require(type(entry) is dict and set(entry) >= {"source_role", "source_ref", "text"},
                 "SOURCE_ENTRY_INVALID")
        role, ref, text = entry["source_role"], entry["source_ref"], entry["text"]
        _require(role in ("prior", "current"), "SOURCE_ROLE_INVALID")
        _require(type(text) is str and 1 <= len(text) <= MAX_SOURCE_CHARS,
                 "SOURCE_TEXT_INVALID")
        _require(type(ref) is dict and type(ref.get("source_id")) is str
                 and ref["source_id"] and ref["source_id"] not in seen_ids,
                 "SOURCE_ID_INVALID")
        seen_ids.add(ref["source_id"])
        _require(ref.get("modality") == "text"
                 and type(ref.get("char_start")) is int and ref["char_start"] == 0
                 and type(ref.get("char_end")) is int and ref["char_end"] == len(text),
                 "FULL_SOURCE_SPAN_REQUIRED")
        _require(type(ref.get("sha256")) is str
                 and ref["sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest(),
                 "SOURCE_HASH_MISMATCH")
        validated.append((role, dict(ref), text))
    bindings = []
    for quote in quotes:
        _require(type(quote) is str and 1 <= len(quote) <= MAX_QUOTE_CHARS,
                 "QUOTE_TEXT_INVALID")
        matches = []
        for role, ref, text in validated:
            pos = text.find(quote)
            while pos >= 0:
                matches.append((role, ref, pos))
                pos = text.find(quote, pos + 1)
                _require(len(matches) <= 1, "AMBIGUOUS_QUOTE_SOURCE")
        _require(len(matches) == 1, "QUOTE_NOT_EXACT_SOURCE")
        role, ref, start = matches[0]
        span = {**ref, "char_start": start, "char_end": start + len(quote)}
        bindings.append({"quote": quote, "source_role": role, "source_ref": span})
    return {"schema": SCHEMA, "status": "SHADOW_EXACT_SOURCE_SPANS_ONLY",
            "bindings": bindings, "evidence_refs": [b["source_ref"] for b in bindings],
            "delivery_authority": 0, "learning_authority": 0,
            "native_utility_proven": False, "registered_scorer_changed": False}
