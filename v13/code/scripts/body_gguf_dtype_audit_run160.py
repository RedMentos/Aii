"""Run160: bounded GGUF v3 tensor-type audit for BodyTrainPort claims.

Metadata-only, never a train master, gradient, weight write or model hash proof.
GGUF structure follows ggml-org/ggml docs/gguf.md (accessed 2026-10-25).
"""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import struct

GATES={'STEP2':'UTILITY_FAIL','B3_L1':'FAIL','Body_JEPA':'UNAVAILABLE',
       'jepa_weight':0,'DS2_H2':'FAIL','V13':'INCOMPLETE'}
TYPES={0:'F32',1:'F16',2:'Q4_0',3:'Q4_1',6:'Q5_0',7:'Q5_1',8:'Q8_0',10:'Q2_K',11:'Q3_K',12:'Q4_K',13:'Q5_K',14:'Q6_K',15:'Q8_K',30:'BF16'}
SIZES={0:1,1:1,2:2,3:2,4:4,5:4,6:4,7:1,10:8,11:8,12:8}
MAX_PREFIX=8*1024*1024


def parse(prefix):
    if not isinstance(prefix,bytes) or len(prefix)>MAX_PREFIX:raise ValueError('prefix_bounds')
    f=io.BytesIO(prefix)
    def take(n):
        if n<0 or n>MAX_PREFIX or f.tell()+n>len(prefix):raise ValueError('truncated_or_oversize')
        return f.read(n)
    def unpack(fmt):return struct.unpack('<'+fmt,take(struct.calcsize('<'+fmt)))[0]
    def string(max_len):
        n=unpack('Q')
        if n>max_len:raise ValueError('string_bounds')
        return take(n).decode('utf-8')
    def value(kind,depth=0):
        if depth>2:raise ValueError('array_depth')
        if kind==8:return string(MAX_PREFIX)
        if kind==9:
            elem=unpack('I');count=unpack('Q')
            if count>1_000_000:raise ValueError('array_bounds')
            for _ in range(count):value(elem,depth+1)
            return None
        if kind not in SIZES:raise ValueError('unknown_metadata_type')
        return take(SIZES[kind])
    if take(4)!=b'GGUF':raise ValueError('magic')
    version=unpack('I')
    if version!=3:raise ValueError('version')
    tensor_count=unpack('Q');kv_count=unpack('Q')
    if tensor_count>100_000 or kv_count>100_000:raise ValueError('counts')
    for _ in range(kv_count):
        key=string(65535);kind=unpack('I')
        value(kind)
    tensors={}
    for _ in range(tensor_count):
        name=string(64);ndims=unpack('I')
        if not 1<=ndims<=4:raise ValueError('dims')
        dims=tuple(unpack('Q') for _ in range(ndims))
        if any(d<1 or d>1_000_000_000 for d in dims):raise ValueError('dim_bounds')
        dtype=unpack('I');offset=unpack('Q')
        if dtype not in TYPES:raise ValueError('unknown_tensor_type')
        if name in tensors:raise ValueError('duplicate_tensor')
        tensors[name]={'type':TYPES[dtype],'dims':dims,'offset':offset}
    return {'gguf_version':version,'tensor_count':len(tensors),'types':dict(sorted(Counter(t['type'] for t in tensors.values()).items())),
            'fp32_tensor_names':sorted(n for n,t in tensors.items() if t['type']=='F32'),
            'tensors':tensors,'metadata_prefix_sha256':hashlib.sha256(prefix).hexdigest()}


def audit(prefix,claimed_fp32_ids=()):
    r=parse(prefix)
    if not isinstance(claimed_fp32_ids,(tuple,list)) or any(not isinstance(x,str) for x in claimed_fp32_ids):raise ValueError('claims')
    missing=sorted(set(claimed_fp32_ids)-set(r['tensors']))
    non_fp32=sorted(x for x in set(claimed_fp32_ids)&set(r['tensors']) if r['tensors'][x]['type']!='F32')
    return {'schema':'V13_RUN160_GGUF_DTYPE_AUDIT_V1',
            'gguf_version':r['gguf_version'],'tensor_count':r['tensor_count'],'tensor_types':r['types'],
            'fp32_count':len(r['fp32_tensor_names']),'fp32_tensor_names':r['fp32_tensor_names'][:256],
            'claimed_fp32_count':len(claimed_fp32_ids),'missing_claims':missing,'quantized_claims':non_fp32,
            'fp32_claims_valid':not missing and not non_fp32,
            'prefix_sha256':r['metadata_prefix_sha256'],
            'evidence_class':'UNVERIFIED_GGUF_PREFIX_METADATA_ONLY',
            'full_model_sha256_verified':False,'master_weights_verified':False,
            'body_training_authority':0,'gate':'UNVERIFIED','gates':GATES,
            'limitations':['prefix-only metadata is not full model SHA-256 verification',
                           'inference FP32 tensors are not a separate train master',
                           'no gradient/EMA/requantizer/retention or native receiver proof',
                           'no Redmi or Body-JEPA completion']}


def main():
    p=argparse.ArgumentParser();p.add_argument('--prefix',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--claim-fp32',action='append',default=[])
    a=p.parse_args();r=audit(a.prefix.read_bytes(),a.claim_fp32)
    with a.output.open('x',encoding='utf-8') as f:f.write(json.dumps(r,sort_keys=True,indent=2)+'\n')
    print('RUN160_GGUF',r['tensor_count'],r['fp32_count'],'CLAIMS',r['fp32_claims_valid'],'AUTHORITY',r['body_training_authority'])

if __name__=='__main__':main()
