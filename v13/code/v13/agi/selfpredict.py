"""WP-FS4 testable self-prediction: "would this change to the question change my answer?" predicted first, checked after.

No introspection claim (Singh et al., arXiv 2605.26242: such evidence is explained by the input alone; Zeng et al.,
arXiv 2608.30980 for the self-modeling idea). So every predictor is scored against controls that see only the
question text: the base-rate guess and an input-only guess. The system "knows itself" only to the extent that it beats both.
Pure measurement harness: answer_fn, perturb_fn and predict_fn are supplied by the caller (runtime, tool or toy).
"""
from .metaeff import report

def run(items,answer_fn,perturb_fn,predict_fn,input_only_fn=None,same=lambda a,b:a==b):
    """predict_fn(item,perturbed)->P(answer changes) is called BEFORE the perturbed answer is computed."""
    rows=[]
    for it in items:
        p_item=perturb_fn(it);a0=answer_fn(it);pred=float(predict_fn(it,p_item))
        changed=int(not same(a0,answer_fn(p_item)))
        rows.append((pred,changed,None if input_only_fn is None else float(input_only_fn(it,p_item))))
    n=len(rows);rate=sum(c for _,c,_ in rows)/n if n else 0.
    def acc(idx):return round(sum(int((r[idx]>=.5)==bool(r[1])) for r in rows)/n,4)
    out={'n':n,'change_rate':round(rate,4),'base_rate_acc':round(max(rate,1-rate),4),'self_acc':acc(0),
         'self':report([(r[0],r[1]) for r in rows])}
    if input_only_fn is not None:
        out['input_only_acc']=acc(2);out['input_only']=report([(r[2],r[1]) for r in rows])
    ctrl=max(out['base_rate_acc'],out.get('input_only_acc',0))
    out['verdict']='SELF_KNOWS' if out['self_acc']>ctrl+.05 and out['self']['perm_p']<.05 else 'NO_SELF_ADVANTAGE'
    return out
