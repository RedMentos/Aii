"""WP-Z2i: which sentences B2 may pick from (cfg b2_quote_choices all|earlier|earlier_oldest), four slots, recency guard on.

WP-Z2h (scripts/step2_z2h_slots.py) found more slots useless because B2 picks mostly by position: about half of all
picked ids were 1-3, the current task sentences that C3 receives anyway; only 9/178 picks on changed-rule episodes came
from the revision note. Here the choice list leaves out the current source (earlier) and also lists the newest earlier
source first (named earlier_newest in the recorded run).
Correction after the run: body_context lists earlier sources newest first, so 'earlier' already was newest first and the
recorded 'earlier_newest' arm was in fact OLDEST first, with a prompt that wrongly said 'newest first' (E4's prompt named
no order). The mode is now earlier_oldest with matching prompts; rerunning this script uses the corrected prompts.

Ten fresh episodes (never run before), new seeds 32-34, b2_context_chars=1536, pointer with 4 slots in every arm:
  REVISED 5, TWICE 2 (same rule revised twice), LONG 1, CONFIRM 2
Arms A4 (all = the WP-Z2h P4 pointer), E4 (earlier), N4 (earlier_oldest, recorded as earlier_newest). Every recorded extraction is re-decided with
the recency guard on (and off, consistency), as in WP-Z2g. Preregistration:
docs/proofs/continuation-20261026/step2-z2i-choices/PREREG.md. Diagnosis only (Linux cloud, no Redmi).
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

h=_private('step2_z2h_for_z2i','scripts/step2_z2h_slots.py')
g,z=h.g,h.z
SEEDS=(32,33,34)
CHOICES={'A4':'all','E4':'earlier','N4':'earlier_oldest'}
ARMS={a:('C','pointer') for a in CHOICES}
CONTROL='A4';CANDIDATES=('E4','N4')
TYPES=('REVISED','TWICE','LONG','CONFIRM')

EPISODES=[
 ('Hamal','REVISED',(75,5,True),(70,4,True),(60,6,True),[('deadline',6)]),
 ('Keid','REVISED',(90,4,False),(85,3,False),(55,4,True),[('budget',50)]),
 ('Mebsuta','REVISED',(100,6,True),(50,5,False),(80,4,True),[('local_only',False)]),
 ('Nashira','REVISED',(65,7,False),(60,8,False),(70,3,True),[('budget',75)]),
 ('Okab','REVISED',(95,6,True),(45,5,True),(90,3,True),[('deadline',4)]),
 ('Pollux','TWICE',(80,5,True),(55,6,True),(65,5,True),[('deadline',7),('deadline',4)]),
 ('Rasalas','TWICE',(70,5,True),(45,6,True),(60,3,True),[('deadline',7),('deadline',2)]),
 ('Sadr','LONG',(85,5,True),(60,6,True),(80,4,True),[]),
 ('Tureis','CONFIRM',(70,4,True),(65,5,True),(50,4,True),[('deadline',4)]),
 ('Wasat','CONFIRM',(95,5,False),(90,3,False),(70,5,True),[('local_only',False)]),
]

FIXTURES=[h.episode(*x) for x in EPISODES]
FIX={f['id']:f for f in FIXTURES}
for m in (h,g):m.FIX=FIX;m.FIXTURES=FIXTURES
z.FIXTURES=FIXTURES;z.z2.FIXTURES=FIXTURES;z.FIX=FIX
z.HARD_TYPES=TYPES;g.HARD_TYPES=TYPES;z.HARD=[f['id'] for f in FIXTURES]
z.ARMS.clear();z.ARMS.update(ARMS);z.z2b.ARMS.clear()
for _arm,(_base,_) in ARMS.items():z.z2b.ARMS[_arm]={'base':_base,'query':True}
z.SEEDS=SEEDS;z.z2b.SEEDS=SEEDS;g.SEEDS=SEEDS;h.SEEDS=SEEDS
h.ARMS=ARMS;h.SLOTS={a:4 for a in ARMS}
_settings=h.settings  # b2_context_chars=1536 and b2_quote_slots
def settings(arm,seed):return _settings(arm,seed)|{'b2_quote_choices':CHOICES[arm]}
z.settings=settings;z.z2b.settings=settings

def picked_kinds(report,fixture_ids=None):
    """B2 variants: which source each B2 quote came from (current task, kickoff, a status note, data sheet)."""
    out={'current':0,'kickoff':0,'note':0,'sheet':0,'other':0}
    for r in report['rows']:
        if r['variant'] not in z.B2_VARIANTS or (fixture_ids and r['fixture'] not in fixture_ids):continue
        f=FIX[r['fixture']]
        for o in r['offers']:
            if o['role']!='B2_GIST':continue
            for q in (o.get('offer') or {}).get('quotes') or []:
                k=('kickoff' if q in f['history'][0] else 'sheet' if q in f['history'][-1] else 'note' if any(q in x for x in f['history'][1:-1])
                   else 'current' if q in f['current'] else 'other')
                out[k]+=1
    return out

def run(installed,work,arm,seed):
    from v13.common import atomic_write
    summary=h.run(installed,work,arm,seed)
    report=json.loads((Path(work)/('step2_'+z.z2b.run_id(arm,seed)+'.json')).read_text())
    summary['z2i']={'b2_quote_choices':CHOICES[arm],'picked_kinds':picked_kinds(report),
                    'picked_kinds_changed':picked_kinds(report,{f['id'] for f in FIXTURES if f['type'] in ('REVISED','TWICE')})}
    atomic_write(Path(work)/('summary_'+z.z2b.run_id(arm,seed)+'.json'),json.dumps(summary,ensure_ascii=False,indent=2))
    return summary

def compare(runs,arm,ids):
    rate=z.z2b.cluster_ci([[h.episode_value(runs,arm,f,h.rule_rate)-h.episode_value(runs,CONTROL,f,h.rule_rate)] for f in ids])
    exact=z.z2b.cluster_ci([[h.episode_value(runs,arm,f,h.exact_on)-h.episode_value(runs,CONTROL,f,h.exact_on)] for f in ids])
    n={a:sum(h.exact_on(runs[(a,s)],f) for s in SEEDS for f in ids) for a in (arm,CONTROL)}
    return {'rule_rate_minus_control':rate,'both_exact_minus_control':exact,'both_exact_guarded_exact':n,
            'helps':rate['ci95'][0]>0 and n[arm]>n[CONTROL],'rate_only':rate['ci95'][0]>0 and n[arm]<=n[CONTROL]}

def gate(runs):
    """Preregistered decision (PREREG.md)."""
    need=[(a,s) for a in ARMS for s in SEEDS]
    if any(k not in runs for k in need):return {'status':'INCOMPLETE','missing':[z.z2b.run_id(*k) for k in need if k not in runs]}
    ids=[f['id'] for f in FIXTURES]
    pairs={a:[p for s in SEEDS for p in runs[(a,s)]['z2g']['pairs']] for a in ARMS}
    structural=all(r['tool_status']!='STRUCTURAL_FAIL' and r['step2_status']!='DIAGNOSTIC_INCOMPLETE' for r in runs.values())
    consistent=all(runs[k]['z2g']['consistent'] for k in need)
    share={a:sum(runs[(a,s)]['z2g']['validity']['kickoff_in_context'] for s in SEEDS)/max(1,sum(runs[(a,s)]['z2g']['validity']['offers'] for s in SEEDS)) for a in ARMS}
    no_current={a:sum(runs[(a,s)]['z2i']['picked_kinds']['current'] for s in SEEDS) for a in CANDIDATES}
    wrong_on={a:g.tally(pairs[a],'on')['wrong'] for a in ARMS}
    cmp={a:compare(runs,a,ids) for a in CANDIDATES}
    if not (structural and consistent and not any(no_current.values())):status='Z2I_INVALID'
    elif min(share.values())<g.VALID_SHARE:status='Z2I_NOT_TESTABLE'
    elif any(wrong_on.values()):status='Z2I_UNSAFE'
    elif any(c['helps'] for c in cmp.values()):status='Z2I_CHOICES_HELP'
    elif any(c['rate_only'] for c in cmp.values()):status='Z2I_CHOICES_PARTIAL'
    else:status='Z2I_CHOICES_NO_GAIN'
    best=max(CANDIDATES,key=lambda a:(cmp[a]['helps'],cmp[a]['both_exact_guarded_exact'][a],cmp[a]['rule_rate_minus_control']['mean']))
    def by(a,key,t):return g.tally([p for p in pairs[a] if p['type']==t],key)
    return {'status':status,'best_candidate':best,'structural':structural,'consistent':consistent,'current_picked_in_candidates':no_current,
            'validity':{'kickoff_in_context_share':share,'required':g.VALID_SHARE},'wrong_guard_on':wrong_on,'vs_control':cmp,
            'b2_rule_rate':{a:sum(h.rule_rate(runs[(a,s)],f) for s in SEEDS for f in ids)/(len(SEEDS)*len(ids)) for a in ARMS},
            'all_rows':{a:{'off':g.tally(pairs[a],'off'),'on':g.tally(pairs[a],'on')} for a in ARMS},
            'by_type':{a:{t:{'off':by(a,'off',t),'on':by(a,'on',t)} for t in TYPES} for a in ARMS},
            'picked_kinds_changed':{a:{k:sum(runs[(a,s)]['z2i']['picked_kinds_changed'][k] for s in SEEDS) for k in ('current','kickoff','note','sheet','other')} for a in ARMS},
            'picked_mean':{a:sum(runs[(a,s)]['z2h']['picked_per_offer']['mean'] for s in SEEDS)/len(SEEDS) for a in ARMS},
            'superseded_quoted_rows':{a:sum(runs[(a,s)]['z2e']['superseded_quoted_rows'] for s in SEEDS) for a in ARMS},
            'b2_prompt_tokens_mean':{a:h._mean([t for s in SEEDS for t in runs[(a,s)]['z2e']['b2_prompt_tokens'] if t]) for a in ARMS},
            'utility':{a:{v:z.z2b.mean_u(runs,a,v) for v in ('b1_only','b2_only','both_exact')} for a in ARMS},'canonical_gate_pass':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--installed-home',required=True);p.add_argument('--work',required=True)
    a=p.parse_args()
    from v13.common import atomic_write
    work=Path(a.work);work.mkdir(parents=True,exist_ok=True);runs={}
    for s in SEEDS:
        for arm in ARMS:
            f=work/('summary_'+z.z2b.run_id(arm,s)+'.json')
            if f.exists() and 'z2i' in json.loads(f.read_text()):runs[(arm,s)]=json.loads(f.read_text());continue
            print(json.dumps({'run_start':z.z2b.run_id(arm,s)}),flush=True);runs[(arm,s)]=run(a.installed_home,work,arm,s)
    result={'gate':gate(runs),'runs':{z.z2b.run_id(*k):{'on':v['z2g']['on'],'picked_kinds':v['z2i']['picked_kinds'],'b2_rule_rate':v['z2e']['b2_rule_rate']} for k,v in sorted(runs.items())}}
    atomic_write(work/'z2i_result.json',json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result['gate'],indent=1)[:4000])
if __name__=='__main__':main()
