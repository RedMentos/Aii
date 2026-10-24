"""Run46: learned query-key attention on Run44's source-staged synthetic corpus."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

SEED=20261024
HELDOUT=20261025
STEPS=300
LR=.005
BATCH=64
DIM=32


def data_builder():
    path=Path(__file__).resolve().parents[1]/'vendor/run44/sleep_context_utility.py'
    data=path.read_bytes()
    sha=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    if sha!='5b7a7a1f8db720c78feaa6e2efd9f1d0e110ad8b':raise RuntimeError('Run44 source changed')
    spec=importlib.util.spec_from_file_location('run44_source',path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod.stage


def tensorize(rows):
    return (torch.tensor([r[0] for r in rows],dtype=torch.long),
            torch.tensor([r[1] for r in rows],dtype=torch.long),
            torch.tensor([r[2] for r in rows],dtype=torch.long),
            torch.tensor([r[3] for r in rows],dtype=torch.long))


class KeyBinding(nn.Module):
    def __init__(self):
        super().__init__()
        self.key=nn.Embedding(8,DIM)
        self.query=nn.Embedding(8,DIM)
        self.value=nn.Embedding(8,DIM)
        self.kproj=nn.Linear(DIM,DIM,bias=False)
        self.qproj=nn.Linear(DIM,DIM,bias=False)
        self.log_temperature=nn.Parameter(torch.tensor(math.log(1/math.sqrt(DIM))))
        self.out=nn.Linear(DIM,8)
    def forward(self,keys,values,query,no_context=False,uniform=False):
        q=self.qproj(self.query(query))
        k=self.kproj(self.key(keys))
        logits=(k*q[:,None]).sum(-1)*self.log_temperature.exp()
        weights=(torch.full_like(logits,1/3) if uniform else logits.softmax(-1))
        vec=(weights[:,:,None]*self.value(values)).sum(1)
        if no_context:vec=vec*0.
        return self.out(vec)


def fit(model,rows,no_context=False):
    keys,values,query,target=tensorize(rows)
    opt=torch.optim.Adam(model.parameters(),lr=LR)
    rng=torch.Generator().manual_seed(SEED+2)
    for _ in range(STEPS):
        ix=torch.randperm(len(rows),generator=rng)[:BATCH]
        opt.zero_grad(set_to_none=True)
        loss=F.cross_entropy(model(keys[ix],values[ix],query[ix],no_context=no_context),target[ix])
        loss.backward();opt.step()
    return model


@torch.no_grad()
def acc(model,rows,no_context=False,uniform=False,shuffle=False):
    keys,values,query,target=tensorize(rows)
    if shuffle:
        rng=np.random.default_rng(HELDOUT+1)
        perm=np.array([rng.permutation(3) for _ in range(len(rows))])
        values=values.gather(1,torch.tensor(perm,dtype=torch.long))
    return float((model(keys,values,query,no_context=no_context,uniform=uniform).argmax(1)==target).float().mean())


def cohort():
    torch.set_num_threads(1);torch.manual_seed(SEED)
    stage=data_builder()
    train=stage(SEED,512,'train')
    heldout=stage(HELDOUT,256,'heldout')
    baseline=KeyBinding();init=baseline.state_dict()
    candidate=KeyBinding();candidate.load_state_dict(init)
    no_context=KeyBinding();no_context.load_state_dict(init)
    fit(candidate,train)
    fit(no_context,train,no_context=True)
    values={'context':acc(candidate,heldout),'no_context':acc(no_context,heldout,no_context=True),
            'shuffled_context':acc(candidate,heldout,shuffle=True),
            'uniform_attention':acc(candidate,heldout,uniform=True),
            'untrained':acc(baseline,heldout)}
    passed=(values['context']>=.70 and values['context']-values['no_context']>=.40 and
            values['context']-values['shuffled_context']>=.25 and
            values['context']-values['uniform_attention']>=.25)
    return {'schema':'V13_RUN46_SYNTHETIC_KEY_BINDING_V1','train_seed':SEED,'heldout_seed':HELDOUT,
            'train_n':512,'heldout_n':256,'steps':STEPS,'parameters':sum(p.numel() for p in candidate.parameters()),
            'metrics':values,'synthetic_pass':passed,'claim':'SYNTHETIC_ONLY_NOT_V13_NATIVE',
            'jepa_weight':0,'original_gates_unchanged':True}


if __name__=='__main__':print(json.dumps(cohort(),indent=2,sort_keys=True))
