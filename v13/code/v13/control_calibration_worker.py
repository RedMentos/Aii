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
    if not isinstance(validation,dict) or validation.get('negation') or validation.get('ungrounded'):raise ValueError('Native control validation failed')
    confidence=control.get('confidence')
    if isinstance(confidence,bool) or not isinstance(confidence,(int,float)) or not np.isfinite(confidence) or not 0<=confidence<=1:raise ValueError('Actual finite native confidence required')
    calls=control.get('function_calls',[]);routes=[]
    if not isinstance(calls,list):raise ValueError('Native function calls malformed')
    for call in calls:
        if not isinstance(call,dict):continue
        args=call.get('arguments',{}) if isinstance(call,dict) else {}
        if isinstance(args,str):
            try:args=json.loads(args)
            except ValueError:continue
        if call.get('name')=='select_processing' and isinstance(args,dict) and args.get('route') in ROUTES:routes.append(args['route'])
    if not routes:raise ValueError('Validated native route proposal required')
    # The existing runtime's native advisory selects the first proposal. Score
    # exactly that decision; do not substitute a later, label-matching call.
    return {'route':routes[0],'raw_confidence':float(confidence),'proposal_count':len(routes),'ambiguous':len(set(routes))>1}

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
    for _ in range(cfg['calibration_steps']):
        _,g=loss_gradient(x,y,w);step=-cfg['calibration_lr']*g;norm=float(np.linalg.norm(step));scale=min(1.,cfg['max_update_norm']/max(norm,1e-12));w+=step*scale;max_norm=max(max_norm,norm*scale)
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
    w=np.zeros(6);old_temperature=1.;old_x=np.empty((0,6));old_y=np.empty(0);old_ids=[];old_ranges=None;old_counts=None
    if inp.get('active_checkpoint'):
        with np.load(inp['active_checkpoint'],allow_pickle=False) as a:
            w=a['weights'];old_temperature=float(a['temperature']);old_ranges=a['confidence_ranges'];old_counts=a['route_counts']
            # Existing v1 heads remain usable for inference. A shadow replacement
            # must carry its original held-out cases; do not invent lost targets.
            if not {'retention_x','retention_y','retention_ids'}<=set(a.files):raise ValueError('Active calibration lacks fixed old-case retention; explicit revalidation required')
            old_x=a['retention_x'];old_y=a['retention_y'];old_ids=a['retention_ids'].tolist()
        if w.shape!=(6,) or not np.isfinite(w).all():raise ValueError('Calibration checkpoint malformed')
        if old_x.shape!=(len(old_y),6) or len(old_ids)!=len(old_y) or len(set(old_ids))!=len(old_ids) or not np.isfinite(old_x).all() or not np.isin(old_y,[0,1]).all():raise ValueError('Calibration retained cases malformed')
    err=gradient_check(x[ti],y[ti],w);new,max_norm=optimize(x[ti],y[ti],w,cfg);repeat,_=optimize(x[ti],y[ti],w,cfg)
    temperature=float(min(np.exp(np.linspace(np.log(.2),np.log(5.),65)),key=lambda t:scores(probabilities(x[ci]@new,t),y[ci])['loss']))
    before=scores(probabilities(x[vi]@w,old_temperature),y[vi]);after=scores(probabilities(x[vi]@new,temperature),y[vi]);native=scores(np.asarray([r['raw_confidence'] for r in rows])[vi],y[vi])
    ranges=np.zeros((4,2));counts=np.zeros(4,dtype=int)
    for k,role in enumerate(ROUTES):
        vals=[rows[i]['raw_confidence'] for i in ti if rows[i]['route']==role];counts[k]=len(vals)
        if vals:ranges[k]=[min(vals),max(vals)]
    if old_ranges is not None:
        if old_ranges.shape!=(4,2) or old_counts.shape!=(4,) or not np.isfinite(old_ranges).all():raise ValueError('Calibration support malformed')
        for k in range(4):
            if old_counts[k]>0:
                ranges[k]=[min(ranges[k,0],old_ranges[k,0]),max(ranges[k,1],old_ranges[k,1])] if counts[k] else old_ranges[k]
            # Do not count repeated source observations as independent evidence.
            counts[k]=max(counts[k],old_counts[k])
    supported=all(counts[ROUTES.index(rows[i]['route'])]>=3 and ranges[ROUTES.index(rows[i]['route']),0]-.05<=rows[i]['raw_confidence']<=ranges[ROUTES.index(rows[i]['route']),1]+.05 for i in vi)
    retained_test={'n':len(old_y),'pass':True,'per_route':{}}
    if len(old_y):
        old_before=scores(probabilities(old_x@w,old_temperature),old_y);old_after=scores(probabilities(old_x@new,temperature),old_y)
        retained_test.update(before=old_before,after=old_after)
        for k,role in enumerate(ROUTES):
            ids=np.flatnonzero(old_x[:,2+k]==1.)
            if not len(ids):continue
            a=scores(probabilities(old_x[ids]@w,old_temperature),old_y[ids]);b=scores(probabilities(old_x[ids]@new,temperature),old_y[ids])
            ok=b['brier']<=a['brier']+cfg['retention_max_delta'] and b['loss']<=a['loss']+cfg['retention_max_delta']
            retained_test['per_route'][role]={'before':a,'after':b,'pass':ok}
        retained_test['pass']=all(v['pass'] for v in retained_test['per_route'].values()) and old_after['brier']<=old_before['brier']+cfg['retention_max_delta'] and old_after['loss']<=old_before['loss']+cfg['retention_max_delta']
    retained=after['brier']<=before['brier']+cfg['retention_max_delta'] and retained_test['pass'];improved=after['brier']<=native['brier']-.02 and after['loss']<native['loss'] and after['ece']<=.2
    retained_cases={key:(vec,label) for key,vec,label in zip(old_ids,old_x,old_y)}
    for i in vi:
        key=hashlib.sha256(dumps([groups[i],rows[i],float(y[i])]).encode()).hexdigest();retained_cases.setdefault(key,(x[i],y[i]))
    if len(retained_cases)>2048:raise ValueError('Fixed calibration retention capacity reached; old cases cannot be dropped')
    case_ids=sorted(retained_cases);rx=np.asarray([retained_cases[k][0] for k in case_ids]);ry=np.asarray([retained_cases[k][1] for k in case_ids])
    path=Path(out)/'candidate.npz';np.savez(path,weights=new,temperature=np.asarray(temperature),confidence_ranges=ranges,route_counts=counts,format=np.asarray('native-route-calibration-v1'),retention_x=rx,retention_y=ry,retention_ids=np.asarray(case_ids))
    with np.load(path,allow_pickle=False) as a:reload_ok=np.array_equal(a['weights'],new) and np.array_equal(a['confidence_ranges'],ranges) and np.array_equal(a['retention_x'],rx) and np.array_equal(a['retention_y'],ry)
    repeat_ok=np.array_equal(new,repeat);finite=bool(np.isfinite(new).all());eligible=bool(improved and retained and supported and repeat_ok and finite and reload_ok and err<1e-6)
    m={'objective':'native-route-confidence-calibration-v1','trainable_parameter_count':7,'native_body_parameters_modified':0,'calibration_scope':'HELD_OUT_NATIVE_ROUTE_AGREEMENT_ONLY','partition':{'train':ti.tolist(),'calibration':ci.tolist(),'test':vi.tolist()},
       'source_groups':groups,'native_baseline':native,'before':before,'after':after,'temperature':temperature,'optimizer_steps':cfg['calibration_steps'],'max_applied_step_norm':max_norm,
       'finite_difference_max_error':err,'gradient_check':err<1e-6,'finite':finite,'deterministic_repeat':bool(repeat_ok),'checkpoint_reload':bool(reload_ok),'calibration_pass':bool(improved),'retention_pass':bool(retained),'held_out_support_pass':bool(supported),
       'retained_test':retained_test,'retained_cases_saved':len(case_ids),'retained_support_preserved':old_ranges is None or bool(np.all(counts>=old_counts) and all(not old_counts[k] or (ranges[k,0]<=old_ranges[k,0] and ranges[k,1]>=old_ranges[k,1]) for k in range(4))),
       'semantic_truth_authority':False,'commit_eligible':eligible,'duration_s':time.monotonic()-start,'device':device(),'process_memory':process_memory()}
    m.update(effective_learning_rate=cfg['calibration_lr'],effective_max_update_norm=cfg['max_update_norm'])
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
