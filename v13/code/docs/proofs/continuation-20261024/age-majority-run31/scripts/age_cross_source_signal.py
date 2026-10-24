"""V13 WP-Z8: independent repeated-case cross-source disagreement feature (SHADOW).

No self-error, model confidence, labels inferred by an LLM, Age writes or authority.
Opaque source IDs and case IDs must be supplied by an independently audited
provenance layer; this module cannot establish that sources are independent.
"""
from collections import defaultdict
import math

SCHEMA='V13_AGE_CROSS_SOURCE_SHADOW_V1'
MIN_QUALITY=.7
MIN_SOURCES=2
MIN_CHANGED=3
SHIFT_FRACTION=.8
MAX_RECORDS=10000


def _vote(rows):
    """One latest vote per qualified source/case; conflicting duplicates invalid."""
    if type(rows) is not list or len(rows)>MAX_RECORDS:
        raise ValueError('bounded list required')
    cases=defaultdict(dict)
    for r in rows:
        if type(r) is not dict or set(r)!={'case_id','source_id','label','source_quality'}:
            raise ValueError('closed observation schema')
        case,source=r['case_id'],r['source_id']
        if not (type(case) is str and 0<len(case)<=80 and type(source) is str and 0<len(source)<=80):
            raise ValueError('opaque IDs required')
        quality=r['source_quality'];label=r['label']
        if type(quality) not in (int,float) or not math.isfinite(quality) or not 0<=quality<=1:
            raise ValueError('invalid source quality')
        if type(label) is not int or label not in (0,1):
            raise ValueError('binary comparable label required')
        if quality<MIN_QUALITY:continue
        if source in cases[case] and cases[case][source]!=label:
            raise ValueError('conflicting duplicate source vote')
        cases[case][source]=label
    out={}
    for case,votes in cases.items():
        if len(votes)<MIN_SOURCES:continue
        values=set(votes.values())
        out[case]=next(iter(values)) if len(values)==1 else None
    return out


def assess(baseline,current):
    """Classify only consensus flips, not own model errors. No Age action."""
    base=_vote(baseline);now=_vote(current)
    shared=set(base)&set(now)
    valid=[case for case in shared if base[case] is not None and now[case] is not None]
    changed=sum(base[case]!=now[case] for case in valid)
    disputed=sum(now[case] is None for case in shared)
    fraction=changed/len(valid) if valid else 0.
    if len(valid)>=MIN_CHANGED and changed>=MIN_CHANGED and fraction>=SHIFT_FRACTION:
        status='SHIFT_CANDIDATE'
    elif disputed:
        status='NOISE_SUSPECTED'
    else:
        status='INSUFFICIENT_EVIDENCE' if len(valid)<MIN_CHANGED else 'NO_SHIFT_EVIDENCE'
    return {'schema':SCHEMA,'status':status,'qualified_cases':len(valid),
            'changed_cases':changed,'disputed_cases':disputed,
            'changed_fraction':round(fraction,4),'authority':'SHADOW_NO_AGE_ACTION',
            'source_independence_verified':False,'canonical_gate_pass':False}
