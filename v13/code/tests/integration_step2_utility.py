"""Preregistered source-grounded STEP2 utility proof on existing native ports.

All variants use the same C3 consumer and scoring schema. Real B1/B2 offers,
channels and persisted state are used; no training or gate promotion is done.
A FAIL remains a FAIL. --fixtures limits diagnose only, never satisfy the gate.
"""
import argparse
import copy
import fcntl
import json
import os
from pathlib import Path,PurePosixPath
import shutil
import sys
import time
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.common import APP,atomic_write,dumps,file_hash,digest
from v13.config import initialize,save_config
from v13.proofs import archive_previous
from v13.resources import device
from v13.runtime import Runtime
from v13.models import ModelManager
from v13.memory_server import runtime_library_hashes
from v13.utility import paired_utility,score_decision

# Frozen before inference. Prior rules are never repeated directly to C3.
EPISODE_PARAMETERS=[
 ('Aurora',100,5,True,(40,2,True),(70,7,False)),
 ('Borealis',90,4,True,(55,5,True),(65,3,True)),
 ('Cygnus',75,6,True,(80,2,True),(60,4,True)),
 ('Dorado',120,3,True,(70,2,False),(95,3,True)),
 ('Equinox',85,7,False,(35,6,False),(50,4,True)),
 ('Fornax',60,4,True,(65,2,True),(45,5,True)),
 ('Gemini',110,5,True,(85,3,True),(75,4,True)),
 ('Helios',95,6,True,(60,6,True),(60,7,True)),
 ('Indigo',70,4,True,(50,3,True),(40,3,False)),
 ('Juno',None,5,True,(45,2,True),(55,3,True)),
]
VARIANTS=[('b1_only',['B1_DETAIL'],'NO_MESSAGE',False),('b2_only',['B2_GIST'],'NO_MESSAGE',False),
 ('both_none',['B1_DETAIL','B2_GIST'],'NO_MESSAGE',False),('both_exact',['B1_DETAIL','B2_GIST'],'SOURCE_EXACT',False),
 ('both_control',['B1_DETAIL','B2_GIST'],'CONTROL',False),('same_policy_dual',['B1_DETAIL','B1_DETAIL'],'NO_MESSAGE',False),
 ('prompt_only_dual',['B1_DETAIL','B2_GIST'],'NO_MESSAGE',True)]
SYSTEM=('You make a source-grounded decision. Return the required JSON only. Current source and verified quotations are evidence; analyst summaries are fallible hypotheses. '
 'Use earlier project rules only if supplied by an analyst with source evidence. Explicit updated rules in the current source override earlier rules. Choose the cheapest eligible option, choosing A on a tie. '
 'eligible means cost <= budget, days <= deadline, and local if local-only is required. remaining = budget - cost even for ineligible options. '
 'If budget or any required earlier rule is unavailable, return action UNKNOWN and null remaining and eligible. If no option is eligible choose NONE. '
 'Keep costs, days and locality assigned to their actual entity. Never invent missing earlier rules.')
SCHEMA={'type':'object','additionalProperties':False,'required':['project','action','options'],'properties':{
 'project':{'type':'string'},'action':{'type':'string','enum':['A','B','NONE','UNKNOWN']},
 'options':{'type':'array','minItems':2,'maxItems':2,'items':{'type':'object','additionalProperties':False,
 'required':['entity','cost','remaining','days','local','eligible'],'properties':{'entity':{'type':'string','enum':['A','B']},
 'cost':{'type':'integer'},'remaining':{'type':['integer','null']},'days':{'type':'integer'},'local':{'type':'boolean'},'eligible':{'type':['boolean','null']}}}}}}

def episodes():
    result=[]
    for name,budget,deadline,local,a,b in EPISODE_PARAMETERS:
        current_override=name in {'Cygnus','Equinox','Gemini','Indigo'}
        prior_budget=budget+40 if current_override else budget
        prior_deadline=deadline+5 if current_override else deadline
        prior_local=not local if current_override else local
        prior=f'Project {name}. '+(f'Budget {prior_budget} euros. ' if prior_budget is not None else 'Budget has not been provided. ')+f'Deadline {prior_deadline} days. Local-only requirement: {str(prior_local).lower()}.'
        current=f'Project {name}. Decide from the earlier project rules. Option A: cost {a[0]} euros, duration {a[1]} days, local {str(a[2]).lower()}. Option B: cost {b[0]} euros, duration {b[1]} days, local {str(b[2]).lower()}. Compute each remaining budget and eligibility; choose cheapest eligible.'
        if current_override:
            current+=f' Updated rules, overriding the earlier rules: budget {budget} euros, deadline {deadline} days, local-only requirement {str(local).lower()}.'
        options=[]
        for entity,(cost,days,is_local) in zip(('A','B'),(a,b)):
            options.append({'entity':entity,'cost':cost,'remaining':None if budget is None else budget-cost,'days':days,'local':is_local,
                            'eligible':None if budget is None else cost<=budget and days<=deadline and (is_local or not local)})
        eligible=[o for o in options if o['eligible'] is True]
        action='UNKNOWN' if budget is None else min(eligible,key=lambda o:(o['cost'],o['entity']))['entity'] if eligible else 'NONE'
        result.append({'id':name,'prior':prior,'distractor':'Project Zenith. The unrelated maintenance meeting is scheduled for tomorrow. No budget or decision is requested.',
                       'current':current,'temporal_mode':'CURRENT_EXPLICIT_OVERRIDE' if current_override else 'RETAIN_PRIOR_RULES','oracle':{'project':name,'action':action,'options':options}})
    return result

FIXTURES=episodes()

def source_hashes():
    paths=list((APP/'v13').glob('*.py'))+[Path(__file__).resolve()]
    return {str(p.relative_to(APP)):file_hash(p) for p in sorted(paths)}

def installed_artifacts(installed):
    models=ModelManager(installed);hash_cache={};hashes={};revisions={}
    for role in ('B1_DETAIL','B2_GIST','C3_LANGUAGE'):
        path=models.path_for(role).resolve()
        if path not in hash_cache:hash_cache[path]=file_hash(path)
        hashes[role]=hash_cache[path];revisions[role]=models.revision(role)
    runner=Path(os.environ.get('V13_LLAMA_SERVER',str(installed/'bin/llama-server')))
    return {'model_sha256':hashes,'model_revisions':revisions,'runner_sha256':file_hash(runner),
            'runner_runtime_libraries_sha256':runtime_library_hashes(runner)}

def installed_links(home,installed):
    for name in ('models','bin'):
        target=home/name
        if target.is_symlink():target.unlink()
        elif target.exists():shutil.rmtree(target)
        target.symlink_to(installed/name,target_is_directory=True)
    shutil.copyfile(installed/'config/models.json',home/'config/models.json')

def states(runtime):return {role:runtime.store.state(role+':'+runtime.session,{}) for role in ('B1_DETAIL','B2_GIST')}

def same_persisted_state(observed,recorded):
    return dumps(observed)==dumps(recorded)

def prepare_base(home,installed,cfg,fixture):
    initialize(home);save_config(home,cfg);installed_links(home,installed);r=Runtime(home)
    data={'prior_events':[],'offers':[],'status':'ERROR'}
    try:
        for text in (fixture['prior'],fixture['distractor']):
            e=r.store.event(r.session,text);data['prior_events'].append(e)
            for role in ('B1_DETAIL','B2_GIST'):
                data['offers'].append(r.cognition.offer(role,e,0,time.monotonic()+cfg['observer_seconds']))
        data['state_before_restart']=states(r);data['generation']=r.store.generation_id;data['session']=r.session;data['model_revisions']=r.revisions()
        data['model_sha256']={role:file_hash(r.models.path_for(role)) for role in ('B1_DETAIL','B2_GIST','C3_LANGUAGE')}
        data['runner_sha256']=file_hash(Path(os.environ.get('V13_LLAMA_SERVER',str(installed/'bin/llama-server'))))
        data['runner_runtime_libraries_sha256']=runtime_library_hashes(Path(os.environ.get('V13_LLAMA_SERVER',str(installed/'bin/llama-server'))))
        data['integrity_before_restart']=not r.store.integrity(True);data['status']='RECORDED'
    except Exception as exc:
        data.update(error_type=type(exc).__name__,error=str(exc)[:500],state_after_failed_preparation=states(r))
    finally:
        data['body_attempts']=[dict(row) for row in r.store.rows("SELECT kind,event_id,metrics FROM telemetry WHERE kind='body_offer_attempt' ORDER BY id")]
        r.close();data['process_releases']=list(r.pool.release_history)
    return data

CHECKPOINT_META='__V13_CLOSED_CHECKPOINT__.json'
CHECKPOINT_SKIP={'models','bin','logs','tmp','exports','backups'}

def checkpoint_path(home,relative):
    if not isinstance(relative,str):raise ValueError('Unsafe checkpoint path')
    path=PurePosixPath(relative)
    if not path.parts or str(path)!=relative or path.is_absolute() or any(p in {'.','..'} for p in path.parts) or '\\' in relative:
        raise ValueError('Unsafe checkpoint path')
    if path.parts[0] in CHECKPOINT_SKIP or relative==CHECKPOINT_META or path.name=='coordinator.lock' or path.name.endswith(('-wal','-shm')):
        raise ValueError('Transient or reserved checkpoint path')
    target=home.joinpath(*path.parts)
    if any(p.is_symlink() for p in [target,*target.parents] if p.is_relative_to(home)) or not target.resolve().is_relative_to(home.resolve()):
        raise ValueError('Checkpoint symlink or path escape')
    return target

def checkpoint_bytes(base,expected):
    if not isinstance(expected,dict) or 'data/db/brain.sqlite3' not in expected:
        raise ValueError('Closed database checkpoint required')
    contents={}
    for relative,sha in expected.items():
        path=checkpoint_path(base,relative)
        payload=path.read_bytes()
        if digest(payload)!=sha:raise ValueError('Checkpoint bytes changed: '+relative)
        contents[relative]=payload
    return contents

def seal_checkpoint(base,expected):
    """Capture the declared closed files once, never a later directory snapshot.

    The original failed proof demonstrated correct main DB bytes overlaid by
    unregistered stale WAL files. Those files are not authoritative checkpoint
    data. No live database is backed up or silently repaired by this function.
    """
    path=base.with_name(base.name+'.closed.zip');partial=path.with_suffix('.partial')
    with open(base/'data/coordinator.lock','a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        contents=checkpoint_bytes(base,expected)
        with zipfile.ZipFile(partial,'w',zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(CHECKPOINT_META,dumps({'format':'STEP2_CLOSED_CHECKPOINT_V1','files':expected}))
            for relative,payload in contents.items():archive.writestr(relative,payload)
        os.replace(partial,path)
    return {'path':str(path),'sha256':file_hash(path),'format':'STEP2_CLOSED_CHECKPOINT_V1'}

def clone_base(base,home,installed,expected,sealed):
    # Verify authoritative originals as well as the sealed archive on every row.
    # Newly appearing sidecars are reported explicitly, never copied into SQLite.
    checkpoint_bytes(base,expected)
    sidecars=[{'path':str(p.relative_to(base)),'sha256':file_hash(p)} for p in sorted((base/'data/db').glob('brain.sqlite3-*')) if p.is_file()]
    path=Path(sealed['path'])
    if file_hash(path)!=sealed['sha256']:raise ValueError('Sealed checkpoint bytes changed')
    if home.exists():raise ValueError('Checkpoint destination already exists')
    contents={}
    with zipfile.ZipFile(path) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)) or set(names)!={CHECKPOINT_META,*expected}:
            raise ValueError('Sealed checkpoint member set changed')
        manifest=json.loads(archive.read(CHECKPOINT_META))
        if manifest!={'format':'STEP2_CLOSED_CHECKPOINT_V1','files':expected}:raise ValueError('Sealed checkpoint manifest changed')
        for relative,sha in expected.items():
            checkpoint_path(home,relative)
            payload=archive.read(relative)
            if digest(payload)!=sha:raise ValueError('Sealed checkpoint payload changed: '+relative)
            contents[relative]=payload
    # Validate all bytes before writing even the first destination file.
    home.mkdir(parents=True)
    for relative,payload in contents.items():atomic_write(checkpoint_path(home,relative),payload)
    initialize(home);installed_links(home,installed)
    return {'method':'VERIFIED_CLOSED_MANIFEST','sealed_sha256':sealed['sha256'],'files_verified':len(contents),'excluded_unregistered_sidecars':sidecars}

def run_variant(home,fixture,variant,base_data,cfg):
    name,roles,channel,disable_state=variant;r=Runtime(home);row={'fixture':fixture['id'],'variant':name,'status':'RUNNING','raw_answer':'','offers':[]}
    started=time.monotonic();turn_deadline=started+cfg['deadline_seconds'];runner=None;mid=None
    row['turn_deadline_monotonic_ns']=int(turn_deadline*1e9)
    try:
        before=states(r);row['restart_state_identical']=same_persisted_state(before,base_data['state_before_restart']);row['model_revisions']=r.revisions()
        r.cfg['channel']=channel
        if disable_state:r.cfg['b2_state_slots']=0
        e=r.store.event(r.session,fixture['current']);row['event']=e;row['generation_before']=r.store.generation_id
        initial_b1=copy.deepcopy(before['B1_DETAIL'][0]);peer=None
        for index,role in enumerate(roles):
            if name=='same_policy_dual' and index==1:
                # Two native calls from independently reset identical prior state;
                # never let the first current offer become the second's history.
                r.store.set_state('B1_DETAIL:'+r.session,initial_b1)
            offer=r.cognition.offer(role,e,0,min(turn_deadline,time.monotonic()+cfg['observer_seconds']),peer=peer,valid_until=turn_deadline);row['offers'].append(offer)
            if len(roles)>1 and name!='same_policy_dual':peer=r.cognition.communicate(offer,'B2_GIST' if role=='B1_DETAIL' else 'B1_DETAIL')
        selected=r.cognition.focal(row['offers'],e,0);row['focal_offer_ids']=[o['packet_id'] for o in selected]
        refs=[e['source_ref']]
        for offer in selected:
            for ref in offer['provenance']+offer['evidence_refs']:
                r.store.read_source(ref)
                if ref not in refs:refs.append(ref)
        row['source_evidence']=[{'source_ref':ref,'text':r.store.read_source(ref)} for ref in refs]
        # No oracle, full prior, prior messages or hidden history are passed here.
        context={'current_source':fixture['current'],'analysts':[{'role':o['role'],'hypothesis':o['offer'],
                    'verified_quotes':[r.store.read_source(ref) for ref in o['evidence_refs']]} for o in selected]}
        messages=[{'role':'system','content':SYSTEM},{'role':'user','content':dumps(context)}]
        row['consumer_messages']=messages;row['consumer_role']='C3_LANGUAGE';row['consumer_schema_sha256']=digest(dumps(SCHEMA));row['oracle_visible_to_native']=False
        mid=r.store.message(r.session,e['event_id'],'assistant',status='DRAFT',metadata={'proof_kind':'STEP2_UTILITY','context_source_refs':refs})
        runner=r.pool.get('C3_LANGUAGE')
        for chunk in runner.generate(messages,r.cancel_event,turn_deadline,cfg['answer_tokens'],SCHEMA,seed=cfg['seed']):
            row['raw_answer']+=chunk;r.store.append_message(mid,chunk)
        row['native_consumer_metrics']=dict(runner.last_metrics);row['score']=score_decision(row['raw_answer'],fixture['oracle'])
        r.store.finish_message(mid,'FINAL',{'proof_kind':'STEP2_UTILITY','runner':row['native_consumer_metrics'],'context_source_refs':refs})
        row['checks']={'real_C3_final':runner.last_metrics.get('status')=='FINAL','restarted_exact_body_state':row['restart_state_identical'],
                       'generation_unchanged':row['generation_before']==r.store.generation_id,'integrity':not r.store.integrity(True),
                       'expected_offer_count':len(selected)==len(roles),'every_source_read_validated':True}
        row['status']='RECORDED' if all(row['checks'].values()) else 'STRUCTURAL_FAIL'
    except Exception as exc:
        row.update(status='ERROR',error_type=type(exc).__name__,error=str(exc)[:500],score={'utility':0.,'exact':False,'contradictions':['inference_or_structure_failed']})
        if mid:r.store.finish_message(mid,'ERROR',{'proof_kind':'STEP2_UTILITY','error_type':type(exc).__name__})
    finally:
        row['elapsed_s']=time.monotonic()-started
        if runner:row['native_consumer_metrics']=dict(runner.last_metrics)
        metrics=[o.get('native_metrics',{}) for o in row['offers']]+[row.get('native_consumer_metrics',{})]
        row['sampled_native_peak_rss_bytes']=max((m['sampled_peak_rss_bytes'] for m in metrics if m.get('sampled_peak_rss_bytes') is not None),default=None)
        r.close();row['process_releases']=list(r.pool.release_history)
        row['processes_reaped']=all(p['process_reaped'] for p in row['process_releases']) and bool(row['process_releases'])
        if not row['processes_reaped']:row['status']='STRUCTURAL_FAIL'
    return row

def checkpoint_hashes(home):
    return {str(p.relative_to(home)):file_hash(p) for p in sorted(home.rglob('*')) if p.is_file() and not p.is_symlink() and p.parts[len(home.parts)] not in CHECKPOINT_SKIP and p.name!='coordinator.lock' and not p.name.endswith(('-wal','-shm'))}

def validate_resume(old,current):
    for key in ('proof_kind','proof_version','source_hashes','fixture_sha256','variant_spec','config','device','installed_artifacts'):
        if dumps(old.get(key))!=dumps(current[key]):raise ValueError('Resume guard changed: '+key)
    existing={(r['fixture'],r['variant']) for r in old['rows']}
    if len(existing)!=len(old['rows']):raise ValueError('Duplicate earlier proof rows')
    for row in old['rows']:
        key=row['fixture']+':'+row['variant']
        if old.get('row_sha256',{}).get(key)!=digest(dumps(row)):raise ValueError('Earlier proof row bytes changed: '+key)
    return existing

def run(installed,out,fixture_limit=None,resume=False):
    installed=Path(installed).resolve();out=Path(out).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    if not resume:archive_previous(out)
    cfg=initialize(installed)|{'learning_mode':'RECORD_ONLY','teacher_enabled':False,'history_turns':0,'memory_top_k':0,'observer_mode':'off'}
    fixtures=FIXTURES if fixture_limit is None else FIXTURES[:fixture_limit]
    report={'proof_kind':'STEP2_PREREGISTERED_SEMANTIC_UTILITY','proof_version':3,'status':'RUNNING','device':device(),'phone_measured':device()['android'],
            'source_hashes':source_hashes(),'installed_artifacts':installed_artifacts(installed),'fixtures':FIXTURES,'fixture_sha256':digest(dumps(FIXTURES)),'variant_spec':VARIANTS,'rows':[],'row_sha256':{},'preparations':[],
            'config':cfg,'body_sampling_seed':13,'uses_real_weights':True,'full_runner_proof':False,'canonical_gate':'G-B-TIMESCALE-DIVERGENCE-001','canonical_gate_pass':False,
            'controls':{'same_model_same_policy':'same_policy_dual','same_model_prompt_only':'prompt_only_dual',
                        'shared_body_dual_timescale_state':'both_none with existing B1/B2 state policies and sequential same-file weight execution',
                        'true_distinct_weight_bodies':'UNAVAILABLE when installed B1/B2 SHA is identical'},
            'claim_limits':['This fixed ten-episode set cannot prove broad reasoning quality.','Shared GGUF bodies have distinct persisted state/prompt policies, not native sparse learning.',
                            'Cold sequential process RSS is measured; total-device bounded memory, sustained thermal/energy and target-phone retention are separate proofs.',
                            'No genuine distinct-body comparison exists unless distinct native model weights are installed.','Prompt-only control disables B2 retained-source context; B1 short prior hypothesis remains.',
                            'Each paired variant starts from a copy of the same genuinely generated prior and distractor state; prior cost is measured separately.']}
    def save():atomic_write(out,json.dumps(report,ensure_ascii=False,indent=2))
    work=out.with_suffix('.checkpoint')
    if resume:
        old=json.loads(out.read_text())
        existing=validate_resume(old,report)
        report=old;report['status']='RUNNING';report.setdefault('resume_segments',[]).append({'time':time.time(),'source_hashes':source_hashes()})
    else:
        if work.exists():
            archive=work.with_name(work.name+'.previous-'+str(time.time_ns()));work.rename(archive)
        existing=set()
    work.mkdir(parents=True,exist_ok=True);save()
    try:
        for fixture in fixtures:
            if all((fixture['id'],v[0]) in existing for v in VARIANTS):continue
            base=work/('base-'+fixture['id']);started=time.monotonic()
            prep=next((p for p in report['preparations'] if p['fixture']==fixture['id']),None)
            if prep is not None and prep['status']=='RECORDED':
                if not base.exists() or checkpoint_hashes(base)!=prep['checkpoint_hashes']:raise ValueError('Resume checkpoint bytes changed: '+fixture['id'])
                check_models=ModelManager(base)
                for role,expected in prep['model_sha256'].items():
                    if file_hash(check_models.path_for(role))!=expected:raise ValueError('Resume model bytes changed: '+role)
                if file_hash(Path(os.environ.get('V13_LLAMA_SERVER',str(installed/'bin/llama-server'))))!=prep['runner_sha256']:raise ValueError('Resume native runner bytes changed')
                if runtime_library_hashes(Path(os.environ.get('V13_LLAMA_SERVER',str(installed/'bin/llama-server'))))!=prep.get('runner_runtime_libraries_sha256',{}):
                    raise ValueError('Resume native runtime library bytes changed')
            if prep is None:
                if base.exists():base.rename(base.with_name(base.name+'.unfinished-preparation-'+str(time.time_ns())))
                try:
                    prep=prepare_base(base,installed,cfg,fixture);prep['checkpoint_hashes']=checkpoint_hashes(base)
                    if prep['status']=='RECORDED' and (prep['model_sha256']!=report['installed_artifacts']['model_sha256'] or prep['runner_sha256']!=report['installed_artifacts']['runner_sha256']):
                        prep.update(status='ERROR',error_type='ArtifactChanged',error='Native artifact changed during preparation')
                    if prep['status']=='RECORDED' and prep['runner_runtime_libraries_sha256']!=report['installed_artifacts']['runner_runtime_libraries_sha256']:
                        prep.update(status='ERROR',error_type='ArtifactChanged',error='Native runtime libraries changed during preparation')
                    if prep['status']=='RECORDED':prep['sealed_checkpoint']=seal_checkpoint(base,prep['checkpoint_hashes'])
                except Exception as exc:prep={'status':'ERROR','error_type':type(exc).__name__,'error':str(exc)[:500]}
                prep.update(fixture=fixture['id'],elapsed_s=time.monotonic()-started);report['preparations'].append(prep);save()
            for variant in VARIANTS:
                if (fixture['id'],variant[0]) in existing:continue
                print(dumps({'starting':fixture['id'],'variant':variant[0]}),flush=True)
                if prep['status']!='RECORDED':row={'fixture':fixture['id'],'variant':variant[0],'status':'ERROR','error':'native prior preparation failed','score':{'utility':0.,'exact':False}}
                else:
                    home=work/(fixture['id']+'-'+variant[0])
                    if home.exists():home.rename(home.with_name(home.name+'.interrupted-'+str(time.time_ns())))
                    try:
                        clone=clone_base(base,home,installed,prep['checkpoint_hashes'],prep['sealed_checkpoint']);row=run_variant(home,fixture,variant,prep,cfg);row['checkpoint_clone']=clone
                    except Exception as exc:
                        row={'fixture':fixture['id'],'variant':variant[0],'status':'ERROR','error_type':type(exc).__name__,'error':str(exc)[:500],
                             'score':{'utility':0.,'exact':False,'contradictions':['variant_startup_or_cleanup_failed']}}
                    if row['status']=='RECORDED':shutil.rmtree(home)
                    else:row['failed_checkpoint']=str(home)
                report['rows'].append(row);report['row_sha256'][fixture['id']+':'+variant[0]]=digest(dumps(row));save();print(dumps({'finished':fixture['id'],'variant':variant[0],'status':row['status'],'utility':row['score']['utility']}),flush=True)
            if prep['status']=='RECORDED':shutil.rmtree(base,ignore_errors=True)
            else:prep['failed_checkpoint']=str(base);save()
        report['paired']=paired_utility(report['rows'],[f['id'] for f in FIXTURES]);report['source_unchanged']=report['source_hashes']==source_hashes()
        report['installed_artifacts_unchanged']=report['installed_artifacts']==installed_artifacts(installed)
        report['all_structural_checks_passed']=report['source_unchanged'] and report['installed_artifacts_unchanged'] and all(r['status']=='RECORDED' for r in report['rows'])
        report['same_weight_file']=bool(report['preparations']) and all(p['status']=='RECORDED' and p['model_sha256']['B1_DETAIL']==p['model_sha256']['B2_GIST'] for p in report['preparations'])
        report['scoped_utility_gate_pass']=report['paired']['scoped_utility_gate_pass'] and report['all_structural_checks_passed']
        # WP-N11: with B2 = its own pinned weights (models.json 'gist'), both_* rows are the true two-body control.
        report['distinct_bodies']=bool(report['preparations']) and not report['same_weight_file']
        report['controls']['true_distinct_weight_bodies']='both_none/both_exact/both_control on distinct installed B1/B2 weights' if report['distinct_bodies'] else 'UNAVAILABLE when installed B1/B2 SHA is identical'
        # Current source intentionally does not synthesize the missing distinct-body control.
        report['status']='UTILITY_PASS_SCOPED' if report['scoped_utility_gate_pass'] else 'UTILITY_FAIL' if report['paired']['complete'] else 'DIAGNOSTIC_INCOMPLETE'
    except BaseException as exc:report.update(status='INTERRUPTED',error_type=type(exc).__name__);raise
    finally:save()
    return report

def run_locked(installed,out,fixture_limit=None,resume=False):
    # The installed runtime owns this same lock. Cloned fixture Stores have
    # independent locks; they do not exclude concurrent phone chat by themselves.
    installed=Path(installed).expanduser().resolve()
    with open(installed/'data/coordinator.lock','a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return run(installed,out,fixture_limit,resume)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--installed-home',required=True);parser.add_argument('--out',required=True);parser.add_argument('--fixtures',type=int,choices=range(1,11));parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    try:report=run_locked(args.installed_home,args.out,args.fixtures,args.resume)
    except BlockingIOError:
        print('STEP2 refused: close the active V13 chat before running the native comparison.',file=sys.stderr)
        return 1
    print(dumps({'status':report['status'],'artifact':str(Path(args.out).resolve()),'canonical_gate_pass':False}),flush=True)
    return 0 if report['status']=='UTILITY_PASS_SCOPED' else 2
if __name__=='__main__':sys.exit(main())
