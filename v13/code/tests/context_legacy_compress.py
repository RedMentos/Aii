"""Frozen pre-Run350 ContextOS.compress algorithm for Run198/Run199 RED replay.

Only historical test code. This must not be imported by production ContextOS.
Pre-fix source SHA256: 832aaea23c3790c42720d5b7174b1a90f9ec677d60005b3424d9a93d85a8ecb2.
"""
from v13 import context_os as C


def legacy_compress_run199(text, cap):
    spans = C.exact_spans(text)
    if text.count('```') % 2:
        return text, spans, False
    if sum(len(x) for x in spans) > C.SPAN_CHARS or len(spans) > C.SPAN_MAX:
        return text, spans, False
    head = C.first_sentence(text, cap)
    missing = [x for x in spans if x not in head]
    out = '[compressed earlier turn; exact source kept] ' + head + (
        (' | exact: ' + ' ; '.join(missing)) if missing else '')
    ok = len(out) < len(text) and all(x in out for x in spans)
    return (out, spans, True) if ok else (text, spans, False)
