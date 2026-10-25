"""Run162: full-SHA-bound FP32 inference-slice export to isolated candidate master.

This is NOT body training: no gradients, EMA, native runner, requantization,
Runtime updates or authority. Never exports quantized tensors as FP32 masters.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.body_gguf_dtype_audit_run160 import parse,MAX_PREFIX

GATES={'STEP2':'UTILITY_FAIL','B3_L1':'FAIL','Body_JEPA':'UNAVAILABLE',
       'jepa_weight':0,'DS2_H2':'FAIL','V13':'INCOMPLETE'}


def file_sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()


def export(model,expected_sha,selection,out):
    model=Path(model);out=Path(out)
    if not isinstance(expected_sha,str) or len(expected_sha)!=64 or any(c not in '0123456789abcdef' for c in expected_sha):
        raise ValueError('expected_sha')
    if not isinstance(selection,(list,tuple)) or not selection or len(selection)>8 or len(set(selection))!=len(selection):
        raise ValueError('selection')
    if any(not isinstance(x,str) or not x or len(x)>64 for x in selection):raise ValueError('selection')
    if out.exists():raise FileExistsError('output_exists')
    actual=file_sha(model)
    if actual!=expected_sha:raise ValueError('full_model_hash_mismatch')
    with open(model,'rb') as f:prefix=f.read(MAX_PREFIX)
    meta=parse(prefix)
    arrays={};manifest=[]
    with open(model,'rb') as f:
        for name in selection:
            t=meta['tensors'].get(name)
            if t is None:raise ValueError('missing_tensor:'+name)
            if t['type']!='F32':raise ValueError('not_fp32:'+name)
            if len(t['dims'])!=1:raise ValueError('nonvector_slice:'+name)
            count=1
            for dim in t['dims']:count*=dim
            nbytes=count*4
            if nbytes>16*1024*1024:raise ValueError('slice_size')
            pos=meta['tensor_data_start']+t['offset']
            if pos+nbytes>model.stat().st_size:raise ValueError('tensor_out_of_file')
            f.seek(pos);raw=f.read(nbytes)
            if len(raw)!=nbytes:raise ValueError('short_tensor')
            x=np.frombuffer(raw,dtype='<f4').copy()
            if not np.isfinite(x).all():raise ValueError('nonfinite_master')
            arrays[name]=x.reshape(t['dims'])
            manifest.append({'name':name,'shape':list(t['dims']),'dtype':'float32',
                             'bytes':nbytes,'offset_in_gguf':pos,
                             'sha256':hashlib.sha256(raw).hexdigest()})
    # No pickle or writes to inference GGUF. Distinct candidate file is private.
    with out.open('xb') as f:np.savez(f,**arrays)
    with np.load(out,allow_pickle=False) as z:
        if sorted(z.files)!=sorted(selection):raise ValueError('roundtrip_names')
        for name in selection:
            if not np.array_equal(z[name],arrays[name]):raise ValueError('roundtrip_values')
    return {'schema':'V13_RUN162_FP32_SLICE_EXPORT_V1',
            'registered_model_sha256':expected_sha,'full_model_sha256_verified':True,
            'master_candidate_sha256':file_sha(out),'master_candidate_bytes':out.stat().st_size,
            'selected_tensors':manifest,'roundtrip':'BYTE_EXACT_FLOAT32_VALUES',
            'model_file_unchanged':file_sha(model)==expected_sha,
            'train_master_authority':0,'body_training_authority':0,
            'evidence_class':'FP32_INFERENCE_SLICE_EXPORT_ONLY_NO_TRAINING',
            'gates':GATES,'gate':'UNVERIFIED',
            'limitations':['isolated export is not a native train master or active model update',
                           'no gradients, EMA, requantization, native receiver, retention or Redmi proof',
                           'model and candidate weights must not be published']}


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--model',required=True,type=Path)
    p.add_argument('--sha256',required=True);p.add_argument('--tensor',required=True,action='append')
    p.add_argument('--master',required=True,type=Path);p.add_argument('--report',required=True,type=Path)
    a=p.parse_args();r=export(a.model,a.sha256,a.tensor,a.master)
    with a.report.open('x') as f:f.write(json.dumps(r,sort_keys=True,indent=2)+'\n')
    print('RUN162_FP32_EXPORT',len(r['selected_tensors']),r['roundtrip'],'AUTHORITY',r['body_training_authority'])

if __name__=='__main__':main()
