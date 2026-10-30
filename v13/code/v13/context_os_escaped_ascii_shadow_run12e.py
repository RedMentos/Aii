"""Run12E isolated Context OS exact-quote SHADOW candidate.

Existing Context OS uses an ASCII double-quote regex that can split an escaped
literal such as "use \\"blue\\" key" into two partial spans. An extractive
summary can then lose the middle literal. This candidate refuses compression
for ambiguous backslash-escaped ASCII quotes; production context_os.py is
untouched and this module has no Runtime consumer or activation authority.
"""
from __future__ import annotations

from . import context_os

REVISION = "v13-contextos-escaped-ascii-quote-shadow-run12e-v1"
AUTHORITY = "SHADOW_ONLY_NO_RUNTIME_CONSUMER"


def escaped_ascii_quote_offsets(text):
    """Return quote offsets preceded by an odd count of backslashes.

    Odd parity means the quote is escaped in ordinary string-like syntax;
    even parity is a literal delimiter. This is deliberately conservative:
    there is no attempt to infer the user's intended language or quote grammar.
    """
    if type(text) is not str:
        raise TypeError("TEXT_REQUIRED")
    offsets = []
    for i, char in enumerate(text):
        if char != '"':
            continue
        backslashes = 0
        j = i - 1
        while j >= 0 and text[j] == "\\":
            backslashes += 1
            j -= 1
        if backslashes % 2:
            offsets.append(i)
    return tuple(offsets)


def compress_shadow(text, cap):
    """Never compress ambiguous escaped quotes; otherwise delegate exactly."""
    offsets = escaped_ascii_quote_offsets(text)
    if offsets:
        return {
            "revision": REVISION, "authority": AUTHORITY,
            "text": text, "spans": context_os.exact_spans(text),
            "ok": False, "reason": "ESCAPED_ASCII_QUOTE_RAW",
            "escaped_quote_offsets": offsets,
        }
    output, spans, ok = context_os.compress(text, cap)
    return {
        "revision": REVISION, "authority": AUTHORITY,
        "text": output, "spans": spans, "ok": ok,
        "reason": "DELEGATED_UNCHANGED",
        "escaped_quote_offsets": (),
    }
