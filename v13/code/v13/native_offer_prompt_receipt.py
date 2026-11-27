"""Bounded no-text evidence of selected C4 offers in the native C3 template.

Checks the CURRENT typed HYPOTHESES layer after ContextOS and prompt reduction
against the actual /apply-template text. Token-piece mapping measures where
each offer appears in the native tokenized prompt; it does not prove attention,
semantic use, source truth or native latent exchange. HTTP transport is separate.
"""
from __future__ import annotations

import hashlib
import json
import re

REVISION = "v13.native-offer-prompt-receipt/2"
LEGACY_REVISION = "v13.native-offer-prompt-receipt/1"
MAX_TEMPLATE_CHARS = 2_000_000
MAX_LAYER_CHARS = 131_072
MAX_OFFERS = 2
MAX_QUOTES = 8
MAX_TOKEN_ROWS = 100_000
IDENTIFIER = re.compile(r"[A-Za-z0-9_.:-]{1,160}\Z", re.ASCII)
VOLATILE_HEAD = "Context for the next message (reference material, not a question):"
ROLES = ("B1_DETAIL", "B2_GIST")
MAPPED_SPAN_STATUSES = frozenset(("EXACT", "BOUNDARY_CONTEXT_INCLUDED"))


def _result(status, offers=()):
    return {"revision": REVISION, "status": status, "offers": list(offers),
            "native_template_rendered": status == "RENDERED_WITH_QUOTES",
            "native_token_spans_status": "NOT_MAPPED",
            "native_token_spans_verified": False,
            "source_span_revalidated_here": False,
            "native_semantic_use_proven": False,
            "learned_latent_exchange_proven": False}


def _array_object_spans(fragment, values):
    """Return character spans for the exact objects in the selected JSON array."""
    start = fragment.find("[")
    if start < 0:
        return None
    decoder = json.JSONDecoder()
    cursor = start + 1
    spans = []
    for expected in values:
        while cursor < len(fragment) and fragment[cursor] in " \r\n\t,":
            cursor += 1
        object_start = cursor
        try:
            parsed, cursor = decoder.raw_decode(fragment, cursor)
        except (TypeError, ValueError, RecursionError):
            return None
        if type(parsed) is not dict or parsed != expected:
            return None
        spans.append((object_start, cursor))
    while cursor < len(fragment) and fragment[cursor] in " \r\n\t":
        cursor += 1
    if cursor >= len(fragment) or fragment[cursor] != "]":
        return None
    cursor += 1
    while cursor < len(fragment) and fragment[cursor] in " \r\n\t":
        cursor += 1
    return spans if cursor == len(fragment) else None


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
    object_spans = _array_object_spans(fragment, values)
    if object_spans is None or len(object_spans) != len(values):
        return _result("INVALID_SELECTED_OFFERS")
    offers = []
    seen_roles, seen_ids = set(), set()
    for value, (object_start, object_end) in zip(values, object_spans):
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
                       "rendered_quote_count": valid,
                       "prompt_byte_start": None, "prompt_byte_end": None})
    # Demand the entire exact selected-hypothesis JSON slice in the actual
    # native-rendered prompt, not loose IDs in unrelated old/user messages.
    occurrences = rendered_prompt.count(fragment)
    if occurrences == 0:
        return _result("HYPOTHESES_NOT_IN_NATIVE_TEMPLATE")
    if occurrences != 1:
        return _result("AMBIGUOUS_NATIVE_TEMPLATE_FRAGMENT")
    fragment_char_start = rendered_prompt.find(fragment)
    for offer, (object_start, object_end) in zip(offers, object_spans):
        absolute_start = fragment_char_start + object_start
        absolute_end = fragment_char_start + object_end
        offer["prompt_byte_start"] = len(rendered_prompt[:absolute_start].encode("utf-8"))
        offer["prompt_byte_end"] = len(rendered_prompt[:absolute_end].encode("utf-8"))
    if any(o["rendered_quote_count"] == 0 for o in offers):
        return _result("RENDERED_WITH_UNQUOTED_OFFER", offers)
    return _result("RENDERED_WITH_QUOTES", offers)


def _piece_bytes(value):
    if type(value) is str:
        try:
            return value.encode("utf-8")
        except UnicodeError:
            return None
    if (type(value) is list and all(type(byte) is int and 0 <= byte <= 255
                                    for byte in value)):
        return bytes(value)
    return None


def _token_piece_offsets(rendered_prompt, token_rows):
    """Map llama-server token pieces to UTF-8 prompt byte offsets; skip one leading BOS piece."""
    if (type(rendered_prompt) is not str or len(rendered_prompt) > MAX_TEMPLATE_CHARS
            or type(token_rows) is not list or not 1 <= len(token_rows) <= MAX_TOKEN_ROWS):
        return None
    prompt_bytes = rendered_prompt.encode("utf-8")
    token_ids, pieces = [], []
    for row in token_rows:
        if type(row) is not dict or set(row) != {"id", "piece"}:
            return None
        ident = row.get("id")
        piece = _piece_bytes(row.get("piece"))
        if (type(ident) is not int or not 0 <= ident <= 0x7FFFFFFF
                or piece is None):
            return None
        token_ids.append(ident)
        pieces.append(piece)
    offsets = []
    cursor = 0
    for index, piece in enumerate(pieces):
        # /tokenize add_special=true may prepend one BOS piece that is not
        # represented in the prompt string. Only the first token may be skipped.
        if index == 0 and (not piece or prompt_bytes[:len(piece)] != piece):
            offsets.append(None)
            continue
        if not piece or prompt_bytes[cursor:cursor + len(piece)] != piece:
            return None
        offsets.append((cursor, cursor + len(piece)))
        cursor += len(piece)
    if cursor != len(prompt_bytes):
        return None
    return token_ids, offsets


def attach_token_spans(receipt, rendered_prompt, token_rows):
    """Attach only token indices/counts/hashes; never persist raw token pieces or quotes."""
    if type(receipt) is not dict or receipt.get("status") != "RENDERED_WITH_QUOTES":
        return receipt
    mapped = _token_piece_offsets(rendered_prompt, token_rows)
    if mapped is None:
        return {**receipt, "native_token_spans_status": "TOKEN_PIECES_UNAVAILABLE",
                "native_token_spans_verified": False}
    token_ids, offsets = mapped
    updated = []
    for offer in receipt.get("offers", []):
        start, end = offer.get("prompt_byte_start"), offer.get("prompt_byte_end")
        if (type(start) is not int or type(end) is not int or start < 0
                or end <= start or end > len(rendered_prompt.encode("utf-8"))):
            updated.append({**offer, "token_span": {"status": "INVALID_BYTE_RANGE"}})
            continue
        covered = [(index, span[0], span[1]) for index, span in enumerate(offsets)
                   if span is not None and span[1] > start and span[0] < end]
        if not covered:
            updated.append({**offer, "token_span": {"status": "NO_TOKEN_COVERAGE"}})
            continue
        first, last = covered[0][0], covered[-1][0]
        cover_start, cover_end = covered[0][1], covered[-1][2]
        contiguous = (all(covered[i][0] + 1 == covered[i + 1][0]
                          and covered[i][2] == covered[i + 1][1]
                          for i in range(len(covered) - 1))
                      and cover_start <= start and cover_end >= end)
        if not contiguous:
            updated.append({**offer, "token_span": {"status": "NONCONTIGUOUS_TOKEN_COVERAGE"}})
            continue
        prefix = start - cover_start
        suffix = cover_end - end
        status = "EXACT" if prefix == 0 and suffix == 0 else "BOUNDARY_CONTEXT_INCLUDED"
        ids = token_ids[first:last + 1]
        ids_raw = json.dumps(ids, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        span = {
            "status": status,
            "token_start": first,
            "token_end": last + 1,
            "token_count": last + 1 - first,
            "token_ids_sha256": hashlib.sha256(ids_raw).hexdigest(),
            "covered_byte_start": cover_start,
            "covered_byte_end": cover_end,
            "boundary_prefix_bytes": prefix,
            "boundary_suffix_bytes": suffix,
        }
        updated.append({**offer, "token_span": span})
    ranges = []
    for offer in updated:
        span = offer.get("token_span")
        if type(span) is dict and span.get("status") in MAPPED_SPAN_STATUSES:
            ranges.append((span["token_start"], span["token_end"]))
    overlap = any(max(a[0], b[0]) < min(a[1], b[1])
                  for i, a in enumerate(ranges) for b in ranges[i + 1:])
    if overlap:
        updated = [{**offer, "token_span": (
            {**offer["token_span"], "status": "OVERLAPPING_OFFER_TOKEN_SPANS"}
            if type(offer.get("token_span")) is dict
            and offer["token_span"].get("status") in MAPPED_SPAN_STATUSES
            else offer.get("token_span"))} for offer in updated]
    verified = (not overlap and len(updated) == len(receipt.get("offers", []))
                and all(type(o.get("token_span")) is dict
                        and o["token_span"].get("status") in MAPPED_SPAN_STATUSES
                        for o in updated))
    statuses = {o.get("token_span", {}).get("status") for o in updated
                if type(o.get("token_span")) is dict}
    if verified and statuses == {"EXACT"}:
        overall = "MAPPED_EXACT"
    elif verified:
        overall = "MAPPED_WITH_BOUNDARY_CONTEXT"
    elif any(status in MAPPED_SPAN_STATUSES for status in statuses):
        overall = "PARTIAL_OR_OVERLAPPING"
    else:
        overall = "UNAVAILABLE"
    return {**receipt, "offers": updated,
            "native_token_spans_status": overall,
            "native_token_spans_verified": verified,
            "native_token_span_method": "LLAMA_SERVER_TOKENIZE_WITH_PIECES"}
