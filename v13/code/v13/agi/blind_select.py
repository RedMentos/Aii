"""WP-HX4 blind selector for benches (Harness² "blind selector", research/HARNESS2_AUSWERTUNG.md).

With k > 1 outputs for the same task, the judge sees only anonymous labels and redacted texts; origins (arm, model,
variant) are sealed with a commitment hash before judging and revealed only after the pick. Two rounds in different
orders guard against position bias: if the judge picks different underlying outputs, the result is INCONSISTENT and
nothing is chosen. A judge error or an unknown label is NO_PICK, never a silent default.
"""
import random
import re
from ..common import digest,dumps

REVISION='hx4-blind-select-v1'
LABELS='ABCDEFGHIJKLMNOP'

def _redact(text,terms):
    out=str(text)
    for t in sorted({str(x) for x in terms if str(x).strip()},key=len,reverse=True):
        out=re.sub(r'(?i)(?<!\w)'+re.escape(t)+r'(?!\w)','[...]',out)
    return out

def blind_select(candidates,judge,seed,rounds=2,redact=()):
    """candidates: [{'origin': str, 'output': str}], 2..16. judge(items) -> label, items = [{'label','output'}] only."""
    k=len(candidates)
    if not 2<=k<=len(LABELS):raise ValueError(f'2..{len(LABELS)} Kandidaten')
    if rounds not in (1,2):raise ValueError('rounds 1|2')
    origins=[str(c['origin']) for c in candidates]
    if len(set(origins))!=k:raise ValueError('Herkunft muss eindeutig sein')
    texts=[_redact(c['output'],origins+list(redact)) for c in candidates]
    rng=random.Random(f'{REVISION}:{seed}');salt=f'{rng.getrandbits(64):016x}'
    order=list(range(k));rng.shuffle(order)
    orders=[order]+([order[::-1]] if rounds==2 else [])
    sealed={'orders':orders,'origins':origins,'salt':salt}
    commitment=digest(dumps(sealed))  # fixed before the judge sees anything
    picks=[];log=[]
    for ordr in orders:
        items=[{'label':LABELS[i],'output':texts[j]} for i,j in enumerate(ordr)]
        try:lab=judge([dict(x) for x in items])
        except Exception as exc:log.append({'error':type(exc).__name__});picks.append(None);continue
        lab=str(lab).strip().upper() if lab is not None else None
        idx=LABELS.index(lab) if lab and len(lab)==1 and lab in LABELS[:k] else None
        picks.append(None if idx is None else ordr[idx]);log.append({'label':lab})
    if any(p is None for p in picks):status,pick='NO_PICK',None
    elif len(set(picks))>1:status,pick='INCONSISTENT',None
    else:status,pick='PICKED',picks[0]
    return {'revision':REVISION,'status':status,'pick_index':pick,'pick_origin':None if pick is None else origins[pick],
            'commitment':commitment,'reveal':sealed,'rounds':log,'k':k}

def verify(result):
    """Recompute the commitment from the revealed mapping (for audit of a stored result)."""
    return digest(dumps(result['reveal']))==result['commitment']
