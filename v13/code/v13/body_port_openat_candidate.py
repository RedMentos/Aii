"""Review-only, descriptor-relative artifact inspection for the Body port.

Hashes bytes from already-open, non-symlink regular files and rechecks path
identity during the inspection. This does not open a training port or promise
that a returned pathname remains unchanged after inspection returns.
"""
import errno
import hashlib
import json
import os
from pathlib import Path
import stat

from . import body_training as original


SOURCE_SHA='08ec4a996048026b8e2a6d81c8ca9cd6c56f9a8159caecce7483ddb24504f9ff'
MAX_DESCRIPTOR=256*1024


class InspectionError(ValueError):
    def __init__(self,reason):
        super().__init__(reason);self.reason=reason


def _paths(raw):
    if (type(raw) is not str or not raw or len(raw)>4096 or '\x00' in raw or '\\' in raw
            or raw.startswith('/') or '..' in Path(raw).parts):
        raise InspectionError('INVALID_ARTIFACT_BINDING')
    parts=Path(raw).parts
    if not parts or any(len(part)>255 for part in parts):
        raise InspectionError('INVALID_ARTIFACT_BINDING')
    return parts


def _open_relative(root,parts):
    """Open each component relative to an already opened directory."""
    opened=[];current=root
    try:
        for index,name in enumerate(parts):
            last=index==len(parts)-1
            flags=os.O_RDONLY|os.O_NOFOLLOW|getattr(os,'O_CLOEXEC',0)|getattr(os,'O_NONBLOCK',0)
            if not last:flags|=os.O_DIRECTORY
            try:fd=os.open(name,flags,dir_fd=current)
            except OSError as exc:
                try:mode=os.stat(name,dir_fd=current,follow_symlinks=False).st_mode
                except OSError:mode=None
                if mode is not None and (stat.S_ISLNK(mode) or not last):
                    raise InspectionError('UNSAFE_ARTIFACT_PATH') from exc
                if exc.errno in (errno.ENOENT,errno.ENOTDIR):raise InspectionError('MISSING_ARTIFACT') from exc
                raise InspectionError('UNSAFE_ARTIFACT_PATH') from exc
            opened.append(fd);current=fd
        result=opened.pop()
        return result
    finally:
        for fd in reversed(opened):os.close(fd)


def _identity(st):
    return (st.st_dev,st.st_ino,st.st_mode,st.st_size,st.st_mtime_ns,st.st_ctime_ns)


def _stream(fd,relative,limit=None):
    result=hashlib.sha256();chunks=[];total=0
    while True:
        chunk=os.read(fd,1024*1024)
        if not chunk:break
        total+=len(chunk)
        if limit is not None and total>limit:raise InspectionError('INVALID_TRAIN_PORT_DESCRIPTOR')
        result.update(chunk)
        if limit is not None:chunks.append(chunk)
    return result.hexdigest(),total,b''.join(chunks) if limit is not None else None


def _measure(root,relative,limit=None):
    parts=_paths(relative);fd=_open_relative(root,parts)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):raise InspectionError('UNSAFE_ARTIFACT_TYPE')
        if limit is not None and before.st_size>limit:raise InspectionError('INVALID_TRAIN_PORT_DESCRIPTOR')
        sha,size,content=_stream(fd,relative,limit)
        after=os.fstat(fd)
        if _identity(before)!=_identity(after) or size!=after.st_size:
            raise InspectionError('ARTIFACT_CHANGED_DURING_INSPECTION')
    finally:os.close(fd)
    return {'path':relative,'sha256':sha,'bytes':size,'identity':_identity(after),'mode':after.st_mode},content


def _still_same(root,entry):
    try:
        fd=_open_relative(root,_paths(entry['path']))
        try:return _identity(os.fstat(fd))==entry['identity']
        finally:os.close(fd)
    except (InspectionError,OSError):return False


def _unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate descriptor key')
        result[key]=value
    return result


def _ids(value):
    return (type(value) is list and 0<len(value)<=4096
            and all(type(x) is str and original.PARAM_ID.fullmatch(x) for x in value)
            and len(set(value))==len(value))


def inspect_train_port(home,role,descriptor='config/native-body-train-port.json'):
    """Return point-in-time port evidence; update authority remains zero."""
    base={'role':role,'available':False,'update_authority':0,'reason':'NO_DECLARED_NATIVE_TRAIN_PORT'}
    source=Path(original.__file__).read_bytes()
    if hashlib.sha256(source).hexdigest()!=SOURCE_SHA:raise ValueError('unsupported body port source')
    if not all(hasattr(os,name) for name in ('O_NOFOLLOW','O_DIRECTORY')) or os.open not in os.supports_dir_fd:
        return base|{'reason':'SECURE_OPEN_UNAVAILABLE'}
    try:root=os.open(os.fspath(home),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|getattr(os,'O_CLOEXEC',0))
    except OSError as exc:
        return base if exc.errno==errno.ENOENT else base|{'reason':'UNSAFE_ARTIFACT_PATH'}
    try:
        try:
            descriptor_entry,content=_measure(root,descriptor,MAX_DESCRIPTOR)
        except InspectionError as exc:
            return base if exc.reason=='MISSING_ARTIFACT' else base|{'reason':exc.reason}
        try:d=json.loads(content,object_pairs_hook=_unique)
        except (ValueError,UnicodeDecodeError):return base|{'reason':'INVALID_TRAIN_PORT_DESCRIPTOR'}
        if type(d) is not dict or d.get('schema')!='v13-native-body-train-port-v1' or d.get('role')!=role:
            return base|{'reason':'INVALID_TRAIN_PORT_DESCRIPTOR'}
        fp32=d.get('fp32_inference_parameter_ids')
        no_requant=d.get('requantizer_artifact') is None and d.get('requantizer_sha256') is None and fp32 is not None
        required=('model_artifact','model_sha256','master_artifact','master_sha256','master_dtype',
                  'trainable_parameter_ids','runner_artifact','runner_sha256')+(() if no_requant else
                  ('requantizer_artifact','requantizer_sha256'))
        if any(d.get(k) is None for k in required):return base|{'reason':'INCOMPLETE_TRAIN_PORT_DESCRIPTOR'}
        ids=d['trainable_parameter_ids']
        if not _ids(ids):return base|{'reason':'INVALID_TRAINABLE_PARAMETER_SET'}
        if type(d['master_dtype']) is not str or d['master_dtype'] not in original.MASTER_DTYPES:
            return base|{'reason':'MASTER_DTYPE_NOT_TRAINABLE'}
        if no_requant and (not _ids(fp32) or not set(ids)<=set(fp32) or d['master_dtype']!='float32'):
            return base|{'reason':'REQUANTIZER_EXCEPTION_NOT_FP32'}
        if d['master_artifact']==d['model_artifact'] or d['master_sha256']==d['model_sha256']:
            return base|{'reason':'INFERENCE_ARTIFACT_IS_NOT_TRAIN_MASTER'}
        measured={};entries=[descriptor_entry]
        for key in original.ARTIFACTS:
            if key=='requantizer' and no_requant:continue
            relative=d[key+'_artifact'];expected=d[key+'_sha256']
            if type(expected) is not str or len(expected)!=64 or any(c not in '0123456789abcdef' for c in expected):
                return base|{'reason':'INVALID_ARTIFACT_BINDING'}
            try:entry,_=_measure(root,relative)
            except InspectionError as exc:
                reason='MISSING_'+key.upper()+'_ARTIFACT' if exc.reason=='MISSING_ARTIFACT' else exc.reason
                return base|{'reason':reason}
            entries.append(entry)
            measured[key]={k:entry[k] for k in ('path','sha256','bytes')}
            if entry['sha256']!=expected:
                return base|{'reason':'HASH_MISMATCH_'+key.upper(),'artifacts':measured}
            if key in {'runner','requantizer'} and not entry['mode'] & 0o111:
                reason='TRAIN_RUNNER_NOT_EXECUTABLE' if key=='runner' else 'REQUANTIZER_NOT_EXECUTABLE'
                return base|{'reason':reason,'artifacts':measured}
        if not all(_still_same(root,entry) for entry in entries):
            return base|{'reason':'ARTIFACT_CHANGED_DURING_INSPECTION'}
        return base|{'reason':'PORT_BOUND_PROOF_REQUIRED','port_bound':True,'artifacts':measured,
                     'master_dtype':d['master_dtype'],
                     'requantization':'NOT_APPLICABLE_FP32_SLICES' if no_requant else 'REQUIRED',
                     'trainable_parameter_count_declared':len(ids),
                     'trainable_parameter_ids_sha256':hashlib.sha256('\n'.join(ids).encode()).hexdigest()}
    except (OSError,ValueError,TypeError):
        return base|{'reason':'ARTIFACT_INSPECTION_FAILED'}
    finally:os.close(root)
