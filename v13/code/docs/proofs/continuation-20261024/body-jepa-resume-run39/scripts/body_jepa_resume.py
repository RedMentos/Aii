"""V13 Run39: exact synthetic Adam + RNG resume; no native/production authority.

Safe NPZ tensor storage with closed schema and SHA256, never torch.load/pickle.
"""
from pathlib import Path
import hashlib
import json
import os
import tempfile
import zipfile
import io

import numpy as np
import torch

import body_jepa_micro as B

SCHEMA='V13_BODY_JEPA_SYNTHETIC_RESUME_V1'
SOURCE_SHA256='af899ca76c615e1b0954a4c3727601ff58c24ab496268289170d5360aa5daa11'
MAX_BYTES=4*1024*1024
MAX_UNCOMPRESSED=4*1024*1024
MANIFEST_KEYS={'schema','source_sha256','dataset_sha256','step','wrong_target','bytes','sha256','keys','authority','native_body_gate_pass'}


def source_ok():
    return hashlib.sha256((Path(__file__).parent/'body_jepa_micro.py').read_bytes()).hexdigest()==SOURCE_SHA256


def data_sha(x,a,y):
    h=hashlib.sha256()
    for v in (x,a,y):
        z=v.detach().cpu().numpy()
        h.update(str(z.shape).encode());h.update(str(z.dtype).encode());h.update(z.tobytes())
    return h.hexdigest()


class Session:
    def __init__(self,wrong_target=False):
        if not source_ok():raise ValueError('source revision mismatch')
        torch.set_num_threads(1)
        torch.manual_seed(B.SEED)
        self.model=B.MicroLearner('SYNTHETIC_SANDBOX')
        self.x,self.a,self.y=B.pairs()
        self.data_sha=data_sha(self.x,self.a,self.y)
        self.index_rng=torch.Generator().manual_seed(B.SEED+2)
        self.shuffle_rng=torch.Generator().manual_seed(B.SEED+3)
        self.step=0
        self.wrong_target=bool(wrong_target)

    def advance(self,n):
        if type(n) is not int or n<0 or self.step+n>B.STEPS:raise ValueError('invalid step count')
        for _ in range(n):
            ids=torch.randperm(128,generator=self.index_rng)[:32]
            self.model.step(self.x[ids],self.a[ids],self.y[ids],torch.ones(len(ids)),
                            wrong_target=self.wrong_target,shuffle_generator=self.shuffle_rng)
            self.step+=1
        return self

    def heldout_mse(self):return self.model.mse(self.x[128:],self.a[128:],self.y[128:])

    def state_arrays(self):
        arrays={'model.'+k:v.detach().cpu().numpy() for k,v in self.model.state_dict().items()}
        if self.step:
            for name,p in self.model.named_parameters():
                if not p.requires_grad:continue
                state=self.model.optim.state[p]
                for key in ('step','exp_avg','exp_avg_sq'):
                    arrays['optim.'+name+'.'+key]=state[key].detach().cpu().numpy()
        arrays['rng.index']=self.index_rng.get_state().numpy()
        arrays['rng.shuffle']=self.shuffle_rng.get_state().numpy()
        return arrays


def save(session,folder):
    if not source_ok():raise ValueError('source revision mismatch')
    folder=Path(folder)
    if folder.exists() or folder.is_symlink():raise FileExistsError('checkpoint directory must be new')
    folder.mkdir(parents=True,exist_ok=False)
    arrays=session.state_arrays()
    with tempfile.NamedTemporaryFile(dir=folder,prefix='.weights-',suffix='.npz',delete=False) as tmp:
        name=tmp.name
        np.savez_compressed(tmp,**arrays)
        tmp.flush();os.fsync(tmp.fileno())
    raw=Path(name).read_bytes()
    if len(raw)>MAX_BYTES:raise ValueError('checkpoint exceeds size bound')
    sha=hashlib.sha256(raw).hexdigest()
    os.replace(name,folder/'state.npz')
    info={'schema':SCHEMA,'source_sha256':SOURCE_SHA256,'dataset_sha256':session.data_sha,
          'step':session.step,'wrong_target':session.wrong_target,'bytes':len(raw),'sha256':sha,
          'keys':sorted(arrays),'authority':'SYNTHETIC_SANDBOX_NO_AGE_ACTION',
          'native_body_gate_pass':False}
    (folder/'MANIFEST.json').write_text(json.dumps(info,sort_keys=True,indent=2)+'\n')
    return info


def load(folder):
    if not source_ok():raise ValueError('source revision mismatch')
    folder=Path(folder)
    info=json.loads((folder/'MANIFEST.json').read_text())
    raw=(folder/'state.npz').read_bytes()
    if (type(info) is not dict or set(info)!=MANIFEST_KEYS or
        info.get('authority')!='SYNTHETIC_SANDBOX_NO_AGE_ACTION' or info.get('native_body_gate_pass') is not False or
        info.get('schema')!=SCHEMA or info.get('source_sha256')!=SOURCE_SHA256 or
        type(info.get('step')) is not int or not 0<=info['step']<=B.STEPS or
        type(info.get('wrong_target')) is not bool or
        len(raw)>MAX_BYTES or info.get('bytes')!=len(raw) or
        info.get('sha256')!=hashlib.sha256(raw).hexdigest()):
        raise ValueError('checkpoint integrity or schema mismatch')
    # Bound decompressed data before NumPy reads any arrays. The digest alone
    # is an integrity check, not authentication of a trusted producer.
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries=archive.infolist()
            if len(entries)>64 or sum(e.file_size for e in entries)>MAX_UNCOMPRESSED:
                raise ValueError('checkpoint decompressed size bound')
    except zipfile.BadZipFile as exc:raise ValueError('invalid checkpoint ZIP') from exc
    session=Session(info['wrong_target'])
    if info.get('dataset_sha256')!=session.data_sha:raise ValueError('dataset hash mismatch')
    expected=session.state_arrays()
    names=list(session.model.named_parameters())
    if info['step']:
        for name,p in names:
            if p.requires_grad:
                for k in ('step','exp_avg','exp_avg_sq'):
                    expected['optim.'+name+'.'+k]=None
    with np.load(folder/'state.npz',allow_pickle=False) as z:
        if sorted(z.files)!=sorted(expected) or info.get('keys')!=sorted(expected):
            raise ValueError('checkpoint key mismatch')
        arrays={}
        for k,template in expected.items():
            arr=z[k]
            if template is not None and (arr.shape!=template.shape or arr.dtype!=template.dtype):
                raise ValueError('checkpoint tensor shape/dtype mismatch')
            if arr.dtype.kind not in ('i','u','f') or not np.isfinite(arr).all():
                raise ValueError('checkpoint tensor nonfinite or wrong dtype')
            arrays[k]=arr.copy()
    session.model.load_state_dict({k[6:]:torch.from_numpy(v) for k,v in arrays.items() if k.startswith('model.')})
    for name,p in names:
        if not p.requires_grad or not info['step']:continue
        for key in ('step','exp_avg','exp_avg_sq'):
            arr=arrays['optim.'+name+'.'+key]
            if key=='step' and (arr.shape!=() or arr.dtype!=np.float32 or float(arr)!=info['step']):
                raise ValueError('optimizer step mismatch')
            if key!='step' and (arr.shape!=tuple(p.shape) or arr.dtype!=np.float32):
                raise ValueError('optimizer moment shape/dtype mismatch')
            session.model.optim.state[p][key]=torch.from_numpy(arr)
    for key,generator in (('rng.index',session.index_rng),('rng.shuffle',session.shuffle_rng)):
        arr=arrays[key]
        if arr.dtype!=np.uint8 or arr.shape!=tuple(generator.get_state().shape):
            raise ValueError('RNG state shape/dtype mismatch')
        generator.set_state(torch.from_numpy(arr))
    session.step=info['step']
    return session


def bitwise_equal(a,b):
    if a.step!=b.step or a.wrong_target!=b.wrong_target:return False
    x,y=a.state_arrays(),b.state_arrays()
    return set(x)==set(y) and all(np.array_equal(x[k],y[k]) for k in x)


if __name__=='__main__':
    import sys
    with tempfile.TemporaryDirectory() as d:
        a=Session().advance(B.STEPS)
        b=Session().advance(60)
        save(b,Path(d)/'checkpoint')
        c=load(Path(d)/'checkpoint').advance(100)
        print(json.dumps({'schema':SCHEMA,'bitwise_equal':bitwise_equal(a,c),
                          'full_mse':a.heldout_mse(),'resumed_mse':c.heldout_mse(),
                          'authority':'SYNTHETIC_SANDBOX_NO_AGE_ACTION'},indent=2))
