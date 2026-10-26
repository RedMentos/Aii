"""WP-Z2h: may B2 pick more than two exact sentences (cfg b2_quote_slots 2 -> 4), with the recency guard always on?

WP-Z2g (scripts/step2_z2g_recency.py) confirmed the recency guard (wrong decisions 24 -> 0) but left the system almost
useless on changed rules: 412/420 rows UNKNOWN. With changed rules B2 has to carry the unchanged kickoff rules and the
revision; with long rule notes the three rule sentences sit apart. Two picked sentences rarely hold all current rules.

Ten fresh episodes (never run before), new seeds 29-31, b2_context_chars=1536, pointer on in both arms:
  LONG     3  long kickoff note, the three rules as separate sentences at its end
  REVISED  4  kickoff, one status note revising one rule, data sheet (every revision changes the correct action)
  TWICE    1  the same rule revised twice, newest wins
  CONFIRM  2  a status note restates a kickoff rule with the same value
Arms P2 (b2_quote_slots=2, the Z2g pointer) and P4 (b2_quote_slots=4). Every recorded extraction is re-decided with the
recency guard on (and off, consistency), as in WP-Z2g. Preregistration:
docs/proofs/continuation-20261026/step2-z2h-slots/PREREG.md. Diagnosis only (Linux cloud, no Redmi).
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

g=_private('step2_z2g_for_z2h','scripts/step2_z2g_recency.py')
z=g.z
SEEDS=(29,30,31)
ARMS={'P2':('C','pointer'),'P4':('C','pointer')}
SLOTS={'P2':2,'P4':4}
PRIMARY,CONTROL='P4','P2'
TYPES=('LONG','REVISED','TWICE','CONFIRM')

EPISODES=[
 ('Wezen','LONG',(95,4,True),(80,5,True),(70,4,True),[]),
 ('Yed','LONG',(70,6,False),(65,6,False),(75,2,True),[]),
 ('Zaniah','LONG',(100,3,True),(40,3,False),(90,2,True),[]),
 ('Acrux','REVISED',(80,4,True),(60,5,True),(75,3,True),[('deadline',6)]),
 ('Botein','REVISED',(70,6,False),(45,3,True),(65,5,False),[('budget',40)]),
 ('Caph','REVISED',(110,5,False),(55,4,False),(90,3,True),[('local_only',True)]),
 ('Diphda','REVISED',(90,6,True),(85,6,True),(50,5,False),[('local_only',False)]),
 ('Errai','TWICE',(100,7,True),(70,6,True),(95,3,True),[('deadline',4),('deadline',2)]),
 ('Furud','CONFIRM',(85,5,True),(90,2,True),(60,4,True),[('deadline',5)]),
 ('Gienah','CONFIRM',(60,3,False),(50,4,False),(55,3,True),[('budget',60)]),
]

def episode(name,kind,rules,a,b,notes):
    if kind!='LONG':return g.episode(name,kind,rules,a,b,notes)
    f=z.episode(name,'LONG',rules,a,b,None);f['superseded_all']={};return f

FIXTURES=[episode(*x) for x in EPISODES]
FIX={f['id']:f for f in FIXTURES}
z.FIXTURES=FIXTURES;z.z2.FIXTURES=FIXTURES;z.FIX=FIX;g.FIX=FIX;g.FIXTURES=FIXTURES
z.HARD_TYPES=TYPES;g.HARD_TYPES=TYPES;z.HARD=[f['id'] for f in FIXTURES]
z.ARMS.clear();z.ARMS.update(ARMS);z.z2b.ARMS.clear()
for _arm,(_base,_) in ARMS.items():z.z2b.ARMS[_arm]={'base':_base,'query':True}
z.SEEDS=SEEDS;z.z2b.SEEDS=SEEDS;g.SEEDS=SEEDS
_settings=z.settings  # already carries b2_context_chars=1536 (WP-Z2g wrapper)
def settings(arm,seed):return _settings(arm,seed)|{'b2_quote_slots':SLOTS[arm]}
z.settings=settings;z.z2b.settings=settings

def run(installed,work,arm,seed):
    from v13.common import atomic_write,file_hash
    summary=g.run(installed,work,arm,seed)
    summary['z2h']={'b2_quote_slots':SLOTS[arm],'picked_per_offer':_picked(work,arm,seed),
                    'source_sha256':{str(p.relative_to(ROOT)):file_hash(p) for p in (Path(__file__).resolve(),ROOT/'v13/cognition.py')}}
    atomic_write(Path(work)/('summary_'+z.z2b.run_id(arm,seed)+'.json'),json.dumps(summary,ensure_ascii=False,indent=2))
    return summary

def _picked(work,arm,seed):
    report=json.loads((Path(work)/('step2_'+z.z2b.run_id(arm,seed)+'.json')).read_text())
    n=[len((o.get('b2_quote_select') or {}).get('picked') or []) for r in report['rows'] for o in r['offers'] if o['role']=='B2_GIST']
    return {'offers':len(n),'mean':sum(n)/max(1,len(n)),'max':max(n,default=0)}

def episode_value(runs,arm,fid,fn):
    vals=[fn(runs[(arm,s)],fid) for s in SEEDS];return sum(vals)/len(vals)
def rule_rate(run,fid):return sum(run['z2e']['b2_rule_rows'][f'{fid}:{v}']['rules'] for v in z.B2_VARIANTS)/len(z.B2_VARIANTS)
def exact_on(run,fid):return sum(p['on']==p['oracle'] for p in run['z2g']['pairs'] if p['fixture']==fid and p['variant']=='both_exact')

def gate(runs):
    """Preregistered decision (PREREG.md)."""
    need=[(a,s) for a in ARMS for s in SEEDS]
    if any(k not in runs for k in need):return {'status':'INCOMPLETE','missing':[z.z2b.run_id(*k) for k in need if k not in runs]}
    ids=[f['id'] for f in FIXTURES]
    pairs={a:[p for s in SEEDS for p in runs[(a,s)]['z2g']['pairs']] for a in ARMS}
    structural=all(r['tool_status']!='STRUCTURAL_FAIL' and r['step2_status']!='DIAGNOSTIC_INCOMPLETE' for r in runs.values())
    consistent=all(runs[k]['z2g']['consistent'] for k in need)
    share={a:sum(runs[(a,s)]['z2g']['validity']['kickoff_in_context'] for s in SEEDS)/max(1,sum(runs[(a,s)]['z2g']['validity']['offers'] for s in SEEDS)) for a in ARMS}
    used=all(runs[(PRIMARY,s)]['z2h']['picked_per_offer']['max']>2 for s in SEEDS)
    wrong_on={a:g.tally(pairs[a],'on')['wrong'] for a in ARMS}
    rate_ci=z.z2b.cluster_ci([[episode_value(runs,PRIMARY,f,rule_rate)-episode_value(runs,CONTROL,f,rule_rate)] for f in ids])
    exact_ci=z.z2b.cluster_ci([[episode_value(runs,PRIMARY,f,exact_on)-episode_value(runs,CONTROL,f,exact_on)] for f in ids])
    exact_both={a:sum(exact_on(runs[(a,s)],f) for s in SEEDS for f in ids) for a in ARMS}
    if not (structural and consistent):status='Z2H_INVALID'
    elif min(share.values())<g.VALID_SHARE:status='Z2H_NOT_TESTABLE'
    elif any(wrong_on.values()):status='Z2H_UNSAFE'
    elif rate_ci['ci95'][0]>0 and exact_both[PRIMARY]>exact_both[CONTROL]:status='Z2H_SLOTS_HELP'
    elif rate_ci['ci95'][0]>0:status='Z2H_SLOTS_PARTIAL'
    else:status='Z2H_SLOTS_NO_GAIN'
    def by(a,key,t):return g.tally([p for p in pairs[a] if p['type']==t],key)
    return {'status':status,'structural':structural,'consistent':consistent,'slots_used':used,
            'validity':{'kickoff_in_context_share':share,'required':g.VALID_SHARE},'wrong_guard_on':wrong_on,
            'b2_rule_rate':{a:sum(rule_rate(runs[(a,s)],f) for s in SEEDS for f in ids)/(len(SEEDS)*len(ids)) for a in ARMS},'rule_rate_minus_control':rate_ci,
            'both_exact_guarded_exact':exact_both,'both_exact_minus_control':exact_ci,
            'all_rows':{a:{'off':g.tally(pairs[a],'off'),'on':g.tally(pairs[a],'on')} for a in ARMS},
            'by_type':{a:{t:{'off':by(a,'off',t),'on':by(a,'on',t)} for t in TYPES} for a in ARMS},
            'picked_mean':{a:sum(runs[(a,s)]['z2h']['picked_per_offer']['mean'] for s in SEEDS)/len(SEEDS) for a in ARMS},
            'superseded_quoted_rows':{a:sum(runs[(a,s)]['z2e']['superseded_quoted_rows'] for s in SEEDS) for a in ARMS},
            'b2_prompt_tokens_mean':{a:_mean([t for s in SEEDS for t in runs[(a,s)]['z2e']['b2_prompt_tokens'] if t]) for a in ARMS},
            'utility':{a:{v:z.z2b.mean_u(runs,a,v) for v in ('b1_only','b2_only','both_exact')} for a in ARMS},'canonical_gate_pass':False}

def _mean(x):return sum(x)/len(x) if x else None

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--installed-home',required=True);p.add_argument('--work',required=True)
    a=p.parse_args()
    from v13.common import atomic_write
    work=Path(a.work);work.mkdir(parents=True,exist_ok=True);runs={}
    for s in SEEDS:
        for arm in ARMS:
            f=work/('summary_'+z.z2b.run_id(arm,s)+'.json')
            if f.exists() and 'z2h' in json.loads(f.read_text()):runs[(arm,s)]=json.loads(f.read_text());continue
            print(json.dumps({'run_start':z.z2b.run_id(arm,s)}),flush=True);runs[(arm,s)]=run(a.installed_home,work,arm,s)
    result={'gate':gate(runs),'runs':{z.z2b.run_id(*k):{'on':v['z2g']['on'],'picked':v['z2h']['picked_per_offer'],'b2_rule_rate':v['z2e']['b2_rule_rate']} for k,v in sorted(runs.items())}}
    atomic_write(work/'z2h_result.json',json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result['gate'],indent=1)[:4000])
if __name__=='__main__':main()
