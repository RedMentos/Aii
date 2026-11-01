"""Isolated candidate (thread L, 2026-10-12) after `ablation_latewatch.py` (SUPPORTED_SYNTHETIC with weak spots):
number parsing in `latewatch.disagreement`. `latewatch.py` is not changed here.

Two pure fixes, both independent of the synthetic generator:
  (1) thousands separators: a run like 1,234 or 12,345,678 (groups of exactly three digits) is read as an integer
      without commas; other commas stay decimal commas (2,5 -> 2.5, as now).
  (2) a number still being streamed: if the partial answer ends inside a number (last char a digit, or a digit followed
      by '.' or ','), that last number is not used for the comparison yet (the next check sees it complete).
BODY_REENTRY is left unchanged (its cost in the ablation depends on how the stream couples the flag to answer errors).

PREREG (fixed before the first run), test seeds 13-17, same generator, scoring and controls as the ablation:
  PASS only if
    (a) format stream: candidate > current rule in >= 4/5 seeds,
    (b) standard stream: candidate lower than current rule in at most 1/5 seeds,
    (c) candidate beats never, always and random (random with the candidate's cut count) in >= 4/5 seeds on both streams,
    (d) pure checks: nums('2,5')=={'2.5'}, nums('1,234')=={'1234'}, nums('12,345,678 and 3.5')=={'12345678','3.5'}, nums('is 1,290, because')=={'1290'},
        trailing number dropped for 'is 5026' and 'is 1,2' but kept for 'is 5026.' at sentence end only when followed by a space.
  Otherwise FAIL. A PASS allows integrating (1)+(2) into latewatch.py with tests.
Claim limit: as the ablation (synthetic arithmetic turns, number conflicts, BOOT char thresholds).
"""
import json
import random
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v13.ablation99 import SEEDS,_mean
from v13 import latewatch as L
import ablation_latewatch as A

PREREG={'schema':'LATEWATCH_NUMBERS_PREREG_V1','test_seeds':list(SEEDS),
        'changes':['thousands separators (groups of 3) read as integers','trailing number of a partial answer ignored until complete'],
        'pass':['format: candidate > current in >=4/5','standard: candidate < current in <=1/5','candidate beats never/always/random >=4/5 on both streams','pure checks hold']}
_THOUSANDS=re.compile(r'(?<![\d.,])\d{1,3}(?:,\d{3})+(?!\d|,\d)')
_TAIL=re.compile(r'\d[\d.,]*$')

def nums(t):
    t=_THOUSANDS.sub(lambda m:m.group(0).replace(',',''),t or '')
    return L.nums(t)

def complete(partial):
    """The partial answer without a number that may still be growing at its end."""
    return _TAIL.sub('',partial or '')

def disagreement(offer,partial,source):
    """latewatch.disagreement with (1)+(2); thresholds and BODY_REENTRY unchanged."""
    o=(offer or {}).get('offer',{});src=nums(source)
    body_new=nums(o.get('summary',''))-src;out_new=nums(complete(partial))-src
    if len(partial)>=L.MIN_CHARS and body_new and out_new and not body_new&out_new:return 'RESULT_CONFLICT'
    if len(partial)>=L.REENTRY_CHARS and o.get('needs_reentry') and o.get('quotes'):return 'BODY_REENTRY'
    return None

def pure_checks():
    return {'decimal_comma':nums('2,5')=={'2.5'},'thousands':nums('1,234')=={'1234'},
            'mixed':nums('12,345,678 and 3.5')=={'12345678','3.5'},'thousands_then_comma':nums('is 1,290, because')=={'1290'},'tail_dropped':nums(complete('is 5026'))==set(),'tail_with_separator_dropped':nums(complete('is 1,2'))==set(),
            'tail_kept_after_space':nums(complete('is 5026. Then'))=={'5026'}}

def run_seed(seed,stream):
    ts=A.turns(seed,stream);early=[i for i,t in enumerate(ts) if t['arrive']<len(t['answer'])]
    cur={i for i in early if A.rule_cut(ts[i])}
    with mock.patch.object(L,'disagreement',disagreement):cand={i for i in early if A.rule_cut(ts[i])}
    rng=random.Random(seed*11+3);rnd=set(rng.sample(early,len(cand)))
    arms={'current':cur,'candidate':cand,'never':set(),'always':set(early),'random':rnd}
    return {a:{'primary':round(_mean([A.score(t,i in c) for i,t in enumerate(ts)]),5),'cuts':len(c)} for a,c in arms.items()}

def run():
    test={st:{s:run_seed(s,st) for s in SEEDS} for st in A.PREREG['streams']}
    P=lambda st,s,a:test[st][s][a]['primary']
    ca=sum(P('format',s,'candidate')>P('format',s,'current') for s in SEEDS)
    cb=sum(P('standard',s,'candidate')<P('standard',s,'current') for s in SEEDS)
    cc={st:{a:sum(P(st,s,'candidate')>P(st,s,a) for s in SEEDS) for a in ('never','always','random')} for st in test}
    pc=pure_checks()
    ok=ca>=4 and cb<=1 and all(v>=4 for d in cc.values() for v in d.values()) and all(pc.values())
    means={st:{a:round(_mean([test[st][s][a]['primary'] for s in SEEDS]),4) for a in ('current','candidate','never','always','random')} for st in test}
    return {'prereg':PREREG,'test':test,'means':means,'criteria':{'format_beats_current':ca,'standard_worse_than_current':cb,'beats_controls':cc,'pure_checks':pc},
            'verdict':'PASS' if ok else 'FAIL','claim_limit':'synthetic arithmetic turns; isolated candidate, latewatch.py unchanged'}

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--prereg':
        out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(PREREG,indent=1));sys.exit(0)
    r=run();out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=1))
    print(r['verdict'],json.dumps(r['criteria']));print(json.dumps(r['means']))
