"""Run198 Context OS SHADOW-only candidate: refuse lossy unmatched inline-code compression.

This wraps the frozen ContextOS compress function without modifying Runtime or
ContextOS ACTIVE. The wrapper is opt-in to explicit offline tests only.
"""
import re
from v13 import context_os as C


def unsafe_inline_delimiters(text):
    """True if a Markdown backtick span is incomplete or not understood by v1.

    Ignore escaped backticks; ignore complete fenced blocks (their exact source
    is already pinned by ContextOS). Treat non-single inline delimiter lengths
    conservatively: v1's CODE regex only understands single inline backticks.
    """
    if not isinstance(text, str):
        raise TypeError('text must be str')
    if text.count('```') % 2:
        return True
    # Mask fenced code; its internal backticks are literal, not inline markup.
    without_fences = re.sub(r'```[\s\S]*?```', '', text)
    runs = []
    valid = set()
    for match in re.finditer(r'(?<!\\)`[^`\n]+`', without_fences):
        valid.add(match.start())
        valid.add(match.end()-1)
    i = 0
    while i < len(without_fences):
        if without_fences[i] != '`':
            i += 1
            continue
        # A backslash escapes the backtick when preceded by an odd number of backslashes.
        j = i - 1
        while j >= 0 and without_fences[j] == '\\':
            j -= 1
        if (i - 1 - j) % 2:
            i += 1
            continue
        end = i
        while end < len(without_fences) and without_fences[end] == '`':
            end += 1
        runs.append((i, end-i))
        i = end
    # v1 only preserves paired single-inline delimiters. A multi-run is raw.
    return any(n != 1 or pos not in valid for pos, n in runs) or len(runs) % 2 != 0


def compress_candidate(text, cap):
    if unsafe_inline_delimiters(text):
        return text, C.exact_spans(text), False
    return C.compress(text, cap)