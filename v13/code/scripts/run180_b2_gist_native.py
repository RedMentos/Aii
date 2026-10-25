"""Run180 pinned B2 native readout -> exact-source Gist consumer, raw proof."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import threading
import time

import numpy as np
from v13.config import DEFAULTS
from v13.runners import LlamaRunner, TAP_SPECS
from v13.gist_readout import consume

MODEL_SHA = '57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf'
TEXT = 'The blue robot moved left. It carried 42 bolts to the station.'
SOURCE_REF = {'source_id':'run180-public-synthetic','char_start':0,'char_end':len(TEXT)}


def file_sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
    return h.hexdigest()


def run(model,server,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    if file_sha(model)!=MODEL_SHA:raise ValueError('pinned B2 model SHA mismatch')
    cfg=dict(DEFAULTS,context_tokens=1024,threads=2,native_cache_ram_mb=0,native_ctx_checkpoints=0)
    home=out/'worker';(home/'logs').mkdir(parents=True,exist_ok=True)
    r=LlamaRunner(home,'B2_GIST',Path(model),cfg,purpose='tap')
    r.binary=str(Path(server).resolve())
    r.tap_id,r.tap_dim=TAP_SPECS['gist']
    try:
        packet=r.tap(TEXT,threading.Event(),time.monotonic()+120,max_tokens=64)
        tokens=r._json('POST','/tokenize',{'content':TEXT,'add_special':True,'with_pieces':True},time.monotonic()+30)['tokens']
        ids=[t['id'] for t in tokens]
        if ids!=packet['token_ids']:raise ValueError('native tokenizer piece IDs differ from tap')
        plan,_=consume(TEXT,SOURCE_REF,ids,[t['piece'] for t in tokens],packet['vectors'],
                       size=6,slots=4,mode='text',tap_id=packet['metrics']['tap_id'])
        if not (plan['lossless'] and plan['dim']==1024 and plan['tap_id']=='qwen35.result_norm.final.v1'
                and plan['authority']=='SHADOW' and plan['receiver_read_authority']==0
                and plan['receiver_injection_authority']==0 and plan['body_learning_authority']==0):
            raise ValueError('Gist plan source/dimension/authority mismatch')
        if ''.join(s['text'] for s in plan['slots'])!=TEXT:
            raise ValueError('Gist plan did not reconstruct source text')
        vec=np.asarray(packet['vectors'],dtype='<f8')
        if vec.shape!=(len(ids),1024) or not np.isfinite(vec).all():
            raise ValueError('raw B2 vector shape/finite mismatch')
        np.savez_compressed(out/'raw-token-vectors.npz',token_ids=np.asarray(ids,dtype='<i4'),vectors=vec)
        (out/'native-token-pieces.json').write_text(json.dumps(tokens,ensure_ascii=False,sort_keys=True)+'\n')
        (out/'gist-plan.json').write_text(json.dumps(plan,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
        result={'schema':'V13_RUN180_B2_GIST_NATIVE_RAW_V1','status':'NATIVE_READONLY_GIST_CONSUMER_PASS',
                'evidence_class':'LINUX_NATIVE_MODEL_READONLY','source_text':TEXT,'source_ref':SOURCE_REF,
                'model_sha256':MODEL_SHA,'runner_revision':'b10964','tap_id':plan['tap_id'],
                'token_count':len(ids),'embedding_dim':1024,'slot_count':len(plan['slots']),
                'files_sha256':{p.name:file_sha(p) for p in (out/'raw-token-vectors.npz',
                    out/'native-token-pieces.json',out/'gist-plan.json')},
                'step2_promoted':False,'b3_promoted':False,'body_learning':False,
                'redmi_proven':False,'full_v13_proven':False}
        (out/'manifest.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
        return result
    finally:
        r.unload()


def main():
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--server',required=True)
    p.add_argument('--output-dir',required=True);a=p.parse_args()
    out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
    try:result=run(a.model,a.server,out)
    except BaseException as exc:
        (out/'failure.json').write_text(json.dumps({'status':'FAIL_NOT_PROMOTED',
            'error_type':type(exc).__name__,'error':str(exc)[:300],
            'step2_promoted':False,'b3_promoted':False,'redmi_proven':False},sort_keys=True)+'\n')
        raise
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
