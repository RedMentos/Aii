#!/usr/bin/env python3
"""Export explicit Store output labels with actual causal stream observations.

capture performs native work; assemble is offline. Neither trains, approves or
activates anything. An original explicit output --learn label must be selected
again; model previews never become labels. The installed command is
`:feedback output <reference text> --learn`.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import threading
import time
APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
from scripts.native_prefill_stream_client import StreamingOutputSession,bind_installed,verify_binding,read_json
from scripts.train_live_output_adapter import SCHEMA,prepare,configuration,artifact
from v13.common import atomic_write,digest,dumps,file_hash,Limits
from v13.config import DEFAULTS,home_path
from v13.contracts import packet,validate
from v13.models import ModelManager
from v13.resources import process_memory
from v13.runners import LlamaRunner,check
from v13.store import Store

FRAGMENT='V13_CAUSAL_LIVE_OUTPUT_EXPORT_V1'
NAMES=('observed','features','context','tokens','result','query_source','label_source','human_decision','label_tokenization')
KNOB_NAMES=('output_adapter_steps','output_adapter_lr','max_update_norm','retention_max_delta','output_adapter_max_bias','output_adapter_support_cosine')

def write(path,value):atomic_write(path,dumps(value))

def select_label(store,decision_id,label_source_id,model_revision,learn):
    """Read existing human authority; never infer it from the assistant's text."""
    if learn is not True:raise ValueError('Explicit --learn export intent required')
    row=store.one("SELECT payload FROM packets WHERE id=? AND kind='HumanDecision'",(decision_id,))
    if not row:raise ValueError('Original typed HumanDecision not found')
    d=json.loads(row['payload']);validate('HumanDecision',d)
    if d['producer_component']!='F5_HUMAN_CONTROL' or d['kind']!='output' or d['learning_permission']!='learn' or d['source_ref']['source_id']!=label_source_id or d.get('export_binding'):raise ValueError('Select original explicit output --learn label/source')
    label=store.read_source(d['source_ref']);s=d['selection']
    if not label.strip() or len(label.encode())>4096 or label!=d['value'] or d['source_ref']['char_start']!=0 or d['source_ref']['char_end']!=len(label) or s['target_position']!=0:raise ValueError('Original bounded exact human label differs')
    feedback=store.one("SELECT * FROM feedback WHERE event_id=? AND source_id=? AND kind='output'",(d['event_id'],label_source_id))
    if not feedback or feedback['permission']!='learn' or feedback['value']!=label:raise ValueError('Original feedback authorization absent or revoked')
    erow=store.one('SELECT packet FROM events WHERE id=?',(d['event_id'],))
    if not erow:raise ValueError('Original event missing')
    event=json.loads(erow['packet']);validate('EventEnvelope',event)
    if event['authority']!='AUTHORITATIVE' or event['brain_generation_id']!=d['brain_generation_id']:raise ValueError('Original authoritative event/generation mismatch')
    crow=store.one("SELECT payload FROM packets WHERE id=? AND event_id=? AND kind='OutputAdapterContext'",(s['context_packet_id'],d['event_id']))
    if not crow:raise ValueError('Original C3 context packet absent')
    ctx=json.loads(crow['payload']);validate('OutputAdapterContext',ctx)
    revision=digest(dumps({'worker':file_hash(APP/'v13/output_adapter_worker.py'),'runner':file_hash(APP/'v13/runners.py'),'model':model_revision}))
    if ctx['native_role']!='C3_LANGUAGE' or s['model_revision']!=model_revision or ctx['model_revision']!=model_revision or s['context_revision']!=revision or ctx['context_revision']!=revision or ctx['context_ref']!=s['context_ref'] or ctx['provenance']!=s['source_refs']:raise ValueError('Original model/context/provenance revision differs')
    for ref in d['provenance']+s['source_refs']:store.read_source(ref)
    messages=json.loads(store.read_source(s['context_ref']));query=store.read_source(event['source_ref'])
    if not isinstance(messages,list) or not messages or any(set(m)!={'role','content'} or m['role'] not in {'system','user','assistant'} or not isinstance(m['content'],str) for m in messages) or messages[-1]!={'role':'user','content':query} or s['context_ref']['sha256']!=digest(dumps(messages)):raise ValueError('Exact original query/context differs')
    # A later original correction for this context supersedes the selected label.
    latest=store.one("SELECT id FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.kind')='output' AND json_extract(payload,'$.selection.context_ref.sha256')=? AND json_extract(payload,'$.export_binding') IS NULL ORDER BY created DESC LIMIT 1",(s['context_ref']['sha256'],))
    if not latest or latest['id']!=decision_id:raise ValueError('Original human label superseded; select latest decision')
    return {'decision':d,'original_payload':row['payload'],'context_packet':ctx,'event':event,'query':query,'label':label,'messages':messages}

def persist_export_decision(store,selected,observed_path,abi,learn):
    if learn is not True:raise ValueError('Explicit --learn export intent required')
    original=selected['decision'];observed_sha=file_hash(observed_path)
    observed_ref=store.source(Path(observed_path).read_text(),'NATIVE_CAUSAL_OUTPUT_OBSERVATION')
    selection=dict(original['selection'],feature_abi=abi,live_observation_sha256=observed_sha)
    binding={'schema':'V13_HUMAN_OUTPUT_EXPORT_BINDING_V1','original_human_decision_packet_id':original['packet_id'],
             'original_human_decision_payload_sha256':digest(selected['original_payload']),
             'original_label_source_ref':original['source_ref'],'observed_source_ref':observed_ref,
             'operator_export_intent':'EXPLICIT_CLI_LEARN_UNCHANGED_LABEL_CONTEXT',
             'human_saw_future_features':False,'label_origin':'ORIGINAL_TYPED_HUMAN_OUTPUT_REFERENCE'}
    d=packet('HumanDecision','F5_HUMAN_CONTROL',original['event_id'],original['brain_generation_id'],
             [*original['provenance'],observed_ref],kind='output',value=selected['label'],source_ref=original['source_ref'],
             learning_permission='learn',selection=selection,export_binding=binding)
    store.add_packet('HumanDecision',d);return d

def descriptor(root,path):return {'path':str(Path(path).relative_to(root)),'sha256':file_hash(path)}

def list_labels(home):
    home=Path(home).resolve()
    if not (home/'data/db/brain.sqlite3').is_file():raise ValueError('Existing installed Store required')
    store=Store(home)
    try:
        revision=ModelManager(home).revision('C3_LANGUAGE');labels=[]
        for row in store.rows("SELECT id,payload FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.kind')='output' AND json_extract(payload,'$.learning_permission')='learn' AND json_extract(payload,'$.export_binding') IS NULL ORDER BY created DESC LIMIT 128"):
            d=json.loads(row['payload'])
            try:selected=select_label(store,row['id'],d['source_ref']['source_id'],revision,True)
            except (ValueError,KeyError):continue
            labels.append({'decision':row['id'],'label_source':d['source_ref']['source_id'],'event_id':d['event_id'],'query':selected['query'],'label':selected['label']})
        return {'status':'CURRENT_EXPLICIT_OUTPUT_LABELS','labels':labels,'native_calls':False,'approval_authority':0}
    finally:store.close()

def capture(home,out,decision_id,label_source_id,learn,seconds=90,rss_mb=768):
    if type(seconds) is not int or not 5<=seconds<=90 or type(rss_mb) is not int or not 128<=rss_mb<=2048:raise ValueError('Existing bounded seconds5..90/RSS128..2048MiB required')
    home=Path(home).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();deadline=started+seconds;cancel=threading.Event();done=threading.Event();store=None;runner=None;session=None;watcher=None
    report={'status':'CAPTURE_STARTED','native_calls':False,'approval_authority':0,'production_integration':False,'original_decision_packet_id':decision_id,'label_source_id':label_source_id}
    handlers={}
    for sig in (signal.SIGINT,signal.SIGTERM):handlers[sig]=signal.getsignal(sig);signal.signal(sig,lambda *_:cancel.set())
    try:
        if not (home/'data/db/brain.sqlite3').is_file():raise ValueError('Existing installed Store required; no bootstrap')
        store=Store(home);models=ModelManager(home);binding=bind_installed(home)
        selected=select_label(store,decision_id,label_source_id,models.revision('C3_LANGUAGE'),learn)
        atomic_write(out/'original-human-decision.json',selected['original_payload'])
        write(out/'original-context-packet.json',selected['context_packet']);write(out/'original-event.json',selected['event'])
        atomic_write(out/'query.txt',selected['query']);atomic_write(out/'label.txt',selected['label'])
        write(out/'binding.json',binding)
        cfg=dict(DEFAULTS,context_tokens=2048,threads=2,answer_tokens=64)
        runner=LlamaRunner(home,'C3_LANGUAGE',Path(binding['identity']['model_path']),cfg)
        if Path(runner.binary).resolve(strict=True)!=Path(binding['identity']['server_path']).resolve(strict=True) or file_hash(runner.binary)!=binding['identity']['server_sha256']:raise ValueError('Template/tokenizer server differs from exact installed binding')
        report['template_resources']=[]
        def monitor():
            while not done.wait(.05):
                if runner is not None and runner.proc is not None and runner.proc.poll() is None:
                    memory=process_memory(runner.proc.pid);report['template_resources'].append(memory)
                    if len(report['template_resources'])>64:del report['template_resources'][1]
                    if (memory.get('rss_bytes') or 0)>rss_mb*1024*1024:report['template_resource_exceeded']=True;cancel.set();return
        watcher=threading.Thread(target=monitor,daemon=True);watcher.start();report['native_calls']=True
        runner.load(cancel,deadline);prompt,count,trimmed=runner._prompt(selected['messages'],cancel,deadline,64)
        ids=runner._json('POST','/tokenize',{'content':prompt,'add_special':True},deadline)['tokens']
        targets=runner._json('POST','/tokenize',{'content':selected['label'],'add_special':False},deadline)['tokens']
        check(cancel,deadline)
        if trimmed or count!=len(ids) or not 1<=count<=512 or not targets or any(type(i) is not int or not 0<=i<65536 for i in targets):raise ValueError('Exact bounded untrimmed native context/label tokenization required')
        context={'messages':selected['messages'],'prompt':prompt,'token_ids':ids,'history_trimmed':False}
        write(out/'label-tokenization.json',{'source_sha256':digest(selected['label']),'model_sha256':binding['feature_abi']['model_sha256'],'worker_sha256':binding['feature_abi']['worker_sha256'],'token_ids':targets,'add_special':False,'tokenizer':'PINNED_LLAMA_RUNNER_HTTP_TOKENIZE','server_sha256':binding['identity']['server_sha256']})
        report['template_release']=runner.unload();runner=None;done.set();watcher.join(.25)
        if report.get('template_resource_exceeded') or not report['template_release']['process_reaped']:raise Limits('Template resource bound/reap failed')
        verify_binding(binding);check(cancel,deadline)
        session=StreamingOutputSession(binding,context,out/'native-context',cancel,deadline,rss_limit_bytes=rss_mb*1024*1024,max_tokens=64)
        with session:
            observed=session.pause();write(out/'observed.json',observed)
            complete=None
            for event in session.resume([]):
                if event['event']=='COMPLETE':complete=event
            if complete is None:raise ValueError('Actual native completion missing')
            write(out/'client-complete.json',complete)
        if session.metrics['process_reaped'] is not True:raise ValueError('Native worker not reaped')
        verify_binding(binding)
        reselected=select_label(store,decision_id,label_source_id,models.revision('C3_LANGUAGE'),learn)
        if reselected!=selected:raise ValueError('Original source/permission changed during native capture')
        derived=persist_export_decision(store,selected,out/'observed.json',binding['feature_abi'],learn);write(out/'human-decision.json',derived)
        paths={'observed':out/'observed.json','query_source':out/'query.txt','label_source':out/'label.txt','human_decision':out/'human-decision.json','label_tokenization':out/'label-tokenization.json'}
        paths.update({name:out/'native-context'/(name+'.json') for name in ('features','context','tokens','result')})
        entry={name:descriptor(out,path) for name,path in paths.items()}
        fragment={'schema':FRAGMENT,'feature_abi':binding['feature_abi'],'target_token_id':targets[0],'observation':entry,'original_human_decision':descriptor(out,out/'original-human-decision.json'),'original_context_packet':descriptor(out,out/'original-context-packet.json'),'original_event':descriptor(out,out/'original-event.json'),'export_decision_packet_id':derived['packet_id'],'authority':'EXPLICIT_OPERATOR_LEARN_REEXPORT','production_integration':False,'approval_authority':0}
        write(out/'fragment.json',fragment)
        report.update(status='ACTUAL_CAUSAL_LABEL_EXPORTED',fragment_sha256=file_hash(out/'fragment.json'),export_decision_packet_id=derived['packet_id'],target_token_id=targets[0],native_preview_is_label=False)
        return report
    except BaseException as exc:
        report.update(status='CAPTURE_REJECTED_NO_DATASET',error_type=type(exc).__name__,error=str(exc));raise
    finally:
        done.set()
        if watcher:watcher.join(.25)
        if runner is not None:report['final_template_release']=runner.unload()
        if session is not None:session.close();report['session_metrics']=dict(session.metrics)
        if store is not None:store.close()
        for sig,handler in handlers.items():signal.signal(sig,handler)
        report['elapsed_s']=time.monotonic()-started;write(out/'capture-report.json',report)

def assemble(fragments,out,config=None):
    """Exact portable copies, no native call, rehash all original decision links."""
    if not 1<=len(fragments)<=512:raise ValueError('One to512 explicit fragment paths required')
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);abi=None;entries=[];tokens=[]
    cfg=configuration(config or {k:DEFAULTS[k] for k in KNOB_NAMES})
    for i,path in enumerate(fragments):
        path=Path(path).resolve();root=path.parent;fragment=read_json(path)
        if fragment.get('schema')!=FRAGMENT or fragment.get('authority')!='EXPLICIT_OPERATOR_LEARN_REEXPORT':raise ValueError('Explicit actual capture fragment required')
        if abi is None:abi=fragment['feature_abi']
        if fragment['feature_abi']!=abi:raise ValueError('Cohort exact model/source/library ABI mismatch')
        source=artifact(root,fragment['original_human_decision']);original=json.loads(source.read_text());validate('HumanDecision',original)
        paths={name:artifact(root,fragment['observation'][name]) for name in NAMES};decision=read_json(paths['human_decision']);binding=decision['export_binding']
        if original['learning_permission']!='learn' or original['kind']!='output' or original.get('export_binding') or binding['original_human_decision_packet_id']!=original['packet_id'] or binding['original_human_decision_payload_sha256']!=file_hash(source) or binding['original_label_source_ref']!=original['source_ref'] or decision['source_ref']!=original['source_ref'] or decision['value']!=original['value'] or binding['human_saw_future_features'] is not False or binding['observed_source_ref']['sha256']!=fragment['observation']['observed']['sha256']:raise ValueError('Original human decision export linkage differs')
        ctx=read_json(artifact(root,fragment['original_context_packet']));event=read_json(artifact(root,fragment['original_event']))
        validate('OutputAdapterContext',ctx);validate('EventEnvelope',event)
        selection=original['selection']
        if event['event_id']!=original['event_id'] or event['authority']!='AUTHORITATIVE' or event['source_ref']['sha256']!=fragment['observation']['query_source']['sha256'] or ctx['event_id']!=original['event_id'] or ctx['packet_id']!=selection['context_packet_id'] or ctx['context_ref']!=selection['context_ref'] or ctx['provenance']!=selection['source_refs'] or ctx['model_revision']!=selection['model_revision'] or ctx['context_revision']!=selection['context_revision'] or decision['selection']!={**selection,'feature_abi':abi,'live_observation_sha256':fragment['observation']['observed']['sha256']} or fragment['export_decision_packet_id']!=decision['packet_id']:raise ValueError('Original event/context/derived selection lineage differs')
        folder=out/('observation-'+str(i));folder.mkdir();entry={}
        for name in NAMES:
            destination=folder/(name+'.json');shutil.copyfile(paths[name],destination);entry[name]=descriptor(out,destination)
        # Keep original bytes/provenance alongside descriptors, although the
        # unchanged numerical trainer only consumes the nine bound artifacts.
        for name in ('original_human_decision','original_context_packet','original_event'):
            shutil.copyfile(artifact(root,fragment[name]),folder/(name+'.json'))
        shutil.copyfile(path,folder/'fragment.json');entries.append(entry)
        target=read_json(paths['label_tokenization'])['token_ids'][0]
        if fragment['target_token_id']!=target:raise ValueError('Native label target differs')
        if target not in tokens:tokens.append(target)
    if not 2<=len(tokens)<=16:raise ValueError('Need2..16 distinct explicitly labelled first native target rows; collect more labels')
    dataset=out/'dataset.json';write(dataset,{'schema':SCHEMA,'feature_abi':abi,'config':cfg,'token_ids':tokens,'observations':entries})
    prepare(dataset)
    report={'status':'ASSEMBLED_VALIDATED_NO_TRAINING','observations':len(entries),'target_token_ids':tokens,'dataset_sha256':file_hash(dataset),'native_calls':False,'approval_authority':0}
    write(out/'assembly-report.json',report);return report

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('capture',help='Actual native capture for one original :feedback output --learn label; stop chat first')
    c.add_argument('--installed-home');c.add_argument('--decision',required=True);c.add_argument('--label-source',required=True);c.add_argument('--learn',action='store_true',required=True);c.add_argument('--out',required=True);c.add_argument('--seconds',type=int,default=90);c.add_argument('--rss-limit-mb',type=int,default=768)
    a=sub.add_parser('assemble',help='Offline assembly of exact labelled export fragments')
    a.add_argument('--fragment',action='append',required=True);a.add_argument('--out',required=True);a.add_argument('--config',help='Optional JSON with exactly six existing optimizer knobs')
    l=sub.add_parser('labels',help='List currently valid original explicit output labels with exact packet/source IDs; stop chat first');l.add_argument('--installed-home')
    args=p.parse_args()
    try:
        if args.command=='capture':report=capture(home_path(args.installed_home),args.out,args.decision,args.label_source,args.learn,args.seconds,args.rss_limit_mb)
        elif args.command=='assemble':report=assemble(args.fragment,args.out,read_json(args.config) if args.config else None)
        else:report=list_labels(home_path(args.installed_home))
        print(dumps(report),flush=True);return 0
    except (ValueError,KeyError,OSError,RuntimeError) as exc:
        print(dumps({'status':'EXPORT_OR_ASSEMBLY_REJECTED','error_type':type(exc).__name__,'error':str(exc),'approval_authority':0}),flush=True);return 2

if __name__=='__main__':sys.exit(main())
