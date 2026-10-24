"""V13 §13H ObjectiveAdapter: CPU-only synthetic active-adapter JEPA micro-port.

No production model, no Age rights, no runtime weights. This demonstrates a
local gradient + stop-gradient EMA path and is NOT a Body-JEPA utility proof.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import math
import os
import tempfile

import numpy as np
import torch
from torch import nn

SCHEMA='V13_BODY_JEPA_MICRO_SANDBOX_V1'
SEED=20261024
DIM=8
ACTIONS=2
STEPS=160
LR=.02
EMA=.95

@dataclass(frozen=True)
class ObjectiveAdapter:
    objective_id: str
    applicable_components: tuple
    required_inputs: tuple
    target_builder: str
    stop_gradient_policy: str
    ema_policy: tuple
    loss_terms: tuple
    credit_mapper: str
    update_scope: tuple
    eval_metrics: tuple

OBJECTIVE=ObjectiveAdapter(
    'B_JEPA_ACTIVE_ADAPTER_SYNTHETIC_V1',('B1_DETAIL_SYNTHETIC',),
    ('state_t','action_t','state_t_plus_1','eligibility'),
    'EMA_TARGET_PROJECTOR','DETACH_TARGET',('PROJECTOR_ONLY',EMA),
    ('PREDICTIVE_MSE','VARIANCE_FLOOR'),
    'LOCAL_ELIGIBILITY_WEIGHT',('STUDENT_PROJECTOR','PREDICTOR'),
    ('heldout_mse','wrong_target_mse','ema_delta','gradient_attribution'))


def credit_map(learner_error,eligibility,path='B1_DETAIL_SYNTHETIC'):
    """Bounded local synthetic credit only; never authorizes native updates."""
    if path not in OBJECTIVE.applicable_components:raise ValueError('unregistered learner path')
    if not all(type(v) in (float,int) and math.isfinite(v) for v in (learner_error,eligibility)):
        raise ValueError('nonfinite local credit inputs')
    if learner_error<0 or not 0<=eligibility<=1:raise ValueError('credit input out of bounds')
    return {'path':path,'credit':min(1.,learner_error)*eligibility,
            'authority':'SYNTHETIC_SANDBOX_NO_AGE_ACTION'}


def pairs(seed=SEED,n=192):
    rng=np.random.default_rng(seed)
    x=rng.normal(size=(n,DIM)).astype('float32')
    ids=rng.integers(0,ACTIONS,size=n)
    action=np.eye(ACTIONS,dtype='float32')[ids]
    coeff=np.array([[1,-1,1,-1,1,-1,1,-1],[-1,1,-1,1,-1,1,-1,1]],dtype='float32')
    y=(.65*x+.25*np.roll(x,1,axis=1)+.15*(action@coeff)+
       rng.normal(0,.01,size=(n,DIM))).astype('float32')
    return tuple(torch.from_numpy(v) for v in (x,action,y))


class MicroLearner(nn.Module):
    def __init__(self,mode='SYNTHETIC_SANDBOX'):
        super().__init__()
        if mode!='SYNTHETIC_SANDBOX':raise PermissionError('no production/age learning authority')
        self.student=nn.Linear(DIM,DIM,bias=False)
        self.target=nn.Linear(DIM,DIM,bias=False)
        self.predictor=nn.Linear(DIM+ACTIONS,DIM)
        with torch.no_grad():
            self.student.weight.copy_(torch.eye(DIM))
            self.target.weight.copy_(self.student.weight)
        for p in self.target.parameters():p.requires_grad_(False)
        self.optim=torch.optim.Adam(list(self.student.parameters())+list(self.predictor.parameters()),lr=LR)

    def forward(self,x,a):return self.predictor(torch.cat((self.student(x),a),dim=-1))

    def step(self,x,a,y,eligibility,wrong_target=False,shuffle_generator=None):
        if eligibility.ndim!=1 or eligibility.shape[0]!=x.shape[0]:raise ValueError('eligibility shape')
        if not torch.isfinite(eligibility).all() or (eligibility<0).any() or (eligibility>1).any():
            raise ValueError('eligibility outside [0,1]')
        self.optim.zero_grad(set_to_none=True)
        if not bool((eligibility>0).any()):return 0.
        with torch.no_grad():
            if wrong_target:y=y[torch.randperm(len(y),generator=shuffle_generator)]
            target=self.target(y).detach()
        pred=self.forward(x,a)
        mse=(pred-target).square().mean(1)
        variance_penalty=torch.relu(.1-pred.std(0,unbiased=False)).mean()
        loss=(mse*eligibility).sum()/eligibility.sum()+.01*variance_penalty
        loss.backward()
        if any(p.grad is not None for p in self.target.parameters()):
            raise RuntimeError('EMA target received gradient')
        self.optim.step()
        with torch.no_grad():
            for target_p,student_p in zip(self.target.parameters(),self.student.parameters()):
                target_p.mul_(EMA).add_(student_p,alpha=1-EMA)
        return float(loss.detach())

    @torch.no_grad()
    def mse(self,x,a,y):return float((self.forward(x,a)-self.target(y)).square().mean())


def train(learner,x,a,y,wrong_target=False):
    # Independent RNG streams: identical minibatch order across arms, while
    # the negative control shuffles only target pairings.
    index_rng=torch.Generator().manual_seed(SEED+2)
    shuffle_rng=torch.Generator().manual_seed(SEED+3)
    for _ in range(STEPS):
        ids=torch.randperm(len(x),generator=index_rng)[:32]
        learner.step(x[ids],a[ids],y[ids],torch.ones(len(ids)),wrong_target=wrong_target,shuffle_generator=shuffle_rng)
    return learner


def cohort():
    torch.set_num_threads(1)
    torch.manual_seed(SEED)
    x,a,y=pairs()
    train_x,train_a,train_y=(v[:128] for v in (x,a,y))
    test_x,test_a,test_y=(v[128:] for v in (x,a,y))
    reference=MicroLearner();initial=reference.mse(test_x,test_a,test_y)
    init_student=reference.student.weight.detach().clone()
    init_target=reference.target.weight.detach().clone()
    init_predictor=reference.predictor.weight.detach().clone()
    # Same initial weights and independent optimizer states for both arms.
    candidate=MicroLearner();candidate.load_state_dict(reference.state_dict())
    wrong=MicroLearner();wrong.load_state_dict(reference.state_dict())
    train(candidate,train_x,train_a,train_y)
    train(wrong,train_x,train_a,train_y,wrong_target=True)
    result={'schema':SCHEMA,'seed':SEED,'train_pairs':128,'holdout_pairs':64,
            'steps':STEPS,'lr':LR,'ema':EMA,
            'untrained_mse':initial,'trained_mse':candidate.mse(test_x,test_a,test_y),
            'wrong_target_mse':wrong.mse(test_x,test_a,test_y),
            'student_delta':float(torch.linalg.vector_norm(candidate.student.weight.detach()-init_student)),
            'predictor_delta':float(torch.linalg.vector_norm(candidate.predictor.weight.detach()-init_predictor)),
            'ema_delta':float(torch.linalg.vector_norm(candidate.target.weight.detach()-init_target)),
            'target_gradients_absent':all(p.grad is None for p in candidate.target.parameters()),
            'min_target_singular':float(torch.linalg.svdvals(candidate.target.weight.detach()).min()),
            'checkpoint_scope':'PREDICTION_WEIGHTS_ONLY_NO_OPTIMIZER_RESUME',
            'authority':'SYNTHETIC_SANDBOX_NO_AGE_ACTION','body_jepa_gate_pass':False,
            'jepa_weight_production':0}
    result['synthetic_criterion_pass']=(result['trained_mse']<=.5*initial and
        result['wrong_target_mse']>=1.25*result['trained_mse'] and
        result['student_delta']>0 and result['predictor_delta']>0 and result['ema_delta']>0 and
        result['target_gradients_absent'])
    return result,candidate,(test_x,test_a,test_y)


def save(learner,folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    dest=folder/'weights.npz';manifest=folder/'MANIFEST.json'
    if dest.exists() or manifest.exists():raise FileExistsError('checkpoint already exists')
    weights={k:v.detach().cpu().numpy() for k,v in learner.state_dict().items()}
    with tempfile.NamedTemporaryFile(dir=folder,prefix='.weights-',suffix='.npz',delete=False) as tmp:
        tmpname=tmp.name
        np.savez_compressed(tmp,**weights)
        tmp.flush();os.fsync(tmp.fileno())
    raw=Path(tmpname).read_bytes();sha=hashlib.sha256(raw).hexdigest()
    os.replace(tmpname,dest)
    info={'schema':SCHEMA,'sha256':sha,'bytes':len(raw),'keys':sorted(weights),
          'authority':'SYNTHETIC_SANDBOX_NO_AGE_ACTION'}
    manifest.write_text(json.dumps(info,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    return info


def load(folder):
    folder=Path(folder);info=json.loads((folder/'MANIFEST.json').read_text())
    raw=(folder/'weights.npz').read_bytes()
    if info.get('schema')!=SCHEMA or info.get('bytes')!=len(raw) or info.get('sha256')!=hashlib.sha256(raw).hexdigest():
        raise ValueError('checkpoint hash or schema mismatch')
    torch.manual_seed(SEED)
    learner=MicroLearner()
    expected=learner.state_dict()
    with np.load(folder/'weights.npz',allow_pickle=False) as data:
        if sorted(data.files)!=sorted(expected) or sorted(info['keys'])!=sorted(expected):
            raise ValueError('checkpoint key mismatch')
        state={}
        for k,t in expected.items():
            arr=data[k]
            if arr.shape!=tuple(t.shape) or not np.isfinite(arr).all():raise ValueError('invalid checkpoint tensor')
            state[k]=torch.from_numpy(arr.copy())
    learner.load_state_dict(state)
    return learner


if __name__=='__main__':
    print(json.dumps(cohort()[0],indent=2,sort_keys=True))
