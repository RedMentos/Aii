#!/usr/bin/env python3
"""Resumable, isolated TEST_OPERATOR causal-output diagnostic; never user approval.

prepare/check are read-only with respect to installed native weights. collect and
consume really run the original coordinator; fit is the unchanged offline fitter.
An evaluated failure or ambiguous interrupted native turn is terminal evidence.
"""
import argparse
import fcntl
import json
from pathlib import Path
import shutil
import signal
import sys
import time

APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
from v13.common import atomic_write,dumps,digest,file_hash
from v13.config import initialize,save_config
from v13.causal_prepare import check_prepared
from v13.runtime import Runtime
from v13.operator import Operator
from v13.store import Store,audit_closed,preserve_sqlite
from v13.models import ModelManager
from scripts import export_recorded_live_output_dataset as recorded
from scripts import export_live_output_dataset as export
from scripts.train_live_output_adapter import train_dataset,artifact

SCHEMA='V13_ISOLATED_CAUSAL_OUTPUT_DIAGNOSTIC_V1'
FIXTURE_SHA='16620bd434f77b84c3d6bdd9493424fb03935498f91b9e7ac3d60e02ac324f80'
ORIGINAL_SHA='aff703eb248450f49d49af8dc7e86a50856ed946b0a8c59ecf43a6636bcee6a0'
PROPOSAL=APP/'docs/proofs/causal-output-lifecycle-20261009/native-fixture-proposal.json'
SCOPE='PREAUTHORED_TEST_OPERATOR_DIAGNOSTIC_REFERENCE_NOT_GENUINE_USER'
KNOBS=('output_adapter_steps','output_adapter_lr','max_update_norm','retention_max_delta','output_adapter_max_bias','output_adapter_support_cosine')

def read(path):return json.loads(Path(path).read_text())
def write(path,value):atomic_write(Path(path),dumps(value))

def fixture():
    proposal=read(PROPOSAL);rows=[]
    if file_hash(APP/'tests/integration_output_adapter.py')!=ORIGINAL_SHA:raise ValueError('Original preregistered corpus changed')
    for i in range(23):
        for target,text in enumerate((f'Begrüße Gast {i+1} kurz.',f'Bedanke dich kurz für Hilfe beim Projekt {i+1}.')):
            group=digest(text);rows.append({'input':text,'human_reference':('Hallo','Danke')[target],'source_sha256':group,'target_class':target,'fold':int(digest(group)[:8],16)%5})
    if rows!=proposal['rows'] or digest(dumps(rows))!=FIXTURE_SHA or proposal['query_list_sha256']!=FIXTURE_SHA:raise ValueError('Fixed46 predeclared corpus/hash differs')
    return rows

def sources():
    files=list((APP/'v13').glob('*.py'))+[APP/p for p in (
        'tests/integration_causal_output_lifecycle.py','tests/integration_output_adapter.py',
        'scripts/export_recorded_live_output_dataset.py','scripts/export_live_output_dataset.py',
        'scripts/train_live_output_adapter.py','scripts/live_output_adapter_port.py',
        'scripts/native_prefill_stream_client.py','scripts/test_native_prefill_stream.py',
        'scripts/test_native_prefill_port.py','specs/models.json')]
    files+=list((APP/'scripts').glob('native_prefill*.cpp'))
    return {str(p.relative_to(APP)):file_hash(p) for p in sorted(set(files))}

def canonical_binding(binding):
    # Alias paths must resolve to the SAME exact pinned executable; never omit it.
    return {**binding,'binary':str(Path(binding['binary']).resolve(strict=True))}

def prepare(installed,out):
    installed=Path(installed).resolve(strict=True);out=Path(out).resolve()
    if out.exists():raise ValueError('Fresh diagnostic directory required; use check/collect to resume')
    rows=fixture();binding=canonical_binding(check_prepared(installed));out.mkdir(parents=True)
    home=out/'isolated-home';(home/'config').mkdir(parents=True)
    (home/'bin').symlink_to(installed/'bin',target_is_directory=True)
    for name in ('runner.json','native-prefill-stream.json','settings.json'):shutil.copyfile(installed/'config'/name,home/'config'/name)
    models=read(installed/'config/models.json')
    for model in models.values():
        for entry in model['files'].values():entry['path']=str((installed/entry['path']).resolve(strict=True))
    write(home/'config/models.json',models);cfg=initialize(home)
    cfg.update(history_turns=0,observer_mode='off',route_override='simple',answer_tokens=64,threads=2,c3_decode_mode='same_causal_zero',learning_mode='RECORD_ONLY')
    save_config(home,cfg)
    if canonical_binding(check_prepared(home))!=binding:raise ValueError('Private installed identity differs; no alias bypass')
    manifest={'schema':SCHEMA,'scope':SCOPE,'rows':rows,'fixture_sha256':FIXTURE_SHA,'source_sha256':sources(),'binding':binding,'configuration':cfg,
        'installed_home':str(installed),'model_manifest_sha256':file_hash(home/'config/models.json'),
        'installation_receipts':{name:file_hash(home/'config'/name) for name in ('runner.json','native-prefill-stream.json')},
        'native_collection_limit':46,'approval_scope':'Only explicit consume --test-approval in this isolated Store after unchanged actual fit gates; no user authorization'}
    write(out/'manifest.json',manifest)
    write(out/'report.json',{'schema':SCHEMA,'manifest_sha256':file_hash(out/'manifest.json'),'scope':SCOPE,'status':'PREDECLARED_NO_NATIVE_CALLS','rows':[],
        'native_calls':0,'label_tokenizer_calls':0,'approval_authority':0,'configuration':cfg,'consumers':[]})
    return manifest

def verify(out):
    out=Path(out).resolve(strict=True);manifest=read(out/'manifest.json');report=read(out/'report.json');home=out/'isolated-home'
    if manifest.get('schema')!=SCHEMA or report.get('schema')!=SCHEMA or report['manifest_sha256']!=file_hash(out/'manifest.json'):raise ValueError('Original diagnostic manifest changed')
    if manifest['rows']!=fixture() or manifest['fixture_sha256']!=FIXTURE_SHA or manifest['source_sha256']!=sources():raise ValueError('Frozen diagnostic source/corpus changed')
    if canonical_binding(check_prepared(home))!=manifest['binding']:raise ValueError('Prepared worker/model/library/source binding changed')
    if file_hash(home/'config/models.json')!=manifest['model_manifest_sha256'] or any(file_hash(home/'config'/n)!=h for n,h in manifest['installation_receipts'].items()):raise ValueError('Private installation receipts changed')
    if read(home/'config/settings.json')!=report['configuration']:raise ValueError('Exact diagnostic configuration changed')
    expected=dict(manifest['configuration'])
    fitted=report.get('fit',{})
    if fitted.get('stage') in {'EVALUATED','PENDING_APPROVAL'} and fitted.get('report',{}).get('metrics',{}).get('commit_eligible') is True:expected['learning_mode']='SHADOW_UPDATE'
    if report.get('consume_started'):
        if fitted.get('stage')!='PENDING_APPROVAL':raise ValueError('Consume transition without original gated candidate')
        expected.update(learning_mode='APPROVED_COMMIT',c3_decode_mode='same_causal')
    if report['configuration']!=expected:raise ValueError('Immutable preregistered config/optimizer knobs or exact stage modes changed')
    validate_progress(report,manifest['rows'])
    for row in report['rows']:
        if row.get('raw_sha256'):
            raw=out/row['raw_directory']
            if raw.parent!=out or not raw.name.startswith('raw-row-') or raw.is_symlink() or any(file_hash(raw/n)!=h for n,h in row['raw_sha256'].items()):raise ValueError('Permanent actual raw turn changed')
        if row.get('fragment_sha256'):
            folder=out/row['fragment_directory'];fragment=read(folder/'fragment.json')
            if file_hash(folder/'fragment.json')!=row['fragment_sha256'] or fragment['recorded_runtime_evidence']['prefill_calls']!=0:raise ValueError('Completed portable recorded fragment changed')
            for entry in fragment['observation'].values():artifact(folder,entry)
            for entry in fragment['recorded_runtime_evidence']['raw_artifacts'].values():artifact(folder,entry)
            for name in ('original_human_decision','original_context_packet','original_event'):artifact(folder,fragment[name])
            artifact(folder,fragment['recorded_runtime_evidence']['tokenizer_receipt'])
    # Before fitting/approval, also verify current original F5 authority in the
    # same isolated database. Portable copies cannot impersonate deleted labels.
    if report['rows'] and not report.get('consume_started'):
        store=Store(home)
        try:
            revision=ModelManager(home).revision('C3_LANGUAGE')
            for row in report['rows']:
                if row['stage']=='EXPORTED':
                    selected=export.select_label(store,row['decision_id'],row['label_source_id'],revision,True)
                    if selected['label']!=row['fixture']['human_reference'] or selected['query']!=row['fixture']['input']:raise ValueError('Current original F5 query/label differs from predeclared row')
        finally:store.close()
    return manifest,report,home

def validate_progress(report,rows):
    if report.get('error') or report['status'] in {'EVALUATED_FAIL','DIAGNOSTIC_FAILED'}:raise ValueError('Prior evaluated failure is terminal; preserve attempt, do not retune/retry')
    if not isinstance(report['rows'],list) or len(report['rows'])>len(rows):raise ValueError('Invalid diagnostic progress')
    for i,row in enumerate(report['rows']):
        if row.get('index')!=i or row.get('fixture')!=rows[i]:raise ValueError('Resume must preserve exact original-order prefix')
        if i<len(report['rows'])-1 and row.get('stage')!='EXPORTED':raise ValueError('Unfinished earlier row cannot be skipped')

def save_report(out,report):write(Path(out)/'report.json',report)

def guard_closed(out,home,row,boundary):
    """Integrity probe after each Store close; first failure keeps DB+WAL+SHM untouched."""
    audit=audit_closed(home);row.setdefault('sqlite_boundaries',[]).append(dict(audit,boundary=boundary))
    if not audit['ok']:
        folder=Path(out)/('sqlite-boundary-failure-row-'+str(row['index'])+'-'+boundary)
        if not folder.exists():preserve_sqlite(home,folder)
        raise ValueError('SQLite integrity failed after '+boundary+'; database and sidecars preserved')
    return audit

def wait_answer(runtime,event_id):
    end=time.monotonic()+runtime.cfg['deadline_seconds']+15
    while not runtime.idle() and time.monotonic()<end:time.sleep(.05)
    if not runtime.idle():runtime.cancel();raise RuntimeError('Coordinator exceeded absolute deadline plus cleanup')
    answer=runtime.store.one("SELECT * FROM messages WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1",(event_id,))
    if not answer:raise ValueError('Actual accepted native turn has no persisted answer; ambiguous interruption is retained')
    meta=json.loads(answer['metadata']);runner=meta.get('runner',{});controller=runner.get('causal_controller',{})
    if answer['status']!='FINAL' or meta.get('model_generated') is not True or runner.get('process_reaped') is not True or controller.get('status')!='SAME_CONTEXT_STREAM_COMPLETE' or not controller.get('checks') or not all(x is True for x in controller['checks'].values()) or runtime.pool.pids():raise ValueError('Actual completed checked and reaped native answer required')
    return dict(answer),meta

def preserve(out,row,meta):
    source=Path(meta['runner']['artifact_directory']);destination=Path(out)/('raw-row-'+str(row['index']))
    if destination.exists():
        if {p.name:file_hash(p) for p in source.iterdir() if p.is_file()}!={p.name:file_hash(p) for p in destination.iterdir() if p.is_file()}:raise ValueError('Preserved raw turn changed')
    else:shutil.copytree(source,destination)
    row['raw_directory']=destination.name;row['raw_sha256']={p.name:file_hash(p) for p in destination.iterdir() if p.is_file()}

def collect(out,limit):
    manifest,report,home=verify(out);out=Path(out)
    if type(limit) is not int or not 1<=limit<=46 or limit<len(report['rows']):raise ValueError('Absolute row-limit1..46 cannot truncate completed evidence')
    if report.get('fit'):raise ValueError('Collection is frozen once fit starts')
    runtime=None
    try:
        while len(report['rows'])<limit or (report['rows'] and report['rows'][-1]['stage']!='EXPORTED'):
            if not report['rows'] or report['rows'][-1]['stage']=='EXPORTED':
                i=len(report['rows']);report['rows'].append({'index':i,'fixture':manifest['rows'][i],'stage':'PREPARED'});save_report(out,report)
            row=report['rows'][-1];runtime=Runtime(home)
            if row['stage']=='PREPARED':
                # Accepted input is checkpointed immediately; no second input on resume.
                before=runtime.store.one('SELECT count(*) AS n FROM events')['n']
                if before!=row['index']:raise ValueError('Untracked accepted turn: refuse ambiguous native retry')
                row['event_id']=runtime.submit(row['fixture']['input']);row['stage']='ACCEPTED';report['native_calls']+=1;save_report(out,report)
            if row['stage']=='ACCEPTED':
                answer,meta=wait_answer(runtime,row['event_id']);row['answer']={**answer,'metadata':meta};preserve(out,row,meta)
                row['stage']='ANSWERED';save_report(out,report)
            if row['stage']=='ANSWERED':
                existing=runtime.store.one("SELECT payload FROM packets WHERE kind='HumanDecision' AND event_id=? AND json_extract(payload,'$.export_binding') IS NULL ORDER BY created DESC LIMIT 1",(row['event_id'],))
                if not existing:runtime.learner.output_feedback(row['event_id'],row['fixture']['human_reference'],'learn')
                decision=json.loads(runtime.store.one("SELECT payload FROM packets WHERE kind='HumanDecision' AND event_id=? AND json_extract(payload,'$.export_binding') IS NULL ORDER BY created DESC LIMIT 1",(row['event_id'],))['payload'])
                if decision['value']!=row['fixture']['human_reference'] or decision['learning_permission']!='learn':raise ValueError('Authored original reference/permission differs')
                row.update(decision_id=decision['packet_id'],label_source_id=decision['source_ref']['source_id'],stage='LABELLED');save_report(out,report)
            revision=runtime.models.revision('C3_LANGUAGE');checkpoint=runtime.store;runtime.close();runtime=None
            row['runtime_close_checkpoint']=list(getattr(checkpoint,'last_checkpoint',()) or ());guard_closed(out,home,row,'runtime-close')
            receipt=out/('tokenizer-'+str(row['fixture']['target_class']))/'receipt.json'
            if not receipt.exists():
                recorded.tokenize_label(home,receipt.parent,row['decision_id'],row['label_source_id'],True);report['label_tokenizer_calls']+=1;save_report(out,report);guard_closed(out,home,row,'tokenizer-close')
            tokens=recorded.validate_receipt(receipt,row['fixture']['human_reference'],manifest['binding'],revision)['token_ids']
            other=out/('tokenizer-'+str(1-row['fixture']['target_class']))/'receipt.json'
            if other.exists() and read(other)['response']['tokens'][0]==tokens[0]:raise ValueError('Fixed Hallo/Danke native first IDs collide; do not substitute labels')
            folder=out/('export-row-'+str(row['index']))
            if folder.exists():
                if not (folder/'recorded-export-report.json').exists() or read(folder/'recorded-export-report.json')['status']!='RECORDED_CAUSAL_LABEL_EXPORTED':raise ValueError('Interrupted/rejected export evidence retained; no overwrite')
            else:recorded.export_recorded(home,folder,row['decision_id'],row['label_source_id'],receipt,True);guard_closed(out,home,row,'export-close')
            row.update(stage='EXPORTED',fragment_directory=folder.name,fragment_sha256=file_hash(folder/'fragment.json'),target_token_id=tokens[0]);report['status']='COLLECTED_COMPLETE_NO_FIT' if len(report['rows'])==46 else 'COLLECTED_PARTIAL_NO_FIT';save_report(out,report)
            verify(out)
        return report
    except BaseException as exc:
        report.update(status='DIAGNOSTIC_FAILED',error={'phase':'collect','type':type(exc).__name__,'message':str(exc)});save_report(out,report);raise
    finally:
        if runtime:runtime.close()

def fit(out):
    manifest,report,home=verify(out);out=Path(out)
    if len(report['rows'])!=46 or any(r['stage']!='EXPORTED' for r in report['rows']):raise ValueError('All exact46 actual recorded rows required before unchanged fit')
    if report.get('fit'):raise ValueError('Prior fit attempt retained; no repeated or retuned fit')
    report['fit']={'stage':'STARTED'};save_report(out,report)
    runtime=None
    try:
        export.assemble([out/r['fragment_directory']/'fragment.json' for r in report['rows']],out/'cohort',{k:report['configuration'][k] for k in KNOBS})
        result=train_dataset(out/'cohort/dataset.json',out/'fitted');report['fit'].update(stage='EVALUATED',report=result);save_report(out,report)
        if result['metrics']['commit_eligible'] is not True:report['status']='EVALUATED_FAIL';save_report(out,report);return report
        cfg=report['configuration'];cfg['learning_mode']='SHADOW_UPDATE';save_config(home,cfg);save_report(out,report)
        runtime=Runtime(home);base=runtime.store.generation_id;runtime.learner.import_causal_output(out/'cohort/dataset.json',out/'fitted')
        update=runtime.store.one('SELECT * FROM updates ORDER BY created DESC LIMIT 1')
        if not update or update['status']!='PENDING_APPROVAL' or runtime.store.generation_id!=base:raise ValueError('Exact independently verified pending candidate absent')
        report['fit'].update(stage='PENDING_APPROVAL',update_id=update['id'],base_generation=base,manifest=json.loads(update['manifest']));report['status']='PENDING_ISOLATED_TEST_APPROVAL';save_report(out,report);return report
    except BaseException as exc:
        report.update(status='DIAGNOSTIC_FAILED',error={'phase':'fit','type':type(exc).__name__,'message':str(exc)});save_report(out,report);raise
    finally:
        if runtime:runtime.close()

def consume(out,test_approval=False):
    manifest,report,home=verify(out);out=Path(out)
    if test_approval is not True or report.get('fit',{}).get('stage')!='PENDING_APPROVAL':raise ValueError('Explicit --test-approval and original unchanged gated pending fit required')
    if report.get('consume_started'):raise ValueError('Prior consume attempt retained; no ambiguous approval/native retry')
    report['consume_started']=True;report['test_approval_scope']=SCOPE;save_report(out,report);runtime=None
    try:
        cfg=report['configuration'];cfg.update(learning_mode='APPROVED_COMMIT',c3_decode_mode='same_causal');save_config(home,cfg);save_report(out,report)
        runtime=Runtime(home);update=report['fit']['update_id'];Operator(runtime).run(':approve '+update);generation=runtime.store.generation_id;session=runtime.session;runtime.close();runtime=Runtime(home)
        checks={'approved_restart':runtime.store.generation_id==generation and runtime.session==session and runtime.learner.active('output_adapter') is not None};report['checks']=checks;save_report(out,report)
        for index in report['fit']['report']['metrics']['partition']['test']:
            item=report['rows'][index];eid=runtime.submit(item['fixture']['input']);report['native_calls']+=1;save_report(out,report);answer,meta=wait_answer(runtime,eid)
            proof={'index':index,'event_id':eid,'answer':{**answer,'metadata':meta},'first_token_correct':meta['runner']['native_token_ids'][0]==item['target_token_id']}
            raw=out/('heldout-'+str(index));shutil.copytree(meta['runner']['artifact_directory'],raw);proof['raw_sha256']={p.name:file_hash(p) for p in raw.iterdir() if p.is_file()}
            report['consumers'].append(proof);save_report(out,report)
        consumers=report['consumers'];checks['heldout_first_token_accuracy']=sum(r['first_token_correct'] for r in consumers)/len(consumers)>=.8
        checks['individually_approved_same_context']=all(r['answer']['metadata']['runner'].get('approved_update_id')==update and r['answer']['metadata']['runner'].get('same_context_lifetime') is True and r['answer']['metadata']['runner'].get('resume_prefill_calls')==0 for r in consumers)
        checks['remaining_positions_unbiased']=all(r['answer']['metadata']['runner'].get('unbiased_continuation_steps')==max(0,len(r['answer']['metadata']['runner']['native_token_ids'])-1) for r in consumers);save_report(out,report)
        if not all(checks.values()):raise ValueError('Actual held-out consumer failed; stop without retuning')
        first=report['rows'][0];runtime.learner.output_feedback(first['event_id'],first['fixture']['human_reference'],'record')
        for phase in ('revocation','rollback'):
            if phase=='rollback':runtime.store.rollback(update)
            eid=runtime.submit(first['fixture']['input']);report['native_calls']+=1;save_report(out,report);answer,meta=wait_answer(runtime,eid)
            raw=out/phase;shutil.copytree(meta['runner']['artifact_directory'],raw)
            report[phase]={'event_id':eid,'answer':{**answer,'metadata':meta},'raw_sha256':{p.name:file_hash(p) for p in raw.iterdir() if p.is_file()}}
            checks[phase+'_zero_fallback']=meta['runner'].get('learned_head_loaded') is False and read(raw/'result.json').get('bias_applied_positions')==0
            if phase=='rollback':checks['rollback_component_absent']=runtime.learner.active('output_adapter') is None
            save_report(out,report)
        checks['unchanged_native_weights']=file_hash(manifest['binding']['identity']['model_path'])==manifest['binding']['identity']['model_sha256'];checks['store_integrity']=runtime.store.integrity(True)==[]
        report['status']='ISOLATED_TEST_OPERATOR_LIFECYCLE_PASS' if all(checks.values()) else 'DIAGNOSTIC_FAILED';save_report(out,report);return report
    except BaseException as exc:
        report.update(status='DIAGNOSTIC_FAILED',error={'phase':'consume','type':type(exc).__name__,'message':str(exc)});save_report(out,report);raise
    finally:
        if runtime:runtime.close()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=('prepare','check','collect','fit','consume'));parser.add_argument('--out',type=Path,required=True);parser.add_argument('--installed-home',type=Path);parser.add_argument('--row-limit',type=int,default=46);parser.add_argument('--test-approval',action='store_true');args=parser.parse_args()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    # Convert process-stop signals to Python unwinding so Runtime.close reaps
    # native children. Such an interrupted accepted row remains terminal proof.
    def interrupted(signum,frame):raise KeyboardInterrupt('Diagnostic interrupted by signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted)
    with (args.out.parent/('.'+args.out.name+'-diagnostic.lock')).open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.phase=='prepare':
            if args.installed_home is None:parser.error('prepare requires --installed-home')
            prepare(args.installed_home,args.out);result=read(args.out/'report.json')
        elif args.phase=='check':result=verify(args.out)[1]
        elif args.phase=='collect':result=collect(args.out,args.row_limit)
        elif args.phase=='fit':result=fit(args.out)
        else:result=consume(args.out,args.test_approval)
    print(dumps({'status':result['status'],'scope':SCOPE,'rows':len(result['rows']),'report':str(args.out/'report.json')}));return 2 if result['status'] in {'EVALUATED_FAIL','DIAGNOSTIC_FAILED'} else 0

if __name__=='__main__':raise SystemExit(main())
