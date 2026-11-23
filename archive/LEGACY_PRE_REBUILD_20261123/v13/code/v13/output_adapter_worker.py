"""Human-gated first-token residual on actual frozen C3 vocabulary logits.

Only the listed native vocabulary rows have trainable external deltas. The
remaining vocabulary is an exact measured probability-mass category, not a
negative sampler. This is a first-position adapter, never base-weight training.
"""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from .common import atomic_write, dumps

FORMAT = 'c3-native-first-token-delta-v2'
DIM = 1024

def native_context(pool,messages,cancel,deadline,token_ids=None):
    """Actual exact-template C3 state, optionally full-vocabulary baseline.

    Generation and feature runners are sequential to preserve the phone's
    existing one-body residency policy. Sources are never silently truncated.
    """
    import math
    from .common import Limits,Unavailable
    baseline=None;native=None;baseline_prompt=None;baseline_ids=None
    try:
      if token_ids is not None:
        runner=pool.get('C3_LANGUAGE');runner.load(cancel,deadline)
        prompt,n,truncated=runner._prompt(messages,cancel,deadline,runner.cfg['answer_tokens'])
        if truncated or not 1<=n<=512:raise Limits('Output adapter requires exact untrimmed context of at most 512 native tokens')
        baseline_prompt=prompt
        baseline_ids=runner._json('POST','/tokenize',{'content':prompt,'add_special':True},deadline)['tokens']
        if len(baseline_ids)!=n:raise Unavailable('Native baseline token count changed after template measurement')
        native=runner.completion_one({'prompt':prompt,'temperature':-1,'n_probs':65536,'post_sampling_probs':False,'cache_prompt':False,'seed':13},cancel,deadline)
        rows=native.get('completion_probabilities',[])
        if len(rows)!=1:raise Unavailable('One actual native output probability position required')
        rows=rows[0].get('top_logprobs',[])
        if len(rows)!=65536 or {r.get('id') for r in rows}!=set(range(65536)):raise Unavailable('Complete pinned C3 native vocabulary distribution unavailable')
        values={r['id']:r['logprob'] for r in rows}
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in values.values()):raise Unavailable('Actual native output probabilities malformed')
        mass=sum(math.exp(v) for v in values.values())
        if not .999<=mass<=1.001:raise Unavailable('Native vocabulary probability mass invalid')
        selected=[math.exp(values[i])/mass for i in token_ids];other=1.-sum(selected)
        if other<=0:raise Unavailable('Native unchanged-vocabulary mass is empty')
        baseline=[math.log(p) for p in selected]+[math.log(other)]
        native={'token_ids':native.get('tokens',[]),'content':native.get('content',''),'timings':native.get('timings',{}),'raw_probability_mass':mass,'vocabulary_size':65536}
        pool.unload()
      runner=pool.get_tap('C3_LANGUAGE');runner.load(cancel,deadline)
      prompt,n,truncated=runner._prompt(messages,cancel,deadline,runner.cfg['answer_tokens'])
      if truncated or not 1<=n<=512:raise Limits('Output adapter requires exact untrimmed context of at most 512 native tokens')
      if baseline_prompt is not None and prompt!=baseline_prompt:raise Unavailable('Native baseline and feature tap templates differ')
      tap=runner.tap(prompt,cancel,deadline,max_tokens=512)
      if len(tap['token_ids'])!=n:raise Unavailable('Native feature tap token count differs from exact template count')
      if baseline_ids is not None and tap['token_ids']!=baseline_ids:raise Unavailable('Native baseline and feature tap token IDs differ')
      prompt_hash=hashlib.sha256(prompt.encode()).hexdigest()
      return {'feature':tap['vectors'][-1],'native_prompt_token_ids':tap['token_ids'],'prompt_sha256':prompt_hash,'native_metrics':tap['metrics'],'base_log_probabilities':baseline,'native_baseline':native,
              'native_context_binding':{'template_token_count':n,'tap_token_count':len(tap['token_ids']),'baseline_prompt_sha256':prompt_hash if baseline_prompt is not None else None,'tap_prompt_sha256':prompt_hash,'baseline_token_ids_match':True if baseline_ids is not None else None,'scope':'EXACT_SEPARATE_READ_ONLY_PREFILL','live_generation_kv_tap':False}}
    finally:pool.unload()

def features(vectors):
    x = np.asarray(vectors, dtype=float)
    if x.ndim != 2 or x.shape[1] != DIM or not np.isfinite(x).all():
        raise ValueError('Actual finite 1024D native C3 states required')
    norms = np.linalg.norm(x, axis=1)
    if np.any(norms <= 1e-12): raise ValueError('Empty native C3 state')
    return np.column_stack((np.ones(len(x)), x / norms[:, None]))

def distribution(base, x, weights, temperature=1., max_bias=12.):
    delta = np.clip(x @ weights / temperature, -max_bias, max_bias)
    logits = base.copy(); logits[:, :-1] += delta
    shift = logits.max(axis=1, keepdims=True)
    p = np.exp(logits-shift); p /= p.sum(axis=1, keepdims=True)
    return p, delta

def loss_gradient(base, x, y, weights, max_bias=12.):
    p, delta = distribution(base, x, weights, max_bias=max_bias)
    loss = -np.log(np.maximum(p[np.arange(len(y)), y], 1e-300)).mean() + 1e-4*np.sum(weights*weights)
    error = p[:, :-1].copy(); error[np.arange(len(y)), y] -= 1.
    raw = x @ weights; error *= (np.abs(raw) < max_bias)
    return float(loss), x.T @ error / len(y) + 2e-4*weights

def scores(p, y):
    confidence = p.max(axis=1); correct = p.argmax(axis=1)==y
    target = np.zeros_like(p); target[np.arange(len(y)), y] = 1.
    ece = sum(float(mask.mean()) * abs(float(confidence[mask].mean()-correct[mask].mean()))
              for lo in (0., .2, .4, .6, .8)
              if (mask := (confidence>=lo)&(confidence<(lo+.2) if lo<.8 else confidence<=1.)).any())
    return {'n':len(y), 'loss':float(-np.log(np.maximum(p[np.arange(len(y)), y],1e-300)).mean()),
            'brier':float(np.mean(np.sum((p-target)**2,axis=1))), 'accuracy':float(correct.mean()), 'ece':ece}

def optimize(base,x,y,w,cfg):
    w=w.copy();largest=0.
    for _ in range(cfg['output_adapter_steps']):
        _,g=loss_gradient(base,x,y,w,cfg['output_adapter_max_bias'])
        step=-cfg['output_adapter_lr']*g; n=float(np.linalg.norm(step));step*=min(1.,cfg['max_update_norm']/max(n,1e-12));w+=step;largest=max(largest,float(np.linalg.norm(step)))
    return w,largest

def gradient_check(base,x,y,w,max_bias):
    _,g=loss_gradient(base,x,y,w,max_bias);eps=1e-5;errors=[]
    # Thirty-two spread-out coordinates; this is explicitly a sampled check.
    coords=np.linspace(0,w.size-1,min(32,w.size),dtype=int)
    for idx in coords:
        a=w.copy();b=w.copy();a.flat[idx]+=eps;b.flat[idx]-=eps
        errors.append(abs((loss_gradient(base,x,y,a,max_bias)[0]-loss_gradient(base,x,y,b,max_bias)[0])/(2*eps)-g.flat[idx]))
    return float(max(errors))

def train(inp,out):
    cfg=inp['config'];tokens=np.asarray(inp['token_ids'],dtype=int);raw_x=features(inp['native_features']);x=raw_x.copy();base=np.asarray(inp['base_log_probabilities'],dtype=float);y=np.asarray(inp['target_indices'],dtype=int);groups=inp['source_groups']
    if not 2<=len(tokens)<=16 or len(set(tokens))!=len(tokens) or np.any(tokens<0):raise ValueError('Two to sixteen unique native vocabulary rows required')
    if len(x)!=len(groups) or len(set(groups))!=len(groups) or y.shape!=(len(x),) or np.any(y<0) or np.any(y>=len(tokens)):raise ValueError('Unique source groups and explicit output labels required')
    if base.shape!=(len(x),len(tokens)+1) or not np.isfinite(base).all() or not np.allclose(np.exp(base).sum(axis=1),1.,atol=1e-5):raise ValueError('Measured complete-vocabulary probabilities required')
    fold=np.array([int(hashlib.sha256(g.encode()).hexdigest()[:8],16)%5 for g in groups]);ti=np.flatnonzero(fold>=2);ci=np.flatnonzero(fold==1);vi=np.flatnonzero(fold==0)
    for ids in (ti,ci,vi):
        if len(ids)<8 or any(np.sum(y[ids]==k)<2 for k in range(len(tokens))):raise ValueError('Train/calibration/test need eight sources and two examples per native token')
    offset=x[ti,1:].mean(axis=0);scale=np.maximum(x[ti,1:].std(axis=0),.001)
    w=np.zeros((DIM+1,len(tokens)));old_t=1.;old_cap=cfg['output_adapter_max_bias'];old_x=np.empty((0,DIM+1));old_base=np.empty((0,len(tokens)+1));old_y=np.empty(0,dtype=int);old_ids=[];anchors=raw_x[ti,1:]
    if inp.get('active_checkpoint'):
        with np.load(inp['active_checkpoint'],allow_pickle=False) as a:
            if str(a['format'])!=FORMAT or not np.array_equal(a['token_ids'],tokens):raise ValueError('Output vocabulary is immutable within a component lineage')
            if float(a['support_cosine'])!=cfg['output_adapter_support_cosine']:raise ValueError('Output support threshold is immutable within a component lineage')
            old_cap=float(a['max_bias'])
            w=a['weights'];old_t=float(a['temperature']);old_x=a['retention_x'];old_base=a['retention_base'];old_y=a['retention_y'];old_ids=a['retention_ids'].tolist();anchors=np.vstack((a['anchors'],anchors));offset=a['feature_offset'];scale=a['feature_scale']
    if offset.shape!=(DIM,) or scale.shape!=(DIM,) or not np.isfinite(offset).all() or not np.isfinite(scale).all() or np.any(scale<.001):raise ValueError('Native train-only feature normalizer invalid')
    x[:,1:]=np.clip((x[:,1:]-offset)/scale,-8.,8.)
    if w.shape!=(DIM+1,len(tokens)) or not np.isfinite(w).all():raise ValueError('Output adapter checkpoint malformed')
    anchors=np.unique(anchors,axis=0)
    if len(anchors)>2048:raise ValueError('Native support capacity reached; old anchors cannot be discarded')
    error=gradient_check(base[ti],x[ti],y[ti],w,cfg['output_adapter_max_bias']);new,norm=optimize(base[ti],x[ti],y[ti],w,cfg);repeat,_=optimize(base[ti],x[ti],y[ti],w,cfg)
    temp=float(min(np.exp(np.linspace(np.log(.5),np.log(2.),33)),key=lambda t:scores(distribution(base[ci],x[ci],new,t,cfg['output_adapter_max_bias'])[0],y[ci])['loss']))
    before=scores(distribution(base[vi],x[vi],w,old_t,old_cap)[0],y[vi]);after=scores(distribution(base[vi],x[vi],new,temp,cfg['output_adapter_max_bias'])[0],y[vi]);native=scores(np.exp(base[vi]),y[vi])
    cosine=(raw_x[vi,1:]@anchors.T).max(axis=1);supported=bool(np.all(cosine>=cfg['output_adapter_support_cosine']))
    held_out_per_token={};retained={'n':len(old_y),'pass':True,'per_native_token':{}}
    for k,token in enumerate(tokens):
        ids=np.flatnonzero(y[vi]==k);a=scores(distribution(base[vi][ids],x[vi][ids],w,old_t,old_cap)[0],y[vi][ids]);b=scores(distribution(base[vi][ids],x[vi][ids],new,temp,cfg['output_adapter_max_bias'])[0],y[vi][ids])
        ok=b['loss']<=a['loss']+cfg['retention_max_delta'] and b['brier']<=a['brier']+cfg['retention_max_delta'] and b['accuracy']>=a['accuracy']-cfg['retention_max_delta']
        held_out_per_token[str(token)]={'before':a,'after':b,'pass':bool(ok)}
    if len(old_y):
        a=scores(distribution(old_base,old_x,w,old_t,old_cap)[0],old_y);b=scores(distribution(old_base,old_x,new,temp,cfg['output_adapter_max_bias'])[0],old_y)
        retained.update(before=a,after=b,**{'pass':b['loss']<=a['loss']+cfg['retention_max_delta'] and b['brier']<=a['brier']+cfg['retention_max_delta'] and b['accuracy']>=a['accuracy']-cfg['retention_max_delta']})
        for k,token in enumerate(tokens):
            ids=np.flatnonzero(old_y==k)
            if not len(ids):continue
            a=scores(distribution(old_base[ids],old_x[ids],w,old_t,old_cap)[0],old_y[ids]);b=scores(distribution(old_base[ids],old_x[ids],new,temp,cfg['output_adapter_max_bias'])[0],old_y[ids])
            ok=b['loss']<=a['loss']+cfg['retention_max_delta'] and b['brier']<=a['brier']+cfg['retention_max_delta'] and b['accuracy']>=a['accuracy']-cfg['retention_max_delta']
            retained['per_native_token'][str(token)]={'before':a,'after':b,'pass':bool(ok)}
        retained['pass']=retained['pass'] and all(v['pass'] for v in retained['per_native_token'].values())
    cases={key:(vec,bl,label) for key,vec,bl,label in zip(old_ids,old_x,old_base,old_y)}
    for i in vi:cases.setdefault(groups[i],(x[i],base[i],y[i]))
    if len(cases)>2048:raise ValueError('Old labelled native cases cannot be discarded')
    keys=sorted(cases);rx=np.asarray([cases[k][0] for k in keys]);rb=np.asarray([cases[k][1] for k in keys]);ry=np.asarray([cases[k][2] for k in keys])
    path=Path(out)/'candidate.npz';np.savez(path,format=np.asarray(FORMAT),token_ids=tokens,weights=new,temperature=np.asarray(temp),max_bias=np.asarray(cfg['output_adapter_max_bias']),support_cosine=np.asarray(cfg['output_adapter_support_cosine']),anchors=anchors,feature_offset=offset,feature_scale=scale,retention_x=rx,retention_base=rb,retention_y=ry,retention_ids=np.asarray(keys))
    with np.load(path,allow_pickle=False) as a:reload_ok=np.array_equal(a['weights'],new) and np.array_equal(a['retention_x'],rx)
    repeat_ok=np.array_equal(new,repeat);improved=after['loss']<=native['loss']-.02 and after['brier']<=native['brier']-.02;retention=retained['pass'] and after['loss']<=before['loss']+cfg['retention_max_delta'] and all(v['pass'] for v in held_out_per_token.values())
    m={'objective':FORMAT,'scope':'EXTERNAL_FIRST_NATIVE_TOKEN_VOCABULARY_ROW_DELTA','trainable_parameter_count':new.size+1,'native_body_parameters_modified':0,'native_state_dimension':DIM,'vocabulary_rows':tokens.tolist(),'partition':{'train':ti.tolist(),'calibration':ci.tolist(),'test':vi.tolist()},'source_groups':groups,'native_baseline':native,'before':before,'after':after,'temperature':temp,'max_applied_step_norm':norm,'finite_difference_sampled_coordinates':min(32,w.size),'finite_difference_max_error':error,'gradient_check':error<1e-6,'calibration_pass':after['ece']<=.2,'utility_pass':bool(improved),'retention_pass':bool(retention),'retained_test':retained,'held_out_support_pass':supported,'held_out_support_cosines':cosine.tolist(),'checkpoint_reload':bool(reload_ok),'deterministic_repeat':bool(repeat_ok),'semantic_truth_authority':False}
    # The summed unchanged-vocabulary category is a conservative competitor:
    # winning against it also wins against every unchanged individual row.
    m['first_native_token_accuracy_pass']=after['accuracy']>=.8
    m['held_out_per_native_token']=held_out_per_token
    m['commit_eligible']=bool(improved and retention and supported and m['calibration_pass'] and m['first_native_token_accuracy_pass'] and reload_ok and repeat_ok and error<1e-6)
    from .resources import device,process_memory
    m.update(device=device(),process_memory=process_memory(),effective_learning_rate=cfg['output_adapter_lr'],effective_max_update_norm=cfg['max_update_norm'],optimizer_steps=cfg['output_adapter_steps'])
    atomic_write(Path(out)/'metrics.json',dumps(m));return m

def infer(native_feature,checkpoint):
    x=features([native_feature])
    with np.load(checkpoint,allow_pickle=False) as a:
        if str(a['format'])!=FORMAT:raise ValueError('Output adapter format')
        w=a['weights'];anchors=a['anchors'];t=float(a['temperature']);cap=float(a['max_bias']);threshold=float(a['support_cosine']);ids=a['token_ids'];offset=a['feature_offset'];scale=a['feature_scale']
        if w.shape!=(DIM+1,len(ids)) or not np.isfinite(w).all() or anchors.ndim!=2 or anchors.shape[1]!=DIM or not np.isfinite(anchors).all() or not len(anchors) or not .5<=t<=2. or not 0<cap<=12.:raise ValueError('Output adapter malformed')
        if offset.shape!=(DIM,) or scale.shape!=(DIM,) or not np.isfinite(offset).all() or not np.isfinite(scale).all() or np.any(scale<.001):raise ValueError('Output feature normalizer malformed')
        cosine=float((x[:,1:]@anchors.T).max());supported=cosine>=threshold;x[:,1:]=np.clip((x[:,1:]-offset)/scale,-8.,8.);delta=np.clip(x@w/t,-cap,cap)[0]
        return {'in_support':supported,'nearest_native_cosine':cosine,'first_token_bias':[[int(i),float(v)] for i,v in zip(ids,delta)] if supported else [],'scope':'EXTERNAL_FIRST_NATIVE_TOKEN_VOCABULARY_ROW_DELTA','semantic_truth_authority':False,'native_body_parameters_modified':0}

if __name__=='__main__':train(json.loads(Path(sys.argv[1]).read_text()),sys.argv[2])
