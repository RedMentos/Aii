"""WP-Z2j: B2 picks whole earlier sources (cfg b2_quote_choices=sources) vs oldest-first sentences with a correct prompt.

WP-Z2i (scripts/step2_z2i_choices.py) met its preregistered HELP rule only through an arm later found mislabeled: the list
was oldest first while the prompt said newest first; the gain came from LONG/CONFIRM (B2 picks the kickoff sentences by
position), changed rules stayed at ~0 exact. Here: (a) oldest-first sentences with the corrected prompt (earlier_oldest),
(b) whole earlier sources, one per id, oldest first (sources) - with B2's position bias C3 then receives the kickoff and
the revision note; the recency guard turns stale values into UNKNOWN.

Ten fresh episodes, new seeds 35-37, b2_context_chars=1536, pointer with 4 slots in every arm:
  REVISED 5, TWICE 2, LONG 1, CONFIRM 2
Arms A4 (all), O4 (earlier_oldest), S4 (sources). Same replay, guard and metrics as WP-Z2i.
Preregistration: docs/proofs/continuation-20261026/step2-z2j-sources/PREREG.md. Diagnosis only (Linux cloud, no Redmi).
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ROOT/'tests')]

def _private(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

i=_private('step2_z2i_for_z2j','scripts/step2_z2i_choices.py')
h,g,z=i.h,i.g,i.z
SEEDS=(35,36,37)
CHOICES={'A4':'all','O4':'earlier_oldest','S4':'sources'}
ARMS={a:('C','pointer') for a in CHOICES}

EPISODES=[
 ('Alcor','REVISED',(85,5,True),(80,4,True),(70,6,True),[('deadline',6)]),
 ('Baham','REVISED',(60,6,True),(65,4,True),(55,5,False),[('budget',70)]),
 ('Chara','REVISED',(100,5,False),(45,4,False),(75,3,True),[('local_only',True)]),
 ('Dabih','REVISED',(90,3,True),(50,4,True),(85,3,True),[('deadline',4)]),
 ('Elnath','REVISED',(80,6,True),(75,5,True),(60,4,False),[('local_only',False)]),
 ('Fafnir','TWICE',(90,4,True),(50,6,True),(70,3,True),[('deadline',8),('deadline',2)]),
 ('Grumium','TWICE',(60,5,False),(55,6,False),(58,3,True),[('deadline',7),('deadline',2)]),
 ('Heze','LONG',(90,5,True),(70,6,True),(85,4,True),[]),
 ('Iklil','CONFIRM',(75,5,True),(70,3,True),(60,5,True),[('budget',75)]),
 ('Jishui','CONFIRM',(95,4,False),(80,4,False),(90,2,True),[('deadline',4)]),
]

FIXTURES=[h.episode(*x) for x in EPISODES]
FIX={f['id']:f for f in FIXTURES}
for m in (i,h,g):m.FIX=FIX;m.FIXTURES=FIXTURES
z.FIXTURES=FIXTURES;z.z2.FIXTURES=FIXTURES;z.FIX=FIX;z.HARD=[f['id'] for f in FIXTURES]
z.ARMS.clear();z.ARMS.update(ARMS);z.z2b.ARMS.clear()
for _arm,(_base,_) in ARMS.items():z.z2b.ARMS[_arm]={'base':_base,'query':True}
z.SEEDS=SEEDS;z.z2b.SEEDS=SEEDS;g.SEEDS=SEEDS;h.SEEDS=SEEDS;i.SEEDS=SEEDS
h.ARMS=ARMS;h.SLOTS={a:4 for a in ARMS};i.ARMS=ARMS;i.CHOICES=CHOICES;i.CANDIDATES=('O4','S4')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--installed-home',required=True);p.add_argument('--work',required=True)
    a=p.parse_args()
    from v13.common import atomic_write
    work=Path(a.work);work.mkdir(parents=True,exist_ok=True);runs={}
    for s in SEEDS:
        for arm in ARMS:
            f=work/('summary_'+z.z2b.run_id(arm,s)+'.json')
            if f.exists() and 'z2i' in json.loads(f.read_text()):runs[(arm,s)]=json.loads(f.read_text());continue
            print(json.dumps({'run_start':z.z2b.run_id(arm,s)}),flush=True);runs[(arm,s)]=i.run(a.installed_home,work,arm,s)
    gate=i.gate(runs);gate['status']=gate['status'].replace('Z2I_','Z2J_')
    result={'gate':gate,'runs':{z.z2b.run_id(*k):{'on':v['z2g']['on'],'picked_kinds':v['z2i']['picked_kinds'],'b2_rule_rate':v['z2e']['b2_rule_rate']} for k,v in sorted(runs.items())}}
    atomic_write(work/'z2j_result.json',json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result['gate'],indent=1)[:4000])
if __name__=='__main__':main()
