"""Strict no-model German list extraction candidate for operator SHADOW_ONLY.

Only one-label, comma-separated, source-exact Name integer pairs. This is
not a general parser and never invokes C3, C5, ToolStep, learning or tools.
"""
from __future__ import annotations

import json
import re

from . import listarith
from . import listarith_de_shadow_v2_candidate as german

AUTHORITY = "SHADOW_ONLY"
REVISION = "de-deterministic-source-bound-operator-auto11-v1"
LETTERS = "A-Za-zÄÖÜäöüß"
HEADER = re.compile(r"([" + LETTERS + r"]{2,24}):[ \t]*(.+)\.", re.DOTALL)
PAIR = re.compile(r"([" + LETTERS + r"]{2,40})[ \t]+([+\-−]?(?:0|[1-9][0-9]{0,5}))")


def extract(text):
    """Return typed JSON only if a complete narrow source can be proved."""
    if (not isinstance(text, str) or not text.strip()
            or len(text) > listarith.MAX_TEXT):
        raise ValueError("SOURCE_OUT_OF_SCOPE")
    trimmed = text.strip()
    question = listarith.question_part(trimmed).strip()
    if (not question or question == trimmed
            or not question.endswith("?")
            # question_part joins trailing digit-free sentences; only one
            # explicit question sentence is within this parser's contract.
            or question.count("?") != 1 or re.search(r"[.!]", question)
            or re.search(r"\d", question)):
        raise ValueError("QUESTION_BOUNDARY_OR_NUMERIC_AMBIGUOUS")
    proposal = german.propose(trimmed)
    if (proposal.get("authority") != AUTHORITY
            or proposal.get("proposal") not in ("total", "difference_max_min")):
        raise ValueError("UNSUPPORTED_OR_NEGATED_QUESTION")
    data = trimmed[:-len(question)].rstrip()
    match = HEADER.fullmatch(data)
    if match is None:
        raise ValueError("DATA_SYNTAX_OUT_OF_SCOPE")
    fields = match.group(2).split(",")
    if not 2 <= len(fields) <= 8:
        raise ValueError("PAIR_COUNT_OUT_OF_SCOPE")
    values = []
    names = set()
    for field in fields:
        item = PAIR.fullmatch(field.strip())
        if item is None:
            raise ValueError("PAIR_SYNTAX_OUT_OF_SCOPE")
        name, raw_number = item.groups()
        if name.casefold() in names:
            raise ValueError("DUPLICATE_ITEM_NAME")
        names.add(name.casefold())
        if listarith.AGGREGATE.fullmatch(name):
            raise ValueError("AGGREGATE_AS_INPUT")
        if raw_number in ("-0", "+0", "−0"):
            raise ValueError("SIGNED_ZERO_AMBIGUOUS")
        number = int(raw_number.replace("−", "-"))
        if not -999999 <= number <= 999999:
            raise ValueError("NUMBER_OUT_OF_SCOPE")
        values.append({"name": name, "number": number})
    raw = json.dumps({"values": values}, ensure_ascii=False, separators=(",", ":"))
    if len(raw.encode("utf-8")) > 8192:
        raise ValueError("TYPED_RAW_OUT_OF_SCOPE")
    return raw
