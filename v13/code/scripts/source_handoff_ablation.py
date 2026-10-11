"""Preregistered, source-disjoint native B2/C3 source-handoff ablation.

Runs only after the frozen 70-row cohort is complete. All four arms use the
same verified-quote consumer boundary; comparisons isolate the producer view.
No inference happens before a digest-bound preregistration is written.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time
import types
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.source_handoff_candidate import ROOT, SNAPSHOT, _replace, sources
from tests.integration_step2_utility import installed_artifacts, installed_links, SYSTEM, SCHEMA
from v13 import bodyview
from v13.common import atomic_write, digest, dumps, file_hash
from v13.config import DEFAULTS, initialize, save_config
from v13.runtime import Runtime
from v13.utility import score_decision

ARMS = ('baseline', 'state_off', 'semantics_only', 'full_candidate')
CONFIG = DEFAULTS | {'threads':2, 'temperature':0., 'seed':13, 'context_tokens':2048,
          'observer_tokens':160, 'answer_tokens':256, 'observer_seconds':45,
          'deadline_seconds':120, 'observer_mode':'off', 'history_turns':0,
          'memory_top_k':0, 'teacher_enabled':False, 'learning_mode':'RECORD_ONLY',
          'b2_control':'two_body', 'b2_state_slots':4, 'body_residency_mb':0}


def fixtures():
    """Fixed before inference; inputs and scoring oracle are separate fields."""
    rows=[]
    parameters=(
        ('Mira',61,8,False,(45,7,True),(55,4,False),'prior'),
        ('Lumen',43,4,True,(32,3,False),(39,4,True),'current_override'),
        ('Nacre',None,9,False,(28,3,True),(37,4,False),'missing_rule'),
        ('Tessera',None,6,True,(25,2,True),(33,5,True),'corrupt_prior'),
    )
    for name,budget,deadline,local,a,b,control in parameters:
        prior_budget=budget+19 if control=='current_override' else 71 if control=='corrupt_prior' else budget
        prior_deadline=deadline+3 if control=='current_override' else deadline
        prior_local=not local if control=='current_override' else local
        prior=f'Project {name}. '+(f'Budget {prior_budget} euros. ' if prior_budget is not None else 'No budget has been supplied. ')+f'Deadline {prior_deadline} days. Local-only requirement: {str(prior_local).lower()}.'
        current=f'Project {name}. Apply earlier project rules. Option A: cost {a[0]} euros, duration {a[1]} days, local {str(a[2]).lower()}. Option B: cost {b[0]} euros, duration {b[1]} days, local {str(b[2]).lower()}. Compute remaining budget and eligibility; choose cheapest eligible.'
        if control=='current_override':
            current+=f' Current rules replace earlier rules: budget {budget} euros, deadline {deadline} days, local-only requirement {str(local).lower()}.'
        options=[{'entity':entity,'cost':cost,'remaining':None if budget is None else budget-cost,'days':days,'local':is_local,
                  'eligible':None if budget is None else cost<=budget and days<=deadline and (is_local or not local)}
                 for entity,(cost,days,is_local) in zip(('A','B'),(a,b))]
        eligible=[o for o in options if o['eligible'] is True]
        action='UNKNOWN' if budget is None else min(eligible,key=lambda o:(o['cost'],o['entity']))['entity'] if eligible else 'NONE'
        rows.append({'id':name,'control':control,'prior':prior,'current':current,
                     'oracle':{'project':name,'action':action,'options':options}})
    return rows


FIXTURES=fixtures()


def module(name,text):
    result=types.ModuleType('v13._handoff_ablation_'+name)
    result.__package__='v13'
    exec(compile(text,'<bound-handoff-'+name+'>','exec'),result.__dict__)
    return result


def arm_sources():
    original, changed=sources()
    semantics=_replace(original['v13/cognition.py'],
        "body_state is your own world/self/skill state, not a fact.'",
        "body_state is own world/self/skill state, never source evidence. Its world.mode counts only completed own digital actions; it says nothing about available source knowledge. self.external_tools limits tool execution, not reading supplied text or reasoning about its constraints.'")
    return {
        'baseline':{'cognition':original['v13/cognition.py'],'bodyview':original['v13/bodyview.py']},
        'state_off':{'cognition':original['v13/cognition.py'],'bodyview':original['v13/bodyview.py']},
        'semantics_only':{'cognition':semantics,'bodyview':changed['v13/bodyview.py']},
        'full_candidate':{'cognition':changed['v13/cognition.py'],'bodyview':changed['v13/bodyview.py']},
    },module('validator',changed['v13/cognition.py']).Cognition


def binding(installed):
    paths=[p for p in (ROOT/'v13').rglob('*.py') if '__pycache__' not in p.parts]+[Path(__file__).resolve(),ROOT/'scripts/source_handoff_candidate.py',
        ROOT/'tests/integration_step2_utility.py',ROOT/SNAPSHOT/'manifest.json']
    paths += list((ROOT/SNAPSHOT).glob('*.py'))
    return {'source_scope':'ALL_RUNTIME_PYTHON_RECURSIVE_PLUS_HARNESS_AND_BASELINE',
            'source_sha256':{str(p.relative_to(ROOT)):file_hash(p) for p in sorted(paths)},
            'installed':installed_artifacts(installed)}


def ensure_frozen_cohort_complete(path):
    report=json.loads(Path(path).read_text())
    if report.get('status') not in ('UTILITY_FAIL','UTILITY_PASS_SCOPED') or len(report.get('rows',[]))!=70:
        raise ValueError('The original 70-row cohort is not complete; native ablation is blocked')
    return {'path':str(Path(path).resolve()),'sha256':file_hash(path),'status':report['status'],'rows':70}


def preregistration(installed,cohort):
    arms,_=arm_sources()
    return {'schema':'SOURCE_HANDOFF_ABLATION_PREREGISTRATION_V1','fixtures':FIXTURES,
        'fixtures_sha256':digest(dumps(FIXTURES)),'consumer_system':SYSTEM,'consumer_schema':SCHEMA,
        'consumer_schema_sha256':digest(dumps(SCHEMA)),'consumer_boundary':'IDENTICAL_VERIFIED_QUOTES_ALL_ARMS',
        'arm_specs':{'baseline':'original producer state and source instructions',
                     'state_off':'original producer; persisted bodyview state_source off',
                     'semantics_only':'own-action state scope plus state clarification; original earlier-source instructions',
                     'full_candidate':'own-action state scope and full candidate earlier-source instructions'},
        'arm_order':list(ARMS),'arm_source_sha256':{arm:{name:digest(text) for name,text in code.items()} for arm,code in arms.items()},
        'config':CONFIG,'body_sampling_seed':13,'consumer_sampling_seed':13,
        'native_oracle_visibility':False,'scope':'PRODUCER_STATE_AND_SOURCE_TRANSPORT_DIAGNOSIS_ONLY',
        'canonical_gate_pass':False,'previous_frozen_cohort':cohort,'binding':binding(installed)}


def consumer_messages(fixture,analysts):
    # Deliberately no fixture.prior, fixture.oracle, audit inventory or history.
    return [{'role':'system','content':SYSTEM},
            {'role':'user','content':dumps({'current_source':fixture['current'],'analysts':analysts})}]


def run_row(home,installed,fixture,arm,code,validator):
    initialize(home);save_config(home,CONFIG);installed_links(home,installed)
    r=Runtime(home);row={'fixture':fixture['id'],'arm':arm,'control':fixture['control'],
        'status':'RUNNING','raw_answer':'','oracle_visible_to_native':False}
    started=time.monotonic();prior_source=None
    try:
        if arm=='state_off':r.store.set_state('bodyview',{'state_source':'off','b4':'shadow'})
        r.cognition=module('cognition_'+arm,code['cognition']).Cognition(r)
        view=module('bodyview_'+arm,code['bodyview'])
        with patch.object(bodyview,'body_state',view.body_state):
            prior=r.store.event(r.session,fixture['prior']);prior_source=prior['source_ref']
            row['prior_event']=prior
            row['prior_offer']=r.cognition.offer('B2_GIST',prior,0,time.monotonic()+CONFIG['observer_seconds'])
            r.pool.unload()  # separate cold current producer call in every arm
            if fixture['control']=='corrupt_prior':
                blob=r.home/'data/blobs'/prior_source['sha256']
                blob.write_bytes(b'INTENTIONAL_SOURCE_CORRUPTION_CONTROL')
                row['source_corruption']={'source_ref':prior_source,'corrupted_blob_sha256':file_hash(blob),
                                          'expected_original_sha256':prior_source['sha256']}
            event=r.store.event(r.session,fixture['current']);row['event']=event
            deadline=time.monotonic()+CONFIG['deadline_seconds']
            offer=r.cognition.offer('B2_GIST',event,0,min(deadline,time.monotonic()+CONFIG['observer_seconds']),valid_until=deadline)
        row['offer']=offer
        row['available_earlier_sources']=[{'source_ref':ref,'text':r.store.read_source(ref)} for ref in offer['context_source_refs']]
        # The same hash/scope-checked transport is applied in all four arms.
        analysts=validator.analyst_context(r.cognition,[offer],event,0)
        row['delivered_analysts']=analysts
        row['delivered_prior_quotes']=[q for q in analysts[0]['verified_quotes'] if q['source_ref']['source_id']==prior_source['source_id']]
        r.pool.unload()  # C3 is cold too; no producer KV/memory carryover
        messages=consumer_messages(fixture,analysts);row['consumer_messages']=messages
        runner=r.pool.get('C3_LANGUAGE')
        for chunk in runner.generate(messages,r.cancel_event,deadline,CONFIG['answer_tokens'],SCHEMA,seed=13):row['raw_answer']+=chunk
        row['consumer_metrics']=dict(runner.last_metrics)
        row['score']=score_decision(row['raw_answer'],fixture['oracle'])
        row['checks']={'real_B2_final':offer['native_metrics'].get('status')=='FINAL',
            'real_C3_final':runner.last_metrics.get('status')=='FINAL','current_event_bound':offer['event_id']==event['event_id'],
            'corrupt_prior_not_delivered':fixture['control']!='corrupt_prior' or not row['delivered_prior_quotes']}
        row['status']='RECORDED' if all(row['checks'].values()) else 'STRUCTURAL_FAIL'
    except (Exception,KeyboardInterrupt) as exc:
        row.update(status='INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'ERROR',error_type=type(exc).__name__,error=str(exc)[:500],
                   score={'utility':0.,'exact':False,'contradictions':['inference_or_structure_failed']})
    finally:
        r.close();row['process_releases']=list(r.pool.release_history)
        row['processes_reaped']=bool(row['process_releases']) and all(p['process_reaped'] for p in row['process_releases'])
        if not row['processes_reaped'] and row['status']=='RECORDED':row['status']='STRUCTURAL_FAIL'
        row['elapsed_s']=time.monotonic()-started
    return row


def aggregate(rows):
    out={}
    for arm in ARMS:
        items=[r for r in rows if r['arm']==arm]
        out[arm]={'rows':len(items),'mean_strict_utility':sum(r['score']['utility'] for r in items)/len(items) if items else None,
            'exact_decisions':sum(bool(r['score']['exact']) for r in items),
            'rows_with_prior_quote':sum(bool(r.get('delivered_prior_quotes')) for r in items),
            'structural_failures':sum(r['status']!='RECORDED' for r in items)}
    return out


def validate_resume(report,registration_sha):
    if report.get('preregistration_sha256')!=registration_sha:raise ValueError('Resume preregistration changed')
    keys=[(r['fixture'],r['arm']) for r in report['rows']]
    allowed={(f['id'],a) for f in FIXTURES for a in ARMS}
    if len(keys)!=len(set(keys)) or any(k not in allowed for k in keys):raise ValueError('Resume row keys invalid')
    expected={r['fixture']+'/'+r['arm']:digest(dumps(r)) for r in report['rows']}
    if report.get('row_sha256')!=expected:raise ValueError('Resume recorded row bytes changed')
    return set(keys)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed-home',type=Path,required=True)
    parser.add_argument('--step2-report',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--register-only',action='store_true')
    args=parser.parse_args()
    cohort=ensure_frozen_cohort_complete(args.step2_report)
    registration=preregistration(args.installed_home,cohort)
    registration_path=args.out.with_suffix('.preregistration.json')
    args.out.parent.mkdir(parents=True,exist_ok=True)
    if registration_path.exists():
        if json.loads(registration_path.read_text())!=registration:raise ValueError('Preregistration binding changed; use a fresh cohort output path')
    else:atomic_write(registration_path,dumps(registration))
    registration_sha=file_hash(registration_path)
    if args.register_only:
        print(dumps({'status':'PREREGISTERED_NO_INFERENCE','path':str(registration_path),'sha256':registration_sha}));return
    if args.out.exists():
        report=json.loads(args.out.read_text())
        done=validate_resume(report,registration_sha)
    else:
        report={'schema':'SOURCE_HANDOFF_ABLATION_V1','status':'RUNNING','rows':[],
                'row_sha256':{},
                'preregistration_sha256':registration_sha,'canonical_gate_pass':False,
                'learned_semantic_utility_proven':False,'phone_measured':False}
        atomic_write(args.out,dumps(report))
        done=set()
    arms,validator=arm_sources()
    work=args.out.with_suffix('.checkpoint');work.mkdir(exist_ok=True)
    for fixture in FIXTURES:
        for arm in ARMS:
            if (fixture['id'],arm) in done:continue
            if binding(args.installed_home)!=registration['binding']:
                report['status']='ARTIFACT_CHANGED';atomic_write(args.out,dumps(report))
                raise ValueError('Native/source binding changed during ablation')
            home=work/(fixture['id']+'-'+arm)
            if home.exists():shutil.rmtree(home)  # only unfinished isolated scratch arm
            row=run_row(home,args.installed_home,fixture,arm,arms[arm],validator)
            report['rows'].append(row);report['summary']=aggregate(report['rows'])
            report['row_sha256'][fixture['id']+'/'+arm]=digest(dumps(row))
            atomic_write(args.out,dumps(report))
            print(dumps({'fixture':fixture['id'],'arm':arm,'status':row['status'],'utility':row['score']['utility']}),flush=True)
            if row['status']=='INTERRUPTED':
                report['status']='INTERRUPTED';atomic_write(args.out,dumps(report));raise KeyboardInterrupt
    report['installed_artifacts_unchanged']=binding(args.installed_home)==registration['binding']
    report['status']=('RECORDED_DIAGNOSIS' if all(r['status']=='RECORDED' for r in report['rows']) else 'STRUCTURAL_FAIL') if report['installed_artifacts_unchanged'] else 'ARTIFACT_CHANGED'
    report['summary']=aggregate(report['rows']);atomic_write(args.out,dumps(report))


if __name__=='__main__':main()
