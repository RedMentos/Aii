#!/usr/bin/env python3
"""One actual zero-bias C3 client pause/resume probe; no head or promotion."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time
import traceback

APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
from scripts.live_output_adapter_port import bind_installed,PausedOutputSession,verify_binding
from v13.common import atomic_write,digest,dumps,file_hash,safe_text
from v13.config import DEFAULTS,home_path
from v13.resources import device,process_memory
from v13.runners import LlamaRunner,check

MESSAGES=[{'role':'system','content':'Antworte kurz auf Deutsch.'},
          {'role':'user','content':'Hallo! Was kann ich als Erstes fragen?'}]
SOURCE_FILES=['scripts/test_live_output_adapter_port.py','scripts/live_output_adapter_port.py',
              'scripts/native_prefill_session.cpp','scripts/native_prefill_worker.cpp',
              'scripts/test_native_prefill_session.py','scripts/test_native_prefill_port.py',
              'v13/runners.py','v13/output_adapter_worker.py','specs/models.json',
              'docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md']

def save(path,value):atomic_write(path,json.dumps(value,ensure_ascii=False,indent=2))

def collect(home,out,seconds,rss_mb):
    home=Path(home).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    cancel=threading.Event();done=threading.Event();template=None;session=None;lock=None;watcher=None
    report={'schema':'V13_LIVE_OUTPUT_CLIENT_ZERO_PROOF_V1','status':'PREPARING','device':device(),
            'native_inference_performed':False,'native_inference_attempted':False,'production_integration':False,'approval_authority':0,
            'training_authority':0,'old_head_loaded':False,'same_context_execution':'PENDING',
            'scope':'One real causal C3 prefill with actual1024D/65536 features, one zero-bias resume, three unbiased continuation steps. No full streaming, quality, speed, training, phone or Canon claim.',
            'template_resource_samples':[],'template_resource_sample_count':0,'template_peak_rss_bytes':None,'template_peak_pss_bytes':None}
    path=out/'report.json';save(path,report)
    old_handlers={sig:signal.signal(sig,lambda *_:cancel.set()) for sig in (signal.SIGINT,signal.SIGTERM)}
    started=time.monotonic();deadline=started+seconds
    try:
        lock=(home/'data/coordinator.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        binding=bind_installed(home);frozen={name:file_hash(APP/name) for name in SOURCE_FILES}
        cfg=dict(DEFAULTS,context_tokens=2048,threads=2,answer_tokens=16)
        prereg={'messages':MESSAGES,'source_hashes':frozen,'identity':binding,'config':cfg,
                'bias_rows':[],'head_artifact':None,'seconds':seconds,'absolute_deadline_monotonic_ns':int(deadline*1e9),
                'rss_limit_mb_boot':rss_mb,'expected_decoded_tokens':4,'expected_resume_prefill_calls':0,
                'worker_wait_seconds':15,'temperature_policy':'Existing worker greedy first token and continuation'}
        save(out/'preregistration.json',prereg);report['preregistration_sha256']=file_hash(out/'preregistration.json')
        report['source_hashes']=frozen;report['installed_binding']=binding;report['status']='MEASURING_TEMPLATE';save(path,report)
        snapshot=out/'source-snapshot'
        for name in SOURCE_FILES:
            target=snapshot/name;atomic_write(target,(APP/name).read_bytes())
        template=LlamaRunner(home,'C3_LANGUAGE',Path(binding['identity']['model_path']),cfg)
        def monitor_template():
            while not done.wait(.05):
                proc=template.proc
                if proc is not None and proc.poll() is None:
                    memory=process_memory(proc.pid);report['template_resource_sample_count']+=1
                    for field in ('rss_bytes','pss_bytes'):
                        if memory.get(field) is not None:
                            key='template_peak_'+field;report[key]=max(report[key] or 0,memory[field])
                    report['template_resource_samples'].append({'elapsed_s':time.monotonic()-started,**memory})
                    if len(report['template_resource_samples'])>64:del report['template_resource_samples'][1]
                    if (memory.get('rss_bytes') or 0)>rss_mb*1024*1024:
                        report['template_resource_limit_exceeded']=True;cancel.set();return
        watcher=threading.Thread(target=monitor_template,daemon=True);watcher.start()
        template.load(cancel,deadline)
        prompt,count,trimmed=template._prompt(MESSAGES,cancel,deadline,16)
        ids=template._json('POST','/tokenize',{'content':prompt,'add_special':True},deadline)['tokens']
        if trimmed or count!=len(ids) or not 1<=count<=512:raise RuntimeError('Exact untrimmed bounded native template required')
        context={'messages':MESSAGES,'prompt':prompt,'token_ids':ids,'history_trimmed':trimmed}
        save(out/'context.json',context);report['context_source_sha256']=digest(dumps(context));report['exact_template_token_count']=count
        report['template_decode_requests_issued_by_collector']=0
        report['template_release']=template.unload();done.set();watcher.join(.25)
        if report['template_release'].get('process_reaped') is not True:raise RuntimeError('Template server must be reaped before causal worker')
        template=None;verify_binding(binding);check(cancel,deadline)
        if any(file_hash(APP/name)!=sha for name,sha in frozen.items()):raise RuntimeError('Frozen probe source changed before causal worker')
        report['status']='RUNNING_ONE_NATIVE_CONTEXT';save(path,report)
        session=PausedOutputSession(binding,context,out/'native-context',cancel,deadline,rss_limit_bytes=rss_mb*1024*1024)
        report['native_inference_attempted']=True;report['native_inference_performed']=None
        with session:
            observed=session.pause();report['native_inference_performed']=True
            save(out/'observed-context.json',observed)
            report['observed_context_sha256']=file_hash(out/'observed-context.json');report['native_handle_id']=observed['native_context_binding']['handle_id']
            report['live_feature_dimension']=len(observed['feature']);save(path,report)
            result=session.resume([]);save(out/'client-result.json',result)
        report['session_metrics']=dict(session.metrics);raw=result['raw_result']
        checks={'actual_native_result':raw.get('status')=='PAUSE_RESUME_DIAGNOSTIC_COMPLETE' and raw.get('software_fixture') is not True,
                'template_reaped_before_worker':report['template_release']['process_reaped'] is True,
                'one_same_context':raw.get('same_context_lifetime') is True and raw.get('resume_prefill_calls')==0,
                'zero_bias_first_position':raw.get('bias_applied_positions')==0 and raw.get('first_biased_token_id')==raw.get('first_native_greedy_token_id') and raw.get('accepted_command',{}).get('bias')==[],
                'one_consumed_handle':raw.get('handle_consumed') is True and session.metrics['resume_commands_sent']==1,
                'four_actual_decoded_tokens':len(result['native_token_ids'])==4 and raw.get('unbiased_continuation_steps')==3,
                'all_client_binding_checks':all(session.metrics.get('checks',{}).values()) and bool(session.metrics.get('checks')),
                'actual_process_reaped':session.metrics['process_reaped'] is True,
                'exact_source_unchanged':all(file_hash(APP/name)==sha for name,sha in frozen.items())}
        verify_binding(binding);checks['exact_installed_binding_unchanged']=True
        report.update(checks=checks,status='LIVE_OUTPUT_CLIENT_ZERO_PASS' if all(checks.values()) else 'LIVE_OUTPUT_CLIENT_ZERO_FAIL',
                      same_context_execution='MEASURED_SAME_PROCESS_NO_ADDITIONAL_PREFILL',native_preview=result['text'],
                      raw_result_sha256=file_hash(out/'native-context/result.json'),features_sha256=file_hash(out/'native-context/features.json'),
                      decoded_native_token_ids=result['native_token_ids'])
        print('Native Ausgabe: '+safe_text(result['text']),flush=True)
        return 0 if all(checks.values()) else 1
    except BaseException as exc:
        report.update(status='LIVE_OUTPUT_CLIENT_ZERO_FAIL',error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
        return 1
    finally:
        done.set()
        if watcher is not None:watcher.join(.25)
        if template is not None:report['final_template_release']=template.unload()
        if session is not None:session.close();report['session_metrics']=dict(session.metrics)
        if lock is not None:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
        for sig,handler in old_handlers.items():signal.signal(sig,handler)
        report['wall_elapsed_s']=time.monotonic()-started;save(path,report)
        print(dumps({'status':report['status'],'artifact':str(path),'native_inference_performed':report['native_inference_performed'],'production_integration':False}),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--installed-home');p.add_argument('--out-dir');p.add_argument('--seconds',type=int,default=90);p.add_argument('--rss-limit-mb',type=int,default=768);a=p.parse_args()
    if not 5<=a.seconds<=120 or not 128<=a.rss_limit_mb<=2048:p.error('seconds5..120 and RSS128..2048MiB required')
    home=home_path(a.installed_home);out=Path(a.out_dir) if a.out_dir else home/'exports'/('live-output-client-'+time.strftime('%Y%m%d-%H%M%S'))
    return collect(home,out,a.seconds,a.rss_limit_mb)

if __name__=='__main__':sys.exit(main())
