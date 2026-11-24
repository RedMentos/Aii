#!/usr/bin/env python3
"""One actual opt-in coordinator turn. Compilation and mocks are not native proof."""
import argparse
import json
import os
import shutil
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.common import atomic_write,dumps,file_hash,digest,APP
from v13.runtime import Runtime
from v13.config import home_path


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--home',type=Path,required=True);args=ap.parse_args()
    installed=home_path(args.home)
    from v13.causal_prepare import check_prepared
    out=installed/'exports'/('causal-runtime-'+str(time.time_ns()));out.mkdir()
    home=out/'isolated-home';(home/'config').mkdir(parents=True)
    (home/'bin').symlink_to(installed/'bin',target_is_directory=True)
    for filename in ['runner.json','native-prefill-stream.json','settings.json']:
        shutil.copyfile(installed/'config'/filename,home/'config'/filename)
    models=json.loads((installed/'config/models.json').read_text())
    for model in models.values():
        for artifact in model['files'].values():artifact['path']=str(installed/artifact['path'])
    atomic_write(home/'config/models.json',dumps(models))
    report={'status':'STARTED','scope':'ACTUAL_OPT_IN_C3_RUNTIME_LINUX_OR_ANDROID','native_calls':True,'canonical_architecture_complete':False,'phone_measured':bool(os.environ.get('ANDROID_ROOT') or 'com.termux' in os.environ.get('PREFIX','')),'checks':{},'source_sha256':{p:file_hash(APP/p) for p in ['v13/runners.py','v13/runtime.py','v13/config.py','tests/integration_causal_stream.py']}}
    def save():atomic_write(out/'report.json',dumps(report))
    save();runtime=None;cfg=None;session=None
    try:
        runtime=Runtime(home);cfg=dict(runtime.cfg);session=runtime.session
        binding=check_prepared(home);report['binding']=binding;save()
        runtime.cfg.update(c3_decode_mode='same_causal_zero',answer_tokens=64,route_override='simple',observer_mode='off',history_turns=0)
        runtime.session=runtime.store.new_session('Actual causal decoder proof')
        event_id=runtime.submit('Sag kurz Hallo auf Deutsch.')
        end=time.monotonic()+runtime.cfg['deadline_seconds']+10
        while not runtime.idle() and time.monotonic()<end:time.sleep(.05)
        if not runtime.idle():runtime.cancel();raise RuntimeError('Coordinator did not finish within deadline/cleanup margin')
        row=runtime.last_answer()
        if row is None:raise RuntimeError('No persisted answer')
        meta=json.loads(row['metadata']);metrics=meta.get('runner',{});controller=metrics.get('causal_controller',{})
        if metrics.get('artifact_directory'):
            shutil.copytree(metrics['artifact_directory'],out/'causal-session')
        report.update(event_id=event_id,answer_status=row['status'],actual_output=row['text'],metadata=meta,answer_sha256=digest(row['text']),model_sha256_after=file_hash(binding['identity']['model_path']))
        checks={
            'actual_final_visible_answer':row['status']=='FINAL' and bool(row['text'].strip()) and meta.get('model_generated') is True,
            'optin_real_decoder':metrics.get('decode_mode')=='same_causal_zero' and metrics.get('production_integration') is True,
            'no_old_or_unapproved_head':metrics.get('learned_head_loaded') is False and meta.get('output_adapter_status')=='UNAVAILABLE_NO_APPROVED_SAME_CAUSAL_HEAD',
            'same_native_context':metrics.get('same_context_lifetime') is True and metrics.get('resume_prefill_calls')==0,
            'actual_stream_verified':controller.get('status')=='SAME_CONTEXT_STREAM_COMPLETE' and bool(controller.get('checks')) and all(v is True for v in controller['checks'].values()),
            'actual_tokens':isinstance(metrics.get('native_token_ids'),list) and 1<=len(metrics['native_token_ids'])<=64 and metrics.get('generated_tokens')==len(metrics['native_token_ids']),
            'template_reaped':metrics.get('template_release',{}).get('process_reaped') is True,
            'causal_reaped':metrics.get('process_reaped') is True and not runtime.pool.pids(),
            'unchanged_model':report['model_sha256_after']==binding['identity']['model_sha256'],
            'feedback_context_stored':bool(runtime.store.one("SELECT id FROM packets WHERE kind='OutputAdapterContext' AND event_id=?",(event_id,))),
            'store_integrity':runtime.store.integrity(True)==[],
        }
        # Explicit test-operator authored reference; not genuine end-user data.
        reference='Hallo! Dies ist eine ausdrücklich verfasste Testreferenz.'
        runtime.learner.output_feedback(event_id,reference,'record')
        decision=json.loads(runtime.store.one("SELECT payload FROM packets WHERE kind='HumanDecision' AND event_id=? AND json_extract(payload,'$.kind')='output'",(event_id,))['payload'])
        context=json.loads(runtime.store.one("SELECT payload FROM packets WHERE kind='OutputAdapterContext' AND event_id=?",(event_id,))['payload'])
        checks['explicit_test_reference_lineage']=decision['learning_permission']=='record' and runtime.store.read_source(decision['source_ref'])==reference and decision['selection']['context_packet_id']==context['packet_id'] and decision['selection']['source_refs']==context['provenance']
        report['human_feedback_scope']='AUTHORED_TEST_OPERATOR_REFERENCE_RECORD_ONLY_NOT_GENUINE_USER_COHORT'
        # Isolated Store permits a real C5 approved rule without changing user rules.
        from v13.operator import Operator
        op=Operator(runtime)
        request=op.run(':rules fixed "CAUSAL_C5_FIXED_TEST" "Exact C5 test output."').split(';')[0]
        op.run(':approve '+request)
        runtime.submit('CAUSAL_C5_FIXED_TEST')
        fixed_end=time.monotonic()+5
        while not runtime.idle() and time.monotonic()<fixed_end:time.sleep(.01)
        fixed=runtime.last_answer();fixed_meta=json.loads(fixed['metadata'])
        checks['c5_exact_rule_owns_output']=fixed['status']=='FINAL' and fixed['text']=='Exact C5 test output.' and fixed_meta.get('output_authority')=='APPROVED_FIXED_RULE' and fixed_meta.get('model_generated') is False and 'runner' not in fixed_meta
        report['fixed_rule_metadata']=fixed_meta
        runtime.cfg.clear();runtime.cfg.update(cfg);runtime.session=session;runtime.store.set_meta('last_session',session)
        runtime.close();runtime=Runtime(home)
        restored=runtime.store.one('SELECT * FROM messages WHERE id=?',(row['id'],))
        checks['restart_preserves_answer']=bool(restored) and restored['status']==row['status'] and restored['text']==row['text']
        checks['original_decoder_config_preserved']=runtime.cfg['c3_decode_mode']==cfg['c3_decode_mode'] and runtime.cfg['answer_tokens']==cfg['answer_tokens']
        report['restart_decode_mode']=runtime.cfg['c3_decode_mode'];report['checks']=checks;report['status']='ACTUAL_CAUSAL_COORDINATOR_PASS' if all(checks.values()) else 'ACTUAL_CAUSAL_COORDINATOR_FAIL';save()
        print(dumps({'status':report['status'],'actual_output':row['text'],'proof_path':str(out/'report.json'),'checks':checks}),flush=True)
        return 0 if all(checks.values()) else 2
    except BaseException as exc:
        report.update(status='ACTUAL_CAUSAL_COORDINATOR_ERROR',error_type=type(exc).__name__,error=str(exc)[:500]);save();raise
    finally:
        if runtime is not None:
            if cfg is not None:runtime.cfg.clear();runtime.cfg.update(cfg)
            if session is not None:runtime.session=session;runtime.store.set_meta('last_session',session)
            runtime.close()

if __name__=='__main__':raise SystemExit(main())
