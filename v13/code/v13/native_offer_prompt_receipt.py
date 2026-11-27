"""Bounded no-text evidence of selected C4 quotes in the exact native C3 prompt.

The receipt maps serialized UTF-8 quote bytes to llama.cpp token IDs only when
/tokenize?with_pieces=true reconstructs the exact post-admission prompt and the
content-token IDs occur as one unique contiguous subsequence in the add-special
prefill. It does not prove attention, semantic use or learned latent exchange.
"""
from __future__ import annotations

import hashlib
import json
import re

REVISION = "v13.native-offer-prompt-receipt/2"
LEGACY_REVISION = "v13.native-offer-prompt-receipt/1"
TOKENIZER_API = "llama.cpp-server /tokenize with_pieces=true, add_special=false, parse_special=true"
TOKENIZER_API_REVISION = "b29c606e28a01b1bc8c1351026a0fa6e616bf6c4"
MAX_TEMPLATE_CHARS = 2_000_000
MAX_TEMPLATE_BYTES = 2_000_000
MAX_LAYER_CHARS = 131_072
MAX_OFFERS = 2
MAX_QUOTES = 8
MAX_NATIVE_TOKENS = 16_384
IDENTIFIER = re.compile(r"[A-Za-z0-9_.:-]{1,160}\Z", re.ASCII)
VOLATILE_HEAD = "Context for the next message (reference material, not a question):"
ROLES = ("B1_DETAIL", "B2_GIST")


def _sha256(value):
    return hashlib.sha256(value).hexdigest()


def _json_sha256(value):
    return _sha256(json.dumps(value, separators=(",", ":")).encode("utf-8"))


def _result(status, offers=()):
    return {
        "revision": REVISION,
        "status": status,
        "offers": list(offers),
        "native_template_rendered": status == "RENDERED_WITH_QUOTES",
        "source_span_revalidated_here": False,
        "native_semantic_use_proven": False,
        "learned_latent_exchange_proven": False,
        "native_tokenizer_api": TOKENIZER_API,
        "native_tokenizer_api_revision": TOKENIZER_API_REVISION,
        "native_token_span_method": "UTF8_BYTE_PIECE_RECONSTRUCTION_AND_UNIQUE_PREFILL_SUBSEQUENCE",
        "native_token_spans_verified": False,
        "native_token_spans_status": "NOT_ATTEMPTED",
        "native_token_span_semantic_use_proven": False,
    }


def _skip_space(text, pos):
    while pos < len(text) and text[pos] in " \r\n\t":
        pos += 1
    return pos


def _array_object_spans(text, array_start, expected_count):
    """Return exact JSON object character spans for one bounded array."""
    if type(array_start) is not int or not 0 <= array_start < len(text) or text[array_start] != "[":
        return None
    decoder = json.JSONDecoder()
    pos = array_start + 1
    spans = []
    while True:
        pos = _skip_space(text, pos)
        if pos >= len(text):
            return None
        if text[pos] == "]":
            pos += 1
            break
        start = pos
        try:
            value, end = decoder.raw_decode(text, pos)
        except (TypeError, ValueError, RecursionError):
            return None
        if type(value) is not dict or end <= start:
            return None
        spans.append((start, end))
        if len(spans) > expected_count:
            return None
        pos = _skip_space(text, end)
        if pos < len(text) and text[pos] == ",":
            pos += 1
            continue
        if pos < len(text) and text[pos] == "]":
            pos += 1
            break
        return None
    if len(spans) != expected_count:
        return None
    # The same parser is used for nested verified_quotes arrays inside an object;
    # the enclosing object may legitimately contain fields after the array.
    return spans


def _quote_object_spans(object_text, quote_values):
    """Find each exact JSON quote.text literal inside verified_quotes only."""
    key = '"verified_quotes"'
    if object_text.count(key) != 1:
        return None
    key_pos = object_text.find(key)
    colon = object_text.find(":", key_pos + len(key))
    if colon < 0:
        return None
    array_start = _skip_space(object_text, colon + 1)
    quote_objects = _array_object_spans(object_text, array_start, len(quote_values))
    if quote_objects is None:
        return None
    spans = []
    for quote_value, (quote_start, quote_end) in zip(quote_values, quote_objects):
        if type(quote_value) is not dict or type(quote_value.get("text")) is not str:
            return None
        literal = json.dumps(quote_value["text"], ensure_ascii=False)
        raw_quote = object_text[quote_start:quote_end]
        positions = []
        cursor = 0
        while True:
            at = raw_quote.find(literal, cursor)
            if at < 0:
                break
            prefix = raw_quote[:at]
            if re.search(r'"text"\s*:\s*$', prefix):
                positions.append(at)
            cursor = at + max(1, len(literal))
        if len(positions) != 1:
            return None
        start = quote_start + positions[0]
        spans.append((start, start + len(literal)))
    return spans


def inspect(messages, rendered_prompt, hypothesis_heading):
    """Return source-bound offer and serialized quote byte ranges, never text."""
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
    # A repeated fragment would make byte offsets ambiguous even if the same
    # packet IDs appeared in more than one place in the rendered prompt.
    if rendered_prompt.count(fragment) == 0:
        return _result("HYPOTHESES_NOT_IN_NATIVE_TEMPLATE")
    if rendered_prompt.count(fragment) != 1:
        return _result("HYPOTHESES_DUPLICATED_IN_NATIVE_TEMPLATE")
    fragment_char_start = rendered_prompt.find(fragment)
    array_start = fragment.find("[")
    object_spans = _array_object_spans(fragment, array_start, len(values))
    if object_spans is None:
        return _result("OFFER_OBJECT_BYTE_SPANS_UNAVAILABLE")
    prompt_bytes = rendered_prompt.encode("utf-8")
    if len(prompt_bytes) > MAX_TEMPLATE_BYTES:
        return _result("OVERSIZED_NATIVE_PROMPT")
    offers = []
    seen_roles, seen_ids = set(), set()
    for index, value in enumerate(values):
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
        object_start, object_end = object_spans[index]
        object_text = fragment[object_start:object_end]
        quote_spans = _quote_object_spans(object_text, quotes)
        if quote_spans is None:
            return _result("QUOTE_SPAN_MISSING_OR_AMBIGUOUS")
        absolute_object_start = fragment_char_start + object_start
        absolute_object_end = fragment_char_start + object_end
        offer_byte_start = len(rendered_prompt[:absolute_object_start].encode("utf-8"))
        offer_byte_end = len(rendered_prompt[:absolute_object_end].encode("utf-8"))
        quote_byte_spans = []
        for quote_index, (quote_start, quote_end) in enumerate(quote_spans):
            absolute_start = fragment_char_start + object_start + quote_start
            absolute_end = fragment_char_start + object_start + quote_end
            quote_byte_spans.append({
                "quote_index": quote_index,
                "byte_start": len(rendered_prompt[:absolute_start].encode("utf-8")),
                "byte_end": len(rendered_prompt[:absolute_end].encode("utf-8")),
            })
        offers.append({
            "role": role,
            "packet_id": packet_id,
            "rendered_quote_count": valid,
            "offer_byte_start": offer_byte_start,
            "offer_byte_end": offer_byte_end,
            "quote_byte_spans": quote_byte_spans,
        })
    if any(o["rendered_quote_count"] == 0 for o in offers):
        return _result("RENDERED_WITH_UNQUOTED_OFFER", offers)
    result = _result("RENDERED_WITH_QUOTES", offers)
    result["native_prompt_utf8_bytes"] = len(prompt_bytes)
    result["native_prompt_sha256"] = _sha256(prompt_bytes)
    return result


def _piece_bytes(piece):
    if type(piece) is str:
        return piece.encode("utf-8")
    if type(piece) is list and all(type(value) is int and 0 <= value <= 255
                                   for value in piece):
        return bytes(piece)
    return None


def _failure(receipt, status):
    result = dict(receipt)
    result["native_token_spans_verified"] = False
    result["native_token_spans_status"] = status
    result["native_token_span_semantic_use_proven"] = False
    return result


def attach_token_spans(receipt, rendered_prompt, token_rows, prefill_token_ids,
                       failure_reason=None):
    """Map exact serialized quote byte ranges to unique native prefill token spans.

    token_rows must come from /tokenize with add_special=false and with_pieces=true.
    prefill_token_ids must come from /tokenize with add_special=true for the exact
    same prompt. Any reconstruction, boundary, duplicate-subsequence or special
    token ambiguity fails closed without affecting the C3 answer.
    """
    result = dict(receipt) if type(receipt) is dict else _result("INVALID_RECEIPT")
    result["offers"] = [dict(row, quote_byte_spans=[
        dict(span) for span in row.get("quote_byte_spans", [])
    ]) for row in result.get("offers", []) if type(row) is dict]
    if result.get("status") != "RENDERED_WITH_QUOTES":
        return _failure(result, "NOT_APPLICABLE")
    if failure_reason is not None:
        return _failure(result, failure_reason)
    if (type(rendered_prompt) is not str or len(rendered_prompt) > MAX_TEMPLATE_CHARS
            or type(token_rows) is not list or not 1 <= len(token_rows) <= MAX_NATIVE_TOKENS
            or type(prefill_token_ids) is not list
            or not 1 <= len(prefill_token_ids) <= MAX_NATIVE_TOKENS + 2):
        return _failure(result, "TOKEN_PIECES_UNAVAILABLE")
    prompt_bytes = rendered_prompt.encode("utf-8")
    if (len(prompt_bytes) > MAX_TEMPLATE_BYTES
            or result.get("native_prompt_utf8_bytes") != len(prompt_bytes)
            or result.get("native_prompt_sha256") != _sha256(prompt_bytes)):
        return _failure(result, "PROMPT_HASH_OR_LENGTH_MISMATCH")
    if any(type(value) is not int or value < 0 or value > 2_147_483_647
           for value in prefill_token_ids):
        return _failure(result, "INVALID_PREFILL_TOKEN_IDS")
    if (result.get("native_prompt_tokens") is not None
            and result.get("native_prompt_tokens") != len(prefill_token_ids)):
        return _failure(result, "PREFILL_TOKEN_COUNT_MISMATCH")
    if (result.get("native_token_ids_sha256") is not None
            and result.get("native_token_ids_sha256") != _json_sha256(prefill_token_ids)):
        return _failure(result, "PREFILL_TOKEN_ID_HASH_MISMATCH")
    content_ids, token_byte_spans, pieces = [], [], []
    cursor = 0
    for row in token_rows:
        if type(row) is not dict:
            return _failure(result, "INVALID_TOKEN_PIECE_ROW")
        ident, piece = row.get("id"), _piece_bytes(row.get("piece"))
        if (type(ident) is not int or ident < 0 or ident > 2_147_483_647
                or piece is None or not piece):
            return _failure(result, "INVALID_TOKEN_PIECE_ROW")
        end = cursor + len(piece)
        if end > len(prompt_bytes):
            return _failure(result, "TOKEN_PIECE_STREAM_OVERRUN")
        content_ids.append(ident)
        pieces.append(piece)
        token_byte_spans.append((cursor, end))
        cursor = end
    if cursor != len(prompt_bytes) or b"".join(pieces) != prompt_bytes:
        return _failure(result, "TOKEN_PIECES_DO_NOT_RECONSTRUCT_PROMPT")
    if not content_ids or len(content_ids) > MAX_NATIVE_TOKENS:
        return _failure(result, "INVALID_CONTENT_TOKEN_COUNT")
    matches = [
        start for start in range(len(prefill_token_ids) - len(content_ids) + 1)
        if prefill_token_ids[start:start + len(content_ids)] == content_ids
    ]
    if len(matches) != 1:
        return _failure(result, "PREFILL_TOKEN_SUBSEQUENCE_NOT_UNIQUE")
    prefix = matches[0]
    suffix = len(prefill_token_ids) - prefix - len(content_ids)
    if prefix < 0 or suffix < 0 or prefix + suffix > 2:
        return _failure(result, "SPECIAL_TOKEN_OFFSET_AMBIGUOUS")
    start_to_token = {start: index for index, (start, _) in enumerate(token_byte_spans)}
    end_to_token = {end: index + 1 for index, (_, end) in enumerate(token_byte_spans)}
    ranges, all_exact = [], True
    for offer in result["offers"]:
        role_ranges = []
        spans = offer.get("quote_byte_spans")
        if type(spans) is not list or not 1 <= len(spans) <= MAX_QUOTES:
            return _failure(result, "QUOTE_SPAN_MISSING_OR_AMBIGUOUS")
        for span in spans:
            if type(span) is not dict:
                return _failure(result, "QUOTE_SPAN_MISSING_OR_AMBIGUOUS")
            byte_start, byte_end = span.get("byte_start"), span.get("byte_end")
            if (type(byte_start) is not int or type(byte_end) is not int
                    or not 0 <= byte_start < byte_end <= len(prompt_bytes)):
                return _failure(result, "QUOTE_BYTE_SPAN_INVALID")
            content_start = start_to_token.get(byte_start)
            content_end = end_to_token.get(byte_end)
            if (content_start is None or content_end is None
                    or content_end <= content_start):
                return _failure(result, "PARTIAL_TOKEN_BOUNDARY")
            token_start, token_end = prefix + content_start, prefix + content_end
            token_ids = prefill_token_ids[token_start:token_end]
            if token_ids != content_ids[content_start:content_end]:
                return _failure(result, "PREFILL_TOKEN_SPAN_MISMATCH")
            mapped = {
                "quote_index": span.get("quote_index"),
                "byte_start": byte_start,
                "byte_end": byte_end,
                "token_start": token_start,
                "token_end": token_end,
                "token_count": token_end - token_start,
                "token_ids_sha256": _json_sha256(token_ids),
                "token_boundary_exact": True,
                "status": "EXACT",
            }
            role_ranges.append((token_start, token_end))
            span.update(mapped)
        ranges.extend((start, end, offer.get("role"), offer.get("packet_id"))
                      for start, end in role_ranges)
    ordered = sorted(ranges)
    for previous, current in zip(ordered, ordered[1:]):
        if current[0] < previous[1]:
            all_exact = False
    if not all_exact:
        return _failure(result, "OVERLAPPING_TOKEN_SPANS")
    result.update({
        "native_token_spans_verified": True,
        "native_token_spans_status": "VERIFIED_EXACT",
        "native_token_spans_prompt_sha256": _sha256(prompt_bytes),
        "native_token_spans_piece_stream_sha256": _sha256(b"".join(pieces)),
        "native_token_spans_content_tokens": len(content_ids),
        "native_token_spans_prefill_tokens": len(prefill_token_ids),
        "native_token_spans_special_prefix_tokens": prefix,
        "native_token_spans_special_suffix_tokens": suffix,
        "native_token_spans_content_token_ids_sha256": _json_sha256(content_ids),
        "native_token_spans_prefill_token_ids_sha256": _json_sha256(prefill_token_ids),
        "native_tokenizer_api": TOKENIZER_API,
        "native_tokenizer_api_revision": TOKENIZER_API_REVISION,
        "native_token_span_semantic_use_proven": False,
    })
    return result
