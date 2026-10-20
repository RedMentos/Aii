"""Isolated candidate (thread L, 2026-10-12) after `ablation_aplane_gate.py` (PARTIAL: gate too cautious).
`aplane.py` is not changed here.

Candidate gate: agreement window 100 instead of 400 (same GATE_N 50, GATE_AGREE .90); retention fails only on a clear
drop, i.e. the newest 25 comparisons agree less than GATE_AGREE - .15 (= .75), instead of "recent worse than earlier
by more than .05". Promotion, auto-demotion and the simulated user are unchanged.

PREREG (fixed before the first run), test seeds 13-17:
  standard world  = the ablation's world (3000 turns, two drops to .50 for 150 turns)
  stress world    = same, but three drops to .40 for 400 turns each (the student is unreliable for long stretches)
  PASS only if
    (a) standard: candidate > current gate in >= 4/5 seeds,
    (b) stress: candidate > always-student in >= 4/5 seeds,
    (c) stress: candidate lower than never-student (scaffold) in at most 1/5 seeds.
  Otherwise FAIL. A PASS allows changing WINDOW and the retention rule in aplane.py with tests.
Claim limit: as the ablation (synthetic agreement process, teacher assumed right).
"""
import json
import random
import sys
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v13.ablation99 import SEEDS,_mean
from v13 import aplane as AP
import ablation_aplane_gate as A

WINDOW=100;CLEAR_DROP=.15
PREREG={'schema':'APLANE_GATE_CANDIDATE_PREREG_V1','test_seeds':list(SEEDS),'window':WINDOW,'retention':'newest 25 agreement >= GATE_AGREE - .15',
        'worlds':{'standard':'ablation world','stress':'three drops to .40 for 400 turns'},
        'pass':['standard: candidate > current in >=4/5','stress: candidate > always in >=4/5','stress: candidate < never in <=1/5']}
_real=A._real_gate

def candidate_gate(store):
    with mock.patch.object(AP,'WINDOW',WINDOW):g=_real(store)
    rec=g['recent'];g['retention_pass']=rec is None or rec>=AP.GATE_AGREE-CLEAR_DROP
    g['pass']=g['n']>=AP.GATE_N and g['agreement'] is not None and g['agreement']>=AP.GATE_AGREE and g['retention_pass'];return g

def stress_world(seed):
    rng=random.Random(seed);drops=[]
    while len(drops)<3:
        s=rng.randint(800,A.T-400)
        if all(abs(s-d)>=400 for d in drops):drops.append(s)
    out=[]
    for t in range(A.T):
        acc=.4 if any(d<=t<d+400 for d in drops) else (.7+.25*min(1.,t/500))
        out.append({'teacher':rng.random()<A.P_TEACHER,'student_right':rng.random()<acc,'scaffold_right':rng.random()<A.SCAFFOLD})
    return out,drops

def run_candidate(w):
    with mock.patch.object(AP,'student_gate',candidate_gate):return A.run_arm(w,'gated')

def run():
    res={}
    for name,mk in (('standard',A.world),('stress',stress_world)):
        res[name]={}
        for s in SEEDS:
            w=mk(s);res[name][s]={'candidate':run_candidate(w),**{a:A.run_arm(w,a) for a in ('gated','always','never')}}
    P=lambda n,s,a:res[n][s][a]['primary']
    ca=sum(P('standard',s,'candidate')>P('standard',s,'gated') for s in SEEDS)
    cb=sum(P('stress',s,'candidate')>P('stress',s,'always') for s in SEEDS)
    cc=sum(P('stress',s,'candidate')<P('stress',s,'never') for s in SEEDS)
    means={n:{a:round(_mean([P(n,s,a) for s in SEEDS]),4) for a in ('candidate','gated','always','never')} for n in res}
    return {'prereg':PREREG,'test':res,'means':means,'criteria':{'standard_beats_current':ca,'stress_beats_always':cb,'stress_below_never':cc},
            'verdict':'PASS' if ca>=4 and cb>=4 and cc<=1 else 'FAIL','claim_limit':'synthetic agreement process; isolated candidate, aplane.py unchanged'}

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--prereg':
        out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(PREREG,indent=1));sys.exit(0)
    r=run();out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=1))
    print(r['verdict'],r['criteria'],r['means'])
