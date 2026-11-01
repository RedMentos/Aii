"""Small supervised JEF readouts on frozen native embeddings.

The three disjoint partitions have different jobs: weight fitting, temperature
fitting, and untouched evaluation. Labels describe bounded observer/re-entry
decisions, not truth or general reasoning quality. No native body is trained.
"""
import json
from pathlib import Path
import sys
import time
import numpy as np
from .common import atomic_write,dumps
from .learning_worker import features,objective,gradient_check,optimize
from .resources import device,process_memory

LABELS={'wake':('none','detail','gist','both'),'halt':('halt','continue'),
        'skill':('none','skill'),'memory':('skip','recall','deep'),'channel':('NO_MESSAGE','SOURCE_EXACT','CONTROL','SYMBOLIC')}  # = learning.POLICY_LABELS
COSTS={'wake':(0,1,1,2),'skill':(1,0),'memory':(0,1,2),'channel':(0,1,1,1)}  # bounded compute cost per action; halt: action index
EXPLICIT=('wake','skill','memory','channel')  # explicit operator labels, no universal utility claim

def probabilities(logits,temperature=1.):
    a=np.asarray(logits,dtype=np.float64)/float(temperature);a=a-a.max(axis=1,keepdims=True)
    p=np.exp(a);return p/p.sum(axis=1,keepdims=True)

def scores(p,y):
    pred=p.argmax(1);confidence=p.max(1);correct=pred==y;ece=0.
    for lo in np.linspace(0,1,6)[:-1]:
        mask=(confidence>=lo)&(confidence<(lo+.2) if lo<.79 else confidence<=1)
        if mask.any():ece+=float(mask.mean())*abs(float(confidence[mask].mean())-float(correct[mask].mean()))
    return {'n':len(y),'loss':float(-np.log(np.maximum(p[np.arange(len(y)),y],1e-30)).mean()),
            'accuracy':float(correct.mean()),'brier':float(np.square(p-np.eye(p.shape[1])[y]).sum(1).mean()),'ece':ece}

def partitions(y,classes):
    train=[];cal=[];test=[]
    for k in range(classes):
        ids=np.flatnonzero(y==k).tolist()
        if len(ids)<6:raise ValueError('Mindestens sechs verschiedene gelabelte Kontexte je Klasse erforderlich')
        n=max(1,len(ids)//6);train+=ids[:-3*n];cal+=ids[-3*n:-n];test+=ids[-n:]
    return tuple(np.asarray(v,dtype=int) for v in (train,cal,test))

def infer(embedding,checkpoint):
    x=features([embedding])
    with np.load(checkpoint,allow_pickle=False) as z:
        w=z['weights'];temperature=float(z['temperature']);centres=z['support_centres'];floor=float(z['support_floor'])
        if w.shape[0]!=x.shape[1] or not np.isfinite(w).all() or not .2<=temperature<=5:raise ValueError('Readout-Artefakt ungültig')
        p=probabilities(x@w,temperature)[0]
        support=float((x[:,:-1]/8. @ centres.T).max())
    order=np.argsort(p);return {'index':int(order[-1]),'probabilities':p.tolist(),'margin':float(p[order[-1]]-p[order[-2]]),
                               'confidence':float(p.max()),'support_cosine':support,'support_floor':floor,
                               'in_support':bool(support>=floor),'temperature':temperature,'calibration_scope':'held_out_bounded_readout'}

def train(inp,out):
    started=time.monotonic();component=inp['component'];classes=len(LABELS[component]);cfg=dict(inp['config']);cfg['learning_steps']=cfg.get('readout_steps',240)
    x=features(inp['embeddings']);y=np.asarray(inp['labels'],dtype=int);baseline=np.asarray(inp['scaffold_labels'],dtype=int)
    if y.shape!=(len(x),) or baseline.shape!=y.shape or not np.isin(y,range(classes)).all() or not np.isin(baseline,range(classes)).all():raise ValueError('Ungültige Readout-Labels')
    if len(set(inp['context_hashes']))!=len(y):raise ValueError('Doppelte Kontexte würden Holdout verunreinigen')
    ti,ci,vi=partitions(y,classes);w=np.zeros((x.shape[1],classes));trace=np.zeros(x.shape[1]);old_temperature=1.
    if inp.get('active_checkpoint'):
        with np.load(inp['active_checkpoint'],allow_pickle=False) as z:w=z['weights'];trace=z['eligibility'];old_temperature=float(z['temperature'])
        if w.shape!=(x.shape[1],classes) or trace.shape!=(x.shape[1],):raise ValueError('Checkpoint-Dimension')
    err=gradient_check(x[ti],y[ti],w);stats={};new,tr=optimize(x[ti],y[ti],w,trace,cfg,stats);repeat,_=optimize(x[ti],y[ti],w,trace,cfg)
    # A bounded one-parameter calibration fit, never optimized on test rows.
    temperatures=np.exp(np.linspace(np.log(.2),np.log(5.),65))
    temperature=float(min(temperatures,key=lambda t:scores(probabilities(x[ci]@new,t),y[ci])['loss']))
    oldp=probabilities(x[vi]@w,old_temperature);raw=probabilities(x[vi]@new);p=probabilities(x[vi]@new,temperature)
    before=scores(oldp,y[vi]);after=scores(p,y[vi]);uncal=scores(raw,y[vi]);per_class={}
    for k in range(classes):
        mask=y[vi]==k;per_class[str(k)]={'n':int(mask.sum()),'before':float((oldp.argmax(1)[mask]==k).mean()),'after':float((p.argmax(1)[mask]==k).mean())}
    unit=x[:,:-1]/8.;centres=np.stack([unit[ti][y[ti]==k].mean(0) for k in range(classes)])
    centres/=np.maximum(np.linalg.norm(centres,axis=1,keepdims=True),1e-12)
    support_floor=max(.55,float((unit[ci]@centres.T).max(1).min())-.05)
    confidence=p.max(1);ordered=np.sort(p,axis=1);accepted=(confidence>=.6)&((ordered[:,-1]-ordered[:,-2])>=.1)&((unit[vi]@centres.T).max(1)>=support_floor)
    predicted=p.argmax(1);effective=np.where(accepted,predicted,baseline[vi]);baseline_accuracy=float((baseline[vi]==y[vi]).mean());effective_accuracy=float((effective==y[vi]).mean())
    def cost(actions):
        return np.asarray(COSTS[component])[actions] if component in COSTS else actions
    cost_before=float(cost(baseline[vi]).mean());cost_after=float(cost(effective).mean())
    # No early exit on any held-out label requiring another pass.
    missed_continue=int(((effective==0)&(y[vi]==1)).sum()) if component=='halt' else None
    pareto=effective_accuracy>=baseline_accuracy and cost_after<=cost_before and (effective_accuracy>baseline_accuracy or cost_after<cost_before)
    if component in EXPLICIT:pareto=effective_accuracy>=baseline_accuracy  # explicit labels, no universal utility claim
    calibrated=after['loss']<=uncal['loss']+1e-8 and after['brier']<=uncal['brier']+1e-8 and after['ece']<=.2
    finite=bool(np.isfinite(new).all());deterministic=bool(np.array_equal(new,repeat))
    dest=Path(out)/'candidate.npz';np.savez(dest,weights=new,eligibility=tr,temperature=np.asarray(temperature),support_centres=centres,support_floor=np.asarray(support_floor))
    with np.load(dest,allow_pickle=False) as z:reload_ok=bool(np.array_equal(z['weights'],new))
    retained=all(v['after']>=v['before']-cfg['retention_max_delta'] for v in per_class.values())
    eligible=(after['accuracy']>=.75 and after['loss']<before['loss'] and retained
              and calibrated and pareto and bool(accepted.any()) and missed_continue in (None,0) and finite and deterministic and reload_ok and err<1e-6)
    metrics={'objective':'explicit-human-'+component+'-readout-v1','component':component,'n':len(y),'embedding_dim':x.shape[1]-1,
             'trainable_parameter_count':int(new.size+1),'optimizer_steps':cfg['learning_steps'],'loss_before':objective(x,y,w)[0],'loss_after':objective(x,y,new)[0],
             'partition':{'train':ti.tolist(),'calibration':ci.tolist(),'test':vi.tolist()},'held_out':{'before':before,'after':after,'uncalibrated':uncal,'per_class':per_class},
             'temperature':temperature,'calibration_pass':bool(calibrated),'effective_accuracy':effective_accuracy,'scaffold_accuracy':baseline_accuracy,
             'accepted_test_count':int(accepted.sum()),'support_floor':support_floor,'cost_before':cost_before,'cost_after':cost_after,'missed_continue':missed_continue,
             'bounded_label_cost_pareto':bool(pareto),'quality_scope':'explicit operator labels; held-out local corpus only',
             'finite_difference_max_error':err,'gradient_check':err<1e-6,'deterministic_repeat':deterministic,'finite':finite,'checkpoint_reload':reload_ok,
             'body_parameters_modified':0,'device':device(),'duration_s':time.monotonic()-started,'process_memory':process_memory(),'commit_eligible':bool(eligible)}
    metrics.update(retention_pass=bool(retained),**stats)
    metrics.update(effective_learning_rate=cfg['learning_rate'],effective_max_update_norm=cfg['max_update_norm'])
    atomic_write(Path(out)/'metrics.json',dumps(metrics));return metrics

if __name__=='__main__':train(json.loads(Path(sys.argv[1]).read_text()),sys.argv[2])
