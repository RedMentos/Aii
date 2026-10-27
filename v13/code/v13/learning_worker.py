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

def features(v,words=None):
    x=np.asarray(v,dtype=np.float64)
    if x.ndim!=2 or x.shape[1]<1 or not np.isfinite(x).all():raise ValueError('Invalid native embeddings')
    x=x/np.maximum(np.linalg.norm(x,axis=1,keepdims=True),1e-12)*8.
    if words is None:return np.column_stack([x,np.ones(len(x))])
    w=np.asarray(words,dtype=np.float64)  # WP-Z6i: fixed word channel (route_words), between embedding and bias
    if w.shape[0]!=len(x) or w.ndim!=2 or not np.isfinite(w).all():raise ValueError('Invalid word features')
    return np.column_stack([x,w,np.ones(len(x))])
def word_dim(z):return int(z['word_dim']) if 'word_dim' in z.files else 0
def route_logits(z,embedding,text):
    """Logits of a loaded route checkpoint for one request; a word-channel head needs the request text."""
    if word_dim(z):
        from .route_words import vector
        return (features([embedding],[vector(text)])@z['route_w'])[0]
    return (features([embedding])@z['route_w'])[0]
def widen(w,trace,dim,fill):
    """WP-Z6i: an embedding-only checkpoint gets zero rows for the word channel (same function, warm start kept)."""
    return np.vstack([w[:-1],np.zeros((dim,w.shape[1])),w[-1:]]),np.concatenate([trace[:-1],np.full(dim,fill),trace[-1:]])
def objective(x,y,w,sw=None):
    logits=x@w;logits-=logits.max(axis=1,keepdims=True);p=np.exp(logits);p/=p.sum(axis=1,keepdims=True)
    nll=-np.log(np.maximum(p[np.arange(len(y)),y],1e-30));d=p.copy();d[np.arange(len(y)),y]-=1
    if sw is None:return float(nll.mean()),x.T@d/len(y),p
    return float(sw@nll/sw.sum()),x.T@(d*sw[:,None])/sw.sum(),p  # WP-Z6i: per-sample weights (anchors weigh less than human labels)

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
def optimize(x,y,w,trace,cfg,stats=None,sw=None):
    w=w.copy();trace=trace.copy()
    max_norm=0.
    for _ in range(cfg['learning_steps']):
        _,grad,_=objective(x,y,w,sw);trace=cfg['eligibility_decay']*trace+(1-cfg['eligibility_decay'])*np.mean(np.abs(x),axis=0)
        gain=np.clip(trace/max(float(trace.mean()),1e-8),.05,2.)[:,None];delta=-cfg['learning_rate']*grad*gain
        norm=np.linalg.norm(delta);delta*=min(1.,cfg['max_update_norm']/max(float(norm),1e-12));max_norm=max(max_norm,float(np.linalg.norm(delta)));w+=delta
    if stats is not None:stats['max_applied_step_norm']=max_norm
    return w,trace

def train(inp,out):
    started=time.monotonic();cfg=inp['config'];words=inp.get('words');x=features(inp['embeddings'],words);y=np.asarray(inp['labels'],dtype=int)
    wdim=len(words[0]) if words else 0
    if len(x)!=len(y) or len(y)<4 or not np.isin(y,[0,1,2,3]).all():raise ValueError('At least four valid explicit route labels required')
    w=np.zeros((x.shape[1],4));trace=np.zeros(x.shape[1])
    if inp.get('active_checkpoint'):
        with np.load(inp['active_checkpoint'],allow_pickle=False) as z:w=z['route_w'];trace=z['eligibility'];old_wdim=word_dim(z)
        if wdim and not old_wdim and w.shape==(x.shape[1]-wdim,4):w,trace=widen(w,trace,wdim,float(np.mean(np.abs(x[:,-1-wdim:-1]))))
        if w.shape!=(x.shape[1],4) or trace.shape!=(x.shape[1],):raise ValueError('Checkpoint dimension')
    ti,vi=split(y);before=objective(x,y,w)[0];err=gradient_check(x[ti],y[ti],w);stats={}
    xt,yt,sw=x[ti],y[ti],None;anchor=inp.get('anchors');xa=None
    if anchor and inp.get('active_checkpoint'):
        # WP-Z6i: recent unlabelled questions outside the human rule's words keep the active head's own route as a soft
        # target (learning without forgetting): the new rule is learned, its neighbours are held where they were.
        xa=features(anchor['embeddings'],anchor['words']);ya=(xa@w).argmax(1)
        xt=np.vstack([xt,xa]);yt=np.concatenate([yt,ya]);sw=np.concatenate([np.ones(len(ti)),np.full(len(xa),float(anchor.get('weight',.5)))])
    new,tr=optimize(xt,yt,w,trace,cfg,stats,sw);repeat,_=optimize(xt,yt,w,trace,cfg,sw=sw)
    finite=bool(np.isfinite(new).all());deterministic=bool(np.array_equal(new,repeat));held={};eligible=False;retained=False
    if len(vi):
        oldloss,_,oldp=objective(x[vi],y[vi],w);newloss,_,newp=objective(x[vi],y[vi],new)
        perclass={str(k):{'before':float(np.mean(oldp.argmax(1)[y[vi]==k]==k)),'after':float(np.mean(newp.argmax(1)[y[vi]==k]==k))} for k in set(y[vi].tolist())}
        accuracy=float(np.mean(newp.argmax(1)==y[vi]));baseline=float(np.mean(np.asarray(inp['scaffold_labels'])[vi]==y[vi]))
        held={'n':len(vi),'loss_before':oldloss,'loss_after':newloss,'accuracy':accuracy,'scaffold_accuracy':baseline,'per_class':perclass}
        retained=all(v['after']>=v['before']-cfg['retention_max_delta'] for v in perclass.values())
        if wdim:  # WP-Z6i: a word-channel head may also not lose any human-labelled item the active head routes right (train+valid)
            oldall=x@w;newall=x@new;flipped=int(np.sum((oldall.argmax(1)==y)&(newall.argmax(1)!=y)))
            held['known_items_lost']=flipped;retained=retained and flipped==0
            if xa is not None:  # reported, not gated: anchors that still moved into a rule route despite the soft target
                ks=anchor.get('rule_routes',[]);old_a=(xa@w).argmax(1);new_a=(xa@new).argmax(1)
                held['anchors']=len(xa);held['anchors_changed']=int(np.sum(old_a!=new_a));held['anchors_moved_into_rule_route']=int(np.sum((old_a!=new_a)&np.isin(new_a,ks)))
        hurdle=accuracy>=.75
        if wdim and inp.get('gate')=='relative' and inp.get('active_checkpoint'):
            # WP-Z6j: the validation quarter holds 1-4 questions per route, so a fixed 75 % bar mostly measures which old
            # questions landed there (Z6i seed 83). A successor head must instead beat the active head on the same
            # validation questions, lose no known human-labelled question, and route strictly more of them right.
            old_val=float(np.mean(oldp.argmax(1)==y[vi]));known_before=float(np.mean(oldall.argmax(1)==y));known_after=float(np.mean(newall.argmax(1)==y))
            held.update(gate='relative',active_accuracy=old_val,known_accuracy_before=known_before,known_accuracy_after=known_after)
            hurdle=accuracy>=old_val and known_after>known_before
        eligible=len(y)>=12 and len(vi)>=4 and len(perclass)==4 and newloss<oldloss and hurdle and accuracy>=baseline and retained
    path=Path(out)/'candidate.npz'
    with open(path,'wb') as f:np.savez(f,route_w=new,eligibility=tr,word_dim=np.int64(wdim));f.flush();os.fsync(f.fileno())  # durable before metrics.json (TrainRunnerProof crash_during_checkpoint)
    with np.load(path,allow_pickle=False) as z:reload_ok=bool(np.array_equal(z['route_w'],new))
    metrics={'objective':'explicit-human-route-cross-entropy-v1','n':len(y),'embedding_dim':x.shape[1]-1-wdim,'word_dim':wdim,'trainable_parameter_count':int(new.size),'nontrainable_trace_count':int(tr.size),'loss_before':before,'loss_after':objective(x,y,new)[0],'held_out':held,'finite_difference_max_error':err,'gradient_check':err<1e-6,'deterministic_repeat':deterministic,'checkpoint_reload':reload_ok,'finite':finite,'duration_s':time.monotonic()-started,'process_memory':process_memory(),'device':device(),'energy_joules':None,'phone_benchmark':False,'body_parameters_modified':0}
    metrics.update(commit_eligible=bool(eligible and finite and deterministic and reload_ok and err<1e-6),retention_pass=bool(retained),optimizer_steps=cfg['learning_steps'],**stats)
    metrics.update(effective_learning_rate=cfg['learning_rate'],effective_max_update_norm=cfg['max_update_norm'])
    atomic_write(Path(out)/'metrics.json',dumps(metrics));return metrics
if __name__=='__main__':
    request=json.loads(Path(sys.argv[1]).read_text());train(request,sys.argv[2])
