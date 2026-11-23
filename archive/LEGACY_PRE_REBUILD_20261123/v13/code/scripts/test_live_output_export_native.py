#!/usr/bin/env python3
"""ONE actual isolated two-row export lifecycle, TEST_OPERATOR labels only.

Not a genuine end-user cohort, fit, quality improvement, approval or activation.
Two authored first-token classes are necessary to reach unchanged validation.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time
APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from scripts.export_live_output_dataset import capture,assemble
from scripts.train_live_output_adapter import validate_only
from v13.common import atomic_write,dumps,file_hash,digest
from v13.config import initialize
from v13.models import ModelManager
from v13.operator import Operator
from v13.runtime import Runtime
from v13.store import Store

REFERENCES=[('Protokolltest A: Antworte mit einer kurzen Begrüßung.','Ja, TEST_OPERATOR Referenz A.'),('Protokolltest B: Antworte mit einem kurzen Abschied.','Nein, TEST_OPERATOR Referenz B.')]

def save(path,value):atomic_write(path,dumps(value))

def collect(installed,out):
    installed=Path(installed).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    source_files=['scripts/export_live_output_dataset.py','scripts/test_live_output_export_native.py','scripts/train_live_output_adapter.py','scripts/native_prefill_stream_client.py','scripts/live_output_adapter_port.py']+[str(p.relative_to(APP)) for p in sorted((APP/'v13').glob('*.py'))]
    source_hashes={name:file_hash(APP/name) for name in source_files}
    report={'status':'ACTUAL_EXPORT_LIFECYCLE_STARTED','source_hashes':source_hashes,'scope':'TEST_OPERATOR_AUTHORED_REFERENCES_NOT_END_USER_COHORT','native_calls':False,'fit':False,'approval_authority':0,'production_activation':False,'examples':[]}
    runtime=None;started=time.monotonic();save(out/'report.json',report)
    try:
        home=out/'isolated-home';cfg=initialize(home);cfg.update(route_override='simple',observer_mode='off',threads=2,context_tokens=2048,answer_tokens=16)
        save(home/'config/settings.json',cfg)
        # Immutable shared prepared installation, independent actual Store.
        shutil.rmtree(home/'bin');(home/'bin').symlink_to(installed/'bin',target_is_directory=True)
        models=json.loads((installed/'config/models.json').read_text())
        for model in models.values():
            for item in model['files'].values():item['path']=str(installed/item['path'])
        save(home/'config/models.json',models)
        for name in ('runner.json','native-prefill-stream.json'):shutil.copyfile(installed/'config'/name,home/'config'/name)
        installed_models=ModelManager(installed)
        report['installed_model_files']={str(installed/item['path']):file_hash(installed/item['path']) for model in installed_models.installed.values() for item in model['files'].values()}
        selected=[];runtime=Runtime(home);operator=Operator(runtime)
        for query,label in REFERENCES:
            eid=runtime.submit(query);wait_until=time.monotonic()+105;report['native_calls']=True
            while not runtime.idle():
                if time.monotonic()>=wait_until:runtime.cancel();raise RuntimeError('Actual Runtime turn exceeded existing90s deadline plus cleanup')
                time.sleep(.05)
            answer=runtime.last_answer()
            if not answer or answer['event_id']!=eid or answer['status']!='FINAL':raise RuntimeError('Actual ordinary Runtime FINAL answer missing')
            reply=operator.run(':feedback output '+json.dumps(label)+' --learn')
            row=runtime.store.one("SELECT id,payload FROM packets WHERE kind='HumanDecision' AND event_id=? AND json_extract(payload,'$.kind')='output' ORDER BY created DESC LIMIT 1",(eid,))
            if not row:raise RuntimeError('Actual typed output reference missing')
            decision=json.loads(row['payload']);selected.append((row['id'],decision['source_ref']['source_id']))
            report['examples'].append({'event_id':eid,'source_query':query,'authored_label':label,'label_origin':'TEST_OPERATOR_AUTHORED_BEFORE_NATIVE_EXPORT_NOT_MODEL_PREVIEW','runtime_answer':answer['text'],'runtime_status':answer['status'],'operator_command':':feedback output <authored TEST_OPERATOR reference> --learn','operator_reply':reply,'decision_packet_id':row['id'],'original_payload_sha256':digest(row['payload']),'label_source_id':decision['source_ref']['source_id']})
            save(out/'report.json',report)
        runtime.close();runtime=None;fragments=[]
        for i,(decision,source) in enumerate(selected):
            exported=capture(home,out/('example-'+str(i)),decision,source,True)
            report['examples'][i]['export_status']=exported['status'];report['examples'][i]['capture_report_sha256']=file_hash(out/('example-'+str(i))/'capture-report.json');fragments.append(out/('example-'+str(i))/'fragment.json');save(out/'report.json',report)
        assembled=assemble(fragments,out/'cohort');validated=validate_only(out/'cohort/dataset.json',out/'validate-only')
        with_store=Store(home)
        try:
            report['original_packets_unchanged']=all(digest(with_store.one('SELECT payload FROM packets WHERE id=?',(item['decision_packet_id'],))['payload'])==item['original_payload_sha256'] for item in report['examples'])
        finally:with_store.close()
        checks={'two_actual_exports':all(item.get('export_status')=='ACTUAL_CAUSAL_LABEL_EXPORTED' for item in report['examples']),
                'native_template_and_worker_reaped':all(json.loads((out/('example-'+str(i))/'capture-report.json').read_text())['template_release']['process_reaped'] and json.loads((out/('example-'+str(i))/'capture-report.json').read_text())['session_metrics']['process_reaped'] for i in range(2)),
                'original_packets_unchanged':report['original_packets_unchanged'],
                'source_unchanged':all(file_hash(APP/name)==sha for name,sha in source_hashes.items()),
                'installed_models_unchanged':all(file_hash(path)==sha for path,sha in report['installed_model_files'].items()),
                'assembled':assembled['status']=='ASSEMBLED_VALIDATED_NO_TRAINING',
                'honest_incomplete_cohort':validated['status']=='INSUFFICIENT_LABELLED_COHORT' and validated['optimizer_steps']==0}
        report.update(checks=checks,assembly=assembled,validation=validated,status='TEST_OPERATOR_EXPORT_LIFECYCLE_PASS' if all(checks.values()) else 'TEST_OPERATOR_EXPORT_LIFECYCLE_FAIL')
        return 0 if all(checks.values()) else 1
    except BaseException as exc:report.update(status='TEST_OPERATOR_EXPORT_LIFECYCLE_FAIL',error_type=type(exc).__name__,error=str(exc));return 1
    finally:
        if runtime is not None:runtime.close()
        report['elapsed_s']=time.monotonic()-started;save(out/'report.json',report);print(dumps({'status':report['status'],'report':str(out/'report.json'),'scope':report['scope']}),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--installed-home',required=True);p.add_argument('--out',required=True);a=p.parse_args();return collect(a.installed_home,a.out)
if __name__=='__main__':sys.exit(main())
