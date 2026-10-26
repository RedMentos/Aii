"""Learned second opinion for user rules (WP-UR8, 2026-10-22): a small fixed classifier, no language model.

It reads one line the user typed and estimates whether it restricts the AI (prohibition, "ask me first", or unclear) from
hashed character pieces, words, word pairs and the fixed reader's own signal words. Trained offline on known sentences only
(docs/proofs/continuation-20261022/user-rules-v8/train_second.py); weights and threshold are data (userrules_second.json).

It may only add caution: userrules.parse() asks it only when the fixed reader found no restriction in the line, and a "yes"
becomes an open question to the user about everything (UNCLEAR, reason SECOND). It never creates, changes, loosens or
removes a rule; the fixed reader stays authoritative and the user decides. Inference is plain Python (no numpy on the phone).
"""
import json
import re
import zlib
from pathlib import Path

MODEL_FILE=Path(__file__).with_name('userrules_second.json')
DIM=1<<14
_MODEL=None


def _signals(t):
    from . import userrules as U
    named={'neg':U.NET_NEG,'hold':U.NET_HOLD,'cond':U.NET_COND,'you':U.YOU,'modal':U.MODAL,'block':U.STRONG_BLOCK,'forbid':U.FORBID,
           'ask':U.ASK,'loosen':U.LOOSEN,'hedge':U.HEDGE,'reported':U.REPORTED,'first':U.FIRST_PERSON,'want':U.WANT,'q':re.compile(r'\?')}
    out=[k for k,rx in named.items() if rx.search(t)]
    if U._classes(t,U.ACTION_STEMS,U.ACTION_WORDS):out.append('act')
    if U._classes(t,U.OBJECT_STEMS,{},compound=True):out.append('obj')
    return out


def features(text):
    """Sorted feature indices of one line (binary features)."""
    from . import userrules as U
    t=U.norm(text);words=re.findall(r"[a-z0-9]+",t);keys=[]
    for w in words:
        keys.append('w:'+w);p=' '+w+' '
        for n in (3,4,5):keys+=['c:'+p[i:i+n] for i in range(max(len(p)-n+1,0))]
    keys+=['b:'+a+' '+b for a,b in zip(words,words[1:])]
    sig=_signals(t);keys+=['s:'+s for s in sig]+['s2:'+a+'+'+b for i,a in enumerate(sig) for b in sig[i+1:]]
    return sorted({zlib.crc32(k.encode())%DIM for k in keys})


def load(path=MODEL_FILE):
    global _MODEL
    if _MODEL is None or path!=MODEL_FILE:
        d=json.loads(Path(path).read_text(encoding='utf-8'))
        d['w']={int(k):v for k,v in d['weights'].items()}
        if path!=MODEL_FILE:return d
        _MODEL=d
    return _MODEL


def score(text,model=None):
    """Probability-like score in [0,1] that the line restricts the AI."""
    import math
    m=model or load();f=features(text)
    z=m['bias']+sum(m['w'].get(i,0.0) for i in f)/max(len(f),1)**0.5
    return 1/(1+math.exp(-max(min(z,40),-40)))


def suspects(text,model=None):
    m=model or load()
    return score(text,m)>=m['threshold']
