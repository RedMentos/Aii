"""WP-KL1: a learnable word channel next to the frozen Needle embedding for the external route head.

Z6c showed the linear head on frozen Needle embeddings cannot learn a boundary the human changed ("half of X" -> simple
while other arithmetic stays detail): the encoder maps those questions onto the same place. Z6d bridged it with a fixed
human word rule, which is not learning. This module gives the head a second, fixed and deterministic input view that
can carry such a boundary: hashed word unigrams, word bigrams and in-word character 4-grams of the question. Nothing
here is learned or decides a route; the head's weights on these columns are learned only from explicit human route
corrections in the existing shadow job, under the existing gates.

Layout of one feature row: [needle (L2 = 8), bias 1, lexical LEX_DIM (L2 = LEX_SCALE)]. A Needle-only head has
needle_dim + 1 rows; a head with the word channel has needle_dim + 1 + LEX_DIM rows, so the active checkpoint's shape
says which view it reads. An older Needle-only head is extended with zero rows (identical predictions) when the word
channel is switched on, so learning continues from it instead of starting over.
"""
import hashlib
import re
import numpy as np

LEX_DIM = 512      # BOOT: hashed columns; collisions are possible and measured only indirectly (bench accuracy)
LEX_SCALE = 8.     # BOOT: same L2 scale as the Needle part (learning_worker.features)
REVISION = 'kl1-hashed-words-v1'
_WORD = re.compile(r"[0-9a-zäöüß]+")


def _bucket(token):
    h = hashlib.blake2b(token.encode('utf-8'), digest_size=8).digest()
    v = int.from_bytes(h, 'little')
    return v % LEX_DIM, (1. if (v >> 63) & 1 else -1.)


def tokens(text):
    words = ['#' if w.isdigit() else w for w in _WORD.findall(text.lower())]   # numbers carry no route meaning
    out = ['w:' + w for w in words] + ['b:' + a + '_' + b for a, b in zip(words, words[1:])]
    for w in words:
        if len(w) >= 5:
            p = '<' + w + '>'; out += ['c:' + p[i:i+4] for i in range(len(p) - 3)]
    return out


def lexical(texts):
    x = np.zeros((len(texts), LEX_DIM))
    for i, t in enumerate(texts):
        for tok in tokens(t):
            j, s = _bucket(tok); x[i, j] += s
    n = np.linalg.norm(x, axis=1, keepdims=True)
    return np.where(n > 0, x / np.maximum(n, 1e-12) * LEX_SCALE, 0.)


def build(base, texts=None):
    """base: learning_worker.features(...) rows; texts given -> append the word channel."""
    if texts is None: return base
    if len(texts) != len(base): raise ValueError('Text/embedding count mismatch')
    return np.column_stack([base, lexical(texts)])


def for_head(base, texts, rows):
    """Feature rows matching a checkpoint with `rows` input rows (Needle-only or Needle + word channel)."""
    if rows == base.shape[1]: return base
    if rows == base.shape[1] + LEX_DIM: return build(base, texts)
    raise ValueError('Route head dimension does not match Needle or Needle+word features')


def extend(w, trace, rows):
    """Zero-extend an older Needle-only head to the word-channel layout (same logits on every input)."""
    if w.shape[0] == rows: return w, trace
    if w.shape[0] + LEX_DIM != rows: raise ValueError('Checkpoint dimension')
    return np.vstack([w, np.zeros((LEX_DIM, w.shape[1]))]), np.concatenate([trace, np.zeros(LEX_DIM)])


def recency_weights(n, half_life):
    """Per-example weights for chronologically ordered corrections (oldest first); 0 = all equal.

    Newer human evidence counts more, so a changed preference can win over older contradicting labels without the
    human naming the scope (Z6b: old labels blocked every candidate). Mean weight is 1, so the step budget is unchanged."""
    if not half_life or n == 0: return np.ones(n)
    age = np.arange(n)[::-1].astype(float)
    w = .5 ** (age / float(half_life))
    return w / w.mean()
