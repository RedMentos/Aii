"""WP-Z2: STEP2 with information only B1 holds (recent exact details) and only B2 holds (old rules), all four controls.

Canon §85.1 G-B-TIMESCALE-DIVERGENCE-001: B1/B2 need measurably different, complementary error profiles and the
combination must beat two identical instances. Earlier STEP2 fixtures gave B1 nothing of its own (b1_only 5/10).
Here every episode is a session of three earlier turns and one question:

  rules    old turn      budget/deadline/local-only (B2 long window: 4 slots x 240-char excerpts; B1 has 1 slot)
  filler   unrelated     Project Zenith distractor
  recent   last turn     supplier data sheet; the option values start after char 240, i.e. outside B2's excerpt,
                         inside B1's short exact window (cfg b1_recent_source_chars, WP-Z2 switch, 0 = live)
  current  question      refers to "the earlier rules" and "the latest data sheet" without restating them

Types: SPLIT (rules old, details recent: needs both bodies), RULE (details in the current text: B2 alone suffices),
DETAIL (rules in the current text: B1 alone suffices). The unchanged STEP2 harness (tests/integration_step2_utility.py,
7 variants, real B1/B2/C3) runs on these fixtures; only FIXTURES and the preparation turns are replaced in a private
module copy, the file itself is not touched. Each arm is replayed through the eligibility tool (scripts/step2_tool_replay.py)
because C3 does not compute without it (0/70 exact, 20.10.).

Arms (sibling homes, models/bin symlinked, identical hashes):
  A two_body      quote ctx 0    b1 window 0     live-like control
  B two_body      quote ctx 200  b1 window 0     quote pointer only
  C two_body      quote ctx 200  b1 window 600   primary
  D shared_body   quote ctx 200  b1 window 600   B2 = B1 weights + B2 state/prompt (shared body, dual state)
  E two_body      quote ctx 0    b1 window 600   b1 window without quote pointer
Preregistration: docs/proofs/continuation-20261021/step2-z2-timescale/PREREG.md. Diagnosis only (Linux cloud, no Redmi);
the canonical gate is never promoted by this script.
"""
import argparse
import importlib.util
import json
import os
import shutil
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ROOT/'tests')]
from v13.agi.eligibility import recipe

BASE={'b2_offer_body_state':False,'offer_quote_min_chars':90}
ARMS={'A':BASE|{'b2_control':'two_body','offer_quote_context_chars':0,'b1_recent_source_chars':0},
      'B':BASE|{'b2_control':'two_body','offer_quote_context_chars':200,'b1_recent_source_chars':0},
      'C':BASE|{'b2_control':'two_body','offer_quote_context_chars':200,'b1_recent_source_chars':600},
      'D':BASE|{'b2_control':'shared_body_dual_state','offer_quote_context_chars':200,'b1_recent_source_chars':600},
      'E':BASE|{'b2_control':'two_body','offer_quote_context_chars':0,'b1_recent_source_chars':600}}
B2_EXCERPT_CHARS=240  # cognition.body_context excerpt width (live)
# name, type, (budget, deadline, local_only), option A, option B; options are (cost, days, local)
EPISODES=[
 ('Kestrel','SPLIT',(100,5,True),(40,2,True),(70,7,False)),
 ('Lumen','SPLIT',(90,4,True),(95,3,True),(60,4,True)),
 ('Meridian','SPLIT',(80,6,False),(50,8,True),(75,5,False)),
 ('Nimbus','SPLIT',(120,3,True),(70,2,False),(65,4,True)),
 ('Orion','SPLIT',(75,7,True),(30,6,True),(25,7,True)),
 ('Perseus','SPLIT',(60,5,False),(55,5,False),(58,3,True)),
 ('Quasar','RULE',(110,4,True),(85,3,True),(90,2,True)),
 ('Rigel','RULE',(70,6,True),(65,4,False),(50,7,True)),
 ('Sirius','DETAIL',(95,5,True),(99,2,True),(80,5,True)),
 ('Tycho','DETAIL',(85,8,False),(45,9,False),(60,6,False)),
]
DISTRACTOR='Project Zenith. The unrelated maintenance meeting is scheduled for tomorrow. No budget or decision is requested.'
COMPUTE=' Compute each remaining budget and eligibility; choose cheapest eligible.'

def tf(x):return str(bool(x)).lower()
def rules_text(b,d,l):return f'Budget {b} euros. Deadline {d} days. Local-only requirement: {tf(l)}.'
def options_text(a,b):return f'Option A: cost {a[0]} euros, duration {a[1]} days, local {tf(a[2])}. Option B: cost {b[0]} euros, duration {b[1]} days, local {tf(b[2])}.'
def sheet(name,a,b):
    return (f'Project {name} supplier data sheet, revision 3, compiled by the procurement desk after the vendor calls on Monday. '
            'The sheet lists the two remaining offers in the order they were received; earlier offers were withdrawn and are not listed here. '
            'All figures below were confirmed by both vendors in writing. '+options_text(a,b))

def episode(name,kind,rules,a,b):
    budget,deadline,local=rules
    if kind=='DETAIL':
        history=[f'Project {name} kickoff notes. The team was introduced; the project rules will be stated with the decision request.',DISTRACTOR,sheet(name,a,b)]
        current=(f'Project {name}. Decide between Option A and Option B from the latest supplier data sheet. Rules for this decision: '
                 f'budget {budget} euros, deadline {deadline} days, local-only requirement: {tf(local)}.'+COMPUTE)
    elif kind=='RULE':
        history=[f'Project {name} kickoff notes. '+rules_text(*rules),DISTRACTOR,
                 f'Project {name} status note. The procurement desk met the vendors on Monday; the final figures follow with the decision request. No project rule changed.']
        current=f'Project {name}. Decide from the earlier project rules. '+options_text(a,b)+COMPUTE
    else:
        history=[f'Project {name} kickoff notes. '+rules_text(*rules),DISTRACTOR,sheet(name,a,b)]
        current=f'Project {name}. Decide between Option A and Option B from the latest supplier data sheet, using the earlier project rules.'+COMPUTE
    opts=[{'entity':e,'cost':o[0],'days':o[1],'local':o[2]} for e,o in (('A',a),('B',b))]
    action,options=recipe(budget,deadline,local,opts)
    return {'id':name,'type':kind,'rules':{'budget':budget,'deadline':deadline,'local_only':local},'history':history,'current':current,
            'needs':{'SPLIT':['B2_GIST:rules','B1_DETAIL:options'],'RULE':['B2_GIST:rules'],'DETAIL':['B1_DETAIL:options']}[kind],
            'temporal_mode':'RETAIN_PRIOR_RULES' if kind!='DETAIL' else 'CURRENT_RULES','oracle':{'project':name,'action':action,'options':options}}

FIXTURES=[episode(*x) for x in EPISODES]

def harness():
    """Private copy of the frozen STEP2 harness with these fixtures and three preparation turns."""
    spec=importlib.util.spec_from_file_location('step2_z2_harness',ROOT/'tests/integration_step2_utility.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    m.FIXTURES=FIXTURES
    def prepare_base(home,installed,cfg,fixture):
        from v13.common import file_hash
        from v13.config import initialize,save_config
        from v13.memory_server import runtime_library_hashes
        from v13.runtime import Runtime
        initialize(home);save_config(home,cfg);m.installed_links(home,installed);r=Runtime(home)
        data={'prior_events':[],'offers':[],'status':'ERROR'}
        try:
            for text in fixture['history']:
                e=r.store.event(r.session,text);data['prior_events'].append(e)
                for role in ('B1_DETAIL','B2_GIST'):
                    data['offers'].append(r.cognition.offer(role,e,0,time.monotonic()+cfg['observer_seconds']))
            data['state_before_restart']=m.states(r);data['generation']=r.store.generation_id;data['session']=r.session;data['model_revisions']=r.revisions()
            data['model_sha256']={role:file_hash(r.models.path_for(role)) for role in ('B1_DETAIL','B2_GIST','C3_LANGUAGE')}
            runner=Path(os.environ.get('V13_LLAMA_SERVER',str(installed/'bin/llama-server')))
            data['runner_sha256']=file_hash(runner);data['runner_runtime_libraries_sha256']=runtime_library_hashes(runner)
            data['integrity_before_restart']=not r.store.integrity(True);data['status']='RECORDED'
        except Exception as exc:
            data.update(error_type=type(exc).__name__,error=str(exc)[:500],state_after_failed_preparation=m.states(r))
        finally:
            data['body_attempts']=[dict(row) for row in r.store.rows("SELECT kind,event_id,metrics FROM telemetry WHERE kind='body_offer_attempt' ORDER BY id")]
            r.close();data['process_releases']=list(r.pool.release_history)
        return data
    m.prepare_base=prepare_base
    return m

def sibling_home(installed,dest,enable):
    installed=Path(installed).resolve();dest=Path(dest)
    if dest.exists():raise ValueError('Arm home exists; use a fresh path')
    (dest/'config').mkdir(parents=True);(dest/'data').mkdir()
    for name in ('models','bin'):os.symlink(installed/name,dest/name,target_is_directory=True)
    for f in (installed/'config').iterdir():
        if f.is_file():shutil.copyfile(f,dest/'config'/f.name)
    s=json.loads((dest/'config/settings.json').read_text());s.update(enable);(dest/'config/settings.json').write_text(json.dumps(s))
    return dest

def information_access(report):
    """Who actually delivered which information, from the recorded consumer messages (verified quotes per role)."""
    from v13.agi import eligibility as E
    fixtures={f['id']:f for f in report['fixtures']};out={}
    for row in report['rows']:
        if not row.get('consumer_messages'):continue
        f=fixtures[row['fixture']];user=json.loads(next(x['content'] for x in row['consumer_messages'] if x['role']=='user'));acc={}
        for a in user.get('analysts',[]):
            q=' '.join(a['verified_quotes']);r=acc.setdefault(a['role'],{'rules':False,'options':False})
            r['rules']|=all(E.stated(k,v,q) for k,v in f['rules'].items())
            r['options']|=all(E.option_stated(x,a['verified_quotes']) for x in f['oracle']['options'])
        out[row['fixture']+':'+row['variant']]=acc
    return out

def access_counts(access,fixtures):
    """Per variant: episodes where a verified quote of B1/B2 carried all rules / all option values."""
    res={}
    for key,acc in access.items():
        fid,v=key.split(':');c=res.setdefault(v,{})
        for role,x in acc.items():
            for k in ('rules','options'):c[role+':'+k]=c.get(role+':'+k,0)+x[k]
    return res

def error_profile(tool_rows,fixtures):
    """Per variant: fraction of rule-dependent fields (remaining, eligible, action) vs option fields (cost, days, local) correct."""
    res={}
    for v in sorted({x['variant'] for x in tool_rows}):
        rule=opt=nr=no=0
        for x in tool_rows:
            if x['variant']!=v:continue
            fc=x['score'].get('field_checks',{})
            for e in ('A','B'):
                for k in ('remaining','eligible'):rule+=bool(fc.get(e+'.'+k));nr+=1
                for k in ('cost','days','local'):opt+=bool(fc.get(e+'.'+k));no+=1
            rule+=bool(fc.get('action'));nr+=1
        res[v]={'rule_fields_correct':rule/nr if nr else None,'option_fields_correct':opt/no if no else None}
    return res

def run_arm(installed,work,arm):
    from step2_wire_rebind import diagnose
    import step2_tool_replay as replay
    from v13.common import atomic_write
    step2=harness();work=Path(work);home=sibling_home(installed,work/(arm+'-home'),ARMS[arm]);out=work/('step2_'+arm+'.json')
    report=step2.run_locked(home,out)
    report['proof_kind']='STEP2_Z2_TIMESCALE_SPLIT';report['harness_copy_of']='tests/integration_step2_utility.py'
    from v13.common import file_hash
    report['z2_source_sha256']={str(p.relative_to(ROOT)):file_hash(p) for p in (Path(__file__).resolve(),ROOT/'v13/cognition.py',ROOT/'tests/integration_step2_utility.py')}
    report['wire_arm']={'arm':'w1','note':'live wire'};report['z2_arm']={'arm':arm,'enable':ARMS[arm]}
    report['wire_diagnosis']=diagnose(report);report['information_access']=information_access(report)
    atomic_write(out,json.dumps(report,ensure_ascii=False,indent=2))
    tool=replay.run(home,out,work/('tool_'+arm+'.json'))
    fixtures={f['id']:f for f in report['fixtures']}
    summary={'arm':arm,'enable':ARMS[arm],'step2_status':report['status'],'distinct_bodies':report.get('distinct_bodies'),'paired_no_tool':report['paired'],
             'tool_status':tool['status'],'paired_tool':tool['paired_tool'],'tool_summary':tool['summary']['tool'],'no_tool_summary':tool['summary']['no_tool_w1'],
             'error_profile_tool':error_profile(tool['rows'],fixtures),'information_access':access_counts(report['information_access'],fixtures),
             'by_type_tool':{t:{v:sum(x['score']['utility'] for x in tool['rows'] if x['variant']==v and fixtures[x['fixture']]['type']==t)/max(1,sum(fixtures[i]['type']==t for i in fixtures))
                                 for v in sorted({x['variant'] for x in tool['rows']})} for t in ('SPLIT','RULE','DETAIL')}}
    atomic_write(work/('summary_'+arm+'.json'),json.dumps(summary,ensure_ascii=False,indent=2))
    return summary

def gate(summaries):
    """Preregistered decision (PREREG.md). Primary metric: tool-replay mean utility, all 10 episodes."""
    C=summaries.get('C');D=summaries.get('D')
    if not C or not D:return {'status':'INCOMPLETE'}
    u=C['paired_tool']['mean_utility'];ud=D['paired_tool']['mean_utility']
    two=u.get('both_exact',0.);best_single=max(u.get('b1_only',0.),u.get('b2_only',0.))
    ep=C['error_profile_tool']
    complementary=(ep['b1_only']['option_fields_correct']-ep['b2_only']['option_fields_correct']>=.25 and
                   ep['b2_only']['rule_fields_correct']-ep['b1_only']['rule_fields_correct']>=.25)
    controls={'same_model_same_policy':u.get('same_policy_dual',0.),'same_model_prompt_only':ud.get('prompt_only_dual',0.),'shared_body_dual_state':ud.get('both_exact',0.)}
    checks={'combination_beats_best_single':two>best_single,'each_body_wins_an_episode':C['paired_tool']['b1_b2_each_win_an_episode'],
            'complementary_error_profiles':complementary,'beats_same_model_same_policy':two>controls['same_model_same_policy'],
            'beats_same_model_prompt_only':two>controls['same_model_prompt_only'],'structural':C['tool_status']!='STRUCTURAL_FAIL' and D['tool_status']!='STRUCTURAL_FAIL' and C['step2_status']!='DIAGNOSTIC_INCOMPLETE'}
    passed=all(checks.values())
    return {'status':'Z2_DIVERGENCE_SUPPORTED' if passed else 'Z2_DIVERGENCE_NOT_SUPPORTED','checks':checks,'two_body_both_exact':two,'best_single':best_single,
            'controls':controls,'two_bodies_worth_cost':passed and two>controls['shared_body_dual_state'],
            'cheaper_shared_body_enough':controls['shared_body_dual_state']>=two,'canonical_gate_pass':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--installed-home',required=True);p.add_argument('--work',required=True)
    p.add_argument('--arms',nargs='*',default=list(ARMS));a=p.parse_args()
    from v13.common import atomic_write
    work=Path(a.work);work.mkdir(parents=True,exist_ok=True);summaries={}
    for arm in a.arms:
        if (work/('summary_'+arm+'.json')).exists():summaries[arm]=json.loads((work/('summary_'+arm+'.json')).read_text());continue
        print(json.dumps({'arm_start':arm}),flush=True);summaries[arm]=run_arm(a.installed_home,work,arm)
    result={'gate':gate(summaries),'arms':{k:{'tool':v['paired_tool']['mean_utility'],'no_tool':v['paired_no_tool']['mean_utility']} for k,v in summaries.items()}}
    atomic_write(work/'z2_result.json',json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,indent=1))
if __name__=='__main__':main()
