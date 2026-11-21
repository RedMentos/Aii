"""Reject ambiguous bare year-month forms in the narrow arithmetic reflex.

The parser intentionally remains a two-integer/one-operator evaluator. This
overlay only prevents a common date-shaped false positive such as 2026-11 or
"What is 2026/11?" from being rendered as subtraction/division. Explicit
"calculate" / "berechne" prefixes remain eligible arithmetic requests.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

SOURCE_ARITHMETIC_GIT_BLOB = "b721b769157b3df3936752419c5b93bed78bc347"

PATTERN_ANCHOR = (
    b"_EXPRESSION = re.compile(r\"([+-]?\\d{1,8})\\s*([+\\-*/])\\s*([+-]?\\d{1,8})\")\n"
)
FUNCTION_ANCHOR = (
    b"    if type(text) is not str or len(text) > 96:\n"
    b"        return None\n"
    b"    match = _PATTERN.fullmatch(text)\n"
)


def git_blob_sha1(raw: bytes) -> str:
    header = b"blob " + str(len(raw)).encode("ascii") + b"\0"
    return hashlib.sha1(header + raw).hexdigest()


def apply_staged_arithmetic(code_dir: Path, raw: bytes) -> bytes:
    code_dir = Path(code_dir).resolve(strict=True)
    source = code_dir / "v13" / "arithmetic_reflex.py"
    if source.is_symlink() or not source.is_file():
        raise ValueError("frozen arithmetic_reflex.py missing or unsafe")
    if git_blob_sha1(source.read_bytes()) != SOURCE_ARITHMETIC_GIT_BLOB:
        raise ValueError("frozen arithmetic source changed; review a new overlay")
    if raw.count(PATTERN_ANCHOR) != 1 or raw.count(FUNCTION_ANCHOR) != 1:
        raise ValueError("arithmetic date-guard anchors changed")
    if b"_YEAR_MONTH = re.compile(" in raw:
        raise ValueError("arithmetic date guard already present")

    year_month = (
        b"_YEAR_MONTH = re.compile(\n"
        b"    r\"\\s*(?:(?:what\\s+is|what's|was\\s+ist)\\s+)?(?:19|20|21)\\d{2}\\s*[-/]\\s*\\d{1,2}\\s*[?=]?\\s*\",\n"
        b"    re.IGNORECASE,\n"
        b")\n"
    )
    result = raw.replace(PATTERN_ANCHOR, PATTERN_ANCHOR + year_month, 1)
    guarded = (
        b"    if type(text) is not str or len(text) > 96:\n"
        b"        return None\n"
        b"    if _YEAR_MONTH.fullmatch(text):\n"
        b"        return None\n"
        b"    match = _PATTERN.fullmatch(text)\n"
    )
    result = result.replace(FUNCTION_ANCHOR, guarded, 1)
    if result.count(b"_YEAR_MONTH.fullmatch(text)") != 1:
        raise ValueError("arithmetic date guard consumer was not uniquely patched")
    compile(result, "v13/arithmetic_reflex.py", "exec")
    return result
