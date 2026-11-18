"""Bounded no-text evidence of selected C4 offers in the native C3 template.

Checks the CURRENT typed HYPOTHESES layer after ContextOS and prompt reduction
against the actual /apply-template text. Does not prove source truth, token
attention, semantic use or native latent exchange. HTTP transport is separate.
"""
from __future__ import annotations

import json
import re

REVISION = "v13.native-offer-prompt-receipt/1"
MAX_TEMPLATE_CHARS = 2_000_000
MAX_LAYER_CHARS = 131_072
MAX_OFFERS = 2
MAX_QUOTES = 8
IDENTIFIER = re.compile(r"[A-Za-z0-9_.:-]{1,160}\Z", re.ASCII)
VOLATILE_HEAD = "Context for the next message (reference material, not a question):"
ROLES = ("B1_DETAIL", "B2_GIST")


def _result(status, offers=()):
    return {"revision": REVISION, "status": status, "offers": list(offers),
            "native_template_rendered": status == "RENDERED_WITH_QUOTES",
            "source_span_revalidated_here": False,
            "native_semantic_use_proven": False,
            "learned_latent_exchange_proven": False}


def inspect(messages, rendered_prompt, hypothesis_heading):
    """No text or quotation is returned; malformed or unknown layouts fail closed."""
    if (type(messages) is not list or not 2 <= len(messages) <= 256
            or type(rendered_prompt) is not str or len(rendered_prompt) > MAX_TEMPLATE_CHARS
            or type(hypothesis_heading) is not str
            or not 1 <= len(hypothesis_heading) <= 256):
        return _result("INVALID_ENVELOPE")
    if (any(type(m) is not dict or set(m) != {"role", "content"}
            or type(m["content"]) is not str for m in messages)
            or messages[0]["role"] != "system"
            or messages[-1]["role"] != "user"):
        return _result("INVALID_MESSAGE_SHAPE")
    candidates = []
    if (len(messages) >= 3 and messages[-2]["role"] == "user"
            and messages[-2]["content"].startswith(VOLATILE_HEAD + "\n")):
        candidates.append(messages[-2]["content"])
    candidates.append(messages[0]["content"])
    marker = "\n" + hypothesis_heading
    raw_layer = None
    for value in candidates:
        if value.count(marker) > 1:
            return _result("AMBIGUOUS_HYPOTHESES")
        pos = value.find(marker)
        if pos < 0:
            continue
        if raw_layer is not None:
            return _result("AMBIGUOUS_HYPOTHESES")
        start = pos + len(marker)
        while start < len(value) and value[start] in " \r\t":
            start += 1
        if len(value) - start > MAX_LAYER_CHARS:
            return _result("OVERSIZED_HYPOTHESES")
        try:
            parsed, used = json.JSONDecoder().raw_decode(value, start)
        except (TypeError, ValueError, RecursionError):
            return _result("MALFORMED_HYPOTHESES")
        if used < len(value) and value[used] not in "\n\r\t ":
            return _result("AMBIGUOUS_LAYER_BOUNDARY")
        raw_layer = (value[pos:used], parsed)
    if raw_layer is None:
        return _result("NO_TYPED_HYPOTHESES")
    fragment, values = raw_layer
    if (type(values) is not list or not 1 <= len(values) <= MAX_OFFERS
            or len(fragment) > MAX_LAYER_CHARS):
        return _result("INVALID_SELECTED_OFFERS")
    offers = []
    seen_roles, seen_ids = set(), set()
    for value in values:
        if type(value) is not dict:
            return _result("INVALID_SELECTED_OFFERS")
        role, packet_id, quotes = (value.get("role"), value.get("offer_packet_id"),
                                   value.get("verified_quotes"))
        if (type(role) is not str or role not in ROLES or role in seen_roles
                or type(packet_id) is not str or not IDENTIFIER.fullmatch(packet_id)
                or packet_id in seen_ids or type(quotes) is not list
                or len(quotes) > MAX_QUOTES):
            return _result("INVALID_SELECTED_OFFERS")
        seen_roles.add(role)
        seen_ids.add(packet_id)
        valid = 0
        for quote in quotes:
            if type(quote) is not dict:
                return _result("INVALID_SELECTED_QUOTES")
            ref, body = quote.get("source_ref"), quote.get("text")
            if (type(body) is not str or not 1 <= len(body) <= 8192
                    or type(ref) is not dict
                    or type(ref.get("source_id")) is not str
                    or type(ref.get("sha256")) is not str
                    or re.fullmatch(r"[0-9a-f]{64}", ref["sha256"]) is None
                    or not 1 <= len(ref["source_id"]) <= 256
                    or quote.get("verification") not in ("EXACT_SOURCE_SUBSTRING_ONLY",
                                                         "EXACT_SOURCE_SENTENCES_POINTED_BY_QUOTE")
                    or type(ref.get("char_start")) is not int
                    or type(ref.get("char_end")) is not int
                    or ref["char_start"] < 0 or ref["char_end"] <= ref["char_start"]
                    or ref["char_end"] - ref["char_start"] != len(body)):
                return _result("INVALID_SELECTED_QUOTES")
            valid += 1
        offers.append({"role": role, "packet_id": packet_id,
                       "rendered_quote_count": valid})
    # Demand the entire exact selected-hypothesis JSON slice in the actual
    # native-rendered prompt, not loose IDs in unrelated old/user messages.
    if fragment not in rendered_prompt:
        return _result("HYPOTHESES_NOT_IN_NATIVE_TEMPLATE")
    if any(o["rendered_quote_count"] == 0 for o in offers):
        return _result("RENDERED_WITH_UNQUOTED_OFFER", offers)
    return _result("RENDERED_WITH_QUOTES", offers)
