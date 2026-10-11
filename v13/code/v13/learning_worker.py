"""Isolated NumPy optimizer. Receives explicit labels and real frozen embeddings.
No database access, no LLM weight writes, no synthetic latent states.
"""
import json
import os
from pathlib import Path
import sys
import time
import numpy as np
from .common import atomic_write,dumps,file_hash
from .resources import device,process_memory

def features(v):
    x=np.asarray(v,dtype=np.float64)
    if x.ndim!=2 or x.shape[1]<1 or not np.isfinite(x).all():raise ValueError('Invalid native embeddings')
    x=x/np.maximum(np.linalg.norm(x,axis=1,keepdims=True),1e-12)*8.
    return np.column_stack([x,np.ones(len(x))])
def objective(x,y,w):
    logits=x@w;logits-=logits.max(axis=1,keepdims=True);p=np.exp(logits);p/=p.sum(axis=1,keepdims=True)
    loss=-np.log(np.maximum(p[np.arange(len(y)),y],1e-30)).mean()
    d=p.copy();d[np.arange(len(y)),y]-=1
    return float(loss),x.T@d/len(y),p

def gradient_check(x,y,w):
    _,grad,_=objective(x,y,w);inds=np.argsort(np.abs(grad).ravel())[-12:];errs=[];eps=1e-5
    for flat in inds:
        i,j=np.unravel_index(flat,w.shape);a=w.copy();b=w.copy();a[i,j]+=eps;b[i,j]-=eps
        numeric=(objective(x,y,a)[0]-objective(x,y,b)[0])/(2*eps);errs.append(abs(numeric-grad[i,j]))
    return float(max(errs,default=0.))
def split(y):
    train=[];valid=[]
    for k in range(4):
        ids=np.flatnonzero(y==k).tolist();n=max(1,len(ids)//4) if len(ids)>=3 else 0
        train += ids[:-n] if n else ids;valid+=ids[-n:] if n else []
    return np.array(train,dtype=int),np.array(valid,dtype=int)
def optimize(x,y,w,trace,cfg,stats=None):
    w=w.copy();trace=trace.copy()
    max_norm=0.
    for _ in range(cfg['learning_steps']):
        _,grad,_=objective(x,y,w);trace=cfg['eligibility_decay']*trace+(1-cfg['eligibility_decay'])*np.mean(np.abs(x),axis=0)
        gain=np.clip(trace/max(float(trace.mean()),1e-8),.05,2.)[:,None];delta=-cfg['learning_rate']*grad*gain
        norm=np.linalg.norm(delta);delta*=min(1.,cfg['max_update_norm']/max(float(norm),1e-12));max_norm=max(max_norm,float(np.linalg.norm(delta)));w+=delta
    if stats is not None:stats['max_applied_step_norm']=max_norm
    return w,trace

def train(inp,out):
    started=time.monotonic();cfg=inp['config'];x=features(inp['embeddings']);y=np.asarray(inp['labels'],dtype=int)
    if len(x)!=len(y) or len(y)<4 or not np.isin(y,[0,1,2,3]).all():raise ValueError('At least four valid explicit route labels required')
    w=np.zeros((x.shape[1],4));trace=np.zeros(x.shape[1])
    if inp.get('active_checkpoint'):
        with np.load(inp['active_checkpoint'],allow_pickle=False) as z:w=z['route_w'];trace=z['eligibility']
        if w.shape!=(x.shape[1],4) or trace.shape!=(x.shape[1],):raise ValueError('Checkpoint dimension')
    ti,vi=split(y);before=objective(x,y,w)[0];err=gradient_check(x[ti],y[ti],w);stats={};new,tr=optimize(x[ti],y[ti],w,trace,cfg,stats);repeat,_=optimize(x[ti],y[ti],w,trace,cfg)
    finite=bool(np.isfinite(new).all());deterministic=bool(np.array_equal(new,repeat));held={};eligible=False;retained=False
    if len(vi):
        oldloss,_,oldp=objective(x[vi],y[vi],w);newloss,_,newp=objective(x[vi],y[vi],new)
        perclass={str(k):{'before':float(np.mean(oldp.argmax(1)[y[vi]==k]==k)),'after':float(np.mean(newp.argmax(1)[y[vi]==k]==k))} for k in set(y[vi].tolist())}
        accuracy=float(np.mean(newp.argmax(1)==y[vi]));baseline=float(np.mean(np.asarray(inp['scaffold_labels'])[vi]==y[vi]))
        held={'n':len(vi),'loss_before':oldloss,'loss_after':newloss,'accuracy':accuracy,'scaffold_accuracy':baseline,'per_class':perclass}
        retained=all(v['after']>=v['before']-cfg['retention_max_delta'] for v in perclass.values())
        eligible=len(y)>=12 and len(vi)>=4 and len(perclass)==4 and newloss<oldloss and accuracy>=.75 and accuracy>=baseline and retained
    path=Path(out)/'candidate.npz';np.savez(path,route_w=new,eligibility=tr)
    with np.load(path,allow_pickle=False) as z:reload_ok=bool(np.array_equal(z['route_w'],new))
    metrics={'objective':'explicit-human-route-cross-entropy-v1','n':len(y),'embedding_dim':x.shape[1]-1,'trainable_parameter_count':int(new.size),'nontrainable_trace_count':int(tr.size),'loss_before':before,'loss_after':objective(x,y,new)[0],'held_out':held,'finite_difference_max_error':err,'gradient_check':err<1e-6,'deterministic_repeat':deterministic,'checkpoint_reload':reload_ok,'finite':finite,'duration_s':time.monotonic()-started,'process_memory':process_memory(),'device':device(),'energy_joules':None,'phone_benchmark':False,'body_parameters_modified':0}
    metrics.update(commit_eligible=bool(eligible and finite and deterministic and reload_ok and err<1e-6),retention_pass=bool(retained),optimizer_steps=cfg['learning_steps'],**stats)
    metrics.update(effective_learning_rate=cfg['learning_rate'],effective_max_update_norm=cfg['max_update_norm'])
    atomic_write(Path(out)/'metrics.json',dumps(metrics));return metrics
if __name__=='__main__':
    request=json.loads(Path(sys.argv[1]).read_text());train(request,sys.argv[2])
