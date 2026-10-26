"""WP-HX2 same-task probe without gold answers (Harness² Propose-Probe-Compose, research/HARNESS2_AUSWERTUNG.md).

Propose: k harness variants (agi/harness.py allow-list, validated by harness.candidate) are fixed before any run.
Probe:   reference and every variant run the same tasks with the same seed; behaviour differences are logged per task
         (quotes, rejected quotes, summary, answer, prompt tokens) and a gold-free probe score is computed by the caller
         from internal signals only (for the B2 probe: share of emitted quotes that pass the exact source check).
Compose: the variant with the best probe score is chosen only if it beats the reference by MIN_PROBE_GAIN; otherwise
         nothing is chosen (NO_CANDIDATE). Gold answers are never read before the choice.
Gate:    on held-out tasks/seeds the chosen variant must win on the primary axis (cluster bootstrap CI > 0), no axis may
         get worse beyond AXIS_TOLERANCE, wrong commits may not rise, and an unguided change of similar size must not
         explain the gain (otherwise the setup measures "any change", not the probe).

overlay() is the only consumer of harness overrides and is meant for bench processes: it patches the module defaults
for the duration of a with-block and restores them (prompt.b2_earlier_context: rewrites the exact base text in the B2
system message of each native call, because cognition.py is hash-pinned). The live runtime never calls it (authority 0, SHADOW).
"""
import contextlib
import importlib
from .harness import TARGETS,candidate

REVISION='hx2-probe-v1'
MIN_PROBE_GAIN=.05;AXIS_TOLERANCE=.02;BOOT=10000;BOOT_SEED=20261022

class _B2Note:
    """prompt.b2_earlier_context lives inline in cognition.offer (hash-pinned file). The bench overlay rewrites the exact
    base text inside the system message of a native call instead; counts the rewrites. With capture, each B2 call is
    kept as {'messages': the messages under the BASE harness, 'output': raw text under the overlay} (HX5 data source).
    value None = capture only, nothing rewritten (reference arm)."""
    CAP=4096
    def __init__(self,capture=False):self.calls=0;self.rewritten=0;self.capture=[] if capture else None
    def install(self,value):
        from .. import runners
        from .harness import B2_CONTEXT_NOTE
        gen=runners.LlamaRunner.generate;me=self
        def generate(runner,messages,*a,**kw):
            me.calls+=1
            b2=bool(messages) and messages[0].get('role')=='system' and B2_CONTEXT_NOTE in messages[0].get('content','')
            if not b2:return gen(runner,messages,*a,**kw)
            base=[dict(m) for m in messages]
            if value is not None:
                messages=[dict(messages[0],content=messages[0]['content'].replace(B2_CONTEXT_NOTE,value,1))]+list(messages[1:]);me.rewritten+=1
            if me.capture is None:return gen(runner,messages,*a,**kw)
            out=''.join(gen(runner,messages,*a,**kw))
            if len(me.capture)<me.CAP:me.capture.append({'messages':base,'output':out})
            return iter([out])
        runners.LlamaRunner.generate=generate
        return lambda:setattr(runners.LlamaRunner,'generate',gen)

def _setter(target):
    """(getter, setter) of the live default a target names; only targets on the allow-list."""
    if target not in TARGETS:raise PermissionError('Nicht vorschlagbar (Harness): '+target)
    if target.startswith('prompt.') and target.count('.')==2:
        _,lang,key=target.split('.');prompts=importlib.import_module('v13.prompts')
        return (lambda:prompts.TEXT[lang][key]),(lambda v:prompts.TEXT[lang].__setitem__(key,v))
    mods={'tool_hint.list_note':('toolstep','LIST_NOTE'),'tool_hint.eligibility_note':('agi.eligibility','LIVE_NOTE')}
    if target not in mods:raise NotImplementedError('overlay kennt dieses Ziel noch nicht: '+target)
    mod=importlib.import_module('v13.'+mods[target][0]);name=mods[target][1]
    return (lambda:getattr(mod,name)),(lambda v:setattr(mod,name,v))

@contextlib.contextmanager
def overlay(diff,capture_b2=False):
    """Bench-only: apply a validated harness diff to the module defaults, restore on exit (also on error).
    Yields {'diff': applied values, 'b2_note': rewrite counter or None}. capture_b2 also records every B2 call."""
    diff=candidate(diff) if diff else {}
    undo=[];b2=None
    try:
        if capture_b2 and 'prompt.b2_earlier_context' not in diff:b2=_B2Note(True);undo.append(b2.install(None))
        for t,v in diff.items():
            if t=='prompt.b2_earlier_context':b2=_B2Note(capture_b2);undo.append(b2.install(v));continue
            get,put=_setter(t);old=get();put(v);undo.append(lambda put=put,old=old:put(old))
        yield {'diff':diff,'b2_note':b2}
    finally:
        for f in reversed(undo):f()

def behaviour_diff(reference,variant,fields):
    """reference/variant: {task_id: {field: value}}. Per field: how many shared tasks changed, and which."""
    shared=sorted(set(reference)&set(variant));out={}
    for f in fields:
        changed=[t for t in shared if reference[t].get(f)!=variant[t].get(f)]
        out[f]={'changed':len(changed),'of':len(shared),'tasks':changed[:32]}
    return out

def compose(probe,reference_score,min_gain=MIN_PROBE_GAIN):
    """probe: {variant: gold-free score}. Best variant if it beats the reference by min_gain, else None."""
    if not probe:return {'status':'NO_CANDIDATE','choice':None,'reason':'keine Varianten'}
    best=max(sorted(probe),key=lambda v:probe[v])
    gain=probe[best]-reference_score
    if gain<min_gain:return {'status':'NO_CANDIDATE','choice':None,'best':best,'gain':gain,'min_gain':min_gain}
    return {'status':'CHOSEN','choice':best,'gain':gain,'min_gain':min_gain}

def cluster_ci(per_task,n=BOOT,seed=BOOT_SEED):
    """per_task: list of per-task mean differences (all seeds of a task stay one cluster). Mean + 95 % percentile CI."""
    import numpy as np
    per=np.asarray(per_task,dtype=float)
    if not len(per):return {'mean':None,'ci95':[None,None],'tasks':0}
    idx=np.random.default_rng(seed).integers(0,len(per),size=(n,len(per)));boot=per[idx].mean(axis=1)
    return {'mean':float(per.mean()),'ci95':[float(np.percentile(boot,2.5)),float(np.percentile(boot,97.5))],'tasks':int(len(per))}

def paired(a,b):
    """a/b: {task: [value per seed]} -> per-task mean difference a-b over the seeds both have."""
    out=[]
    for t in sorted(set(a)&set(b)):
        d=[x-y for x,y in zip(a[t],b[t])]
        if d:out.append(sum(d)/len(d))
    return out

def holdout_gate(axes,primary,wrong,structural,tol=AXIS_TOLERANCE):
    """axes: {axis: {'ref': {task:[..]}, 'chosen': {...}, 'unguided': {...}}}; primary names one axis (higher = better).
    wrong: {'ref': int, 'chosen': int, 'unguided': int} wrong committed answers. Preregistered decision."""
    res={}
    for ax,v in axes.items():
        res[ax]={'chosen_minus_ref':cluster_ci(paired(v['chosen'],v['ref'])),'unguided_minus_ref':cluster_ci(paired(v['unguided'],v['ref'])),
                 'chosen_minus_unguided':cluster_ci(paired(v['chosen'],v['unguided']))}
    p=res[primary]
    gain=p['chosen_minus_ref']['ci95'][0] is not None and p['chosen_minus_ref']['ci95'][0]>0
    worse=[ax for ax,r in res.items() if r['chosen_minus_ref']['mean'] is not None and r['chosen_minus_ref']['mean']<-tol]
    unspecific=p['unguided_minus_ref']['ci95'][0] is not None and p['unguided_minus_ref']['ci95'][0]>0
    control_worse=(p['chosen_minus_unguided']['mean'] or 0)>0
    checks={'holdout_gain_ci_above_0':gain,'no_axis_worse':not worse,'wrong_not_more':wrong['chosen']<=wrong['ref'],
            'unguided_change_worse':control_worse,'unguided_alone_no_gain':not unspecific,'structural':bool(structural)}
    if not structural:status='HX2_INVALID'
    elif wrong['chosen']>wrong['ref'] or worse:status='HX2_AXIS_WORSE'
    elif not gain:status='HX2_NO_HOLDOUT_GAIN'
    elif unspecific or not control_worse:status='HX2_UNSPECIFIC_CHANGE'
    else:status='HX2_PASS'
    return {'revision':REVISION,'status':status,'checks':checks,'axes':res,'worse_axes':worse,'wrong':wrong,'primary':primary,'tolerance':tol}
