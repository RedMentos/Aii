"""WP-Z6i: fixed word channel for the external route head (§24.32 L11 re-open, "new human hints really learned").

Z6b/Z6c: the frozen Needle embedding does not separate "half of X" from other arithmetic questions (raw cosine .95-.98
between all question kinds), so a linear head on it cannot learn a boundary the human moves. This channel adds what the
human actually sees and names: the words. It is a fixed, deterministic hashing of word unigrams, word bigrams and
character trigrams (no model, no vocabulary to fit, no network); the head learns the weights on it from explicit human
labels like before. Digits are folded to '#', so numbers never become route evidence.
"""
import re
import zlib
import numpy as np

DIM = 512        # BOOT: hashed slots; collisions are signed so they cancel instead of adding up
SCALE = 8.        # same norm as the normalized embedding block in learning_worker.features
REVISION = 'route-words-v1-crc32-w1-b.7-c.5-dim512'
_PARTS = (('w', 1.), ('b', .7), ('c', .5))


def tokens(text):
    return [re.sub(r'\d', '#', t) for t in re.findall(r'\w+', str(text).lower())]


def _grams(text):
    tok = tokens(text)
    yield from (('w', t) for t in tok)
    yield from (('b', a + ' ' + b) for a, b in zip(tok, tok[1:]))
    for t in tok:
        if len(t) >= 3:
            s = '^' + t + '$'; yield from (('c', s[i:i+3]) for i in range(len(s) - 2))


def vector(text):
    v = np.zeros(DIM); weight = dict(_PARTS)
    for kind, g in _grams(text):
        h = zlib.crc32((kind + ':' + g).encode('utf-8')); v[h % DIM] += weight[kind] * (1. if (h >> 31) & 1 else -1.)
    n = float(np.linalg.norm(v))
    return (v / n * SCALE if n > 0 else v).tolist()
