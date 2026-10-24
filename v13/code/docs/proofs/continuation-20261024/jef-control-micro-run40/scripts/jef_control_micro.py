"""V13 §3.4/§13H JEF/C2 synthetic multi-head control objective (SHADOW only)."""
from dataclasses import dataclass
import json
import math

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

SEED=20261024
SCHEMA='V13_JEF_CONTROL_MICRO_SHADOW_V1'
ROUTES=('direct','detail','gist','both')
STEPS=200
LR=.03

@dataclass(frozen=True)
class ObjectiveAdapter:
    objective_id: str
    applicable_components: tuple
    required_inputs: tuple
    target_builder: str
    stop_gradient_policy: str
    ema_policy: str
    loss_terms: tuple
    credit_mapper: str
    update_scope: tuple
    eval_metrics: tuple

OBJECTIVE=ObjectiveAdapter(
    'C2_ROUTE_WAKE_HALT_REPORT_SYNTHETIC_V1',('C2_CONTROL_SYNTHETIC',),
    ('exact_need','gist_need','conflict','resource_pressure','source_valid','urgency','outcome_labels','eligibility'),
    'DETERMINISTIC_SYNTHETIC_OUTCOME_LABELS','FROZEN_LABELS','NOT_APPLICABLE_TO_SUPERVISED_CONTROL',
    ('ROUTE_CE','WAKE_BCE','HALT_BCE','REPORT_BCE'),
    'LOCAL_ELIGIBILITY_WEIGHT',('C2_FAST_SHARED','C2_ROUTE_HEAD','C2_WAKE_HEAD','C2_HALT_HEAD','C2_REPORT_HEAD'),
    ('heldout_route_accuracy','report_brier','wrong_target_route_accuracy'))


def labels(features):
    exact,gist,conflict,pressure,source,urgent=[features[:,i].astype(bool) for i in range(6)]
    route=np.where(~source,0,np.where(conflict&~pressure,3,np.where(exact,1,np.where(gist,2,0))))
    wake=((conflict&source&~pressure)|(exact&~pressure)|urgent)&source
    halt=pressure|~source|(urgent&conflict)
    report=source&~conflict&~pressure
    return (route.astype('int64'),wake.astype('float32'),halt.astype('float32'),report.astype('float32'))


def dataset(seed=SEED,n=640):
    rng=np.random.default_rng(seed)
    x=rng.integers(0,2,size=(n,6),dtype='int32').astype('float32')
    y=labels(x)
    return torch.from_numpy(x),tuple(torch.from_numpy(v) for v in y)


class Control(nn.Module):
    def __init__(self,mode='SYNTHETIC_SHADOW'):
        super().__init__()
        if mode!='SYNTHETIC_SHADOW':raise PermissionError('no native JEF or Age control authority')
        self.shared=nn.Sequential(nn.Linear(6,32),nn.ReLU())
        self.route=nn.Linear(32,4)
        self.wake=nn.Linear(32,1)
        self.halt=nn.Linear(32,1)
        self.report=nn.Linear(32,1)
        self.optim=torch.optim.Adam(self.parameters(),lr=LR)

    def forward(self,x):
        h=self.shared(x)
        return self.route(h),self.wake(h).squeeze(-1),self.halt(h).squeeze(-1),self.report(h).squeeze(-1)

    def step(self,x,y,eligibility):
        if eligibility.shape!=(len(x),) or not torch.isfinite(eligibility).all() or (eligibility<0).any() or (eligibility>1).any():
            raise ValueError('invalid local eligibility')
        self.optim.zero_grad(set_to_none=True)
        if not bool((eligibility>0).any()):return 0.
        route,wake,halt,report=self.forward(x)
        terms=(F.cross_entropy(route,y[0],reduction='none'),
               F.binary_cross_entropy_with_logits(wake,y[1],reduction='none'),
               F.binary_cross_entropy_with_logits(halt,y[2],reduction='none'),
               F.binary_cross_entropy_with_logits(report,y[3],reduction='none'))
        per=terms[0]+.5*(terms[1]+terms[2]+terms[3])
        loss=(per*eligibility).sum()/eligibility.sum()
        loss.backward();self.optim.step()
        return float(loss.detach())

    @torch.no_grad()
    def metrics(self,x,y):
        route,_,_,report=self.forward(x)
        return {'route_accuracy':float((route.argmax(1)==y[0]).float().mean()),
                'report_brier':float((report.sigmoid()-y[3]).square().mean())}

    @torch.no_grad()
    def propose(self,features):
        if len(features)!=6 or any(v not in (0,1,False,True) for v in features):raise ValueError('binary features required')
        x=torch.tensor([features],dtype=torch.float32)
        route,wake,halt,report=self.forward(x)
        source_valid=bool(features[4]);conflict=bool(features[2]);pressure=bool(features[3])
        return {'route_suggestion':ROUTES[int(route.argmax(1))],
                'wake_suggestion':bool(wake.sigmoid().item()>=.5),
                'halt_suggestion':bool(halt.sigmoid().item()>=.5),
                'report_head_probability':float(report.sigmoid().item()),
                'report_allowed':source_valid and not conflict and not pressure,
                'action_authority':False,'authority':'SYNTHETIC_SHADOW_NO_AGE_ACTION'}


def train(model,x,y,wrong_target=False):
    index_rng=torch.Generator().manual_seed(SEED+2)
    shuffle_rng=torch.Generator().manual_seed(SEED+3)
    for _ in range(STEPS):
        idx=torch.randperm(len(x),generator=index_rng)[:64]
        labels_batch=tuple(v[idx] for v in y)
        if wrong_target:
            perm=torch.randperm(len(idx),generator=shuffle_rng)
            labels_batch=tuple(v[perm] for v in labels_batch)
        model.step(x[idx],labels_batch,torch.ones(len(idx)))
    return model


def cohort():
    torch.set_num_threads(1);torch.manual_seed(SEED)
    x,y=dataset();tx,ty=x[:512],tuple(v[:512] for v in y)
    hx,hy=x[512:],tuple(v[512:] for v in y)
    baseline=Control();before=baseline.metrics(hx,hy)
    candidate=Control();candidate.load_state_dict(baseline.state_dict())
    wrong=Control();wrong.load_state_dict(baseline.state_dict())
    old={k:v.detach().clone() for k,v in candidate.state_dict().items()}
    train(candidate,tx,ty)
    train(wrong,tx,ty,wrong_target=True)
    after=candidate.metrics(hx,hy);wrong_metric=wrong.metrics(hx,hy)
    deltas={k:float(torch.linalg.vector_norm(v.detach()-old[k])) for k,v in candidate.state_dict().items()}
    head_deltas={name:max(v for k,v in deltas.items() if k.startswith(name+'.')) for name in ('route','wake','halt','report')}
    result={'schema':SCHEMA,'seed':SEED,'train_rows':512,'heldout_rows':128,'steps':STEPS,'lr':LR,
            'baseline':before,'candidate':after,'wrong_target':wrong_metric,
            'head_deltas':head_deltas,'authority':'SYNTHETIC_SHADOW_NO_AGE_ACTION',
            'native_jef_gate_pass':False,'age_action_authority':False}
    result['synthetic_criterion_pass']=(after['route_accuracy']>=.90 and after['report_brier']<=.10 and
        wrong_metric['route_accuracy']<=.50 and all(v>0 for v in head_deltas.values()))
    return result,candidate


if __name__=='__main__':print(json.dumps(cohort()[0],indent=2,sort_keys=True))
