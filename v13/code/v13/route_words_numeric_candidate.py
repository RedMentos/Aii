"""Isolated C2 route-head feature ablation: numeric-literal invariance.

This module is NOT wired into the active learner. v1 learned weights must not
be reused: identical dimensions do not imply compatible feature semantics.
"""
import re
import zlib

import numpy as np

from .route_words import DIM, SCALE

REVISION = "route-words-v2-candidate-numeric-literals-crc32-dim512"
_PARTS = (("w", 1.), ("b", .7), ("c", .5))
# Complete standalone numbers: decimals, grouping, scientific exponent, %.
# Deliberately leave punctuation/operator modeling to a separate experiment.
_NUMERIC = re.compile(
    r"(?<!\w)(?:\d+(?:[.,]\d+)*|\.\d+)(?:[eE][+-]?\d+)?%?(?!\w)"
)


def tokens(text):
    # Spaces around the replacement preserve the number of operands:
    # "2+3" becomes ["#", "#"], not a single "##" token.
    masked = _NUMERIC.sub(" # ", str(text).casefold())
    return [re.sub(r"\d+", "#", part)
            for part in re.findall(r"[\w#]+", masked)]


def _grams(text):
    tok = tokens(text)
    yield from (("w", t) for t in tok)
    yield from (("b", a + " " + b) for a, b in zip(tok, tok[1:]))
    for t in tok:
        if len(t) >= 3:
            s = "^" + t + "$"
            yield from (("c", s[i:i+3]) for i in range(len(s)-2))


def vector(text):
    v = np.zeros(DIM)
    weight = dict(_PARTS)
    for kind, gram in _grams(text):
        h = zlib.crc32((kind + ":" + gram).encode("utf-8"))
        v[h % DIM] += weight[kind] * (1. if (h >> 31) & 1 else -1.)
    norm = float(np.linalg.norm(v))
    return (v / norm * SCALE if norm > 0 else v).tolist()
