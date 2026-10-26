"""WP-Z2f: the WP-Z2e test of the B2 quote pointer, repeated with a B2 context budget that actually holds the old rule note.

WP-Z2e (scripts/step2_z2e_pointer_hard.py) failed for a reason outside the pointer: in 288/288 B2 offers on its hard
episodes the old kickoff note was not in B2's earlier context, because cfg b2_context_chars (768 serialized chars incl.
hypotheses) fills from the newest turn and drops the oldest. Here the same ten episodes, the same arms and decision rule,
new seeds 23-25, and b2_context_chars=1536 (existing setting, range 0..4096) in every arm. A preregistered validity check
comes first: a verdict on the pointer only if the kickoff note is in B2's context in >= 90 % of hard B2 offers per arm.
Preregistration: docs/proofs/continuation-20261026/step2-z2f-context/PREREG.md. Diagnosis only (Linux cloud, no Redmi).
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

z=_private('step2_z2e_for_z2f','scripts/step2_z2e_pointer_hard.py')
SEEDS=(23,24,25)
CONTEXT_CHARS=1536
VALID_SHARE=.90
z.SEEDS=SEEDS;z.z2b.SEEDS=SEEDS
_settings=z.settings
def settings(arm,seed):return _settings(arm,seed)|{'b2_context_chars':CONTEXT_CHARS}
z.settings=settings;z.z2b.settings=settings

def kickoff_in_context(report):
    """Hard B2 offers whose earlier context holds the whole kickoff note (exact excerpt of its full length)."""
    n=hit=0
    for row in report['rows']:
        f=z.FIX[row['fixture']]
        if f['type'] not in z.HARD_TYPES or row['variant'] not in z.B2_VARIANTS:continue
        for o in row['offers']:
            if o['role']!='B2_GIST':continue
            n+=1;hit+=len(f['history'][0]) in [x['char_end']-x['char_start'] for x in o.get('context_source_refs',[])]
    return {'offers':n,'kickoff_in_context':hit}

def run(installed,work,arm,seed):
    from v13.common import atomic_write
    summary=z.run(installed,work,arm,seed)
    report=json.loads((Path(work)/('step2_'+z.z2b.run_id(arm,seed)+'.json')).read_text())
    summary['z2f']={'b2_context_chars':CONTEXT_CHARS,'validity':kickoff_in_context(report)}
    atomic_write(Path(work)/('summary_'+z.z2b.run_id(arm,seed)+'.json'),json.dumps(summary,ensure_ascii=False,indent=2))
    return summary

def gate(runs):
    need=[(a,s) for a in z.ARMS for s in SEEDS]
    if any(k not in runs for k in need):return {'status':'INCOMPLETE','missing':[z.z2b.run_id(*k) for k in need if k not in runs]}
    share={a:sum(runs[(a,s)]['z2f']['validity']['kickoff_in_context'] for s in SEEDS)/max(1,sum(runs[(a,s)]['z2f']['validity']['offers'] for s in SEEDS)) for a in z.ARMS}
    g=z.gate(runs);g['validity']={'kickoff_in_context_share':share,'required':VALID_SHARE,'valid':all(v>=VALID_SHARE for v in share.values())}
    if not g['validity']['valid']:g['status_z2e_rule']=g['status'];g['status']='Z2F_NOT_TESTABLE'
    else:g['status']=g['status'].replace('Z2E_','Z2F_')
    return g

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--installed-home',required=True);p.add_argument('--work',required=True)
    a=p.parse_args()
    from v13.common import atomic_write
    work=Path(a.work);work.mkdir(parents=True,exist_ok=True);runs={}
    for s in SEEDS:
        for arm in z.ARMS:
            f=work/('summary_'+z.z2b.run_id(arm,s)+'.json')
            if f.exists() and 'z2f' in json.loads(f.read_text()):runs[(arm,s)]=json.loads(f.read_text());continue
            print(json.dumps({'run_start':z.z2b.run_id(arm,s)}),flush=True);runs[(arm,s)]=run(a.installed_home,work,arm,s)
    result={'gate':gate(runs),'runs':{z.z2b.run_id(*k):{'tool':v['paired_tool']['mean_utility'],'b2_rule_rate':v['z2e']['b2_rule_rate'],'validity':v['z2f']['validity']} for k,v in sorted(runs.items())}}
    atomic_write(work/'z2f_result.json',json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result['gate'],indent=1)[:4000])
if __name__=='__main__':main()
