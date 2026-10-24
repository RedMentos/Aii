"""Fail-closed native body-training port contract.

This module does not train a body.  It defines the minimum evidence a future
native backend must supply before V13 may expose any body-update authority.
Quantized inference artifacts are deliberately rejected as master weights.
Restored 2026-10-09 from the lost 2026-10-06 burst5 build (WP-V1).
"""
from pathlib import Path
import hashlib,json,re
from .common import file_hash

MASTER_DTYPES={'float32','float16','bfloat16'}
PARAM_ID=re.compile(r'[A-Za-z0-9_.:/-]{1,160}\Z')
ARTIFACTS=('model','master','runner','requantizer')


def _bound_path(home, rel):
    """Reject absolute/traversal paths and symlinked components before hashing.

    This checks a stable operator-owned tree, not a hostile concurrent rename
    race. No training authority follows from a bound descriptor.
    """
    if not isinstance(rel,(str,Path)) or not str(rel) or '\\' in str(rel):
        return None
    relative=Path(rel)
    if relative.is_absolute() or not relative.parts or '..' in relative.parts:
        return None
    path=home/relative
    try:
        if not path.resolve().is_relative_to(home):
            return None
        current=home
        for part in relative.parts:
            current=current/part
            if current.is_symlink():
                return None
    except (OSError,RuntimeError,ValueError):
        return None
    return path


def _ids(value,limit=4096):
    return isinstance(value,list) and 0<len(value)<=limit and all(isinstance(x,str) and PARAM_ID.fullmatch(x) for x in value) and len(set(value))==len(value)


def inspect_train_port(home, role, descriptor='config/native-body-train-port.json'):
    home=Path(home).resolve()
    base={'role':role,'available':False,'update_authority':0,'reason':'NO_DECLARED_NATIVE_TRAIN_PORT'}
    path=_bound_path(home,descriptor)
    if path is None:return base|{'reason':'INVALID_TRAIN_PORT_DESCRIPTOR'}
    if not path.is_file():return base
    try: d=json.loads(path.read_text())
    except Exception: return base|{'reason':'INVALID_TRAIN_PORT_DESCRIPTOR'}
    if not isinstance(d,dict) or d.get('schema')!='v13-native-body-train-port-v1' or d.get('role')!=role:
        return base|{'reason':'INVALID_TRAIN_PORT_DESCRIPTOR'}
    # A requantizer is mandatory unless every trainable slice is stored unquantized
    # (FP32, e.g. token_embd_norm) in the inference artifact itself.
    fp32=d.get('fp32_inference_parameter_ids')
    no_requant=d.get('requantizer_artifact') is None and d.get('requantizer_sha256') is None and fp32 is not None
    required=('model_artifact','model_sha256','master_artifact','master_sha256','master_dtype','trainable_parameter_ids','runner_artifact','runner_sha256')+(() if no_requant else ('requantizer_artifact','requantizer_sha256'))
    if any(d.get(k) is None for k in required): return base|{'reason':'INCOMPLETE_TRAIN_PORT_DESCRIPTOR'}
    ids=d['trainable_parameter_ids']
    if not _ids(ids): return base|{'reason':'INVALID_TRAINABLE_PARAMETER_SET'}
    if not isinstance(d['master_dtype'],str) or d['master_dtype'] not in MASTER_DTYPES:return base|{'reason':'MASTER_DTYPE_NOT_TRAINABLE'}
    if no_requant and (not _ids(fp32) or not set(ids)<=set(fp32) or d['master_dtype']!='float32'):
        return base|{'reason':'REQUANTIZER_EXCEPTION_NOT_FP32'}
    # The master must be distinct from the quantized inference artifact.
    if d['master_artifact']==d['model_artifact'] or d['master_sha256']==d['model_sha256']:
        return base|{'reason':'INFERENCE_ARTIFACT_IS_NOT_TRAIN_MASTER'}
    measured={}
    for key in ARTIFACTS:
        if key=='requantizer' and no_requant:continue
        rel=d[key+'_artifact']; expected=d[key+'_sha256']
        if not isinstance(rel,str) or rel.startswith('/') or '..' in Path(rel).parts or not re.fullmatch(r'[a-f0-9]{64}',str(expected)):
            return base|{'reason':'INVALID_ARTIFACT_BINDING'}
        p=_bound_path(home,rel)
        if p is None:return base|{'reason':'INVALID_ARTIFACT_BINDING'}
        if not p.is_file():return base|{'reason':'MISSING_'+key.upper()+'_ARTIFACT'}
        actual=file_hash(p);measured[key]={'path':rel,'sha256':actual,'bytes':p.stat().st_size}
        if actual!=expected:return base|{'reason':'HASH_MISMATCH_'+key.upper(),'artifacts':measured}
    if not (home/d['runner_artifact']).stat().st_mode & 0o111:
        return base|{'reason':'TRAIN_RUNNER_NOT_EXECUTABLE','artifacts':measured}
    if not no_requant and not (home/d['requantizer_artifact']).stat().st_mode & 0o111:
        return base|{'reason':'REQUANTIZER_NOT_EXECUTABLE','artifacts':measured}
    # A descriptor proves a bound port exists, not that gradients/EMA/requantization
    # are correct. Runtime authority remains zero until a TrainRunnerProof passes.
    return base|{'reason':'PORT_BOUND_PROOF_REQUIRED','port_bound':True,'artifacts':measured,
                 'master_dtype':d['master_dtype'],'requantization':'NOT_APPLICABLE_FP32_SLICES' if no_requant else 'REQUIRED',
                 'trainable_parameter_count_declared':len(ids),
                 'trainable_parameter_ids_sha256':hashlib.sha256('\n'.join(ids).encode()).hexdigest()}
