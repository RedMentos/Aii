#!/usr/bin/env python3
"""Opt-in, offline exact-alias auditor for *future* experiments only.

Contract v1 accepts exactly one UTF-8 JSON object with exactly one field:
    {"answer": "<one short, unambiguous atomic value>"}

Trusted experiment authors supply aliases that all mean the *same* expected
value.  MATCH means equality with one such alias after the normalization below;
it does not establish truth, semantic equivalence, or successful learning.
Unmatched, refused, qualified, and unsupported values are UNKNOWN. Malformed or
structurally ambiguous responses are INVALID. Unsupported or unsafe aliases are
INVALID_CONFIG.  All evaluated responses, including invalid ones, are bound to
the SHA-256 of their complete original bytes; no response text is printed.
Hashes are not anonymization: keep original responses and any sensitive hashes
private as required, with source-bound raw evidence preserved separately.

This intentionally narrow contract excludes punctuation and common conjunctions,
negations and hedges, even when they appear in a genuine name. It cannot prove
that trusted aliases are correct or synonymous. Use another preregistered method
for unsupported values. No production, training, past cohort, or gate uses it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata


SCHEMA = "v13-strict-answer-audit-candidate-v1"
NORMALIZATION = "nfkc-casefold-space-v1"
MAX_RAW_BYTES = 16384
MAX_VALUE_CHARS = 128
MAX_ALIASES = 32

# A limited conservative syntax filter, not a natural-language understanding
# model. These markers cannot be approved as aliases or scored as MATCH.
_DISALLOWED_WORDS = frozenset({
    "and", "or", "but", "nor", "maybe", "perhaps", "possibly", "probably",
    "uncertain", "unsure", "unknown", "unk", "none", "no", "not", "never",
    "cannot", "cant", "can't", "don't", "dont", "isn't", "isnt", "aren't",
    "arent", "won't", "wont", "unable", "refuse", "refused",
    "decline", "declined", "sorry", "unclear", "und", "oder", "aber", "nein",
    "nicht", "nie", "niemals", "unbekannt", "unsicher", "vielleicht", "keine",
    "kein", "verweigere", "verweigert",
})


class _DuplicateKey(ValueError):
    pass


def _unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise _DuplicateKey("duplicate object key")
        out[key] = value
    return out


def _reject_constant(value):
    raise ValueError("non-standard JSON constant: " + value)


def _atomic_value(text):
    """Return a narrow normalized atomic value, or None for unsupported text."""
    if not isinstance(text, str) or not text or len(text) > MAX_VALUE_CHARS:
        return None
    # Check before normalization as some format characters can otherwise vanish.
    if any(unicodedata.category(char).startswith("C") for char in text):
        return None
    value = unicodedata.normalize("NFKC", text).casefold()
    # Only letters, marks, numbers, ordinary spaces, apostrophes, and hyphens.
    # In particular, punctuation cannot hide an additional sentence or list.
    for char in value:
        if char in " '-":
            continue
        if unicodedata.category(char)[0] not in ("L", "M", "N"):
            return None
    value = " ".join(word for word in value.split(" ") if word)
    if not value or len(value) > MAX_VALUE_CHARS:
        return None
    # A hyphen must not be usable to hide a negation or a second choice.
    if any(word in _DISALLOWED_WORDS for word in value.replace("-", " ").split(" ")):
        return None
    # Standalone punctuation is not an atomic answer.
    if not any(unicodedata.category(char)[0] in ("L", "N") for char in value):
        return None
    return value


def _aliases(aliases):
    if not isinstance(aliases, (list, tuple)) or not 1 <= len(aliases) <= MAX_ALIASES:
        raise ValueError("aliases must be a nonempty, bounded list or tuple")
    values = [_atomic_value(alias) for alias in aliases]
    if any(value is None for value in values):
        raise ValueError("unsupported or non-atomic alias")
    if len(set(values)) != len(values):
        raise ValueError("aliases are duplicated after normalization")
    canonical = json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return values, hashlib.sha256(canonical).hexdigest()


def _evaluate(raw, raw_sha256, raw_size, aliases):
    result = {
        "schema": SCHEMA,
        "normalization": NORMALIZATION,
        "raw_sha256": raw_sha256,
        "raw_size_bytes": raw_size,
        "aliases_sha256": None,
        "status": "INVALID",
        "reason": None,
    }
    try:
        values, result["aliases_sha256"] = _aliases(aliases)
    except ValueError:
        result.update(status="INVALID_CONFIG", reason="invalid_aliases")
        return result
    if raw is None or raw_size > MAX_RAW_BYTES:
        result["reason"] = "response_too_large"
        return result
    try:
        decoded = raw.decode("utf-8", errors="strict")
        obj = json.loads(decoded, object_pairs_hook=_unique_pairs,
                         parse_constant=_reject_constant)
    except (UnicodeDecodeError, ValueError, RecursionError):
        result["reason"] = "invalid_json_or_utf8"
        return result
    if not isinstance(obj, dict) or set(obj) != {"answer"} or not isinstance(obj["answer"], str):
        result["reason"] = "invalid_response_shape"
        return result
    normalized = _atomic_value(obj["answer"])
    if normalized is not None and normalized in values:
        result.update(status="MATCH", reason="exact_normalized_alias")
    else:
        result.update(status="UNKNOWN", reason="unmatched_or_unsupported_answer")
    return result


def audit(raw, aliases):
    """Explicit pure API. ``raw`` is the complete model output as bytes."""
    if not isinstance(raw, bytes):
        raise TypeError("raw must be bytes")
    sha = hashlib.sha256(raw).hexdigest()
    return _evaluate(raw if len(raw) <= MAX_RAW_BYTES else None, sha, len(raw), aliases)


def _read_stdin_and_hash(stream):
    """Bound stored bytes while hashing the entire input, including overflow."""
    digest = hashlib.sha256()
    kept = bytearray()
    size = 0
    while True:
        chunk = stream.read(65536)
        if not chunk:
            break
        digest.update(chunk)
        size += len(chunk)
        if len(kept) <= MAX_RAW_BYTES:
            kept.extend(chunk[:MAX_RAW_BYTES + 1 - len(kept)])
    return bytes(kept) if size <= MAX_RAW_BYTES else None, digest.hexdigest(), size


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enable", action="store_true", help="explicitly run the offline candidate")
    parser.add_argument("--alias", action="append", default=[], help="trusted atomic alias; repeat for synonyms")
    args = parser.parse_args(argv)
    if not args.enable:
        print(json.dumps({"schema": SCHEMA, "status": "DISABLED"}, sort_keys=True))
        return 0
    raw, digest, size = _read_stdin_and_hash(sys.stdin.buffer)
    result = _evaluate(raw, digest, size, args.alias)
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 0 if result["status"] in ("MATCH", "UNKNOWN") else 2


if __name__ == "__main__":
    raise SystemExit(main())
