"""Local digital World objective on actual ActionIntent/Corollary/Outcome pairs.

State and future are measured frozen encoder features. Action role is a typed
observed input, not invented native tokens. Only external projector/predictor
parameters train; the target projection is stop-gradient EMA. This is a narrow
digital-action model, not general causal understanding or external-world truth.
"""
import json
from pathlib import Path
import sys
import time
import numpy as np
from .common import atomic_write,dumps
from .resources import device,process_memory
from .predictor_worker import loss_gradient as base_loss_gradient

DIM=3072
ROLES=('SOURCE_COPY','C3_LANGUAGE','B1_DETAIL','B2_GIST')

def loss_gradient(x,y,p,q,target,anchor):
    loss,gp,gq,parts=base_loss_gradient(x,y,p,q,target,anchor)
    # Preserve the measured state geometry, not just the parameter norm.
    # Action rows and the predictor remain free to learn action-conditioned
    # changes. The immutable anchor never receives gradients or EMA updates.
    drift=x[:,:DIM]@(p[:DIM]-anchor[:DIM])
    geometry=float(np.mean(drift*drift))
    gp[:DIM]+=2*x[:,:DIM].T@drift/drift.size
    return loss+geometry,gp,gq,parts|{'state_geometry_loss':geometry}

def gradient_check(x,y,p,q,target,anchor):
    _,gp,gq,_=loss_gradient(x,y,p,q,target,anchor);errors=[];eps=1e-5
    for param,gradient,name in ((p,gp,'p'),(q,gq,'q')):
        for flat in np.argsort(np.abs(gradient).ravel())[-8:]:
            ix=np.unravel_index(flat,param.shape);plus=param.copy();minus=param.copy();plus[ix]+=eps;minus[ix]-=eps
            a=loss_gradient(x,y,plus if name=='p' else p,plus if name=='q' else q,target,anchor)[0]
            b=loss_gradient(x,y,minus if name=='p' else p,minus if name=='q' else q,target,anchor)[0]
            errors.append(abs((a-b)/(2*eps)-gradient[ix]))
    return float(max(errors))

def normalized(values):
    x=np.asarray(values,dtype=np.float64)
    if x.ndim!=2 or x.shape[1]!=DIM or not np.isfinite(x).all():raise ValueError('World requires measured 3072-dimensional frozen semantic features')
    n=np.linalg.norm(x,axis=1,keepdims=True)
    if np.any(n<1e-8):raise ValueError('Zero world-state observation')
    return x/n*np.sqrt(DIM)

def action_features(state,roles):
    if len(roles)!=len(state) or any(r not in ROLES for r in roles):raise ValueError('Unknown/missing actual action role')
    action=np.zeros((len(state),len(ROLES)))
    for i,r in enumerate(roles):action[i,ROLES.index(r)]=np.sqrt(DIM)/2
    return np.concatenate((state,action),axis=1)

def optimize(x,y,p,q,target,anchor,cfg):
    p=p.copy();q=q.copy();target=target.copy();max_norm=0.;history=[]
    for step in range(cfg['predictor_steps']):
        loss,gp,gq,_=loss_gradient(x,y,p,q,target,anchor)
        dp=-cfg['predictor_lr']*gp;dq=-cfg['predictor_lr']*gq;norm=float(np.sqrt(np.sum(dp*dp)+np.sum(dq*dq)))
        scale=min(1.,cfg['max_update_norm']/max(norm,1e-12));p+=dp*scale;q+=dq*scale;max_norm=max(max_norm,norm*scale)
        # Only the measured-state rows have a corresponding future target.
        target=cfg['ema_decay']*target+(1-cfg['ema_decay'])*p[:DIM]
        if step%32==0:history.append(float(loss))
    return p,q,target,{'sampled_loss':history,'max_applied_step_norm':max_norm}

def evaluate(x,y,p,q,target,anchor):
    actual=y@target;pred=x@p@q;copy=x[:,:DIM]@target
    no_action=x.copy();no_action[:,DIM:]=0
    shuffled_action=x.copy();shuffled_action[:,DIM:]=np.roll(x[:,DIM:],1,axis=0)
    shuffled_target=np.roll(actual,1,axis=0);sv=np.linalg.svd(actual-actual.mean(0),compute_uv=False)
    initial=np.std(y@anchor[:DIM],axis=0).mean()
    return {'prediction_mse':float(np.mean((pred-actual)**2)),'copy_baseline_mse':float(np.mean((copy-actual)**2)),
            'no_action_mse':float(np.mean((no_action@p@q-actual)**2)),'shuffled_action_mse':float(np.mean((shuffled_action@p@q-actual)**2)),
            'shuffled_target_mse':float(np.mean((pred-shuffled_target)**2)),'target_std_mean':float(np.std(actual,axis=0).mean()),
            'target_std_ratio':float(np.std(actual,axis=0).mean()/max(float(initial),1e-12)),
            'effective_rank':int(np.sum(sv>max(float(sv.max()),1e-12)*.01))}

def coverage(state,roles,groups):
    """Training-only measured support; no threshold fit on held-out states."""
    unit=state/np.sqrt(DIM);indices=np.array([ROLES.index(r) for r in roles]);floors=np.ones(len(ROLES));counts=np.zeros(len(ROLES),dtype=int)
    for k in range(len(ROLES)):
        ids=np.flatnonzero(indices==k);counts[k]=len({groups[i] for i in ids})
        if counts[k]<3:continue
        sim=unit[ids]@unit[ids].T
        # Another measurement of the same raw source is not independent support.
        for a,i in enumerate(ids):
            for b,j in enumerate(ids):
                if groups[i]==groups[j]:sim[a,b]=-np.inf
        floors[k]=max(.55,float(sim.max(1).min())-.05)
    return unit,indices,floors,counts

def support(embedding,role,unit,indices,floors,counts):
    if role not in ROLES:raise ValueError('Unknown World action')
    k=ROLES.index(role);mask=indices==k;similarity=float((unit[mask]@embedding).max()) if mask.any() else None
    admitted=bool(counts[k]>=3 and similarity is not None and similarity>=floors[k])
    return {'action_role':role,'action_source_count':int(counts[k]),'support_cosine':similarity,'support_floor':float(floors[k]),'in_support':admitted,
            'confidence_calibrated':False,'coverage_scope':'MEASURED_FROZEN_INPUT_AND_ACTUAL_ACTION_ROLE'}

def train(inp,out):
    start=time.monotonic();cfg=inp['config'];state=normalized(inp['state_embeddings']);y=normalized(inp['outcome_embeddings']);roles=inp['action_roles'];groups=inp['source_groups']
    if len(state)!=len(y) or len(groups)!=len(y) or len(set(groups))<12 or len(set(roles))<2:raise ValueError('World needs 12 actual source sequences and two measured action roles')
    # All action variants of a source remain together, across future updates.
    import hashlib
    mask=np.array([int(hashlib.sha256(g.encode()).hexdigest()[:8],16)%4==0 for g in groups]);vi=np.flatnonzero(mask);ti=np.flatnonzero(~mask)
    if len(ti)<16 or len(vi)<6 or len(set(roles[i] for i in vi))<2:raise ValueError('Insufficient held-out source/action coverage')
    x=action_features(state,roles);rng=np.random.default_rng(cfg['seed']);base=np.linalg.qr(rng.normal(size=(DIM,16)))[0]
    p=np.concatenate((base,np.zeros((len(ROLES),16))),axis=0);q=np.eye(16);target=base.copy();anchor=p.copy()
    if inp.get('active_checkpoint'):
        with np.load(inp['active_checkpoint'],allow_pickle=False) as a:p=a['projector'];q=a['predictor'];target=a['target'];anchor=a['anchor']
        if p.shape!=(DIM+len(ROLES),16) or target.shape!=(DIM,16) or q.shape!=(16,16):raise ValueError('World checkpoint dimensions')
    before=evaluate(x[vi],y[vi],p,q,target,anchor);err=gradient_check(x[ti],y[ti],p,q,target,anchor)
    new,nq,nt,history=optimize(x[ti],y[ti],p,q,target,anchor,cfg);p2,q2,t2,_=optimize(x[ti],y[ti],p,q,target,anchor,cfg)
    after=evaluate(x[vi],y[vi],new,nq,nt,anchor);finite=all(np.isfinite(a).all() for a in (new,nq,nt));repeat=all(np.array_equal(a,b) for a,b in ((new,p2),(nq,q2),(nt,t2)))
    unit,role_indices,floors,counts=coverage(state[ti],[roles[i] for i in ti],[groups[i] for i in ti])
    supported=[support(state[i]/np.sqrt(DIM),roles[i],unit,role_indices,floors,counts) for i in vi]
    support_ok=all(v['in_support'] for v in supported)
    residual=x[ti]@new@nq-y[ti]@nt;spread=np.zeros((len(ROLES),16))
    for k in range(len(ROLES)):
        mask=role_indices==k
        if mask.any():spread[k]=np.sqrt(np.mean(residual[mask]**2,axis=0))
    path=Path(out)/'candidate.npz';np.savez(path,projector=new,predictor=nq,target=nt,anchor=anchor,roles=np.array(ROLES),support_states=unit,support_roles=role_indices,support_floors=floors,action_source_counts=counts,residual_spread=spread)
    with np.load(path,allow_pickle=False) as a:reload_ok=all(np.array_equal(a[k],v) for k,v in (('projector',new),('target',nt),('support_states',unit),('support_roles',role_indices),('support_floors',floors),('action_source_counts',counts),('residual_spread',spread)))
    noncollapse=after['target_std_mean']>=.1 and after['target_std_ratio']>=.75 and after['effective_rank']>=4
    prediction=after['prediction_mse']<.98*after['copy_baseline_mse'] and after['prediction_mse']<.98*after['shuffled_target_mse']
    action_gain=after['prediction_mse']<.98*after['no_action_mse'] and after['prediction_mse']<.98*after['shuffled_action_mse']
    # A moving target must not conceal regression: compare the new predictor
    # to the exact pre-update target coordinates as a separate retention test.
    fixed_target_mse=float(np.mean((x[vi]@new@nq-y[vi]@target)**2))
    retention=fixed_target_mse<=before['prediction_mse']*(1+cfg['retention_max_delta'])
    m={'objective':'world-digital-action-latent-v1','state_geometry_weight':1.0,'state_geometry_loss':loss_gradient(x[vi],y[vi],new,nq,nt,anchor)[3]['state_geometry_loss'],'trainable_parameter_count':int(new.size+nq.size),'native_body_parameters_modified':0,'target_stop_gradient':True,'target_changed':bool(not np.array_equal(nt,target)),
       'train_source_groups':sorted(set(groups[i] for i in ti)),'held_out_source_groups':sorted(set(groups[i] for i in vi)),'train_pairs':len(ti),'held_out_pairs':len(vi),
       'before':before,'after':after,'fixed_target_retention_mse':fixed_target_mse,'noncollapse_pass':bool(noncollapse),'predictive_ablation_pass':bool(prediction),'action_ablation_pass':bool(action_gain),'retention_pass':bool(retention),
       'finite':bool(finite),'gradient_check':err<1e-5,'finite_difference_max_error':err,'deterministic_repeat':bool(repeat),'checkpoint_reload':bool(reload_ok),'optimizer_steps':cfg['predictor_steps'],
       'history':history,'duration_s':time.monotonic()-start,'device':device(),'process_memory':process_memory(),'semantic_truth_authority':False,'external_world_causal_claim':False,
       'held_out_support_pass':bool(support_ok),'held_out_support':supported,'action_source_counts':dict(zip(ROLES,counts.tolist())),
       'support_policy':'training-only nearest measured cosine; per-role source-count >=3; floor >=.55; no probability calibration',
       'support_state_bytes':int(unit.nbytes),'commit_eligible':bool(noncollapse and prediction and action_gain and retention and support_ok and finite and repeat and reload_ok and err<1e-5)}
    m.update(effective_learning_rate=cfg['predictor_lr'],effective_max_update_norm=cfg['max_update_norm'])
    atomic_write(Path(out)/'metrics.json',dumps(m));return m

def predict(embedding,role,checkpoint):
    x=action_features(normalized([embedding]),[role])
    with np.load(checkpoint,allow_pickle=False) as a:
        if not all(k in a for k in ('support_states','support_roles','support_floors','action_source_counts','residual_spread')):raise ValueError('World artifact has no measured state/action coverage; revalidate')
        covered=support(x[0,:DIM]/np.sqrt(DIM),role,a['support_states'],a['support_roles'],a['support_floors'],a['action_source_counts'])
        result=x@a['projector']@a['predictor'];spread=a['residual_spread'][ROLES.index(role)]
    if not np.isfinite(result).all():raise ValueError('Nonfinite World prediction')
    return {'future_latent_prediction':result[0].tolist() if covered['in_support'] else None,'action_role':role,'future_observed':False,'authority':'DIGITAL_ACTION_HYPOTHESIS','external_world_causal_claim':False,
            'coverage':covered,'residual_spread_latent':spread.tolist() if covered['in_support'] else None,'spread_scope':'FITTED_DIGITAL_RESIDUALS_NOT_CALIBRATED_UNCERTAINTY'}

def score(embedding,prediction,checkpoint):
    y=normalized([embedding])
    with np.load(checkpoint,allow_pickle=False) as a:actual=y@a['target']
    pred=np.asarray(prediction['future_latent_prediction'],dtype=float)
    if pred.shape!=(16,) or not np.isfinite(pred).all():raise ValueError('World prediction shape')
    return float(np.mean((pred-actual[0])**2))

if __name__=='__main__':train(json.loads(Path(sys.argv[1]).read_text()),sys.argv[2])
