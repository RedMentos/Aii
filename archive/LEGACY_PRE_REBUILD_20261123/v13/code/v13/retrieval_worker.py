"""Learn source-bound memory cue relevance; never learn facts from model output."""
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import numpy as np
from .common import atomic_write,dumps
from .memory import relevance,terms,entities
from .control_calibration_worker import loss_gradient,gradient_check,scores,probabilities
from .resources import device,process_memory

STEM='needle-source-pair-retrieval-v2-native-interactions'
DIM=6151

def topic_view(text):
    return re.sub(r'\b(?:projekt|project|kunde|client|person)\s+["\']?[\w-]+["\']?', ' ',text,flags=re.I).strip()

def admissible(query,key):
    a,b=entities(query),entities(key)
    return not (a and b and not a&b)

def pair_features(query,key,q,k,qt,kt):
    def cosine(a,b):
        a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float)
        if a.shape!=(3072,) or b.shape!=a.shape or not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('Actual finite Needle feature pair required')
        norm=np.linalg.norm(a)*np.linalg.norm(b)
        if norm<1e-12:raise ValueError('Zero native feature pair')
        return float(np.clip(a@b/norm,-1,1))
    ta,tb=terms(topic_view(query)),terms(topic_view(key));a,b=entities(query),entities(key)
    scalar=[1.,cosine(q,k),cosine(qt,kt),relevance(query,key),len(ta&tb)/max(len(ta|tb),1),float(bool(a&b)),float(bool(a or b))]
    qa=np.asarray(qt,dtype=float);kb=np.asarray(kt,dtype=float);qa/=np.linalg.norm(qa);kb/=np.linalg.norm(kb)
    return scalar+list(qa*kb)+list(np.abs(qa-kb))

def optimize(x,y,w,cfg):
    w=w.copy();max_norm=0.
    for _ in range(cfg['retrieval_steps']):
        _,g=loss_gradient(x,y,w);step=-cfg['retrieval_lr']*g;norm=float(np.linalg.norm(step));scale=min(1.,cfg['max_update_norm']/max(norm,1e-12));w+=step*scale;max_norm=max(max_norm,norm*scale)
    return w,max_norm

def supported(x,bounds,anchors):
    scalar=np.all((x[:,:7]>=bounds[0]-.05)&(x[:,:7]<=bounds[1]+.05),axis=1)
    pair=x[:,7:];norm=np.linalg.norm(pair,axis=1);anorm=np.linalg.norm(anchors,axis=1)
    similarity=pair@anchors.T/np.maximum(norm[:,None]*anorm[None,:],1e-12)
    return scalar & (similarity.max(1)>=.9)

def gradient_evidence(x,y,w):
    # Large native interaction head: explicitly sample 36 distributed coordinates.
    ids=np.unique(np.r_[np.arange(7),np.linspace(7,DIM-1,29,dtype=int)]);_,g=loss_gradient(x,y,w);eps=1e-5;errors=[]
    for i in ids:
        a=w.copy();b=w.copy();a[i]+=eps;b[i]-=eps;errors.append(abs((loss_gradient(x,y,a)[0]-loss_gradient(x,y,b)[0])/(2*eps)-g[i]))
    return float(max(errors)),ids.tolist()

def effective(x,p,support,cfg):
    baseline=x[:,3]>=cfg['memory_threshold']
    return np.where(support&(p>=.8),True,np.where(support&(p<=.2),False,baseline))

def quality(pred,y):
    positive=y==1;negative=~positive
    return {'accuracy':float(np.mean(pred==y)), 'recall':float(pred[positive].mean()),
            'false_positive_rate':float(pred[negative].mean()),'balanced_accuracy':float((pred[positive].mean()+(~pred[negative]).mean())/2)}

def fit(x,y,ti,ci,w,cfg):
    w,norm=optimize(x[ti],y[ti],w,cfg)
    temperature=float(min(np.exp(np.linspace(np.log(.2),np.log(5),65)),key=lambda t:scores(probabilities(x[ci]@w,t),y[ci])['loss']))
    return w,temperature,norm

def train(inp,out):
    start=time.monotonic();cfg=inp['config'];x=np.asarray(inp['features'],dtype=float);y=np.asarray(inp['labels'],dtype=float)
    groups=inp['memory_groups'];pairs=inp['pair_ids']
    if x.shape!=(len(y),DIM) or len(groups)!=len(y) or len(pairs)!=len(y) or len(set(pairs))!=len(pairs) or not np.isfinite(x).all() or not np.isin(y,[0,1]).all() or np.max(np.abs(x))>1.000001:raise ValueError('Unique finite labelled source pairs required')
    fold=np.array([int(hashlib.sha256(g.encode()).hexdigest()[:8],16)%5 for g in groups]);ti=np.flatnonzero(fold>=2);ci=np.flatnonzero(fold==1);vi=np.flatnonzero(fold==0)
    for ids in (ti,ci,vi):
        if len(set(groups[i] for i in ids))<2 or min(int((y[ids]==0).sum()),int((y[ids]==1).sum()))<4:raise ValueError('Each memory-group-disjoint partition needs two memories and four positive/four negative pairs')
    offset=np.zeros(DIM);scale=np.ones(DIM);offset[7:]=x[ti,7:].mean(0);scale[7:]=np.maximum(x[ti,7:].std(0),1e-5)
    w0=np.zeros(DIM);old_temperature=1.;old_x=np.empty((0,DIM));old_y=np.empty(0);old_ids=[]
    old_bounds=None;old_anchors=None
    if inp.get('active_checkpoint'):
        with np.load(inp['active_checkpoint'],allow_pickle=False) as a:
            if str(a['stem'])!=STEM:raise ValueError('Retrieval feature revision changed')
            w0=a['weights'];old_temperature=float(a['temperature']);old_x=a['retention_x'];old_y=a['retention_y'];old_ids=a['retention_ids'].tolist();offset=a['offset'];scale=a['scale'];old_bounds=a['bounds'];old_anchors=a['anchors']
        if w0.shape!=(DIM,) or not np.isfinite(w0).all() or old_x.shape!=(len(old_y),DIM) or not len(old_y) or not np.isfinite(old_x).all() or not np.isin(old_y,[0,1]).all() or len(old_ids)!=len(old_y) or len(set(old_ids))!=len(old_ids) or not .199999<=old_temperature<=5.000001 or old_bounds.shape!=(2,7) or not np.isfinite(old_bounds).all() or old_anchors.ndim!=2 or old_anchors.shape[1]!=DIM-7 or not len(old_anchors) or not np.isfinite(old_anchors).all():raise ValueError('Retrieval checkpoint invalid')
    if offset.shape!=(DIM,) or scale.shape!=(DIM,) or not np.isfinite(offset).all() or not np.isfinite(scale).all() or (scale<=0).any():raise ValueError('Retrieval normalization invalid')
    z=np.clip((x-offset)/scale,-8,8);err,checked=gradient_evidence(z[ti],y[ti],w0);w,t,norm=fit(z,y,ti,ci,w0,cfg);repeat,repeat_t,_=fit(z,y,ti,ci,w0,cfg)
    bounds=np.stack([x[ti,:7].min(0),x[ti,:7].max(0)]);anchors=x[ti,7:]
    if old_anchors is not None:
        anchors=np.unique(np.vstack([old_anchors,anchors]),axis=0);bounds=np.stack([np.minimum(bounds[0],old_bounds[0]),np.maximum(bounds[1],old_bounds[1])])
    if len(anchors)>2048:raise ValueError('Retained cue support budget exhausted; no silent discard')
    support=supported(x[vi],bounds,anchors);p=probabilities(z[vi]@w,t)
    before=scores(probabilities(z[vi]@w0,old_temperature),y[vi]);after=scores(p,y[vi])
    lexical=scores(np.clip(x[vi,3],0,1),y[vi]);native=scores(np.clip(x[vi,2],0,1),y[vi])
    lexical_q=quality(x[vi,3]>=cfg['memory_threshold'],y[vi]);actual_q=quality(effective(x[vi],p,support,cfg),y[vi])
    thresholds=np.linspace(.3,.98,69);cos_floor=float(max(thresholds,key=lambda f:quality(x[ti,2]>=f,y[ti])['balanced_accuracy']))
    native_q=quality(x[vi,2]>=cos_floor,y[vi])
    off=z.copy();off[:,1:3]=0;off[:,7:]=0;off_w,off_t,_=fit(off,y,ti,ci,w0,cfg);off_score=scores(probabilities(off[vi]@off_w,off_t),y[vi])
    retention={'n':0,'pass':True}
    if len(old_y):
        oz=np.clip((old_x-offset)/scale,-8,8);op=probabilities(oz@w0,old_temperature);np_=probabilities(oz@w,t);old_before=scores(op,old_y);old_after=scores(np_,old_y)
        old_quality=quality(effective(old_x,op,supported(old_x,old_bounds,old_anchors),cfg),old_y);new_quality=quality(effective(old_x,np_,supported(old_x,bounds,anchors),cfg),old_y)
        quality_retained=new_quality['recall']>=old_quality['recall']-cfg['retention_max_delta'] and new_quality['false_positive_rate']<=old_quality['false_positive_rate']+cfg['retention_max_delta']
        retention={'n':len(old_y),'before':old_before,'after':old_after,'effective_before':old_quality,'effective_after':new_quality,'pass':quality_retained and old_after['loss']<=old_before['loss']+cfg['retention_max_delta'] and old_after['brier']<=old_before['brier']+cfg['retention_max_delta']}
    gain=actual_q['recall']>=lexical_q['recall']+.05 and actual_q['false_positive_rate']<=lexical_q['false_positive_rate']+.01 and actual_q['balanced_accuracy']>=lexical_q['balanced_accuracy']+.025
    calibration=after['brier']<=lexical['brier']-.02 and after['ece']<=.2
    ablation=after['brier']<=off_score['brier']-.01
    current_retention=after['brier']<=before['brier']+cfg['retention_max_delta']
    retained=bool(retention['pass'] and current_retention);repeat_ok=np.array_equal(w,repeat) and t==repeat_t
    retained_pairs={pid:(row,label) for pid,row,label in zip(old_ids,old_x,old_y)}
    retained_pairs.update({pairs[i]:(x[i],y[i]) for i in vi})
    if len(retained_pairs)>2048:raise ValueError('Retrieval retained-test budget exhausted; no silent discard')
    retained_ids=sorted(retained_pairs);rx=np.stack([retained_pairs[k][0] for k in retained_ids]);ry=np.array([retained_pairs[k][1] for k in retained_ids])
    path=Path(out)/'candidate.npz';np.savez_compressed(path,weights=w,temperature=t,bounds=bounds,anchors=anchors,offset=offset,scale=scale,stem=np.asarray(STEM),retention_x=rx,retention_y=ry,retention_ids=np.array(retained_ids))
    with np.load(path,allow_pickle=False) as a:reload_ok=np.array_equal(a['weights'],w) and np.array_equal(a['retention_x'],rx)
    eligible=bool(gain and calibration and ablation and retained and support.all() and repeat_ok and reload_ok and err<1e-6)
    m={'objective':'source-bound-semantic-retrieval-v1','trainable_parameter_count':DIM+1,'native_body_parameters_modified':0,'target_scope':'EXPLICIT_HUMAN_MEMORY_RELEVANCE_NOT_FACT_TRUTH',
       'partition':{'train':ti.tolist(),'calibration':ci.tolist(),'test':vi.tolist()},'memory_groups':groups,'before':before,'after':after,'lexical_baseline':lexical,'native_cosine_baseline':native,
       'effective_retrieval':actual_q,'lexical_retrieval':lexical_q,'native_cosine_retrieval':native_q,'native_cosine_threshold_train_only':cos_floor,'semantic_off':off_score,
       'retrieval_gain':bool(gain),'calibration_pass':bool(calibration),'semantic_ablation_pass':bool(ablation),'retention_pass':retained,'retained_test':retention,
       'held_out_support_pass':bool(support.all()),'temperature':t,'finite_difference_max_error':err,'gradient_check':err<1e-6,'gradient_coordinates_checked':checked,'normalization_fit_partition':'TRAIN_ONLY_FROZEN_ACROSS_UPDATES','deterministic_repeat':repeat_ok,'checkpoint_reload':bool(reload_ok),
       'max_applied_step_norm':norm,'optimizer_steps':cfg['retrieval_steps'],'commit_eligible':eligible,'semantic_truth_authority':False,'duration_s':time.monotonic()-start,'device':device(),'process_memory':process_memory()}
    m.update(effective_learning_rate=cfg['retrieval_lr'],effective_max_update_norm=cfg['max_update_norm'])
    atomic_write(Path(out)/'metrics.json',dumps(m));return m

def infer(features,checkpoint):
    x=np.asarray([features],dtype=float)
    if x.shape!=(1,DIM) or not np.isfinite(x).all():raise ValueError('Retrieval features invalid')
    with np.load(checkpoint,allow_pickle=False) as a:
        if str(a['stem'])!=STEM:raise ValueError('Retrieval stem changed')
        w=a['weights'];t=float(a['temperature']);bounds=a['bounds'];anchors=a['anchors'];offset=a['offset'];scale=a['scale']
        if w.shape!=(DIM,) or not np.isfinite(w).all() or not .199999<=t<=5.000001 or bounds.shape!=(2,7) or not np.isfinite(bounds).all() or anchors.ndim!=2 or anchors.shape[1]!=DIM-7 or not len(anchors) or not np.isfinite(anchors).all() or offset.shape!=(DIM,) or scale.shape!=(DIM,) or not np.isfinite(offset).all() or not np.isfinite(scale).all() or (scale<=0).any():raise ValueError('Retrieval artifact invalid')
        support=bool(supported(x,bounds,anchors)[0]);p=float(probabilities(np.clip((x-offset)/scale,-8,8)@w,t)[0])
    return {'probability':p if support else None,'in_support':support,'decision':'admit' if support and p>=.8 else 'reject' if support and p<=.2 else 'baseline','semantic_truth_authority':False}

if __name__=='__main__':train(json.loads(Path(sys.argv[1]).read_text()),sys.argv[2])
