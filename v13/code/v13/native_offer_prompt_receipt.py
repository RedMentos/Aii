"""Bounded no-text evidence of selected C4 offers in the native C3 template.

Checks the CURRENT typed HYPOTHESES layer after ContextOS and prompt reduction
against the actual /apply-template text. Does not prove source truth, token
attention, semantic use or native latent exchange. HTTP transport is separate.
"""
from __future__ import annotations

import hashlib
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
TOKEN_SPAN_REVISION = "v13.native-prompt-token-span-receipt/1"
MAX_NATIVE_TOKENS = 32768
MAX_NATIVE_PIECE_BYTES = 2_000_000
TEXT_FIELD = re.compile(r'"text"\s*:\s*')


def _result(status, offers=()):
    return {"revision": REVISION, "status": status, "offers": list(offers),
            "native_template_rendered": status == "RENDERED_WITH_QUOTES",
            "source_span_revalidated_here": False,
            "native_semantic_use_proven": False,
            "learned_latent_exchange_proven": False}



def _token_span_failure(status, token_count=None):
    return {"revision": TOKEN_SPAN_REVISION, "status": status,
            "token_count": token_count,
            "leading_added_special_token_count": None, "offers": []}


def _piece_bytes(value):
    if type(value) is str:
        try:
            return value.encode("utf-8")
        except UnicodeEncodeError:
            return None
    if type(value) is list and len(value) <= MAX_NATIVE_PIECE_BYTES:
        if any(type(item) is not int or not 0 <= item <= 255 for item in value):
            return None
        return bytes(value)
    return None


def _native_token_spans(rendered_prompt, fragment, json_offset, raw_json,
                        quote_records, token_pieces):
    """Map exact serialized source-quote strings onto pinned native token pieces.

    llama.cpp's /tokenize with_pieces=true returns rendered special-token pieces
    and byte arrays for partial UTF-8. The only permitted extra prefix is the
    single token inserted by add_special=true (normally BOS). The remaining
    pieces must reconstruct the exact /apply-template prompt byte-for-byte.
    """
    if (type(token_pieces) is not list or not 1 <= len(token_pieces) <= MAX_NATIVE_TOKENS
            or type(rendered_prompt) is not str or len(rendered_prompt) > MAX_TEMPLATE_CHARS
            or type(fragment) is not str or type(raw_json) is not str
            or type(json_offset) is not int or json_offset < 0):
        return _token_span_failure("INVALID_TOKEN_PIECE_ENVELOPE")

    ids, pieces = [], []
    total_piece_bytes = 0
    for row in token_pieces:
        if type(row) is not dict or set(row) != {"id", "piece"}:
            return _token_span_failure("INVALID_TOKEN_PIECE_ROW", len(token_pieces))
        ident = row["id"]
        if type(ident) is not int or not 0 <= ident <= 1_000_000:
            return _token_span_failure("INVALID_TOKEN_ID", len(token_pieces))
        piece = _piece_bytes(row["piece"])
        if piece is None:
            return _token_span_failure("INVALID_TOKEN_PIECE_BYTES", len(token_pieces))
        total_piece_bytes += len(piece)
        if total_piece_bytes > MAX_NATIVE_PIECE_BYTES:
            return _token_span_failure("TOKEN_PIECE_BYTES_EXCEEDED", len(token_pieces))
        ids.append(ident)
        pieces.append(piece)

    prompt_bytes = rendered_prompt.encode("utf-8")
    all_piece_bytes = b"".join(pieces)
    if all_piece_bytes == prompt_bytes:
        prefix_count = 0
        if pieces and not pieces[0] and b"".join(pieces[1:]) == prompt_bytes:
            return _token_span_failure("AMBIGUOUS_ADDED_SPECIAL_PREFIX", len(ids))
    elif pieces and pieces[0] and b"".join(pieces[1:]) == prompt_bytes:
        prefix_count = 1
    else:
        return _token_span_failure("TOKEN_PIECES_DO_NOT_RECONSTRUCT_PROMPT", len(ids))

    if rendered_prompt.count(fragment) != 1:
        return _token_span_failure("AMBIGUOUS_RENDERED_FRAGMENT", len(ids))
    fragment_char_start = rendered_prompt.find(fragment)
    raw_json_char_start = fragment_char_start + json_offset
    if (raw_json_char_start < fragment_char_start
            or raw_json_char_start + len(raw_json) > fragment_char_start + len(fragment)):
        return _token_span_failure("INVALID_JSON_FRAGMENT_OFFSETS", len(ids))

    matches = list(TEXT_FIELD.finditer(raw_json))
    if len(matches) != len(quote_records):
        return _token_span_failure("QUOTE_TEXT_FIELD_LAYOUT_MISMATCH", len(ids))
    decoder = json.JSONDecoder()
    token_ranges = []
    cursor = 0
    for piece in pieces[prefix_count:]:
        start = cursor
        cursor += len(piece)
        token_ranges.append((start, cursor))
    if cursor != len(prompt_bytes):
        return _token_span_failure("TOKEN_PIECE_LENGTH_MISMATCH", len(ids))

    grouped = {}
    for quote_index, (match, record) in enumerate(zip(matches, quote_records)):
        try:
            decoded, literal_end = decoder.raw_decode(raw_json, match.end())
        except (TypeError, ValueError, RecursionError):
            return _token_span_failure("MALFORMED_QUOTE_TEXT_FIELD", len(ids))
        if type(decoded) is not str or decoded != record.get("text"):
            return _token_span_failure("QUOTE_TEXT_FIELD_VALUE_MISMATCH", len(ids))
        literal_start = match.end()
        prompt_char_start = raw_json_char_start + literal_start
        prompt_char_end = raw_json_char_start + literal_end
        if (prompt_char_start < 0 or prompt_char_end > len(rendered_prompt)
                or prompt_char_end <= prompt_char_start):
            return _token_span_failure("QUOTE_TEXT_FIELD_OFFSETS_INVALID", len(ids))
        prompt_byte_start = len(rendered_prompt[:prompt_char_start].encode("utf-8"))
        prompt_byte_end = len(rendered_prompt[:prompt_char_end].encode("utf-8"))
        literal_bytes = raw_json[literal_start:literal_end].encode("utf-8")
        if prompt_bytes[prompt_byte_start:prompt_byte_end] != literal_bytes:
            return _token_span_failure("QUOTE_PROMPT_BYTE_MISMATCH", len(ids))

        overlapping = [i for i, (start, end) in enumerate(token_ranges)
                       if end > start and end > prompt_byte_start and start < prompt_byte_end]
        if not overlapping:
            return _token_span_failure("QUOTE_HAS_NO_NATIVE_TOKENS", len(ids))
        first, last = overlapping[0], overlapping[-1]
        if not (token_ranges[first][0] <= prompt_byte_start < token_ranges[first][1]
                and token_ranges[last][0] < prompt_byte_end <= token_ranges[last][1]):
            return _token_span_failure("QUOTE_TOKEN_BOUNDARY_MISMATCH", len(ids))
        # Invisible tokens inside or exactly on a quote boundary make attribution ambiguous.
        for start, end in token_ranges:
            if start == end and prompt_byte_start <= start <= prompt_byte_end:
                return _token_span_failure("ZERO_WIDTH_TOKEN_INSIDE_QUOTE_SPAN", len(ids))

        ref = record["source_ref"]
        token_start = prefix_count + first
        token_end = prefix_count + last + 1
        token_slice = ids[token_start:token_end]
        span = {
            "quote_index": quote_index,
            "source_sha256": ref["sha256"],
            "source_char_start": ref["char_start"],
            "source_char_end": ref["char_end"],
            "prompt_byte_start": prompt_byte_start,
            "prompt_byte_end": prompt_byte_end,
            "token_start": token_start,
            "token_end_exclusive": token_end,
            "token_count": token_end - token_start,
            "first_token_byte_start": prompt_byte_start - token_ranges[first][0],
            "last_token_byte_end": prompt_byte_end - token_ranges[last][0],
            "token_ids_sha256": hashlib.sha256(
                json.dumps(token_slice, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        }
        key = (record["role"], record["packet_id"])
        grouped.setdefault(key, []).append(span)

    offers = [{"role": role, "packet_id": packet_id, "quote_spans": spans}
              for (role, packet_id), spans in grouped.items()]
    return {
        "revision": TOKEN_SPAN_REVISION,
        "status": "VERIFIED",
        "token_count": len(ids),
        "leading_added_special_token_count": prefix_count,
        "token_ids_sha256": hashlib.sha256(
            json.dumps(ids, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "offers": offers,
    }


def inspect(messages, rendered_prompt, hypothesis_heading, token_pieces=None):
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
        raw_layer = (value[pos:used], parsed, value[start:used], start - pos)
    if raw_layer is None:
        return _result("NO_TYPED_HYPOTHESES")
    fragment, values, raw_json, json_offset = raw_layer
    if (type(values) is not list or not 1 <= len(values) <= MAX_OFFERS
            or len(fragment) > MAX_LAYER_CHARS):
        return _result("INVALID_SELECTED_OFFERS")
    offers = []
    quote_records = []
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
            quote_records.append({"role": role, "packet_id": packet_id,
                                  "text": body, "source_ref": ref})
        offers.append({"role": role, "packet_id": packet_id,
                       "rendered_quote_count": valid})
    # Demand the entire exact selected-hypothesis JSON slice in the actual
    # native-rendered prompt, not loose IDs in unrelated old/user messages.
    if fragment not in rendered_prompt:
        return _result("HYPOTHESES_NOT_IN_NATIVE_TEMPLATE")
    if any(o["rendered_quote_count"] == 0 for o in offers):
        return _result("RENDERED_WITH_UNQUOTED_OFFER", offers)
    result = _result("RENDERED_WITH_QUOTES", offers)
    if token_pieces is not None:
        result["native_prompt_token_span_receipt"] = _native_token_spans(
            rendered_prompt, fragment, json_offset, raw_json, quote_records, token_pieces)
    return result
