"""WP-Z2g: confirm the recency guard of the eligibility tool on fresh episodes with changed rules.

WP-Z2f (scripts/step2_z2f_context.py) showed that a B2 context budget large enough to hold the old rule note
(b2_context_chars=1536) makes B2 quote superseded rules exactly; the tool then committed 27 wrong decisions, all the
action the old rule would give. An exploratory guard, designed after seeing those rows, removed all 27 without losing an
exact decision. It is now v13.agi.eligibility.decide(..., history=...): a rule value not stated in the current source
counts only if the newest earlier session source that states that rule states this value; otherwise unavailable.

Here, on ten fresh episodes (never run before), new seeds 26-28, arms CQ (pointer off) and CQP (pointer on), both with
b2_context_chars=1536:
  REVISED  6  kickoff rules, one status note revising one rule (each rule, up and down), data sheet; every revision
              changes the correct action
  TWICE    2  kickoff, two status notes revising the same rule twice; the newest wins, each value gives a different action
  CONFIRM  2  a status note restates a kickoff rule with the same value; the guard must not refuse it
The recorded tool replay is unchanged (guard off). Afterwards every row with a recorded extraction is re-decided
deterministically twice: guard off (must reproduce the recorded action, consistency check) and guard on, with history =
the session's earlier sources as retained excerpts (first 240 chars each, the B2 slot excerpt of §85.1).
Preregistration: docs/proofs/continuation-20261026/step2-z2g-recency/PREREG.md. Diagnosis only (Linux cloud, no Redmi).
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ROOT/'tests')]
from v13.agi import eligibility as E

def _private(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

z=_private('step2_z2e_for_z2g','scripts/step2_z2e_pointer_hard.py')
SEEDS=(26,27,28)
ARMS={'CQ':('C','off'),'CQP':('C','pointer')}
CONTEXT_CHARS=1536
EXCERPT=240
VALID_SHARE=.90
MIN_WRONG_OFF=5
HARD_TYPES=('REVISED','TWICE','CONFIRM')
KEYS=z.RULE_KEYS

def confirm_note(name,rule,value):
    text={'budget':f'Confirmed budget {value} euros.','deadline':f'Confirmed deadline {value} days.','local_only':f'Confirmed local-only requirement: {z.tf(value)}.'}[rule]
    return f'Project {name} status note. The steering group reviewed the plan on Monday. {text} All other project rules are unchanged.'

# name, type, kickoff rules (budget, deadline, local_only), option A, option B, notes [(rule, value)] in session order
EPISODES=[
 ('Kochab','REVISED',(70,5,True),(85,3,True),(80,4,True),[('budget',90)]),
 ('Lesath','REVISED',(100,6,False),(60,4,True),(90,5,False),[('budget',50)]),
 ('Merak','REVISED',(95,3,True),(55,5,True),(80,3,True),[('deadline',5)]),
 ('Nunki','REVISED',(90,7,False),(45,7,False),(75,4,False),[('deadline',4)]),
 ('Phact','REVISED',(80,6,True),(40,4,False),(70,5,True),[('local_only',False)]),
 ('Rigel','REVISED',(100,5,False),(50,3,False),(85,4,True),[('local_only',True)]),
 ('Sabik','TWICE',(60,6,True),(75,4,True),(55,5,True),[('budget',80),('budget',50)]),
 ('Tarazed','TWICE',(100,3,True),(60,6,True),(90,4,True),[('deadline',7),('deadline',4)]),
 ('Unuk','CONFIRM',(90,5,True),(95,3,True),(70,6,True),[('budget',90)]),
 ('Vega','CONFIRM',(75,4,False),(50,4,False),(70,2,True),[('deadline',4)]),
]

def options(a,b):return [{'entity':e,'cost':o[0],'days':o[1],'local':o[2]} for e,o in (('A',a),('B',b))]

def episode(name,kind,rules,a,b,notes):
    cur=dict(zip(KEYS,rules));old={};history=[f'Project {name} kickoff notes. '+z.z2.rules_text(*rules)]
    for rule,value in notes:
        if kind=='CONFIRM':history.append(confirm_note(name,rule,value));continue
        old.setdefault(rule,set()).add(cur[rule]);cur[rule]=value;history.append(z.revision_note(name,rule,value))
    history.append(z.z2.sheet(name,a,b))
    current=f'Project {name}. Decide between Option A and Option B from the latest supplier data sheet, using the earlier project rules.'+z.z2.COMPUTE
    action,opts=E.recipe(cur['budget'],cur['deadline'],cur['local_only'],options(a,b))
    superseded={k:sorted(v)[0] for k,v in old.items()} or None  # z2e.b2_rows reads one value per rule
    return {'id':name,'type':kind,'rules':cur,'superseded':superseded,'superseded_all':{k:sorted(v) for k,v in old.items()},'history':history,
            'current':current,'needs':['B2_GIST:rules','B1_DETAIL:options'],'temporal_mode':'RETAIN_PRIOR_RULES','oracle':{'project':name,'action':action,'options':opts}}

FIXTURES=[episode(*x) for x in EPISODES]
z.FIXTURES=FIXTURES;z.z2.FIXTURES=FIXTURES;z.FIX={f['id']:f for f in FIXTURES};z.HARD_TYPES=HARD_TYPES;z.HARD=[f['id'] for f in FIXTURES]
FIX=z.FIX
z.ARMS.clear();z.ARMS.update(ARMS);z.z2b.ARMS.clear()
for _arm,(_base,_) in ARMS.items():z.z2b.ARMS[_arm]={'base':_base,'query':True}
z.SEEDS=SEEDS;z.z2b.SEEDS=SEEDS
_settings=z.settings
def settings(arm,seed):return _settings(arm,seed)|{'b2_context_chars':CONTEXT_CHARS}
z.settings=settings;z.z2b.settings=settings

def history_of(fixture):return [h[:EXCERPT] for h in fixture['history']]

def kickoff_in_context(report):
    """B2 offers whose earlier context holds the whole kickoff note (exact excerpt of its full length)."""
    n=hit=0
    for row in report['rows']:
        f=FIX[row['fixture']]
        if row['variant'] not in z.B2_VARIANTS:continue
        for o in row['offers']:
            if o['role']!='B2_GIST':continue
            n+=1;hit+=len(f['history'][0]) in [x['char_end']-x['char_start'] for x in o.get('context_source_refs',[])]
    return {'offers':n,'kickoff_in_context':hit}

def redecide(report,tool):
    """Paired deterministic re-decision of every recorded extraction: guard off (consistency) and guard on."""
    import step2_tool_replay as replay
    rows={(r['fixture'],r['variant']):r for r in report['rows']};out=[]
    for x in tool['rows']:
        f=FIX[x['fixture']];ex=(x.get('tool') or {}).get('extracted');recorded=replay.action_of(x);ora=f['oracle']['action']
        if ex:
            current,quotes=replay.evidence(rows[(x['fixture'],x['variant'])]['consumer_messages'])
            rules={k:ex[k] for k in KEYS}
            off=E.decide(rules,ex['options'],current,quotes);on=E.decide(rules,ex['options'],current,quotes,history=history_of(f))
            off_a,on_a,rej=off['action'],on['action'],on['rejected']
        else:off_a=on_a=recorded;rej=[]
        out.append({'fixture':x['fixture'],'variant':x['variant'],'type':f['type'],'oracle':ora,'recorded':recorded,'off':off_a,'on':on_a,
                    'extracted':bool(ex),'superseded_rejections':[r for r in rej if r.endswith(':superseded')]})
    return out

def tally(rows,key):
    return {'exact':sum(r[key]==r['oracle'] for r in rows),'wrong':sum(r[key] in ('A','B','NONE') and r[key]!=r['oracle'] for r in rows),
            'unknown':sum(r[key]=='UNKNOWN' for r in rows),'rows':len(rows)}

def run(installed,work,arm,seed):
    from v13.common import atomic_write,file_hash
    summary=z.run(installed,work,arm,seed);rid=z.z2b.run_id(arm,seed)
    report=json.loads((Path(work)/('step2_'+rid+'.json')).read_text());tool=json.loads((Path(work)/('tool_'+rid+'.json')).read_text())
    pairs=redecide(report,tool)
    summary['z2g']={'b2_context_chars':CONTEXT_CHARS,'validity':kickoff_in_context(report),'pairs':pairs,
                    'consistent':all(p['off']==p['recorded'] for p in pairs if p['extracted']),'off':tally(pairs,'off'),'on':tally(pairs,'on'),
                    'source_sha256':{str(p.relative_to(ROOT)):file_hash(p) for p in (Path(__file__).resolve(),ROOT/'v13/agi/eligibility.py')}}
    atomic_write(Path(work)/('summary_'+rid+'.json'),json.dumps(summary,ensure_ascii=False,indent=2))
    return summary

def gate(runs):
    """Preregistered decision (PREREG.md)."""
    need=[(a,s) for a in ARMS for s in SEEDS]
    if any(k not in runs for k in need):return {'status':'INCOMPLETE','missing':[z.z2b.run_id(*k) for k in need if k not in runs]}
    pairs=[p for k in need for p in runs[k]['z2g']['pairs']]
    off,on=tally(pairs,'off'),tally(pairs,'on')
    structural=all(r['tool_status']!='STRUCTURAL_FAIL' and r['step2_status']!='DIAGNOSTIC_INCOMPLETE' for r in runs.values())
    consistent=all(runs[k]['z2g']['consistent'] for k in need)
    share={a:sum(runs[(a,s)]['z2g']['validity']['kickoff_in_context'] for s in SEEDS)/max(1,sum(runs[(a,s)]['z2g']['validity']['offers'] for s in SEEDS)) for a in ARMS}
    lost=[p for p in pairs if p['off']==p['oracle'] and p['on']!=p['oracle']]
    by_type={t:{'off':tally([p for p in pairs if p['type']==t],'off'),'on':tally([p for p in pairs if p['type']==t],'on')} for t in HARD_TYPES}
    by_arm={a:{'off':tally([p for s in SEEDS for p in runs[(a,s)]['z2g']['pairs']],'off'),'on':tally([p for s in SEEDS for p in runs[(a,s)]['z2g']['pairs']],'on')} for a in ARMS}
    if not (structural and consistent):status='Z2G_INVALID'
    elif min(share.values())<VALID_SHARE or off['wrong']<MIN_WRONG_OFF:status='Z2G_NOT_TESTABLE'
    elif on['wrong']==0 and on['exact']>=off['exact']:status='Z2G_GUARD_CONFIRMED'
    elif on['wrong']==0:status='Z2G_GUARD_SAFE_BUT_COSTLY'
    elif on['wrong']<off['wrong']:status='Z2G_GUARD_PARTIAL'
    else:status='Z2G_GUARD_FAILS'
    return {'status':status,'structural':structural,'consistent':consistent,'validity':{'kickoff_in_context_share':share,'required':VALID_SHARE,
            'wrong_off':off['wrong'],'required_wrong_off':MIN_WRONG_OFF},'off':off,'on':on,'lost_exact':lost,'by_type':by_type,'by_arm':by_arm,
            'confirm_false_refusals':sum(1 for p in lost if p['type']=='CONFIRM'),
            'b2_rule_rate':{a:sum(runs[(a,s)]['z2e']['b2_rule_rate'] for s in SEEDS)/len(SEEDS) for a in ARMS},
            'superseded_quoted_rows':{a:sum(runs[(a,s)]['z2e']['superseded_quoted_rows'] for s in SEEDS) for a in ARMS},
            'utility':{a:{v:z.z2b.mean_u(runs,a,v) for v in ('b1_only','b2_only','both_exact')} for a in ARMS},'canonical_gate_pass':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--installed-home',required=True);p.add_argument('--work',required=True)
    a=p.parse_args()
    from v13.common import atomic_write
    work=Path(a.work);work.mkdir(parents=True,exist_ok=True);runs={}
    for s in SEEDS:
        for arm in ARMS:
            f=work/('summary_'+z.z2b.run_id(arm,s)+'.json')
            if f.exists() and 'z2g' in json.loads(f.read_text()):runs[(arm,s)]=json.loads(f.read_text());continue
            print(json.dumps({'run_start':z.z2b.run_id(arm,s)}),flush=True);runs[(arm,s)]=run(a.installed_home,work,arm,s)
    result={'gate':gate(runs),'runs':{z.z2b.run_id(*k):{'off':v['z2g']['off'],'on':v['z2g']['on'],'validity':v['z2g']['validity']} for k,v in sorted(runs.items())}}
    atomic_write(work/'z2g_result.json',json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result['gate'].items() if k!='lost_exact'},indent=1)[:4000])
if __name__=='__main__':main()
