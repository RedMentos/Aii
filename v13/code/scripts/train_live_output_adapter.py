#!/usr/bin/env python3
"""Offline shadow-only first-token fit on genuine labelled causal observations.

No model/native call, checkpoint conversion, approval, or Runtime mutation.
Every exported artifact is rehashed before/after fitting. Numerical training is
the unchanged existing output_adapter_worker.train code with a private serializer
format binding; its optimizer, source folds, calibration and retention gates stay
identical. Dataset exporters must supply actual typed HumanDecision sources.
"""
import argparse
import json
import math
from pathlib import Path
import sys
import types
import numpy as np
APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
from scripts.live_output_adapter_port import HEAD_FORMAT,read_json,unique_json
from v13 import output_adapter_worker as numerical
from v13.common import atomic_write,digest,dumps,file_hash
from v13.contracts import validate
from v13.config import KNOBS

SCHEMA='V13_CAUSAL_LIVE_OUTPUT_TRAIN_INPUT_V1'

def artifact(root,record):
    if set(record)!={'path','sha256'} or not isinstance(record['path'],str):raise ValueError('Exact artifact path/hash required')
    relative=Path(record['path']);path=(root/relative).resolve(strict=True)
    if relative.is_absolute() or '..' in relative.parts or not path.is_relative_to(root):raise ValueError('Artifact must stay inside exported dataset')
    if file_hash(path)!=record['sha256']:raise ValueError('Source/native artifact bytes changed')
    return path

def configuration(cfg):
    names=('output_adapter_steps','output_adapter_lr','max_update_norm','retention_max_delta','output_adapter_max_bias','output_adapter_support_cosine')
    if set(cfg)!=set(names):raise ValueError('Explicit existing output optimizer knobs required')
    for name in names:
        value=cfg[name];_,_,low,high,_=KNOBS[name]
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not low<=value<=high:raise ValueError('Invalid existing optimizer knob: '+name)
    if type(cfg['output_adapter_steps']) is not int:raise ValueError('Integer optimizer steps required')
    return dict(cfg)

def prepare(dataset):
    dataset=Path(dataset).resolve();root=dataset.parent;inp=read_json(dataset);cfg=configuration(inp['config']);abi=inp['feature_abi']
    if inp.get('schema')!=SCHEMA or not isinstance(abi,dict) or abi.get('dimension')!=1024 or abi.get('vocabulary')!=65536 or abi.get('n_batch')!=128 or abi.get('n_ubatch')!=128 or abi.get('embeddings') is not False or abi.get('pooling')!='NONE':raise ValueError('Exact causal live feature ABI required')
    for key in ('model_sha256','worker_sha256','worker_sources','library_sha256','runner_tag','feature_schema'):
        if not abi.get(key):raise ValueError('Missing causal model/source/library ABI: '+key)
    tokens=inp['token_ids']
    if not isinstance(tokens,list) or not 2<=len(tokens)<=16 or len(set(tokens))!=len(tokens) or any(type(i) is not int or not 0<=i<65536 for i in tokens):raise ValueError('Two to sixteen exact native target rows required')
    rows=[];baselines=[];labels=[];groups=[];bindings=[]
    observations=inp['observations']
    if not isinstance(observations,list) or len(observations)>512:raise ValueError('Bounded causal observation cohort required')
    for entry in observations:
        paths={name:artifact(root,entry[name]) for name in ('observed','features','context','tokens','result','query_source','label_source','human_decision','label_tokenization')}
        observed,f,context,token_file,result=(read_json(paths[name]) for name in ('observed','features','context','tokens','result'))
        decision=read_json(paths['human_decision']);tokenization=read_json(paths['label_tokenization'])
        query=paths['query_source'].read_text();label=paths['label_source'].read_text()
        validate('HumanDecision',decision)
        if decision['producer_component']!='F5_HUMAN_CONTROL' or decision['kind']!='output' or decision['learning_permission']!='learn' or decision['value']!=label:raise ValueError('Explicit typed human --learn output source required')
        selection=decision['selection'];ref=decision['source_ref']
        if ref.get('sha256')!=entry['label_source']['sha256'] or ref.get('char_start')!=0 or ref.get('char_end')!=len(label) or selection.get('target_position')!=0:raise ValueError('Human label exact source/position mismatch')
        if selection.get('feature_abi')!=abi or selection.get('live_observation_sha256')!=entry['observed']['sha256']:raise ValueError('Human decision must explicitly bind this live observation/ABI')
        if observed.get('feature_abi')!=abi or f.get('schema')!=abi['feature_schema'] or f.get('software_fixture') is True or result.get('software_fixture') is True:raise ValueError('Actual same-ABI native observation required')
        if context.get('history_trimmed') is not False or not context.get('messages') or context['messages'][-1]!={'role':'user','content':query} or selection.get('context_ref',{}).get('sha256')!=digest(dumps(context['messages'])):raise ValueError('Exact authoritative query/context label mismatch')
        ids=context['token_ids'];source_sha=digest(dumps(context));handle=result['handle'];native_binding=observed['native_context_binding']
        if not isinstance(ids,list) or not 1<=len(ids)<=512 or any(type(i) is not int or not 0<=i<65536 for i in ids):raise ValueError('Exact untrimmed causal token IDs required')
        if token_file.get('token_ids')!=ids or observed.get('native_prompt_token_ids')!=ids or f.get('token_ids')!=ids or result.get('token_ids')!=ids:raise ValueError('Native source token IDs differ')
        if observed.get('prompt_sha256')!=digest(context['prompt']) or any(x.get('context_source_sha256')!=source_sha for x in (token_file,f,result,handle,native_binding)):raise ValueError('Native context/source hashes differ')
        if handle.get('features_sha256')!=entry['features']['sha256'] or native_binding.get('features_sha256')!=entry['features']['sha256'] or handle.get('token_file_sha256')!=entry['tokens']['sha256'] or result.get('token_file_sha256')!=entry['tokens']['sha256']:raise ValueError('Full raw feature/token hash binding missing')
        if native_binding.get('live_generation_kv_tap') is not True or native_binding.get('scope')!='EXACT_SAME_CAUSAL_PREFILL' or native_binding.get('handle_id')!=handle.get('handle_id') or len({x.get('pid') for x in (native_binding,handle,f,result)})!=1:raise ValueError('One actual native context/handle/PID required')
        if f.get('model_sha256')!=abi['model_sha256'] or handle.get('model_sha256')!=abi['model_sha256'] or f.get('lib_sha256') not in abi['library_sha256'].values() or handle.get('lib_sha256')!=f['lib_sha256']:raise ValueError('Observation model/library ABI differs')
        if abi['feature_schema']=='V13_PAUSED_CAUSAL_STREAM_FEATURES_V2' and (f.get('feature_abi')!=abi.get('stream_abi') or f.get('worker_source_sha256')!=abi['worker_sources'].get('scripts/native_prefill_stream.cpp')):raise ValueError('Streaming feature/source ABI differs')
        if result.get('status') not in {'PAUSE_RESUME_DIAGNOSTIC_COMPLETE','CAUSAL_STREAM_DIAGNOSTIC_COMPLETE'} or result.get('same_context_lifetime') is not True or result.get('resume_prefill_calls')!=0 or result.get('handle_consumed') is not True:raise ValueError('Completed actual same-context observation required')
        vector=f['live_last_state'];numerical.features([vector])
        if observed.get('feature')!=vector:raise ValueError('Observed feature differs from raw causal state')
        logits=np.asarray(f['first_position']['logits'],dtype=float);p=np.asarray(f['first_position']['probabilities'],dtype=float)
        if logits.shape!=(65536,) or p.shape!=(65536,) or not np.isfinite(logits).all() or not np.isfinite(p).all() or np.any(p<0) or abs(float(p.sum())-1)>1e-9:raise ValueError('Actual full vocabulary probabilities required')
        soft=np.exp(logits-logits.max());soft/=soft.sum()
        if not np.allclose(p,soft,rtol=1e-8,atol=1e-12):raise ValueError('Actual native logits/probabilities differ')
        if tokenization.get('source_sha256')!=entry['label_source']['sha256'] or tokenization.get('model_sha256')!=abi['model_sha256'] or tokenization.get('worker_sha256')!=abi['worker_sha256'] or tokenization.get('add_special') is not False:raise ValueError('Exact human-source native label tokenization binding required')
        target_ids=tokenization['token_ids']
        if not isinstance(target_ids,list) or not target_ids or any(type(i) is not int or not 0<=i<65536 for i in target_ids) or target_ids[0] not in tokens:raise ValueError('Explicit first native target must be a configured row')
        group=entry['query_source']['sha256']
        if group in groups:raise ValueError('Repeated source group: no train/calibration/test leakage')
        selected=p[tokens];other=1.-float(selected.sum())
        if np.any(selected<=0) or other<=0:raise ValueError('Selected/unchanged native probability mass empty')
        rows.append(vector);baselines.append(np.log(np.r_[selected,other]).tolist());labels.append(tokens.index(target_ids[0]));groups.append(group);bindings.append({k:entry[k] for k in paths})
    active=None
    if inp.get('active_checkpoint'):
        active=artifact(root,inp['active_checkpoint'])
        with np.load(active,allow_pickle=False) as a:
            if str(a['format'])!=HEAD_FORMAT or unique_json(str(a['feature_abi']))!=abi:raise ValueError('Legacy/different-ABI active head cannot be converted or reused')
    return {'config':cfg,'token_ids':tokens,'native_features':rows,'base_log_probabilities':baselines,'target_indices':labels,'source_groups':groups,'active_checkpoint':str(active) if active else None},abi,bindings

def train_dataset(dataset,out):
    dataset=Path(dataset).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    inputs,abi,bindings=prepare(dataset);dataset_sha=file_hash(dataset);worker_sha=file_hash(APP/'v13/output_adapter_worker.py');active_sha=file_hash(inputs['active_checkpoint']) if inputs['active_checkpoint'] else None
    # Only the serializer's explicit format tag differs. The source code and all
    # mathematical helper functions/gates are exactly the existing worker's.
    pure=types.FunctionType(numerical.train.__code__,dict(numerical.train.__globals__,FORMAT=HEAD_FORMAT),name='train_causal_live',argdefs=numerical.train.__defaults__)
    metrics=pure(inputs,out)
    candidate=out/'candidate.npz'
    with np.load(candidate,allow_pickle=False) as a:arrays={key:a[key] for key in a.files}
    arrays['feature_abi']=np.asarray(dumps(abi));np.savez(candidate,**arrays)
    with np.load(candidate,allow_pickle=False) as a:
        metrics['live_checkpoint_reload']=str(a['format'])==HEAD_FORMAT and unique_json(str(a['feature_abi']))==abi and all(np.array_equal(a[key],value) for key,value in arrays.items())
    # Preserve all native retention anchors. The prepared live executor has a
    # lower bounded support capacity; capacity excess is an explicit failing gate.
    metrics['live_execution_support_capacity_pass']=len(arrays['anchors'])<=512
    metrics['commit_eligible']=bool(metrics['commit_eligible'] and metrics['live_execution_support_capacity_pass'] and metrics['live_checkpoint_reload'])
    root=dataset.parent
    if file_hash(dataset)!=dataset_sha or file_hash(APP/'v13/output_adapter_worker.py')!=worker_sha or (active_sha is not None and file_hash(inputs['active_checkpoint'])!=active_sha) or any(file_hash(artifact(root,row[name]))!=row[name]['sha256'] for row in bindings for name in row):raise ValueError('Bound training observation changed during fit')
    report={'schema':'V13_CAUSAL_LIVE_OUTPUT_SHADOW_REPORT_V1','status':'EVALUATED_CANDIDATE_NO_APPROVAL','format':HEAD_FORMAT,'feature_abi':abi,
            'dataset_sha256':dataset_sha,'numerical_worker_sha256':worker_sha,'candidate_sha256':file_hash(candidate),'metrics':metrics,
            'production_integration':False,'approval_authority':0,'native_body_parameters_modified':0,'semantic_truth_authority':False}
    atomic_write(out/'metrics.json',dumps(metrics));atomic_write(out/'report.json',dumps(report));return report

def validate_only(dataset,out):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    try:
        inp,abi,_=prepare(dataset)
        folds=np.asarray([int(digest(group)[:8],16)%5 for group in inp['source_groups']]);labels=np.asarray(inp['target_indices'])
        partition={name:np.flatnonzero(mask).tolist() for name,mask in [('train',folds>=2),('calibration',folds==1),('test',folds==0)]}
        ready=all(len(ids)>=8 and all(np.sum(labels[ids]==k)>=2 for k in range(len(inp['token_ids']))) for ids in partition.values())
        report={'status':'VALIDATED_COHORT_READY_NO_TRAINING' if ready else 'INSUFFICIENT_LABELLED_COHORT',
                'schema':SCHEMA,'observations':len(inp['source_groups']),'partition':partition,'feature_abi':abi,
                'requirements':'Each deterministic source-disjoint split needs8sources and2labels per target row.',
                'native_calls':False,'optimizer_steps':0,'approval_authority':0,'production_integration':False}
    except (ValueError,KeyError,OSError,TypeError) as exc:
        report={'status':'DATASET_REJECTED_NO_TRAINING','error_type':type(exc).__name__,'error':str(exc),'native_calls':False,'optimizer_steps':0,'approval_authority':0,'production_integration':False}
    atomic_write(out/'report.json',dumps(report));return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dataset',required=True);p.add_argument('--out',required=True);p.add_argument('--validate-only',action='store_true');a=p.parse_args()
    out_was_present=Path(a.out).exists()
    try:result=validate_only(a.dataset,a.out) if a.validate_only else train_dataset(a.dataset,a.out)
    except (ValueError,KeyError,OSError,TypeError) as exc:
        result={'status':'DATASET_OR_FIT_REJECTED_NO_APPROVAL','error_type':type(exc).__name__,'error':str(exc),'approval_authority':0}
        out=Path(a.out).resolve()
        if out.exists() and not out_was_present:atomic_write(out/'rejected.json',dumps(result))
    print(dumps({'status':result['status'],'artifact':str(Path(a.out).resolve()),'error':result.get('error'),'approval_authority':0}),flush=True)
    return 0 if result.get('metrics',{}).get('commit_eligible') or result['status']=='VALIDATED_COHORT_READY_NO_TRAINING' else 2

if __name__=='__main__':sys.exit(main())
