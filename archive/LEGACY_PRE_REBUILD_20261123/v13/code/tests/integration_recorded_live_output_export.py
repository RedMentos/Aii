#!/usr/bin/env python3
"""Preregistered two-row actual TEST_OPERATOR diagnostic. Run only after slot grant."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time
APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
from v13.common import atomic_write,dumps,file_hash
from v13.runtime import Runtime
from v13.causal_prepare import check_prepared
from scripts import export_recorded_live_output_dataset as recorded
from scripts.export_live_output_dataset import assemble
from scripts.train_live_output_adapter import validate_only
from v13.resources import device

# Exact first pair of the existing original integration_output_adapter corpus.
CORPUS=(('Begrüße Gast 1 kurz.','Hallo'),('Bedanke dich kurz für Hilfe beim Projekt 1.','Danke'))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--home',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    installed=args.home.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);home=out/'isolated-home';(home/'config').mkdir(parents=True)
    (home/'bin').symlink_to(installed/'bin',target_is_directory=True)
    for name in ('runner.json','native-prefill-stream.json','settings.json'):shutil.copyfile(installed/'config'/name,home/'config'/name)
    models=json.loads((installed/'config/models.json').read_text())
    for model in models.values():
        for artifact in model['files'].values():artifact['path']=str(installed/artifact['path'])
    atomic_write(home/'config/models.json',dumps(models))
    binding=check_prepared(home);started=time.monotonic();overall=started+420;runtime=None;fragments=[]
    report={'status':'RUNNING','scope':'AUTHORED_TEST_OPERATOR_DIAGNOSTIC_NOT_GENUINE_ENDUSER_COHORT','device':device(),'native_calls':True,'approval_authority':0,'optimizer_steps':0,'seconds_limit':420,'corpus':list(CORPUS),'rows':[],'source_sha256':{str(p.relative_to(APP)):file_hash(p) for p in [*sorted((APP/'v13').glob('*.py')),APP/'scripts/export_recorded_live_output_dataset.py',APP/'scripts/export_live_output_dataset.py',APP/'scripts/train_live_output_adapter.py',Path(__file__).resolve()]}}
    def save():atomic_write(out/'report.json',dumps(report))
    save()
    try:
        for index,(query,label) in enumerate(CORPUS):
            if time.monotonic()+5>=overall:raise RuntimeError('Preregistered overall deadline reached')
            runtime=Runtime(home);runtime.cfg.update(c3_decode_mode='same_causal_zero',answer_tokens=64,route_override='simple',observer_mode='off',history_turns=0,deadline_seconds=min(90,int(overall-time.monotonic()-10)))
            runtime.session=runtime.store.new_session('TEST_OPERATOR recorded export diagnostic '+str(index));event=runtime.submit(query);end=min(overall,time.monotonic()+100)
            while not runtime.idle() and time.monotonic()<end:time.sleep(.05)
            if not runtime.idle():runtime.cancel();raise RuntimeError('Actual coordinator deadline reached')
            answer=runtime.last_answer();meta=json.loads(answer['metadata'])
            if answer['status']!='FINAL' or answer['event_id']!=event or meta.get('model_generated') is not True:raise RuntimeError('Actual completed native Runtime answer missing')
            runtime.learner.output_feedback(event,label,'learn')
            decision=json.loads(runtime.store.one("SELECT payload FROM packets WHERE kind='HumanDecision' AND event_id=? AND json_extract(payload,'$.kind')='output' AND json_extract(payload,'$.export_binding') IS NULL ORDER BY created DESC LIMIT 1",(event,))['payload'])
            row={'query':query,'reference':label,'reference_origin':'PREREGISTERED_AUTHORED_TEST_OPERATOR','event_id':event,'actual_output':answer['text'],'answer_status':answer['status'],'metadata':meta,'decision':decision};report['rows'].append(row);save();runtime.close();runtime=None
            token_report=recorded.tokenize_label(home,out/('tokenizer-'+str(index)),decision['packet_id'],decision['source_ref']['source_id'],True,seconds=min(30,int(overall-time.monotonic())),rss_mb=768);row['tokenizer_report']=token_report;save()
            export_report=recorded.export_recorded(home,out/('export-'+str(index)),decision['packet_id'],decision['source_ref']['source_id'],out/('tokenizer-'+str(index))/'receipt.json',True,seconds=min(90,int(overall-time.monotonic())));row['export_report']=export_report;fragments.append(out/('export-'+str(index))/'fragment.json');save()
        report['assembly']=assemble(fragments,out/'dataset');report['unchanged_cohort_validation']=validate_only(out/'dataset/dataset.json',out/'validation')
        report['checks']={'two_actual_runtime_contexts':len(report['rows'])==2,'completed_reaped_original_contexts':all(row['metadata']['runner']['process_reaped'] is True and row['metadata']['runner']['causal_controller']['status']=='SAME_CONTEXT_STREAM_COMPLETE' for row in report['rows']),
            'zero_export_native_calls':all(row['export_report']['native_calls'] is False and row['export_report']['prefill_calls']==0 for row in report['rows']),
            'actual_label_tokenizer_reaped':all(row['tokenizer_report']['status']=='ACTUAL_LABEL_TOKENIZED_REAPED' and row['tokenizer_report']['release']['process_reaped'] is True for row in report['rows']),
            'original_dataset_schema_usable':report['assembly']['status']=='ASSEMBLED_VALIDATED_NO_TRAINING','insufficient_cohort_no_optimizer':report['unchanged_cohort_validation']['status']=='INSUFFICIENT_LABELLED_COHORT' and report['unchanged_cohort_validation']['optimizer_steps']==0,
            'unchanged_native_model':file_hash(binding['identity']['model_path'])==binding['identity']['model_sha256'],'source_unchanged':all(file_hash(APP/p)==sha for p,sha in report['source_sha256'].items()),'overall_budget':time.monotonic()<overall}
        report['status']='ACTUAL_RECORDED_EXPORT_LIFECYCLE_PASS' if all(report['checks'].values()) else 'ACTUAL_RECORDED_EXPORT_LIFECYCLE_FAIL';save();print(dumps({'status':report['status'],'proof_path':str(out/'report.json'),'checks':report['checks']}),flush=True);return 0 if all(report['checks'].values()) else 2
    except BaseException as exc:
        report.update(status='ACTUAL_RECORDED_EXPORT_LIFECYCLE_ERROR',error_type=type(exc).__name__,error=str(exc));save();raise
    finally:
        if runtime:runtime.close()
        report['elapsed_s']=time.monotonic()-started;save()

if __name__=='__main__':sys.exit(main())
