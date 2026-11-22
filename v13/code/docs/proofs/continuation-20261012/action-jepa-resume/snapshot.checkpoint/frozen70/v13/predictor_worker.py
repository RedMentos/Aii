"""Predictor-first local future-state experiment on actual causal native taps.

Only a small external projector/predictor trains. The target projector is a
stop-gradient EMA copy. Native quantized body/router weights remain frozen.
WP-S4 adds LeJEPA SIGReg (arXiv 2511.08544) as an alternative or companion to
the EMA target: config 'predictor_regularizer' is 'ema' (default, unchanged),
'sigreg' (online stop-gradient target, SIGReg instead of the variance floor)
or 'both' (EMA target plus SIGReg). Every update logs rank/isotropy telemetry.
This objective is not a claim that a sparse body or cross-body JEPA is complete.
"""
import json
from pathlib import Path
import sys
import time
import numpy as np
from .common import atomic_write,dumps
from .resources import device,process_memory

TAP_DIMS=(1024,2048)

def normalize(x):
    x=np.asarray(x,dtype=np.float64)
    # 2048 = B1 LFM2.5-1.2B, 1024 = B2 Qwen3.5-0.8B (WP-N11 distinct body); one predictor per body.
    if x.ndim!=2 or x.shape[1] not in TAP_DIMS or not np.isfinite(x).all():raise ValueError('Expected actual 1024/2048-dimensional native tap rows')
    return x/np.maximum(np.sqrt(np.mean(x*x,axis=1,keepdims=True)),1e-8)

SIGREG_KNOTS=np.linspace(0.,3.,17)
SIGREG_WEIGHTS=np.exp(-SIGREG_KNOTS**2/2)*np.r_[.5,np.ones(15),.5]*(SIGREG_KNOTS[1]-SIGREG_KNOTS[0])

def sigreg_directions(dim,count,seed):
    # LeJEPA resamples random unit slicing directions per step; seeded for determinism.
    a=np.random.default_rng(seed).normal(size=(dim,count));return a/np.linalg.norm(a,axis=0,keepdims=True)

def sigreg(z,directions):
    """Sliced Epps-Pulley distance of z to an isotropic standard Gaussian and dL/dz."""
    s=z@directions;n=len(s);ts=s[:,:,None]*SIGREG_KNOTS;c=np.cos(ts);sn=np.sin(ts);target=np.exp(-SIGREG_KNOTS**2/2)
    dc=c.mean(0)-target;ds=sn.mean(0);loss=float(np.mean((dc*dc+ds*ds)@SIGREG_WEIGHTS))
    m=directions.shape[1];gs=((-2*dc*sn+2*ds*c)*SIGREG_KNOTS*SIGREG_WEIGHTS).sum(2)/(n*m)
    return loss,gs@directions.T

def regularizer(cfg):
    mode=cfg.get('predictor_regularizer','ema')
    if mode not in ('ema','sigreg','both'):raise ValueError('predictor_regularizer must be ema, sigreg or both')
    return mode

def loss_gradient(x,y,p,q,target,anchor,mode='ema',directions=None,sigreg_weight=1.):
    z=x@p;future=y@target;pred=z@q;delta=pred-future;n,d=delta.shape
    mse=float(np.mean(delta*delta));dpred=2*delta/(n*d);gq=z.T@dpred;dz=dpred@q.T;parts={'prediction_mse':mse}
    if mode=='ema':
        # Variance floor and a pretrained-geometry anchor prevent trivial shrinking.
        centred=z-z.mean(0);std=np.sqrt(np.mean(centred*centred,axis=0)+1e-4);short=np.maximum(.25-std,0)
        variance=float(np.mean(short*short));dz+=.1*(-2*short/std/(n*d))*centred;reg=.1*variance;parts['variance_penalty']=variance
    else:
        # SIGReg replaces the variance floor; the online target carries no gradient.
        value,gz=sigreg(z,directions);dz+=sigreg_weight*gz;reg=sigreg_weight*value;parts['sigreg']=value
    anchor_loss=float(np.mean((p-anchor)**2));gp=x.T@dz+.02*(p-anchor)/p.size;parts['anchor_loss']=anchor_loss
    return mse+reg+.01*anchor_loss,gp,gq,parts

def collapse_telemetry(z):
    """Embedding rank and isotropy; isotropy 1 = equal covariance spectrum, 1/d = one direction."""
    centred=z-z.mean(0);ev=np.clip(np.linalg.eigvalsh(centred.T@centred/max(len(z)-1,1)),0,None);total=float(ev.sum())
    if total<=1e-12:return {'effective_rank':0,'participation_rank':0.,'isotropy':0.,'std_mean':0.}
    return {'effective_rank':int(np.sum(ev>ev.max()*1e-4)),'participation_rank':total*total/float(np.sum(ev*ev)),
            'isotropy':total*total/float(np.sum(ev*ev))/len(ev),'std_mean':float(np.sqrt(ev).mean())}

def gradient_check(x,y,p,q,target,anchor,**kw):
    _,gp,gq,_=loss_gradient(x,y,p,q,target,anchor,**kw);errors=[];eps=1e-5
    for param,gradient,name in ((p,gp,'p'),(q,gq,'q')):
        for flat in np.argsort(np.abs(gradient).ravel())[-8:]:
            ix=np.unravel_index(flat,param.shape);plus=param.copy();minus=param.copy();plus[ix]+=eps;minus[ix]-=eps
            a=loss_gradient(x,y,plus if name=='p' else p,plus if name=='q' else q,target,anchor,**kw)[0]
            b=loss_gradient(x,y,minus if name=='p' else p,minus if name=='q' else q,target,anchor,**kw)[0]
            errors.append(abs((a-b)/(2*eps)-gradient[ix]))
    return float(max(errors))

def regularizer_kwargs(cfg,dim,step):
    mode=regularizer(cfg)
    if mode=='ema':return {}
    return {'mode':mode,'directions':sigreg_directions(dim,int(cfg.get('sigreg_projections',32)),int(cfg['seed'])*100003+step),'sigreg_weight':float(cfg.get('sigreg_weight',1.))}

def optimize(x,y,p,q,target,anchor,cfg):
    p=p.copy();q=q.copy();target=target.copy();max_norm=0.;losses=[];telemetry=[];mode=regularizer(cfg)
    for step in range(cfg['predictor_steps']):
        loss,gp,gq,parts=loss_gradient(x,y,p,q,target,anchor,**regularizer_kwargs(cfg,p.shape[1],step));dp=-cfg['predictor_lr']*gp;dq=-cfg['predictor_lr']*gq
        norm=float(np.sqrt(np.sum(dp*dp)+np.sum(dq*dq)));scale=min(1.,cfg['max_update_norm']/max(norm,1e-12));p+=dp*scale;q+=dq*scale;max_norm=max(max_norm,norm*scale)
        # 'sigreg' alone uses the current online projector as stop-gradient target.
        target=p.copy() if mode=='sigreg' else cfg['ema_decay']*target+(1-cfg['ema_decay'])*p
        if step%32==0:losses.append(float(loss));telemetry.append({'step':step,**{k:v for k,v in parts.items()},**collapse_telemetry(x@p)})
    return p,q,target,{'sampled_loss':losses,'max_applied_step_norm':max_norm,'regularizer':mode,'collapse_telemetry':telemetry}

def ablation(x,y,p,q,target,anchor,cfg,modes=('ema','sigreg','both')):
    """WP-S4 ablation: identical data, start and budget; only the anti-collapse mechanism differs."""
    out={}
    for mode in modes:
        a,b,t,h=optimize(x,y,p,q,target,anchor,cfg|{'predictor_regularizer':mode})
        out[mode]={'context_embedding':collapse_telemetry(x@a),'target_embedding':collapse_telemetry(y@t),'final_sampled_loss':h['sampled_loss'][-1],
                   'prediction_mse':float(np.mean(((x@a)@b-y@t)**2)),'copy_baseline_mse':float(np.mean((x@t-y@t)**2))}
    return out

def evaluate(x,y,p,q,target,anchor):
    actual=y@target;pred=(x@p)@q;copy=x@target;shuffled=np.roll(actual,1,axis=0)
    centred=actual-actual.mean(0);sv=np.linalg.svd(centred,compute_uv=False);std=np.std(actual,axis=0);initial_std=np.std(y@anchor,axis=0)
    return {'n':len(x),'prediction_mse':float(np.mean((pred-actual)**2)),'copy_baseline_mse':float(np.mean((copy-actual)**2)),
            'shuffled_target_mse':float(np.mean((pred-shuffled)**2)),'target_std_mean':float(std.mean()),
            'target_std_ratio':float(std.mean()/max(float(initial_std.mean()),1e-12)),
            'effective_rank':int(np.sum(sv>max(float(sv.max()),1e-12)*.01)),'predicted_std_mean':float(np.std(pred,axis=0).mean()),
            'context_embedding':collapse_telemetry(x@p),'target_embedding':collapse_telemetry(actual)}

def train(inp,out):
    start=time.monotonic();cfg=inp['config'];x=normalize(inp['context_states']);y=normalize(inp['future_states']);groups=np.asarray(inp['source_groups'])
    if x.shape!=y.shape or len(groups)!=len(x) or len(set(groups))<12:raise ValueError('At least 12 distinct source sequences; same-source pairs stay together')
    order=list(dict.fromkeys(groups.tolist()));held=order[-max(3,len(order)//4):];vi=np.flatnonzero(np.isin(groups,held));ti=np.flatnonzero(~np.isin(groups,held))
    if len(ti)<12 or len(vi)<6:raise ValueError('Insufficient actual temporal pairs')
    rng=np.random.default_rng(cfg['seed']);p=np.linalg.qr(rng.normal(size=(x.shape[1],16)))[0];q=np.eye(16);target=p.copy();anchor=p.copy()
    if inp.get('active_checkpoint'):
        with np.load(inp['active_checkpoint'],allow_pickle=False) as z:p=z['projector'];q=z['predictor'];target=z['target'];anchor=z['anchor']
        if p.shape!=(x.shape[1],16) or q.shape!=(16,16) or target.shape!=p.shape or anchor.shape!=p.shape:raise ValueError('Predictor checkpoint dimensions')
    before=evaluate(x[vi],y[vi],p,q,target,anchor);err=gradient_check(x[ti],y[ti],p,q,target,anchor,**regularizer_kwargs(cfg,p.shape[1],0))
    new,nq,nt,history=optimize(x[ti],y[ti],p,q,target,anchor,cfg);repeat=optimize(x[ti],y[ti],p,q,target,anchor,cfg)
    after=evaluate(x[vi],y[vi],new,nq,nt,anchor);finite=all(np.isfinite(v).all() for v in (new,nq,nt));deterministic=all(np.array_equal(a,b) for a,b in zip((new,nq,nt),repeat[:3]))
    dest=Path(out)/'candidate.npz';np.savez(dest,projector=new,predictor=nq,target=nt,anchor=anchor,horizon=np.asarray(2))
    with np.load(dest,allow_pickle=False) as z:reload_ok=bool(np.array_equal(z['target'],nt) and np.array_equal(z['predictor'],nq))
    noncollapse=after['target_std_ratio']>=.75 and after['target_std_mean']>=.1 and after['effective_rank']>=min(4,len(vi)-1)
    predictive_gain=after['prediction_mse']<after['copy_baseline_mse']*.98 and after['prediction_mse']<after['shuffled_target_mse']*.98
    retention=after['prediction_mse']<=before['prediction_mse']*(1+cfg['retention_max_delta'])
    m={'objective':'dense-body-future-state-predictor-v1','trainable_parameter_count':int(new.size+nq.size),'target_parameter_count':int(nt.size),
       'master_precision':'float64','optimizer':'bounded_full_batch_SGD','gradient_method':'analytic','native_body_parameters_modified':0,
       'horizon_native_tokens':2,'ema_decay':cfg['ema_decay'],'regularizer':regularizer(cfg),'target_stop_gradient':True,'target_changed':bool(not np.array_equal(nt,target)),
       'train_source_groups':[g for g in order if g not in held],'held_out_source_groups':held,'train_pairs':len(ti),'held_out_pairs':len(vi),
       'before':before,'after':after,'noncollapse_pass':bool(noncollapse),'predictive_ablation_pass':bool(predictive_gain),'retention_pass':bool(retention),
       'finite_difference_max_error':err,'gradient_check':err<1e-5,'deterministic_repeat':bool(deterministic),'checkpoint_reload':reload_ok,'finite':bool(finite),
       'master_weight_bytes':int(new.nbytes+nq.nbytes),'ema_target_bytes':int(nt.nbytes),'activation_input_bytes':int(x.nbytes+y.nbytes),'optimizer_steps':cfg['predictor_steps'],
       'history':history,'duration_s':time.monotonic()-start,'process_memory':process_memory(),'device':device(),
       'semantic_quality_proven':False,'receiver_authority':0,'commit_eligible':bool(noncollapse and predictive_gain and retention and finite and deterministic and reload_ok and err<1e-5)}
    m.update(effective_learning_rate=cfg['predictor_lr'],effective_max_update_norm=cfg['max_update_norm'])
    atomic_write(Path(out)/'metrics.json',dumps(m));return m

def predict(states,checkpoint):
    x=normalize(states)
    with np.load(checkpoint,allow_pickle=False) as z:p=z['projector'];q=z['predictor'];target=z['target'];horizon=int(z['horizon'])
    pred=x@p@q;actual=x@target;errors=np.mean((pred[:-horizon]-actual[horizon:])**2,axis=1) if len(x)>horizon else np.array([])
    return {'horizon_native_tokens':horizon,'future_latent_prediction':pred[-1].tolist(),'observed_pair_count':len(errors),
            'retrospective_mse':float(errors.mean()) if len(errors) else None,'future_observed':False,'authority':'LOCAL_PREDICTION_HYPOTHESIS','receiver_injection':False}

if __name__=='__main__':train(json.loads(Path(sys.argv[1]).read_text()),sys.argv[2])
