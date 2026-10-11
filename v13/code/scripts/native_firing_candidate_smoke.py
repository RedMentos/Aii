#!/usr/bin/env python3
"""Isolated real-model Exact/Trace/Combined diagnostic, never a quality gate.

--prepare creates an immutable registration without launching a child. --run
requires those identical source, fixture, model and runner bytes. Synthetic slots
are approved only in this new diagnostic home; no user home is read or modified.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import threading
import time
import types

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import native_firing_runtime_candidate as firing
from scripts import approval_reader_runtime_candidate as reader
from v13.common import atomic_write,file_hash
from v13.memory_server import MANIFEST,runtime_library_hashes
from v13.memory_trainer import ROLE,live_system
from v13.sparse_memory import DELIVERY_SCHEMA,fact_item_bindings,native_items_path

QUESTION='What is the name of my cat?'
FACT='Mitzi'
CASES=(QUESTION,'What is the name of my neighbour\'s cat?',QUESTION)
ARMS=('exact','trace','combined')
CFG={'context_tokens':2048,'threads':2,'answer_tokens':40,'temperature':0.,
     'c3_sampling':'default','offer_logprobs':False}


def merged_sources():
    original,_=firing.sources()
    approval_original,_=reader.sources()
    if any(original[k]!=v for k,v in approval_original.items()):
        raise ValueError('Candidate baselines differ')
    interim=dict(original);interim.update(reader.transform(approval_original))
    return original,firing.transform(interim)


def load_merged(name):
    _,changed=merged_sources()
    module=types.ModuleType('v13._merged_native_firing_'+name)
    module.__package__='v13';module.__file__=str(ROOT/('v13/'+name+'.py'))
    exec(compile(changed['v13/'+name+'.py'],module.__file__,'exec'),module.__dict__)
    return module


def fixture_bytes():
    # One authored, nonzero, always-threshold-eligible row; guard disabled.
    # This fixture tests writes and source lineage, not keyed useful learning.
    hidden=1024
    centre=[0.]*hidden;key=[1.]+[0.]*(hidden-1);value=[.001]+[0.]*(hidden-1)
    return (b'V13SMEM1'+struct.pack('<6i2f',0,hidden,1,1,1,0,.01,1.)+
            struct.pack('<%df'%(3*hidden+1),*(centre+key+[-1.]+value))+
            struct.pack('<i',-1))


def binding(binary,model):
    original,changed=merged_sources()
    return {'schema':'V13_MERGED_NATIVE_FIRING_DIAGNOSTIC_V1',
            'binary_sha256':file_hash(binary),'runtime_libraries_sha256':runtime_library_hashes(binary),
            'model_sha256':file_hash(model),'script_sha256':file_hash(__file__),
            'firing_helper_sha256':file_hash(firing.__file__),'reader_helper_sha256':file_hash(reader.__file__),
            'baseline_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in original.items()},
            'candidate_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in changed.items()},
            'support_sha256':{n:file_hash(ROOT/n) for n in ('v13/sparse_audit.py','v13/sparse_memory.py',
                'v13/lora_trainer.py','v13/memory_trainer.py','v13/memory.py','v13/agi/weights.py')},
            'recursive_runtime_sha256':{p.relative_to(ROOT).as_posix():file_hash(p)
                for p in sorted((ROOT/'v13').rglob('*.py')) if '__pycache__' not in p.parts},
            'fixture_sha256':hashlib.sha256(fixture_bytes()).hexdigest(),
            'questions':list(CASES),'fact':FACT,'arms':list(ARMS),'config':CFG,'seed':13,
            'memory_origin':'SYNTHETIC_PROTOCOL_FIXTURE','learned_recall_proven':False,
            'synthetic_guard_disabled':True,'trace_only_is_explicit_comparison_arm':True,
            'selective_omission_enabled':False,'semantic_truth_authority':False,
            'activation_authorized':False,'phone_measured':False}


def prepare(binary,model,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    registration=binding(binary,model)
    atomic_write(out/'registration.json',json.dumps(registration,indent=2,allow_nan=False))
    return registration


def run(binary,model,out):
    from v13.runtime import Runtime
    from v13.lora_trainer import AdapterRegistry
    out=Path(out);registered=json.loads((out/'registration.json').read_text())
    if binding(binary,model)!=registered:raise ValueError('Registered diagnostic bytes/config changed')
    if (out/'report.json').exists():raise ValueError('Report already exists; preserve this attempt')
    runner_module=load_merged('runners');memory_module=load_merged('memory_server')
    report={'status':'RUNNING','registration_sha256':file_hash(out/'registration.json'),
            'binding':registered,'rows':[],'cleanup':[],'quality_gate_changed':False}
    def save():atomic_write(out/'report.json',json.dumps(report,indent=2,allow_nan=False))
    save()
    try:
        for arm in ARMS:
            for enabled in (False,True):
                name=arm+('-audit-on' if enabled else '-audit-off')
                home=out/(name+'.checkpoint')
                if home.exists():raise ValueError('Diagnostic home already exists')
                runtime=Runtime(home);runtime.sleep.cycle.set_policy('enabled','off');runner=None
                try:
                    event=runtime.store.event(runtime.session,QUESTION)
                    runtime.memory.feedback(event['event_id'],'fact',FACT)
                    memory=runtime.memory.recall('cat',runtime.session)[0]
                    (home/'bin/llama-server').symlink_to(Path(binary).resolve())
                    (home/'bin/llama-server-mem').symlink_to(Path(binary).resolve())
                    atomic_write(home/MANIFEST,json.dumps({'binary_sha256':file_hash(binary),
                        'runtime_libraries_sha256':runtime_library_hashes(binary)}))
                    if arm!='exact':
                        native=home/'synthetic-memory.bin';native.write_bytes(fixture_bytes())
                        side={'schema':DELIVERY_SCHEMA,'native_sha256':file_hash(native),
                              'source_pt':None,'rows':[memory['id']],'forgotten':[],
                              'item_bindings':fact_item_bindings([{'memory_id':memory['id'],'kind':'fact',
                                'prompt':memory['key_text'],'target':memory['value'],'source_ref':memory['source_ref']}])}
                        atomic_write(native_items_path(native),json.dumps(side))
                        (out/(name+'.synthetic-memory.bin')).write_bytes(native.read_bytes())
                        atomic_write(out/(name+'.synthetic-memory.items.json'),json.dumps(side,indent=2))
                        AdapterRegistry(runtime.store).activate(ROLE,native,file_hash(native),file_hash(model),
                            'SYNTHETIC_DIAGNOSTIC_ONLY')
                    cfg=dict(CFG,native_memory_audit=enabled)
                    runner=runner_module.LlamaRunner(home,'C3_LANGUAGE',Path(model),cfg,approval_store=runtime.store)
                    runner.binary=str(Path(binary).resolve())
                    for index,question in enumerate(CASES):
                        memories=[memory] if arm in ('exact','combined') else []
                        system=live_system(memories=[{'topic':memory['key_text'],'correction':memory['value']}]
                            if memories else [])
                        answer=''.join(runner.generate([{'role':'system','content':system},
                            {'role':'user','content':question}],threading.Event(),time.monotonic()+180,seed=13))
                        observed=runner.last_metrics.get('native_memory_firing')
                        delivery=memory_module.observed_shadow_delivery(runtime.store,home,'C3_LANGUAGE',model,
                            runner.memory_delivery_binding,[memory],observed) if observed is not None else None
                        report['rows'].append({'arm':arm,'audit_enabled':enabled,'index':index,'question':question,
                            'answer':answer,'metrics':runner.last_metrics,'shadow_delivery':delivery,
                            'exact_in_prompt':bool(memories),'authored_fixture':True})
                        save()
                finally:
                    cleanup=runner.unload() if runner else {'process_reaped':True,'no_runner_created':True}
                    native_log=home/'logs/C3_LANGUAGE.log'
                    if native_log.is_file():(out/(name+'.native.log')).write_bytes(native_log.read_bytes())
                    report['cleanup'].append({'arm':arm,'audit_enabled':enabled,'result':cleanup})
                    runtime.close();save()
        pairs={(r['arm'],r['audit_enabled'],r['index']):r for r in report['rows']}
        checks={'all_18_rows':len(pairs)==18,
            'paired_answers_identical':all(pairs[a,False,i]['answer']==pairs[a,True,i]['answer'] for a in ARMS for i in range(3)),
            'paired_prompt_tokens_identical':all(pairs[a,False,i]['metrics'].get('prompt_tokens')==pairs[a,True,i]['metrics'].get('prompt_tokens') for a in ARMS for i in range(3)),
            'audit_off_has_no_observation':all('native_memory_firing' not in r['metrics'] for r in report['rows'] if not r['audit_enabled']),
            'exact_only_has_no_observation':all('native_memory_firing' not in r['metrics'] for r in report['rows'] if r['arm']=='exact'),
            'first_trace_combined_observed':all(pairs[a,True,i]['metrics'].get('native_memory_firing',{}).get('status')=='OBSERVED_NATIVE_WRITES' for a in ('trace','combined') for i in (0,1)),
            'first_trace_combined_maps_bound_fact':all(len(pairs[a,True,i]['shadow_delivery'].get('observed_memory_ids',[]))==1 for a in ('trace','combined') for i in (0,1)),
            'all_shadow_retains_exact':all(r['shadow_delivery']['exact_retained'] and r['shadow_delivery']['mode']=='SHADOW' and not r['shadow_delivery']['quality_proven'] and not r['shadow_delivery']['activation_authorized'] and not r['shadow_delivery']['semantic_truth_authority'] for r in report['rows'] if r['shadow_delivery']),
            'all_processes_reaped':all(r['result'].get('process_reaped') is True for r in report['cleanup'])}
        report.update(checks=checks,status='PASS_EXECUTION_ONLY' if all(checks.values()) else 'FAIL_EXECUTION_DIAGNOSTIC')
        save();return report
    except BaseException as exc:
        report.update(status='INCOMPLETE',error={'type':type(exc).__name__,'detail':str(exc)[:600]});save();raise


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--binary',required=True);ap.add_argument('--model',required=True);ap.add_argument('--out',type=Path,required=True)
    action=ap.add_mutually_exclusive_group(required=True);action.add_argument('--prepare',action='store_true');action.add_argument('--run',action='store_true')
    a=ap.parse_args();result=prepare(a.binary,a.model,a.out) if a.prepare else run(a.binary,a.model,a.out)
    print(json.dumps({'status':result.get('status','REGISTERED_NO_INFERENCE'),'out':str(a.out)}))
