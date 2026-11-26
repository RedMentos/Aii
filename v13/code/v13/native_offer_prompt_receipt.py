"""Bounded no-text evidence of selected C4 offers in the native C3 template.

Checks the CURRENT typed HYPOTHESES layer after ContextOS and prompt reduction
against the exact /apply-template text. Character spans are bound to the full
rendered-prompt digest; the runner separately binds that digest to the native
prompt/tokenizer request. This does not prove attention, semantic use or latent
exchange.
"""
from __future__ import annotations

import hashlib
import json
import re

REVISION = "v13.native-offer-prompt-receipt/2"
MAX_TEMPLATE_CHARS = 2_000_000
MAX_LAYER_CHARS = 131_072
MAX_OFFERS = 2
MAX_QUOTES = 8
IDENTIFIER = re.compile(r"[A-Za-z0-9_.:-]{1,160}\Z", re.ASCII)
VOLATILE_HEAD = "Context for the next message (reference material, not a question):"
ROLES = ("B1_DETAIL", "B2_GIST")


def _unique_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON object key")
        out[key] = value
    return out


def _reject_json_constant(_value):
    raise ValueError("non-finite JSON constant")


def _decoder():
    return json.JSONDecoder(object_pairs_hook=_unique_object,
                            parse_constant=_reject_json_constant)


def _result(status, offers=(), *, rendered_prompt_sha256=None,
            rendered_prompt_chars=None):
    result = {
        "revision": REVISION,
        "status": status,
        "offers": list(offers),
        "native_template_rendered": status in (
            "RENDERED_WITH_QUOTES", "RENDERED_WITH_UNQUOTED_OFFER"),
        "source_span_revalidated_here": False,
        "native_semantic_use_proven": False,
        "learned_latent_exchange_proven": False,
    }
    if rendered_prompt_sha256 is not None and rendered_prompt_chars is not None:
        result["rendered_prompt_sha256"] = rendered_prompt_sha256
        result["rendered_prompt_chars"] = rendered_prompt_chars
    return result


def _array_object_spans(array_text, expected_values):
    """Return exact JSON-object character spans, or None on ambiguity."""
    decoder = _decoder()
    pos = 0
    while pos < len(array_text) and array_text[pos] in " \r\n\t":
        pos += 1
    if pos >= len(array_text) or array_text[pos] != "[":
        return None
    pos += 1
    spans = []
    while True:
        while pos < len(array_text) and array_text[pos] in " \r\n\t":
            pos += 1
        if pos >= len(array_text):
            return None
        if array_text[pos] == "]":
            pos += 1
            break
        start = pos
        try:
            value, end = decoder.raw_decode(array_text, pos)
        except (TypeError, ValueError, RecursionError):
            return None
        if type(value) is not dict:
            return None
        spans.append((start, end, value))
        pos = end
        while pos < len(array_text) and array_text[pos] in " \r\n\t":
            pos += 1
        if pos >= len(array_text):
            return None
        if array_text[pos] == "]":
            pos += 1
            break
        if array_text[pos] != ",":
            return None
        pos += 1
        while pos < len(array_text) and array_text[pos] in " \r\n\t":
            pos += 1
        if pos >= len(array_text) or array_text[pos] == "]":
            return None
    while pos < len(array_text) and array_text[pos] in " \r\n\t":
        pos += 1
    if pos != len(array_text) or len(spans) != len(expected_values):
        return None
    if any(value != expected_values[index]
           for index, (_, _, value) in enumerate(spans)):
        return None
    return [(start, end) for start, end, _ in spans]


def inspect(messages, rendered_prompt, hypothesis_heading):
    """Return only hashes, bounded IDs, roles and character spans; never text."""
    if (type(messages) is not list or not 2 <= len(messages) <= 256
            or type(rendered_prompt) is not str
            or len(rendered_prompt) > MAX_TEMPLATE_CHARS
            or type(hypothesis_heading) is not str
            or not 1 <= len(hypothesis_heading) <= 256):
        return _result("INVALID_ENVELOPE")

    prompt_sha256 = hashlib.sha256(rendered_prompt.encode("utf-8")).hexdigest()
    prompt_chars = len(rendered_prompt)

    def result(status, offers=()):
        return _result(status, offers,
                       rendered_prompt_sha256=prompt_sha256,
                       rendered_prompt_chars=prompt_chars)

    if (any(type(message) is not dict
            or set(message) != {"role", "content"}
            or type(message["content"]) is not str
            for message in messages)
            or messages[0]["role"] != "system"
            or messages[-1]["role"] != "user"):
        return result("INVALID_MESSAGE_SHAPE")

    candidates = []
    if (len(messages) >= 3 and messages[-2]["role"] == "user"
            and messages[-2]["content"].startswith(VOLATILE_HEAD + "\n")):
        candidates.append(messages[-2]["content"])
    candidates.append(messages[0]["content"])
    marker = "\n" + hypothesis_heading
    raw_layer = None
    decoder = _decoder()
    for value in candidates:
        if value.count(marker) > 1:
            return result("AMBIGUOUS_HYPOTHESES")
        pos = value.find(marker)
        if pos < 0:
            continue
        if raw_layer is not None:
            return result("AMBIGUOUS_HYPOTHESES")
        start = pos + len(marker)
        while start < len(value) and value[start] in " \r\t":
            start += 1
        if len(value) - start > MAX_LAYER_CHARS:
            return result("OVERSIZED_HYPOTHESES")
        try:
            parsed, used = decoder.raw_decode(value, start)
        except (TypeError, ValueError, RecursionError):
            return result("MALFORMED_HYPOTHESES")
        if used < len(value) and value[used] not in "\n\r\t ":
            return result("AMBIGUOUS_LAYER_BOUNDARY")
        raw_layer = (value[pos:used], parsed, pos, start, used)

    if raw_layer is None:
        return result("NO_TYPED_HYPOTHESES")
    fragment, values, marker_start, array_start, array_end = raw_layer
    if (type(values) is not list or not 1 <= len(values) <= MAX_OFFERS
            or len(fragment) > MAX_LAYER_CHARS):
        return result("INVALID_SELECTED_OFFERS")

    offers = []
    seen_roles, seen_ids = set(), set()
    for value in values:
        if type(value) is not dict:
            return result("INVALID_SELECTED_OFFERS")
        role, packet_id, quotes = (
            value.get("role"), value.get("offer_packet_id"),
            value.get("verified_quotes"))
        if (type(role) is not str or role not in ROLES or role in seen_roles
                or type(packet_id) is not str or not IDENTIFIER.fullmatch(packet_id)
                or packet_id in seen_ids or type(quotes) is not list
                or len(quotes) > MAX_QUOTES):
            return result("INVALID_SELECTED_OFFERS")
        seen_roles.add(role)
        seen_ids.add(packet_id)
        valid = 0
        for quote in quotes:
            if type(quote) is not dict:
                return result("INVALID_SELECTED_QUOTES")
            ref, body = quote.get("source_ref"), quote.get("text")
            if (type(body) is not str or not 1 <= len(body) <= 8192
                    or type(ref) is not dict
                    or type(ref.get("source_id")) is not str
                    or type(ref.get("sha256")) is not str
                    or re.fullmatch(r"[0-9a-f]{64}", ref["sha256"]) is None
                    or not 1 <= len(ref["source_id"]) <= 256
                    or quote.get("verification") not in (
                        "EXACT_SOURCE_SUBSTRING_ONLY",
                        "EXACT_SOURCE_SENTENCES_POINTED_BY_QUOTE")
                    or type(ref.get("char_start")) is not int
                    or type(ref.get("char_end")) is not int
                    or ref["char_start"] < 0
                    or ref["char_end"] <= ref["char_start"]
                    or ref["char_end"] - ref["char_start"] != len(body)):
                return result("INVALID_SELECTED_QUOTES")
            valid += 1
        offers.append({"role": role, "packet_id": packet_id,
                       "rendered_quote_count": valid})

    occurrences = rendered_prompt.count(fragment)
    if occurrences == 0:
        return result("HYPOTHESES_NOT_IN_NATIVE_TEMPLATE")
    if occurrences != 1:
        return result("AMBIGUOUS_NATIVE_TEMPLATE")

    fragment_start = rendered_prompt.find(fragment)
    array_text = fragment[array_start - marker_start:array_end - marker_start]
    object_spans = _array_object_spans(array_text, values)
    if object_spans is None:
        return result("INVALID_SELECTED_OFFERS")

    array_prompt_start = fragment_start + (array_start - marker_start)
    for offer_item, (relative_start, relative_end) in zip(offers, object_spans):
        absolute_start = array_prompt_start + relative_start
        absolute_end = array_prompt_start + relative_end
        span_text = rendered_prompt[absolute_start:absolute_end]
        if (absolute_start < 0 or absolute_end > prompt_chars
                or absolute_end <= absolute_start
                or len(span_text) != relative_end - relative_start):
            return result("INVALID_SELECTED_OFFERS")
        offer_item["native_prompt_char_start"] = absolute_start
        offer_item["native_prompt_char_end"] = absolute_end
        offer_item["native_prompt_span_sha256"] = hashlib.sha256(
            span_text.encode("utf-8")).hexdigest()

    if any(offer["rendered_quote_count"] == 0 for offer in offers):
        return result("RENDERED_WITH_UNQUOTED_OFFER", offers)
    return result("RENDERED_WITH_QUOTES", offers)
