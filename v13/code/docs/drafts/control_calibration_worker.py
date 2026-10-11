"""External calibration of actual native route confidence against human labels.

Correctness here means route agreement, never semantic truth or task success.
The native encoder/control head stays frozen. Source-stable fit/calibration/test
partitions, measured raw-confidence coverage and explicit activation are required.
"""
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
from .common import atomic_write,dumps
from .resources import device,process_memory

ROUTES=('simple','detail','gist','both')

def observation(control):
    if not isinstance(control,dict) or control.get('success') is not True:raise ValueError('Successful actual native control required')
    validation=control.get('validation',{})
    if validation.get('negation') or validation.get('ungrounded'):raise ValueError('Native control validation failed')
    confidence=control.get('confidence')
    if isinstance(confidence,bool) or not isinstance(confidence,(int,float)) or not np.isfinite(confidence) or not 0<=confidence<=1:raise ValueError('Actual finite native confidence required')
    calls=control.get('function_calls',[]);routes=[]
    for call in calls:
        args=call.get('arguments',{}) if isinstance(call,dict) else {}
        if isinstance(args,str):
            try:args=json.loads(args)
            except ValueError:continue
        if call.get('name')=='select_processing' and isinstance(args,dict) and args.get('route') in ROUTES:routes.append(args['route'])
    if len(routes)!=1:raise ValueError('Exactly one validated native route proposal required')
    return {'route':routes[0],'raw_confidence':float(confidence)}

def features(rows):
    result=np.zeros((len(rows),6));result[:,0]=1.
    for i,row in enumerate(rows):
        c=row['raw_confidence'];route=row['route']
        if route not in ROUTES or isinstance(c,bool) or not isinstance(c,(int,float)) or not np.isfinite(c) or not 0<=c<=1:raise ValueError('Calibration observation malformed')
        c=float(np.clip(c,1e-4,1-1e-4));result[i,1]=np.log(c/(1-c))/8;result[i,2+ROUTES.index(route)]=1.
    return result

def probabilities(logits,temperature=1.):return 1/(1+np.exp(-np.clip(logits/temperature,-60,60)))

def loss_gradient(x,y,w):
    logits=x@w;p=probabilities(logits)
    return float(np.mean(np.logaddexp(0,logits)-y*logits)+1e-4*np.sum(w*w)),x.T@(p-y)/len(y)+2e-4*w

def gradient_check(x,y,w):
    _,g=loss_gradient(x,y,w);errors=[];eps=1e-5
    for i in range(len(w)):
        a=w.copy();b=w.copy();a[i]+=eps;b[i]-=eps;errors.append(abs((loss_gradient(x,y,a)[0]-loss_gradient(x,y,b)[0])/(2*eps)-g[i]))
    return float(max(errors))

def optimize(x,y,w,cfg):
    w=w.copy();max_norm=0.
    for _ in range(cfg['readout_steps']):
        _,g=loss_gradient(x,y,w);step=-cfg['learning_rate']*g;norm=float(np.linalg.norm(step));scale=min(1.,cfg['max_update_norm']/max(norm,1e-12));w+=step*scale;max_norm=max(max_norm,norm*scale)
    return w,max_norm

def scores(p,y):
    p=np.clip(p,1e-8,1-1e-8);ece=0.
    for lo in (0.,.2,.4,.6,.8):
        mask=(p>=lo)&(p<(lo+.2) if lo<.8 else p<=1.)
        if mask.any():ece+=float(mask.mean())*abs(float(p[mask].mean()-y[mask].mean()))
    return {'n':len(y),'brier':float(np.mean((p-y)**2)),'loss':float(-np.mean(y*np.log(p)+(1-y)*np.log(1-p))),'ece':ece,'correct_rate':float(y.mean()),'mean_confidence':float(p.mean())}

def train(inp,out):
    start=time.monotonic();cfg=inp['config'];rows=inp['observations'];groups=inp['source_groups'];y=np.asarray(inp['correct_labels'],dtype=float);x=features(rows)
    if len(groups)!=len(x) or len(set(groups))!=len(groups) or y.shape!=(len(x),) or not np.isin(y,[0,1]).all():raise ValueError('Unique actual source observations with binary route agreement labels required')
    fold=np.array([int(hashlib.sha256(g.encode()).hexdigest()[:8],16)%5 for g in groups]);ti=np.flatnonzero(fold>=2);ci=np.flatnonzero(fold==1);vi=np.flatnonzero(fold==0)
    for ids in (ti,ci,vi):
        if len(ids)<6 or min(int((y[ids]==0).sum()),int((y[ids]==1).sum()))<2:raise ValueError('Fit/calibration/test each require six sources and two correct/two incorrect native proposals')
    w=np.zeros(6);old_temperature=1.
    if inp.get('active_checkpoint'):
        with np.load(inp['active_checkpoint'],allow_pickle=False) as a:w=a['weights'];old_temperature=float(a['temperature'])
        if w.shape!=(6,) or not np.isfinite(w).all():raise ValueError('Calibration checkpoint malformed')
    err=gradient_check(x[ti],y[ti],w);new,max_norm=optimize(x[ti],y[ti],w,cfg);repeat,_=optimize(x[ti],y[ti],w,cfg)
    temperature=float(min(np.exp(np.linspace(np.log(.2),np.log(5.),65)),key=lambda t:scores(probabilities(x[ci]@new,t),y[ci])['loss']))
    before=scores(probabilities(x[vi]@w,old_temperature),y[vi]);after=scores(probabilities(x[vi]@new,temperature),y[vi]);native=scores(np.asarray([r['raw_confidence'] for r in rows])[vi],y[vi])
    ranges=np.zeros((4,2));counts=np.zeros(4,dtype=int)
    for k,role in enumerate(ROUTES):
        vals=[rows[i]['raw_confidence'] for i in ti if rows[i]['route']==role];counts[k]=len(vals)
        if vals:ranges[k]=[min(vals),max(vals)]
    supported=all(counts[ROUTES.index(rows[i]['route'])]>=3 and ranges[ROUTES.index(rows[i]['route']),0]-.05<=rows[i]['raw_confidence']<=ranges[ROUTES.index(rows[i]['route']),1]+.05 for i in vi)
    retained=after['brier']<=before['brier']+cfg['retention_max_delta'];improved=after['brier']<=native['brier']-.02 and after['loss']<native['loss'] and after['ece']<=.2
    path=Path(out)/'candidate.npz';np.savez(path,weights=new,temperature=np.asarray(temperature),confidence_ranges=ranges,route_counts=counts,format=np.asarray('native-route-calibration-v1'))
    with np.load(path,allow_pickle=False) as a:reload_ok=np.array_equal(a['weights'],new) and np.array_equal(a['confidence_ranges'],ranges)
    repeat_ok=np.array_equal(new,repeat);finite=bool(np.isfinite(new).all());eligible=bool(improved and retained and supported and repeat_ok and finite and reload_ok and err<1e-6)
    m={'objective':'native-route-confidence-calibration-v1','trainable_parameter_count':7,'native_body_parameters_modified':0,'calibration_scope':'HELD_OUT_NATIVE_ROUTE_AGREEMENT_ONLY','partition':{'train':ti.tolist(),'calibration':ci.tolist(),'test':vi.tolist()},
       'source_groups':groups,'native_baseline':native,'before':before,'after':after,'temperature':temperature,'optimizer_steps':cfg['readout_steps'],'max_applied_step_norm':max_norm,
       'finite_difference_max_error':err,'gradient_check':err<1e-6,'finite':finite,'deterministic_repeat':bool(repeat_ok),'checkpoint_reload':bool(reload_ok),'calibration_pass':bool(improved),'retention_pass':bool(retained),'held_out_support_pass':bool(supported),
       'semantic_truth_authority':False,'commit_eligible':eligible,'duration_s':time.monotonic()-start,'device':device(),'process_memory':process_memory()}
    atomic_write(Path(out)/'metrics.json',dumps(m));return m

def infer(control,checkpoint):
    row=observation(control);x=features([row]);k=ROUTES.index(row['route'])
    with np.load(checkpoint,allow_pickle=False) as a:
        if str(a['format'])!='native-route-calibration-v1':raise ValueError('Calibration format')
        w=a['weights'];temperature=float(a['temperature']);bounds=a['confidence_ranges'][k];count=int(a['route_counts'][k])
        if w.shape!=(6,) or not np.isfinite(w).all() or not .2<=temperature<=5:raise ValueError('Calibration artifact invalid')
        in_support=bool(count>=3 and bounds[0]-.05<=row['raw_confidence']<=bounds[1]+.05)
        probability=float(probabilities(x@w,temperature)[0])
    return row|{'calibrated_confidence':probability if in_support else None,'in_support':in_support,'route_observation_count':count,'calibration_scope':'HELD_OUT_NATIVE_ROUTE_AGREEMENT_ONLY','semantic_truth_authority':False}

if __name__=='__main__':train(json.loads(Path(sys.argv[1]).read_text()),sys.argv[2])
