"""A3 text port: learned raw-byte projection; frozen measured semantic targets.

Hashing is a deterministic raw stem, not a pretrained semantic representation.
Alignment and reconstruction have distinct targets/ablations. No native body,
router, teacher or receiver weights are modified by this worker.
"""
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
from .common import atomic_write,dumps
from .resources import device,process_memory

RAW_DIM=512
LATENT_DIM=16
TEACHER_DIM=3072
STEM='utf8-signed-byte-ngrams-1-3-v1'

def raw_features(text):
    data=text.encode('utf-8')
    if not data or len(data)>4096:raise ValueError('A3 text observation requires 1..4096 UTF-8 bytes')
    v=np.zeros(RAW_DIM,dtype=np.float64)
    for width in (1,2,3):
        for i in range(len(data)-width+1):
            h=int.from_bytes(hashlib.blake2b(data[i:i+width],digest_size=8,person=b'V13-A3-raw-v1').digest(),'little')
            v[h%RAW_DIM]+=1. if h>>63 else -1.
    return v/max(float(np.linalg.norm(v)),1e-12)

def split(groups):
    if len(set(groups))!=len(groups) or len(groups)<32:raise ValueError('A3 needs 32 distinct immutable sources, no duplicate raw/teacher pairs')
    mask=np.array([int(hashlib.sha256(g.encode()).hexdigest()[:8],16)%4==0 for g in groups])
    ti=np.flatnonzero(~mask);vi=np.flatnonzero(mask)
    if len(ti)<20 or len(vi)<6:raise ValueError('A3 source split needs 20 training and six held-out sources')
    return ti,vi

def objective(x,t,p,r,alignment=1.,reconstruction=.1):
    z=x@p;dt=z-t;dr=z@r-x
    la=float(np.mean(dt*dt));lr=float(np.mean(dr*dr));reg=float(np.mean(p*p))
    dz=alignment*2*dt/dt.size+reconstruction*2*dr@r.T/dr.size
    return alignment*la+reconstruction*lr+1e-4*reg,x.T@dz+2e-4*p/p.size,reconstruction*2*z.T@dr/dr.size,{'alignment':la,'reconstruction':lr,'regularization':reg}

def optimize(x,t,p,r,cfg,alignment=1.,reconstruction=.1):
    p=p.copy();r=r.copy();history=[];max_norm=0.
    for step in range(cfg['student_steps']):
        loss,gp,gr,_=objective(x,t,p,r,alignment,reconstruction)
        # Per-dimension MSE otherwise makes the 512-feature decoder update 32x
        # smaller than the 16-feature alignment update. Compensate that known
        # scale, then enforce the same combined parameter-step norm ceiling.
        dp=-cfg['student_lr']*gp;dr=-cfg['student_lr']*gr*(RAW_DIM/LATENT_DIM);norm=float(np.sqrt(np.sum(dp*dp)+np.sum(dr*dr)))
        scale=min(1.,cfg['max_update_norm']/max(norm,1e-12));p+=dp*scale;r+=dr*scale;max_norm=max(max_norm,norm*scale)
        if step%64==0:history.append(float(loss))
    return p,r,{'sampled_loss':history,'max_applied_step_norm':max_norm}

def gradient_check(x,t,p,r):
    _,gp,gr,_=objective(x,t,p,r);errors=[];eps=1e-5
    for a,g,name in ((p,gp,'p'),(r,gr,'r')):
        for flat in np.argsort(np.abs(g).ravel())[-6:]:
            ix=np.unravel_index(flat,a.shape);plus=a.copy();minus=a.copy();plus[ix]+=eps;minus[ix]-=eps
            f=objective(x,t,plus if name=='p' else p,plus if name=='r' else r)[0]
            b=objective(x,t,minus if name=='p' else p,minus if name=='r' else r)[0]
            errors.append(abs((f-b)/(2*eps)-g[ix]))
    return float(max(errors))

def evaluate(x,y,p,r,basis,mean):
    z=x@p;pred=z@basis+mean;rec=z@r
    norm=np.linalg.norm(pred,axis=1)*np.linalg.norm(y,axis=1)
    sv=np.linalg.svd(pred-pred.mean(0),compute_uv=False)
    return {'teacher_mse':float(np.mean((pred-y)**2)),'reconstruction_mse':float(np.mean((rec-x)**2)),
            'teacher_cosine_mean':float(np.mean(np.sum(pred*y,axis=1)/np.maximum(norm,1e-12))),
            'teacher_variance_ratio':float(np.std(pred,axis=0).mean()/max(float(np.std(y,axis=0).mean()),1e-12)),
            'effective_rank':int(np.sum(sv>max(float(sv.max()),1e-12)*.01))}

def train(inp,out):
    start=time.monotonic();cfg=inp['config'];groups=inp['source_groups'];ti,vi=split(groups)
    raw=np.stack([raw_features(t) for t in inp['texts']]);y=np.asarray(inp['teacher_embeddings'],dtype=np.float64)
    if y.shape!=(len(raw),TEACHER_DIM) or not np.isfinite(y).all():raise ValueError('A3 requires actual finite 3072-dimensional teacher embeddings')
    yn=np.linalg.norm(y,axis=1,keepdims=True)
    if np.any(yn<1e-8):raise ValueError('Zero teacher observation')
    y=y/yn*np.sqrt(TEACHER_DIM)
    input_mean=raw[ti].mean(0);mean=y[ti].mean(0)
    _,_,b=np.linalg.svd(y[ti]-mean,full_matrices=False);basis=b[:LATENT_DIM]
    x=(raw-input_mean)*np.sqrt(RAW_DIM)
    _,_,rb=np.linalg.svd(x[ti],full_matrices=False);p0=np.zeros((RAW_DIM,LATENT_DIM));r0=rb[:LATENT_DIM]
    if inp.get('active_checkpoint'):
        with np.load(inp['active_checkpoint'],allow_pickle=False) as a:
            p0=a['projector'];r0=a['reconstruction_decoder'];input_mean=a['input_mean'];mean=a['teacher_mean'];basis=a['teacher_basis']
        if p0.shape!=(RAW_DIM,LATENT_DIM) or r0.shape!=(LATENT_DIM,RAW_DIM) or basis.shape!=(LATENT_DIM,TEACHER_DIM):raise ValueError('A3 checkpoint dimensions')
        x=(raw-input_mean)*np.sqrt(RAW_DIM)
    t=(y-mean)@basis.T;before=evaluate(x[vi],y[vi],p0,r0,basis,mean)
    err=gradient_check(x[ti],t[ti],p0,r0)
    p,r,history=optimize(x[ti],t[ti],p0,r0,cfg)
    p2,r2,_=optimize(x[ti],t[ti],p0,r0,cfg)
    # Same initializer and partitions: a disabled term cannot fit its target.
    pa,ra,_=optimize(x[ti],t[ti],p0,r0,cfg,alignment=0.)
    pr,rr,_=optimize(x[ti],t[ti],p0,r0,cfg,reconstruction=0.)
    after=evaluate(x[vi],y[vi],p,r,basis,mean)
    no_alignment=evaluate(x[vi],y[vi],pa,ra,basis,mean);no_reconstruction=evaluate(x[vi],y[vi],pr,rr,basis,mean)
    baseline={'teacher_mse':float(np.mean((mean-y[vi])**2)),'reconstruction_mse':float(np.mean(x[vi]**2))}
    support_floor=float(np.min(np.max(raw[vi]@raw[ti].T,axis=1))-.02)
    support_floor=max(.5,min(.99,support_floor))
    path=Path(out)/'candidate.npz';np.savez(path,projector=p,reconstruction_decoder=r,teacher_basis=basis,teacher_mean=mean,input_mean=input_mean,support=raw[ti],support_floor=support_floor,stem=np.array(STEM))
    with np.load(path,allow_pickle=False) as a:reload_ok=np.array_equal(a['projector'],p) and np.array_equal(a['reconstruction_decoder'],r)
    finite=all(np.isfinite(v).all() for v in (p,r,basis,mean));repeat=np.array_equal(p,p2) and np.array_equal(r,r2)
    observed_variance=float(np.std(y[vi],axis=0).mean())
    noncollapse=observed_variance>=1e-4 and after['teacher_variance_ratio']>=.5 and after['effective_rank']>=min(4,len(vi)-1)
    align_gain=after['teacher_mse']<baseline['teacher_mse']*.98 and after['teacher_cosine_mean']>=.95
    rec_gain=after['reconstruction_mse']<baseline['reconstruction_mse']*.98
    ablation=after['teacher_mse']<no_alignment['teacher_mse']*.98 and after['reconstruction_mse']<no_reconstruction['reconstruction_mse']*.98
    retention=not inp.get('active_checkpoint') or all(after[k]<=before[k]*(1+cfg['retention_max_delta']) for k in ('teacher_mse','reconstruction_mse'))
    m={'objective':'a3-text-teacher-alignment-reconstruction-v1','trainable_parameter_count':int(p.size+r.size),'teacher_parameter_updates':0,'native_body_parameters_modified':0,
       'raw_stem':STEM,'raw_dim':RAW_DIM,'latent_dim':LATENT_DIM,'teacher_dim':TEACHER_DIM,'train_sources':len(ti),'held_out_sources':len(vi),'observed_target_std_mean':observed_variance,'reconstruction_preconditioner':RAW_DIM/LATENT_DIM,
       'train_source_groups':[groups[i] for i in ti],'held_out_source_groups':[groups[i] for i in vi],'before':before,'after':after,'mean_baseline':baseline,
       'alignment_off':no_alignment,'reconstruction_off':no_reconstruction,'alignment_gain':bool(align_gain),'reconstruction_gain':bool(rec_gain),'separate_ablation_pass':bool(ablation),
       'noncollapse_pass':bool(noncollapse),'retention_pass':bool(retention),'support_floor':support_floor,'finite':bool(finite),'gradient_check':err<1e-5,
       'finite_difference_max_error':err,'deterministic_repeat':bool(repeat),'checkpoint_reload':bool(reload_ok),'optimizer_steps':cfg['student_steps'],'history':history,
       'device':device(),'process_memory':process_memory(),'duration_s':time.monotonic()-start,'teacher_truth_authority':False,'native_receiver_authority':0,
       'commit_eligible':bool(align_gain and rec_gain and ablation and noncollapse and retention and finite and repeat and reload_ok and err<1e-5)}
    m.update(effective_learning_rate=cfg['student_lr'],effective_max_update_norm=cfg['max_update_norm'])
    atomic_write(Path(out)/'metrics.json',dumps(m));return m

def infer(text,checkpoint):
    raw=raw_features(text)
    with np.load(checkpoint,allow_pickle=False) as a:
        if str(a['stem'])!=STEM:raise ValueError('A3 stem changed')
        latent=(raw-a['input_mean'])*np.sqrt(RAW_DIM)@a['projector'];teacher=latent@a['teacher_basis']+a['teacher_mean']
        support=float(np.max(a['support']@raw));floor=float(a['support_floor'])
    if not np.isfinite(latent).all() or not np.isfinite(teacher).all():raise ValueError('Nonfinite A3 inference')
    teacher=teacher/max(float(np.linalg.norm(teacher)),1e-12)
    return {'latent':latent.tolist(),'teacher_feature_prediction':teacher.tolist(),'support_cosine':support,'support_floor':floor,'in_support':support>=floor,'raw_stem':STEM,'teacher_truth_authority':False,'receiver_injection':False}

if __name__=='__main__':train(json.loads(Path(sys.argv[1]).read_text()),sys.argv[2])
