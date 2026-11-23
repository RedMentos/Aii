"""Fail-closed native body-training port contract.

This module does not train a body.  It defines the minimum evidence a future
native backend must supply before V13 may expose any body-update authority.
Quantized inference artifacts are deliberately rejected as master weights.
"""
from pathlib import Path
import json,re
from .common import file_hash

MASTER_DTYPES={'float32','float16','bfloat16'}
PARAM_ID=re.compile(r'[A-Za-z0-9_.:/-]{1,160}\Z')


def inspect_train_port(home, role, descriptor='config/native-body-train-port.json'):
    home=Path(home); path=home/descriptor
    base={'role':role,'available':False,'update_authority':0,'reason':'NO_DECLARED_NATIVE_TRAIN_PORT'}
    if not path.is_file(): return base
    try: d=json.loads(path.read_text())
    except Exception: return base|{'reason':'INVALID_TRAIN_PORT_DESCRIPTOR'}
    if d.get('schema')!='v13-native-body-train-port-v1' or d.get('role')!=role:
        return base|{'reason':'INVALID_TRAIN_PORT_DESCRIPTOR'}
    required=('model_artifact','model_sha256','master_artifact','master_sha256','master_dtype','trainable_parameter_ids','runner_artifact','runner_sha256','requantizer_artifact','requantizer_sha256')
    if any(k not in d for k in required): return base|{'reason':'INCOMPLETE_TRAIN_PORT_DESCRIPTOR'}
    ids=d['trainable_parameter_ids']
    if not isinstance(ids,list) or not ids or len(ids)>4096 or len(set(ids))!=len(ids) or any(not isinstance(x,str) or not PARAM_ID.fullmatch(x) for x in ids):
        return base|{'reason':'INVALID_TRAINABLE_PARAMETER_SET'}
    if d['master_dtype'] not in MASTER_DTYPES:return base|{'reason':'MASTER_DTYPE_NOT_TRAINABLE'}
    # The master must be distinct from the quantized inference artifact.
    if d['master_artifact']==d['model_artifact'] or d['master_sha256']==d['model_sha256']:
        return base|{'reason':'INFERENCE_ARTIFACT_IS_NOT_TRAIN_MASTER'}
    measured={}
    for key in ('model','master','runner','requantizer'):
        rel=d[key+'_artifact']; expected=d[key+'_sha256']
        if not isinstance(rel,str) or rel.startswith('/') or '..' in Path(rel).parts or not re.fullmatch(r'[a-f0-9]{64}',str(expected)):
            return base|{'reason':'INVALID_ARTIFACT_BINDING'}
        p=home/rel
        if not p.is_file():return base|{'reason':'MISSING_'+key.upper()+'_ARTIFACT'}
        actual=file_hash(p);measured[key]={'path':rel,'sha256':actual,'bytes':p.stat().st_size}
        if actual!=expected:return base|{'reason':'HASH_MISMATCH_'+key.upper(),'artifacts':measured}
    if not (home/d['runner_artifact']).stat().st_mode & 0o111:
        return base|{'reason':'TRAIN_RUNNER_NOT_EXECUTABLE','artifacts':measured}
    if not (home/d['requantizer_artifact']).stat().st_mode & 0o111:
        return base|{'reason':'REQUANTIZER_NOT_EXECUTABLE','artifacts':measured}
    # A descriptor proves a bound port exists, not that gradients/EMA/requantization
    # are correct. Runtime authority remains zero until a TrainRunnerProof passes.
    return base|{'reason':'PORT_BOUND_PROOF_REQUIRED','port_bound':True,'artifacts':measured,
                 'master_dtype':d['master_dtype'],'trainable_parameter_count_declared':len(ids),
                 'trainable_parameter_ids_sha256':__import__('hashlib').sha256('\n'.join(ids).encode()).hexdigest()}
