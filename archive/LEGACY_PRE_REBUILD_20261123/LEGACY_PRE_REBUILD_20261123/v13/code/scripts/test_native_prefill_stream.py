#!/usr/bin/env python3
"""Adjacent actual same-context C3 streaming test/client entry point."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback
import numpy as np
APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP));sys.path.insert(0,str(APP/'scripts'))
import test_native_prefill_port as port
from scripts.native_prefill_stream_client import STREAM_ABI,StreamingOutputSession,bind_installed
from v13.common import dumps,file_hash,safe_text
from v13.config import DEFAULTS,home_path
from v13.models import ModelManager,catalog
from v13.resources import device
from v13.runners import LlamaRunner
SCOPE=('Actual C3 causalprefill -> one bounded authored first-position numeric command -> '
       'unbiased same-context streaming to real EOS or64/128 tokens. New streaming V2 ABI; '
       'no old-head reuse, learned-head loading, production activation, approval, '
       'receiver injection, native training, latency or phone claim.')
SOURCE_FILES=['scripts/native_prefill_stream.cpp','scripts/native_prefill_stream_client.py',
              'scripts/test_native_prefill_stream.py','scripts/test_native_prefill_stream_protocol.py',
              'scripts/native_prefill_worker.cpp','scripts/test_native_prefill_port.py']


def build_stream(home, identity, runner, cancel, out):
    _, base = port.prepare_worker(home, identity, runner, cancel, out)
    key = {'base_build_identity': base['identity_key'],
           'source_sha256': file_hash(APP / 'scripts/native_prefill_stream.cpp'),
           'helper_sha256': file_hash(Path(__file__)),
           'client_sha256': file_hash(APP / 'scripts/native_prefill_stream_client.py'),
           'feature_abi': STREAM_ABI}
    binary = home / 'bin/native-prefill-stream'
    marker = home / 'config/native-prefill-stream.json'
    prior = json.loads(marker.read_text()) if marker.exists() else {}
    if binary.is_file() and prior.get('identity_key') == key and prior.get('binary_sha256') == file_hash(binary):
        return binary, prior
    original = base['command']
    sha_attempt = base['sha_build']
    sha_command = json.loads((out / 'worker-sha-build-attempt.json').read_text())['command'] if (out / 'worker-sha-build-attempt.json').exists() else [key['base_build_identity']['c_compiler'], '-std=c11', '-O2', '-I', str(home / 'tmp/native-prefill-port/source' / ('llama.cpp-' + runner['tag']) / 'vendor/hash'), '-c', str(home / 'tmp/native-prefill-port/source' / ('llama.cpp-' + runner['tag']) / 'vendor/hash/sha256/sha256.c'), '-o', str(home / 'tmp/native-prefill-port/sha256.o')]
    # Never trust a transient SHA object merely because a previous worker was valid.
    sha_attempt = port.bounded_process(sha_command, out / 'session-sha-build.log', cancel, 60)
    if sha_attempt['exit_code'] or sha_attempt['stop_reason']:
        raise RuntimeError('Pinned SHA compilation failed')
    temp = binary.with_name(binary.name + '.new')
    command = [str(APP / 'scripts/native_prefill_stream.cpp') if x == str(APP / 'scripts/native_prefill_worker.cpp') else str(temp) if x == str(home / 'bin/native-prefill-worker.new') else x for x in original]
    build = port.bounded_process(command, out / 'session-build.log', cancel, 180)
    port.save(out / 'session-build-attempt.json', {'identity_key': key, 'command': command, 'build': build})
    if build['exit_code'] or build['stop_reason'] or not temp.exists():
        raise RuntimeError('Session worker compilation failed')
    temp.chmod(0o700)
    os.replace(temp, binary)
    result = {'schema': 'V13_PREFILL_STREAM_BUILD_V2', 'identity_key': key,
              'command': command, 'build': build, 'sha_build': sha_attempt,
              'binary_sha256': file_hash(binary)}
    port.save(marker, result)
    return binary, result


def first_position_fixture(session,mode):
    if mode=='zero':return [],{'policy':'ZERO_NUMERIC_DELTA','authority':'DIAGNOSTIC_ONLY'}
    order=np.argsort(-session.logits,kind='stable')
    top,second=int(order[0]),int(order[1])
    value=float(session.logits[top])-float(session.logits[second])+1.
    if not 0<value<=12:raise RuntimeError('Preregistered numeric second-row fixture exceeds12; no retuning')
    return [[second,value]],{'policy':'SECOND_BEST_NATIVE_ROW_PLUS_GAP_PLUS_ONE',
                            'baseline_top_token_id':top,'diagnostic_target_token_id':second,
                            'bias':value,'authority':'DIAGNOSTIC_ONLY'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed-home')
    parser.add_argument('--out-dir')
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--mode',choices=['zero','nonzero'],default='zero')
    parser.add_argument('--pair',action='store_true')
    parser.add_argument('--baseline-zero',action='store_true')
    parser.add_argument('--prompt','--message',dest='message',default='Hallo! Was kann ich als Erstes fragen?')
    parser.add_argument('--max-tokens',type=int,choices=[64,128],default=64)
    parser.add_argument('--seconds',type=int,default=90)
    parser.add_argument('--rss-limit-mb',type=int,default=768)
    args=parser.parse_args()
    if not 5<=args.seconds<=90 or not 128<=args.rss_limit_mb<=2048 or not 1<=len(args.message)<=5000:
        parser.error('seconds5..90, RSS128..2048MiB and message1..5000 characters required')
    home=home_path(args.installed_home)
    out=Path(args.out_dir).resolve() if args.out_dir else home/'exports'/('prefill-stream-'+time.strftime('%Y%m%d-%H%M%S'))
    if out.exists() and any(out.iterdir()):parser.error('Fresh attempt directory required')
    out.mkdir(parents=True,exist_ok=True)
    report={'schema':'V13_PREFILL_STREAM_PROOF_V2','status':'PREPARING','scope':SCOPE,
            'device':device(),'feature_abi':STREAM_ABI,'production_integration':False,
            'approval_authority':0,'receiver_authority':0,'training_authority':0,
            'old_head_reuse':'REFUSED_NEW_ABI','native_inference_performed':False,'variants':[]}
    path=out/'report.json';port.save(path,report)
    cancel=threading.Event();lock=None;template=None
    handlers={sig:signal.signal(sig,lambda *_:cancel.set()) for sig in [signal.SIGINT,signal.SIGTERM]}
    try:
        lock=(home/'data/coordinator.lock').open('a+')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        specs=catalog();models=ModelManager(home);model=models.path_for('C3_LANGUAGE')
        if file_hash(model)!=specs['models']['language']['files'][0]['sha256'] or models.revision('C3_LANGUAGE')!=specs['models']['language']['revision']:
            raise RuntimeError('Exact pinned C3 required')
        identity=port.installed_identity(home,model,specs['runner'])
        binary,build=build_stream(home,identity,specs['runner'],cancel,out)
        report['build']=build
        snapshot=out/'source-snapshot';snapshot.mkdir()
        for name in SOURCE_FILES:
            source=APP/name;target=snapshot/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        frozen={name:file_hash(APP/name) for name in SOURCE_FILES+['v13/runners.py','specs/models.json','docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md']}
        report['source_hashes']=frozen
        messages=[{'role':'system','content':'Antworte kurz auf Deutsch.'},{'role':'user','content':args.message}]
        if args.pair and args.baseline_zero:raise ValueError('Choose pair or baseline-zero')
        prereg={'messages':messages,'variants':['baseline','zero'] if args.baseline_zero else ['zero','nonzero'] if args.pair else [args.mode],
                'source_hashes':frozen,'feature_abi':STREAM_ABI,'binary_sha256':file_hash(binary),
                'nonzero_policy':'Actual second-best row +(top-minus-second+1), only0<bias<=12; else retainedFAIL',
                'max_tokens':args.max_tokens,'deadline_seconds':args.seconds,'rss_limit_mib':args.rss_limit_mb,
                'bias_positions':1,'resume_prefill_calls':0,'eos_policy':'llama_vocab_is_eog(actual_native_token)',
                'scope':SCOPE,'installed_identity':identity}
        port.save(out/'preregistration.json',prereg);report['preregistration_sha256']=file_hash(out/'preregistration.json')
        guards=subprocess.run([str(binary),'--guard-test'],capture_output=True,text=True,timeout=10)
        if guards.returncode:raise RuntimeError('Streaming command guards failed')
        report['native_command_guards']=json.loads(guards.stdout);port.save(out/'native-command-guards.json',report['native_command_guards'])
        from scripts.test_native_prefill_stream_protocol import protocol_guards
        protocol=protocol_guards()
        report['client_protocol_guards']=protocol;port.save(out/'client-protocol-guards.json',protocol)
        if not all(protocol['checks'].values()):raise RuntimeError('Streaming client guards failed')
        if args.prepare_only:
            report['status']='STREAM_PREPARED_GUARDS_PASS_NO_INFERENCE';return 0
        report['native_inference_performed']=True;port.save(path,report)
        cfg=dict(DEFAULTS,context_tokens=2048,threads=2,answer_tokens=args.max_tokens)
        template=LlamaRunner(home,'C3_LANGUAGE',model,cfg)
        deadline=time.monotonic()+args.seconds;template.load(cancel,deadline)
        prompt,count,trimmed=template._prompt(messages,cancel,deadline,args.max_tokens)
        ids=template._json('POST','/tokenize',{'content':prompt,'add_special':True},deadline)['tokens']
        if trimmed or count!=len(ids) or not 1<=count<=512:raise RuntimeError('Exact bounded untrimmed template token binding required')
        context={'messages':messages,'prompt':prompt,'token_ids':ids,'history_trimmed':False}
        port.save(out/'exact-context-source.json',context)
        report['template_release']=template.unload();template=None
        binding=bind_installed(home);report['feature_fingerprint']=binding['feature_abi']
        report['status']='RUNNING';port.save(path,report)
        for mode in prereg['variants']:
            if any(file_hash(APP/name)!=value for name,value in frozen.items()):raise RuntimeError('Frozen source changed')
            row={'mode':mode,'status':'RUNNING','pass':False};report['variants'].append(row);port.save(path,report)
            if mode=='baseline':
                baseline=out/'baseline';baseline.mkdir()
                token_file=baseline/'tokens.json';pins=baseline/'pins.json'
                context_sha=hashlib.sha256(dumps(context).encode()).hexdigest()
                port.save(token_file,{'token_ids':ids,'context_source_sha256':context_sha});port.save(pins,{'libraries':identity['libraries']})
                command=[str(binary),'--model',str(model),'--tokens',str(token_file),'--output',str(baseline/'result.json'),
                         '--features',str(baseline/'features.json'),'--model-sha256',identity['model_sha256'],
                         '--lib-sha256',identity['libraries'][identity['llama_library']],'--backend-pins',str(pins),
                         '--context-source-sha256',context_sha,'--nonce',os.urandom(16).hex(),
                         '--worker-source-sha256',frozen['scripts/native_prefill_stream.cpp'],'--max-tokens',str(args.max_tokens),
                         '--seconds',str(args.seconds),'--resume-mode','baseline']
                metrics=port.bounded_process(command,baseline/'native.log',cancel,args.seconds,args.rss_limit_mb)
                raw=json.loads((baseline/'result.json').read_text()) if (baseline/'result.json').exists() else {}
                checks={'actual_completed':raw.get('status')=='CAUSAL_STREAM_DIAGNOSTIC_COMPLETE' and metrics['exit_code']==0 and metrics['stop_reason'] is None,
                        'unpaused_no_command':raw.get('handle_consumed') is False and raw.get('accepted_command')=={'command':'UNPAUSED_NUMERIC_BASELINE'},
                        'no_bias_no_reprefill':raw.get('bias_applied_positions')==0 and raw.get('resume_prefill_calls')==0 and raw.get('same_context_lifetime') is True,
                        'bounded_output':type(raw.get('generated_token_count')) is int and 1<=raw['generated_token_count']<=args.max_tokens,
                        'model_unchanged':raw.get('model',{}).get('sha256')==identity['model_sha256']==raw.get('model_sha256_after'),
                        'source_binary_bound':raw.get('worker_source_sha256')==frozen['scripts/native_prefill_stream.cpp'] and raw.get('executable_sha256')==file_hash(binary),
                        'actual_loaded_pins':raw.get('all_loaded_libraries_verified') is True,'reaped':metrics['process_reaped'] is True}
                row.update(status=raw.get('status'),checks=checks,metrics=metrics,generated_tokens=raw.get('generated_token_count'),
                           stop_reason=raw.get('stop_reason'),native_preview=raw.get('decoded_native_preview'),pass_=all(checks.values()))
                row['pass']=row.pop('pass_');port.save(path,report)
                if not row['pass']:raise RuntimeError('Actual unpaused baseline failed; preserve attempt')
                continue
            with StreamingOutputSession(binding,context,out/mode,cancel,time.monotonic()+args.seconds,
                                        rss_limit_bytes=args.rss_limit_mb*1024*1024,max_tokens=args.max_tokens) as session:
                session.pause();rows,fixture=first_position_fixture(session,mode);row['numeric_fixture']=fixture
                port.save(out/mode/'fixture.json',fixture)
                completed=None
                for event in session.resume(rows):
                    if event['event']=='TOKEN':print(safe_text(event['text']),end='',flush=True)
                    else:completed=event
                print(flush=True)
                if completed is None:raise RuntimeError('Actual native streaming COMPLETE required')
                raw=completed['raw_result'];checks=dict(completed['metrics']['checks'])
                checks['all_processes_reaped']=completed['metrics']['process_reaped'] is True
                if mode=='zero':checks['zero_preserves_first_token']=raw['first_biased_token_id']==raw['first_native_greedy_token_id'] and raw['bias_applied_positions']==0
                else:checks['nonzero_fixture_changes_first_token']=raw['first_biased_token_id']==fixture['diagnostic_target_token_id'] and raw['first_biased_token_id']!=raw['first_native_greedy_token_id']
                row.update(status=raw['status'],pass_=all(checks.values()),checks=checks,
                           native_preview=completed['text'],generated_tokens=raw['generated_token_count'],
                           stop_reason=raw['stop_reason'],controller_artifact=str(Path(mode)/'controller.json'),
                           raw_result_artifact={'path':str(Path(mode)/'result.json'),'sha256':file_hash(out/mode/'result.json')})
                row['pass']=row.pop('pass_');port.save(path,report)
        if args.baseline_zero:
            base=json.loads((out/'baseline/result.json').read_text());zero=json.loads((out/'zero/result.json').read_text())
            bf=json.loads((out/'baseline/features.json').read_text());zf=json.loads((out/'zero/features.json').read_text())
            same=lambda a,b,dt:np.asarray(a,dtype=dt).tobytes()==np.asarray(b,dtype=dt).tobytes()
            comparison={'native_token_ids_byte_equivalent':base['decoded_native_token_ids']==zero['decoded_native_token_ids'],
                        'native_text_bytes_identical':base['decoded_native_preview_hex']==zero['decoded_native_preview_hex'],
                        'full_prefill_state_byte_identical':same(bf['live_last_state'],zf['live_last_state'],'<f4'),
                        'full_prefill_logits_byte_identical':same(bf['first_position']['logits'],zf['first_position']['logits'],'<f4'),
                        'full_prefill_probabilities_byte_identical':same(bf['first_position']['probabilities'],zf['first_position']['probabilities'],'<f8'),
                        'same_unbiased_continuation':base['continuation']==zero['continuation'],
                        'same_real_stop_reason':base['stop_reason']==zero['stop_reason'],
                        'no_extra_prefill':base['resume_prefill_calls']==zero['resume_prefill_calls']==0}
            report['baseline_zero_comparison']=comparison
        report['final_source_unchanged']=all(file_hash(APP/name)==value for name,value in frozen.items()) and port.installed_identity(home,model,specs['runner'])==identity and file_hash(binary)==prereg['binary_sha256']
        passed=all(x['pass'] for x in report['variants']) and report['final_source_unchanged'] and all(report.get('baseline_zero_comparison',{}).values())
        report['status']='BOUNDED_CAUSAL_STREAM_PASS' if passed else 'BOUNDED_CAUSAL_STREAM_FAIL'
        return 0 if report['status'].endswith('_PASS') else 1
    except BaseException as exc:
        report.update(status='BOUNDED_CAUSAL_STREAM_FAIL',error=str(exc),error_type=type(exc).__name__,traceback=traceback.format_exc())
        return 1
    finally:
        if template is not None:report['final_template_release']=template.unload()
        if lock is not None:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
        for sig,handler in handlers.items():signal.signal(sig,handler)
        port.save(path,report);print(dumps({'status':report['status'],'report':str(path),'scope':SCOPE}),flush=True)


if __name__=='__main__':raise SystemExit(main())


