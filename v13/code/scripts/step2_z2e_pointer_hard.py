"""WP-Z2e: does the B2 quote pointer (cfg b2_quote_select='pointer', WP-Z2d) hold on harder episodes, and with one body?

WP-Z2d (scripts/step2_z2c_b2_rule.py) lifted B2's rule-quote rate .167 -> .969 on the Z2 episodes. Two limits were
named there: the earlier rule note was short (~96 chars), so a picked header sentence widened to the whole note, and
the shared-body control (one body, two states) with the pointer was not run. Here, on ten new episodes:

  LONG     4  the rule note is ~236 chars (still inside B2's 240-char excerpt); a long header sentence first, the three
              rules at the end. Picking the header widens to at most 200 chars and carries the budget only.
  REVISED  4  kickoff rules, then a status note that revises one rule ("New budget 130 euros."), then the data sheet.
              The revision changes the correct action; quoting only the kickoff gives a stale rule.
  DETAIL   2  rules in the current text (B2 not needed); sanity that the pointer does not break these.

Arms (Z2 settings + Z2b targeted question, Z2b runner as private module copy, eligibility tool replay):
  CQ   two bodies (Qwen B2), b2_quote_select off   (control)
  CQP  two bodies, pointer                          (primary)
  DQP  one body + two states (B2 = B1 weights), pointer   (shared-body control, Z2b criterion 4b and Canon §99)
Seeds 20, 21, 22 (new). Preregistration: docs/proofs/continuation-20261022/step2-z2e-pointer-hard/PREREG.md.
Diagnosis only (Linux cloud, no Redmi); the canonical gate is never promoted by this script.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ROOT/'tests')]
from v13.agi.eligibility import recipe,stated

def _private(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

z2=_private('step2_z2_for_z2e','scripts/step2_z2_timescale.py')
z2b=_private('step2_z2b_for_z2e','scripts/step2_z2b_seeds.py')
z2b.z2=z2  # the Z2b runner reads harness, fixtures and helpers through this module copy

SEEDS=(20,21,22)
ARMS={'CQ':('C','off'),'CQP':('C','pointer'),'DQP':('D','pointer')}
PRIMARY,CONTROL,SHARED='CQP','CQ','DQP'
B2_VARIANTS=('b2_only','both_none','both_exact','both_control')
HARD_TYPES=('LONG','REVISED')
TARGET_RATE=.60
RULE_KEYS=('budget','deadline','local_only')

def tf(x):return str(bool(x)).lower()
def long_note(name,b,d,l):
    return (f'Project {name} kickoff notes, written up by the coordinator after the first planning call with the design and procurement '
            f'teams on Monday morning. Attendance was complete. Budget {b} euros. Deadline {d} days. Local-only requirement: {tf(l)}.')
REVISION_TEXT={'budget':lambda v:f'New budget {v} euros.','deadline':lambda v:f'New deadline {v} days.','local_only':lambda v:f'New local-only requirement: {tf(v)}.'}
def revision_note(name,rule,value):
    return f'Project {name} status note. The steering group revised one rule on Monday. {REVISION_TEXT[rule](value)} All other project rules are unchanged.'

# name, type, old rules (budget, deadline, local_only), option A, option B, revision (rule, new value) for REVISED
EPISODES=[
 ('Altair','LONG',(100,5,True),(40,2,True),(70,7,False),None),
 ('Bellatrix','LONG',(90,4,True),(95,3,True),(60,4,True),None),
 ('Capella','LONG',(80,6,False),(50,8,True),(75,5,False),None),
 ('Deneb','LONG',(120,3,True),(70,2,False),(65,4,True),None),
 ('Electra','REVISED',(60,5,True),(70,3,True),(75,4,True),('budget',80)),
 ('Fomalhaut','REVISED',(100,6,True),(45,3,False),(80,5,True),('local_only',False)),
 ('Gemma','REVISED',(90,3,False),(40,5,True),(85,2,False),('deadline',6)),
 ('Hadar','REVISED',(110,7,True),(95,4,True),(70,6,True),('budget',60)),
 ('Izar','DETAIL',(95,5,True),(99,2,True),(80,5,True),None),
 ('Jabbah','DETAIL',(85,8,False),(45,9,False),(60,6,False),None),
]

def episode(name,kind,rules,a,b,revision):
    budget,deadline,local=rules
    opts=[{'entity':e,'cost':o[0],'days':o[1],'local':o[2]} for e,o in (('A',a),('B',b))]
    current_rules=dict(zip(RULE_KEYS,rules));superseded=None
    if kind=='DETAIL':
        f=z2.episode(name,'DETAIL',rules,a,b);f['superseded']=None;return f
    if kind=='LONG':
        history=[long_note(name,*rules),z2.DISTRACTOR,z2.sheet(name,a,b)]
    else:
        rule,value=revision;superseded={rule:current_rules[rule]};current_rules[rule]=value
        history=[f'Project {name} kickoff notes. '+z2.rules_text(*rules),revision_note(name,rule,value),z2.sheet(name,a,b)]
    current=f'Project {name}. Decide between Option A and Option B from the latest supplier data sheet, using the earlier project rules.'+z2.COMPUTE
    action,options=recipe(current_rules['budget'],current_rules['deadline'],current_rules['local_only'],opts)
    return {'id':name,'type':kind,'rules':current_rules,'superseded':superseded,'history':history,'current':current,
            'needs':['B2_GIST:rules','B1_DETAIL:options'],'temporal_mode':'RETAIN_PRIOR_RULES','oracle':{'project':name,'action':action,'options':options}}

FIXTURES=[episode(*x) for x in EPISODES]
z2.FIXTURES=FIXTURES
FIX={f['id']:f for f in FIXTURES}
HARD=[f['id'] for f in FIXTURES if f['type'] in HARD_TYPES]

for _arm,(_base,_) in ARMS.items():z2b.ARMS[_arm]={'base':_base,'query':True}
z2b.SEEDS=SEEDS
def settings(arm,seed):
    base,mode=ARMS[arm];return z2.ARMS[base]|{'seed':seed}|({'b2_quote_select':mode} if mode!='off' else {})
z2b.settings=settings

def b2_rows(report):
    """Per (fixture, variant) on hard episodes: B2's verified quotes (as C3 receives them) state every current rule;
    also whether a superseded value is quoted too, and whether any rule value is neither current nor superseded."""
    from v13.agi.eligibility import stated_values
    out={}
    for row in report['rows']:
        f=FIX[row['fixture']]
        if f['type'] not in HARD_TYPES or row['variant'] not in B2_VARIANTS or not row.get('consumer_messages'):continue
        user=json.loads(next(x['content'] for x in row['consumer_messages'] if x['role']=='user'))
        text=' '.join(q for a in user.get('analysts',[]) if a['role']=='B2_GIST' for q in a['verified_quotes'])
        old=f.get('superseded') or {}
        found={k:stated_values(k,text) for k in RULE_KEYS}
        out[(row['fixture'],row['variant'])]={'rules':all(stated(k,v,text) for k,v in f['rules'].items()),
            'superseded_quoted':any(stated(k,v,text) for k,v in old.items()),
            'invented_value':any(v!=f['rules'][k] and v!=old.get(k) for k in RULE_KEYS for v in found[k])}
    return out

def run(installed,work,arm,seed):
    from v13.common import atomic_write,file_hash
    summary=z2b.run_one(installed,work,arm,seed)
    report=json.loads((Path(work)/('step2_'+z2b.run_id(arm,seed)+'.json')).read_text())
    rows=b2_rows(report);tool=json.loads((Path(work)/('tool_'+z2b.run_id(arm,seed)+'.json')).read_text())
    wrong_rows=[{'fixture':x['fixture'],'variant':x['variant'],'action':(x.get('answer') or {}).get('action')} for x in tool['rows']
                if (x.get('answer') or {}).get('action') in ('A','B','NONE') and x['answer']['action']!=FIX[x['fixture']]['oracle']['action']]
    picked=sum(len((o.get('b2_quote_select') or {}).get('picked') or []) for r in report['rows'] for o in r['offers'] if o['role']=='B2_GIST')
    summary['z2e']={'b2_quote_select':ARMS[arm][1],'b2_rule_rows':{f'{k[0]}:{k[1]}':v for k,v in sorted(rows.items())},
        'b2_rule_rate':sum(v['rules'] for v in rows.values())/len(rows),'superseded_quoted_rows':sum(v['superseded_quoted'] for v in rows.values()),
        'invented_value_rows':sum(v['invented_value'] for v in rows.values()),'picked_ids':picked,
        'wrong_committed_tool':sum(s['wrong_committed'] for s in summary['tool_summary'].values()),'wrong_committed_rows':wrong_rows,
        'b2_prompt_tokens':[o['native_metrics'].get('prompt_tokens') for r in report['rows'] for o in r['offers'] if o['role']=='B2_GIST'],
        'source_sha256':{str(x.relative_to(ROOT)):file_hash(x) for x in (Path(__file__).resolve(),ROOT/'scripts/step2_z2b_seeds.py',ROOT/'scripts/step2_z2_timescale.py',ROOT/'v13/cognition.py')}}
    atomic_write(Path(work)/('summary_'+z2b.run_id(arm,seed)+'.json'),json.dumps(summary,ensure_ascii=False,indent=2))
    return summary

def episode_rate(runs,arm,fid):
    vals=[sum(runs[(arm,s)]['z2e']['b2_rule_rows'][f'{fid}:{v}']['rules'] for v in B2_VARIANTS)/len(B2_VARIANTS) for s in SEEDS]
    return sum(vals)/len(vals)

def rate(runs,arm,ids):return sum(episode_rate(runs,arm,f) for f in ids)/len(ids)

def holds(runs,arm,ids):
    ci=z2b.cluster_ci([[episode_rate(runs,arm,f)-episode_rate(runs,CONTROL,f)] for f in ids]);r=rate(runs,arm,ids)
    return {'rate':r,'control_rate':rate(runs,CONTROL,ids),'minus_control':ci,
            'status':'POINTER_HOLDS' if ci['ci95'][0]>0 and r>=TARGET_RATE else 'POINTER_PARTIAL' if ci['ci95'][0]>0 else 'POINTER_FAILS'}

def gate(runs):
    """Preregistered decision (PREREG.md)."""
    need=[(a,s) for a in ARMS for s in SEEDS]
    if any(k not in runs for k in need):return {'status':'INCOMPLETE','missing':[z2b.run_id(*k) for k in need if k not in runs]}
    structural=all(r['tool_status']!='STRUCTURAL_FAIL' and r['step2_status']!='DIAGNOSTIC_INCOMPLETE' for r in runs.values())
    queried=all(runs[k]['queried_offers']['with_question']==runs[k]['queried_offers']['offers']>0 for k in need)
    used=all(runs[(a,s)]['z2e']['picked_ids']>0 for a in (PRIMARY,SHARED) for s in SEEDS) and all(runs[(CONTROL,s)]['z2e']['picked_ids']==0 for s in SEEDS)
    wrong={a:sum(runs[(a,s)]['z2e']['wrong_committed_tool'] for s in SEEDS) for a in ARMS}
    invented={a:sum(runs[(a,s)]['z2e']['invented_value_rows'] for s in SEEDS) for a in ARMS}
    safe=structural and queried and used and wrong[PRIMARY]==0 and invented[PRIMARY]==0
    primary=holds(runs,PRIMARY,HARD)
    status=('Z2E_UNSAFE_OR_INVALID' if not safe else {'POINTER_HOLDS':'Z2E_POINTER_HOLDS','POINTER_PARTIAL':'Z2E_POINTER_PARTIAL','POINTER_FAILS':'Z2E_POINTER_FAILS'}[primary['status']])
    by_type={t:holds(runs,PRIMARY,[f for f in HARD if FIX[f]['type']==t]) for t in HARD_TYPES}
    # Z2b gate on the new episodes: primary CQP, shared-body control DQP (same criteria, all 10 episodes)
    P,K=PRIMARY,SHARED;single=max(z2b.SINGLE,key=lambda v:z2b.mean_u(runs,P,v))
    vs_single=z2b.cluster_ci(z2b.episode_diff(runs,(P,'both_exact'),(P,single)))
    per_seed=all(runs[(P,s)]['paired_tool']['mean_utility'].get('both_exact',0.)>max(runs[(P,s)]['paired_tool']['mean_utility'].get(v,0.) for v in z2b.SINGLE) for s in SEEDS)
    ep={v:{k:sum(runs[(P,s)]['error_profile_tool'][v][k] for s in SEEDS)/len(SEEDS) for k in ('rule_fields_correct','option_fields_correct')} for v in z2b.SINGLE}
    complementary=(ep['b1_only']['option_fields_correct']-ep['b2_only']['option_fields_correct']>=.25 and ep['b2_only']['rule_fields_correct']-ep['b1_only']['rule_fields_correct']>=.25)
    wins=sum(bool(runs[(P,s)]['paired_tool']['b1_b2_each_win_an_episode']) for s in SEEDS)
    vs_same=z2b.cluster_ci(z2b.episode_diff(runs,(P,'both_exact'),(P,'same_policy_dual')))
    vs_prompt=z2b.cluster_ci(z2b.episode_diff(runs,(P,'both_exact'),(K,'prompt_only_dual')))
    vs_shared=z2b.cluster_ci(z2b.episode_diff(runs,(P,'both_exact'),(K,'both_exact')))
    step2={'combination_beats_best_single':z2b.mean_u(runs,P,'both_exact')>z2b.mean_u(runs,P,single) and vs_single['ci95'][0]>0 and per_seed,
           'each_body_wins_an_episode':wins>=2,'complementary_error_profiles':complementary,
           'beats_same_model_same_policy':vs_same['ci95'][0]>0,'beats_same_model_prompt_only':vs_prompt['ci95'][0]>0,'structural':structural and queried}
    return {'status':status,'safe':safe,'primary':primary,'by_type':by_type,'wrong_committed_tool':wrong,'invented_value_rows':invented,
            'superseded_quoted_rows':{a:sum(runs[(a,s)]['z2e']['superseded_quoted_rows'] for s in SEEDS) for a in ARMS},
            'shared_body_pointer_rate':rate(runs,SHARED,HARD),'mode_used':used,
            'step2_z2b_criteria':{'checks':step2,'all_pass':all(step2.values()),'best_single':single,'both_exact_mean':z2b.mean_u(runs,P,'both_exact'),
                                  'best_single_mean':z2b.mean_u(runs,P,single),'error_profile':ep,'ci':{'vs_best_single':vs_single,'vs_same_policy_dual':vs_same,
                                  'vs_shared_prompt_only_dual':vs_prompt,'vs_shared_body_pointer':vs_shared},
                                  'two_bodies_worth_cost':all(step2.values()) and vs_shared['ci95'][0]>0,'cheaper_shared_body_enough':vs_shared['ci95'][0]<=0},
            'utility':{a:{v:z2b.mean_u(runs,a,v) for v in ('b1_only','b2_only','both_none','both_exact','both_control','same_policy_dual','prompt_only_dual')} for a in ARMS},
            'canonical_gate_pass':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--installed-home',required=True);p.add_argument('--work',required=True);p.add_argument('--runs',nargs='*')
    a=p.parse_args()
    from v13.common import atomic_write
    work=Path(a.work);work.mkdir(parents=True,exist_ok=True);runs={}
    order=[(arm,s) for s in SEEDS for arm in ARMS]
    if a.runs:order=[(r.split('_s')[0],int(r.split('_s')[1])) for r in a.runs]
    for arm,s in order:
        f=work/('summary_'+z2b.run_id(arm,s)+'.json')
        if f.exists() and 'z2e' in json.loads(f.read_text()):runs[(arm,s)]=json.loads(f.read_text());continue
        print(json.dumps({'run_start':z2b.run_id(arm,s)}),flush=True);runs[(arm,s)]=run(a.installed_home,work,arm,s)
    for f in work.glob('summary_*_s*.json'):
        x=json.loads(f.read_text())
        if 'z2e' in x:runs.setdefault((x['arm'],x['seed']),x)
    result={'gate':gate(runs),'runs':{z2b.run_id(*k):{'tool':v['paired_tool']['mean_utility'],'b2_rule_rate':v['z2e']['b2_rule_rate']} for k,v in sorted(runs.items())}}
    atomic_write(work/'z2e_result.json',json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result['gate'],indent=1)[:4000])
if __name__=='__main__':main()
