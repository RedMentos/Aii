#!/usr/bin/env python3
"""Reuse a completed Runtime causal observation with current explicit human labels.

export is offline: no tokenizer, prefill, model generation, fit or approval.
tokenize is an explicit bounded native label-only operation; stop chat first.
The original capture/exporter and numerical trainer remain unchanged.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import signal
import sys
import threading
import time
import numpy as np
APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
from scripts import export_live_output_dataset as original
from scripts.native_prefill_stream_client import (bind_installed,verify_binding,read_json,
    STREAM_ABI,bias_rows,completion_checks,validate_token_event,loaded_library_pins_match)
from scripts.train_live_output_adapter import prepare,SCHEMA
from v13.common import atomic_write,dumps,digest,file_hash,Limits
from v13.config import DEFAULTS,home_path
from v13.models import ModelManager
from v13.resources import process_memory
from v13.runners import LlamaRunner,check
from v13.store import Store

RECEIPT='V13_PINNED_LABEL_TOKENIZATION_RECEIPT_V1'
RAW_NAMES=('observed','features','context','tokens','result','controller','events','pins','resume')
MAX_BYTES=64*1024*1024

def write(path,value):atomic_write(path,dumps(value))

def bounded(seconds):
    if type(seconds) is not int or not 5<=seconds<=90:raise ValueError('Integer seconds5..90 required')
    return time.monotonic()+seconds

def deadline_check(deadline):
    if time.monotonic()>=deadline:raise Limits('Recorded export time budget reached')

def recorded_answer(store,selected,home):
    rows=store.rows("SELECT id,status,metadata FROM messages WHERE event_id=? AND role='assistant' ORDER BY id DESC",(selected['event']['event_id'],))
    if not rows:raise ValueError('Completed original Runtime assistant turn absent')
    row=rows[0];meta=json.loads(row['metadata']);runner=meta.get('runner',{})
    if row['status']!='FINAL' or meta.get('model_generated') is not True or runner.get('status')!='FINAL' or runner.get('role')!='C3_LANGUAGE' or runner.get('decode_mode') not in {'same_causal_zero','same_causal'} or runner.get('process_reaped') is not True:raise ValueError('Completed reaped same-causal Runtime turn required')
    path=Path(runner.get('artifact_directory',''))
    # Exact Runtime nonce directory only; no symlinks or external captured folder.
    if not path.is_absolute() or not re.fullmatch(r'c3-causal-stream-[0-9a-f]{32}',path.name) or path.parent!=Path(home).resolve()/'tmp' or path.is_symlink() or path.resolve(strict=True)!=path:raise ValueError('Original Runtime artifact nonce/path differs')
    return path,runner,row['id']

def validate_record(folder,runner,selected,binding):
    """Recompute native protocol checks offline; controller booleans alone are insufficient."""
    folder=Path(folder);paths={name:folder/(name+'.json') for name in RAW_NAMES}
    for path in paths.values():
        if path.is_symlink() or not path.is_file() or path.stat().st_size>16*1024*1024:raise ValueError('Bounded original raw artifact required')
    if sum(p.stat().st_size for p in paths.values())>MAX_BYTES:raise ValueError('Recorded artifacts exceed64MiB')
    hashes={name:file_hash(path) for name,path in paths.items()}
    raw={name:read_json(path) for name,path in paths.items()}
    o,f,c,t,r,ctl,e,pins,cmd=(raw[n] for n in RAW_NAMES);abi=binding['feature_abi'];ident=binding['identity'];h=r['handle'];pid=h['pid'];cap=h['max_tokens'];source=digest(dumps(c))
    if any(x.get('software_fixture') is True for x in (o,f,r,ctl)) or o['feature_abi']!=abi or runner['feature_abi']!=abi:raise ValueError('Actual current exact-ABI observation required')
    if c['messages']!=selected['messages'] or c['history_trimmed'] is not False or digest(dumps(c['messages']))!=selected['decision']['selection']['context_ref']['sha256']:raise ValueError('Original authoritative context/source differs')
    if runner.get('observed_sha256')!=hashes['observed']:raise ValueError('Runtime observation bytes changed or unbound')
    if ctl!=runner.get('causal_controller') or ctl.get('status')!='SAME_CONTEXT_STREAM_COMPLETE' or ctl.get('process_reaped') is not True or type(ctl.get('exit_code')) is not int or ctl['exit_code']!=0 or ctl.get('resume_commands_sent')!=1 or ctl.get('pid')!=pid or ctl.get('error_type') or not ctl.get('checks') or any(v is not True for v in ctl['checks'].values()):raise ValueError('Checked complete reaped Runtime controller required')
    required={'schema':'V13_CAUSAL_STREAM_HANDLE_V2','feature_abi':STREAM_ABI,'worker_source_sha256':binding['source_hashes']['scripts/native_prefill_stream.cpp'],'executable_sha256':binding['binary_sha256'],'max_tokens':cap,'nonce':h['nonce'],'pid':pid,'model_sha256':ident['model_sha256'],'lib_sha256':ident['libraries'][ident['llama_library']],'backend_pins_sha256':hashes['pins'],'token_file_sha256':hashes['tokens'],'context_source_sha256':source,'features_sha256':hashes['features'],'sequence_id':0,'next_position':len(c['token_ids']),'context_tokens':2048,'prefill_generation':1,'wait_ttl_seconds':15}
    bare=dict(h);bare.pop('handle_id',None)
    if type(pid) is not int or pid<=0 or type(cap) is not int or cap not in (64,128) or not re.fullmatch('[0-9a-f]{32}',h['nonce']) or set(h)!=set(required)|{'handle_id'} or any(type(h[k]) is not type(v) or h[k]!=v for k,v in required.items()) or digest(dumps(bare))!=h['handle_id']:raise ValueError('Exact checked native handle binding differs')
    if pins!={'libraries':ident['libraries']}:raise ValueError('Actual backend pins differ')
    rows=bias_rows(cmd['bias']);expected={'command':'resume','handle_id':h['handle_id'],'nonce':h['nonce'],'context_source_sha256':source,'feature_abi':STREAM_ABI,'worker_source_sha256':required['worker_source_sha256'],'bias':rows}
    if cmd!=expected or r.get('accepted_command')!=cmd:raise ValueError('Actual single resume command differs')
    logits=np.asarray(f['first_position']['logits'],dtype=np.float32)
    if logits.shape!=(65536,) or not np.isfinite(logits).all():raise ValueError('Actual finite native vocabulary logits required')
    biased=logits.copy()
    for token,value in rows:biased[token]+=np.float32(value)
    predicted=int(biased.argmax());pieces=bytearray()
    if not isinstance(e,list) or len(e)>cap:raise ValueError('Bounded actual token events required')
    for i,event in enumerate(e):pieces.extend(validate_token_event(event,h,i,cap,bool(rows),bool(i and e[i-1]['is_eog'])))
    checks={'status':r.get('status')=='CAUSAL_STREAM_DIAGNOSTIC_COMPLETE','pid':r.get('pid')==pid,
        'same_context':r.get('same_context_lifetime') is True and r.get('resume_prefill_calls')==0 and r.get('handle_consumed') is True,
        'single_resume':r.get('additional_commands_accepted')==0,'token_sha':r.get('token_file_sha256')==hashes['tokens'],
        'source':r.get('context_source_sha256')==source,'pins':r.get('all_loaded_libraries_verified') is True and r.get('backend_pins_sha256')==hashes['pins'],
        'model':r.get('model',{}).get('sha256')==ident['model_sha256']==r.get('model_sha256_after'),
        'worker':r.get('feature_abi')==STREAM_ABI and r.get('worker_source_sha256')==required['worker_source_sha256'] and r.get('executable_sha256')==binding['binary_sha256'],
        'bias':r.get('bias_applied_positions')==(1 if rows else 0) and r.get('first_native_greedy_token_id')==int(logits.argmax()) and r.get('first_biased_token_id')==predicted,
        'template_reaped':runner.get('template_release',{}).get('process_reaped') is True,
        'recorded_tokens':runner.get('native_token_ids')==r.get('decoded_native_token_ids')}
    loaded=[r.get(k,{}) for k in ('loaded_llama_library','loaded_ggml_library','loaded_ggml_base_library')]+r.get('loaded_cpu_backend_libraries',[])
    checks['libraries']=loaded_library_pins_match(loaded,ident['libraries'])
    checks.update(completion_checks(r,e,c['token_ids'],bytes(pieces),cap,predicted))
    if any(v is not True for v in checks.values()):raise ValueError('Recorded native completion binding failed: '+','.join(k for k,v in checks.items() if v is not True))
    return paths,hashes,checks

def validate_receipt(path,label,binding,revision):
    receipt=read_json(path);ident=binding['identity'];tok=receipt['label_tokenization'];response=receipt['response']
    expected={'source_sha256':digest(label),'model_sha256':ident['model_sha256'],'worker_sha256':binding['binary_sha256'],'add_special':False,'tokenizer':'PINNED_LLAMA_RUNNER_HTTP_TOKENIZE','server_sha256':ident['server_sha256']}
    if receipt.get('schema')!=RECEIPT or receipt.get('status')!='ACTUAL_LABEL_TOKENIZED_REAPED' or receipt.get('software_fixture') is True or receipt.get('feature_abi')!=binding['feature_abi'] or receipt.get('model_revision')!=revision or receipt.get('request')!={'content':label,'add_special':False} or receipt.get('release',{}).get('process_reaped') is not True or any(tok.get(k)!=v for k,v in expected.items()) or tok.get('token_ids')!=response.get('tokens'):raise ValueError('Exact actual text/model/server/reaped tokenizer receipt required')
    ids=tok['token_ids']
    if not isinstance(ids,list) or not ids or len(ids)>4096 or any(type(i) is not int or not 0<=i<65536 for i in ids):raise ValueError('Bounded actual native label token IDs required')
    return tok

def export_recorded(home,out,decision_id,label_source_id,receipt_path,learn,seconds=90):
    started=time.monotonic();deadline=bounded(seconds);home=Path(home).resolve();out=Path(out).resolve();store=None;created=False
    report={'status':'RECORDED_EXPORT_STARTED','native_calls':False,'prefill_calls':0,'approval_authority':0,'seconds_limit':seconds}
    try:
        if not (home/'data/db/brain.sqlite3').is_file():raise ValueError('Existing Store required; no bootstrap')
        store=Store(home);models=ModelManager(home);binding=bind_installed(home);deadline_check(deadline)
        revision=models.revision('C3_LANGUAGE');selected=original.select_label(store,decision_id,label_source_id,revision,learn)
        folder,runner,mid=recorded_answer(store,selected,home);paths,hashes,checks=validate_record(folder,runner,selected,binding)
        receipt_path=Path(receipt_path).resolve(strict=True);receipt_sha=file_hash(receipt_path);tok=validate_receipt(receipt_path,selected['label'],binding,revision);deadline_check(deadline)
        if out.is_relative_to(folder) or out==folder or out.exists():raise ValueError('New separate portable output directory required')
        out.mkdir(parents=True);created=True;report['original_message_id']=mid
        for name,path in paths.items():shutil.copyfile(path,out/(name+'.json'))
        shutil.copyfile(receipt_path,out/'tokenizer-receipt.json');write(out/'label-tokenization.json',tok)
        atomic_write(out/'original-human-decision.json',selected['original_payload']);write(out/'original-context-packet.json',selected['context_packet']);write(out/'original-event.json',selected['event'])
        atomic_write(out/'query.txt',selected['query']);atomic_write(out/'label.txt',selected['label']);write(out/'binding.json',binding)
        # Validate all trainer numeric/source rules BEFORE persisting an export decision.
        # A provisional derived packet is never inserted and cannot grant authority.
        from v13.contracts import packet
        original_decision=selected['decision'];selection=dict(original_decision['selection'],feature_abi=binding['feature_abi'],live_observation_sha256=hashes['observed'])
        provisional=packet('HumanDecision','F5_HUMAN_CONTROL',original_decision['event_id'],original_decision['brain_generation_id'],original_decision['provenance'],kind='output',value=selected['label'],source_ref=original_decision['source_ref'],learning_permission='learn',selection=selection)
        write(out/'human-decision.json',provisional)
        portable={name:out/(name+'.json') for name in ('observed','features','context','tokens','result')}
        portable.update(query_source=out/'query.txt',label_source=out/'label.txt',human_decision=out/'human-decision.json',label_tokenization=out/'label-tokenization.json')
        entry={name:original.descriptor(out,path) for name,path in portable.items()};target=tok['token_ids'][0]
        write(out/'validation-only.json',{'schema':SCHEMA,'feature_abi':binding['feature_abi'],'config':{k:DEFAULTS[k] for k in original.KNOB_NAMES},'token_ids':[target,(target+1)%65536],'observations':[entry]})
        prepare(out/'validation-only.json');(out/'validation-only.json').unlink();deadline_check(deadline)
        verify_binding(binding)
        if file_hash(receipt_path)!=receipt_sha or any(file_hash(path)!=hashes[name] or file_hash(out/(name+'.json'))!=hashes[name] for name,path in paths.items()) or original.select_label(store,decision_id,label_source_id,revision,learn)!=selected:raise ValueError('Original permission/source/record changed during export')
        deadline_check(deadline)
        derived=original.persist_export_decision(store,selected,out/'observed.json',binding['feature_abi'],learn);write(out/'human-decision.json',derived)
        entry['human_decision']=original.descriptor(out,out/'human-decision.json')
        fragment={'schema':original.FRAGMENT,'feature_abi':binding['feature_abi'],'target_token_id':target,'observation':entry,
            'original_human_decision':original.descriptor(out,out/'original-human-decision.json'),'original_context_packet':original.descriptor(out,out/'original-context-packet.json'),'original_event':original.descriptor(out,out/'original-event.json'),
            'export_decision_packet_id':derived['packet_id'],'authority':'EXPLICIT_OPERATOR_LEARN_REEXPORT','production_integration':False,'approval_authority':0,
            'recorded_runtime_evidence':{'original_message_id':mid,'raw_artifacts':{name:original.descriptor(out,out/(name+'.json')) for name in RAW_NAMES},'tokenizer_receipt':original.descriptor(out,out/'tokenizer-receipt.json'),'checks':checks,'prefill_calls':0}}
        write(out/'fragment.json',fragment);report.update(status='RECORDED_CAUSAL_LABEL_EXPORTED',fragment_sha256=file_hash(out/'fragment.json'),target_token_id=target,export_decision_packet_id=derived['packet_id'],checks=checks)
        return report
    except BaseException as exc:
        report.update(status='RECORDED_EXPORT_REJECTED',error_type=type(exc).__name__,error=str(exc));raise
    finally:
        if store:store.close()
        report['elapsed_s']=time.monotonic()-started
        if created:write(out/'recorded-export-report.json',report)

def tokenize_label(home,out,decision_id,label_source_id,learn,seconds=90,rss_mb=768):
    started=time.monotonic();deadline=bounded(seconds)
    if type(rss_mb) is not int or not 128<=rss_mb<=2048:raise ValueError('RSS128..2048MiB required')
    home=Path(home).resolve();out=Path(out).resolve();store=None;runner=None;watcher=None;cancel=threading.Event();done=threading.Event();handlers={};created=False
    report={'status':'LABEL_TOKENIZATION_STARTED','native_calls':False,'prefill_calls':0,'approval_authority':0,'seconds_limit':seconds,'rss_limit_mb':rss_mb}
    try:
        if out.exists() or not (home/'data/db/brain.sqlite3').is_file():raise ValueError('Existing Store/new receipt directory required')
        store=Store(home);binding=bind_installed(home);revision=ModelManager(home).revision('C3_LANGUAGE');selected=original.select_label(store,decision_id,label_source_id,revision,learn);out.mkdir(parents=True);created=True
        for sig in (signal.SIGINT,signal.SIGTERM):handlers[sig]=signal.getsignal(sig);signal.signal(sig,lambda *_:cancel.set())
        runner=LlamaRunner(home,'C3_LANGUAGE',Path(binding['identity']['model_path']),dict(DEFAULTS,context_tokens=2048,threads=2));runner.binary=binding['identity']['server_path']
        report['resource_samples']=[]
        def monitor():
            while not done.wait(.05):
                if runner.proc is not None and runner.proc.poll() is None:
                    memory=process_memory(runner.proc.pid);report['resource_samples'].append(memory)
                    if len(report['resource_samples'])>64:del report['resource_samples'][1]
                    if (memory.get('rss_bytes') or 0)>rss_mb*1024*1024:report['resource_exceeded']=True;cancel.set();return
        watcher=threading.Thread(target=monitor,daemon=True);watcher.start();report['native_calls']=True
        runner.load(cancel,deadline);request={'content':selected['label'],'add_special':False};response=runner._json('POST','/tokenize',request,deadline);check(cancel,deadline)
        release=runner.unload();done.set();watcher.join(.25)
        if report.get('resource_exceeded'):raise Limits('Label tokenizer RSS bound exceeded')
        verify_binding(binding);check(cancel,deadline)
        if original.select_label(store,decision_id,label_source_id,revision,learn)!=selected:raise ValueError('Original permission/source changed during tokenization')
        tok={'source_sha256':digest(selected['label']),'model_sha256':binding['identity']['model_sha256'],'worker_sha256':binding['binary_sha256'],'token_ids':response['tokens'],'add_special':False,'tokenizer':'PINNED_LLAMA_RUNNER_HTTP_TOKENIZE','server_sha256':binding['identity']['server_sha256']}
        receipt={'schema':RECEIPT,'status':'ACTUAL_LABEL_TOKENIZED_REAPED','feature_abi':binding['feature_abi'],'model_revision':revision,'request':request,'response':response,'release':release,'label_tokenization':tok}
        path=out/'receipt.json';write(path,receipt);validate_receipt(path,selected['label'],binding,revision)
        report.update(status='ACTUAL_LABEL_TOKENIZED_REAPED',receipt_sha256=file_hash(path),release=release);return report
    except BaseException as exc:
        report.update(status='LABEL_TOKENIZATION_REJECTED',error_type=type(exc).__name__,error=str(exc));raise
    finally:
        done.set()
        if watcher:watcher.join(.25)
        if runner:report['final_release']=runner.unload()
        if store:store.close()
        for sig,handler in handlers.items():signal.signal(sig,handler)
        report['elapsed_s']=time.monotonic()-started
        if created:write(out/'tokenizer-report.json',report)

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    for command in ('export','tokenize'):
        p=sub.add_parser(command);p.add_argument('--installed-home');p.add_argument('--decision',required=True);p.add_argument('--label-source',required=True);p.add_argument('--learn',action='store_true',required=True);p.add_argument('--out',required=True);p.add_argument('--seconds',type=int,default=90)
        if command=='export':p.add_argument('--tokenizer-receipt',required=True)
        else:p.add_argument('--rss-limit-mb',type=int,default=768)
    args=parser.parse_args()
    try:
        if args.command=='export':report=export_recorded(home_path(args.installed_home),args.out,args.decision,args.label_source,args.tokenizer_receipt,args.learn,args.seconds)
        else:report=tokenize_label(home_path(args.installed_home),args.out,args.decision,args.label_source,args.learn,args.seconds,args.rss_limit_mb)
        print(dumps(report),flush=True);return 0
    except (ValueError,KeyError,OSError,RuntimeError) as exc:
        print(dumps({'status':'RECORDED_EXPORT_OR_TOKENIZER_REJECTED','error_type':type(exc).__name__,'error':str(exc),'approval_authority':0}),flush=True);return 2

if __name__=='__main__':sys.exit(main())
