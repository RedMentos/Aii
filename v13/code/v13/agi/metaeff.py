"""WP-FS3 metacognitive efficiency (BP6 measure): how well does confidence separate right from wrong answers.

Model-free: normalised mutual information meta_I = I(correct; confidence bin) / H(correct), in [0,1], plus the
type-2 AUROC, a permutation null and a bootstrap CI. Idea after Cacioli, arXiv 2603.25112 (meta-I_2r); the exact
binning and normalisation of the paper were NOT verified here (only the abstract was read), so this is our own
variant and reported as `meta_i`, not as the paper's number. ECE stays reported next to it, never replaced.
abstain_utility() gives the payoff of "say I don't know below a confidence threshold", the quantity meta_i should predict.
"""
import bisect
import itertools
import math,random

def _h(p):return 0. if p<=0 or p>=1 else -(p*math.log2(p)+(1-p)*math.log2(1-p))

def _validated_pairs(pairs):
    """Normalise the documented domain before sorting or resampling."""
    result=[]
    for confidence,correct in pairs:
        try:confidence=float(confidence)
        except (TypeError,ValueError,OverflowError) as exc:
            raise ValueError('confidence must be finite and between 0 and 1') from exc
        if not math.isfinite(confidence) or not 0.<=confidence<=1.:
            raise ValueError('confidence must be finite and between 0 and 1')
        if correct not in (0,1):raise ValueError('correct must be 0 or 1')
        result.append((confidence,int(correct)))
    return result

def meta_i(pairs,bins=5):
    """Normalised mutual information using approximately equal-count confidence bins.

    Equal confidence values always share one bin. Each tie group is placed in
    the original equal-count bin containing its lower midpoint; this preserves
    the original boundaries when all values differ, but some bins may be empty.
    """
    if isinstance(bins, bool) or not isinstance(bins, int) or bins < 1:
        raise ValueError('bins must be a positive integer')
    pairs=_validated_pairs(pairs)
    n=len(pairs)
    if n<2:return None
    k=sum(y for _,y in pairs);hy=_h(k/n)
    if hy==0:return 0.  # all right or all wrong: confidence has nothing to separate
    s=sorted(pairs,key=lambda t:t[0]);b=max(1,min(bins,n))
    bounds=[i*n//b for i in range(b+1)];cells=[[] for _ in range(b)];start=0
    for _,group in itertools.groupby(s,key=lambda t:t[0]):
        members=list(group);end=start+len(members)
        midpoint=(start+end-1)//2
        cells[bisect.bisect_right(bounds,midpoint)-1].extend(members)
        start=end
    hyc=sum(len(c)/n*_h(sum(y for _,y in c)/len(c)) for c in cells if c)
    return max(0.,(hy-hyc)/hy)

def auroc2(pairs):
    """P(confidence of a right answer > confidence of a wrong one), ties count half. None if one class is missing."""
    pos=[c for c,y in pairs if y];neg=[c for c,y in pairs if not y]
    if not pos or not neg:return None
    return sum((p>q)+.5*(p==q) for p in pos for q in neg)/(len(pos)*len(neg))

def report(pairs,bins=5,perm=500,boot=300,seed=0):
    """meta_i with permutation null (p-value) and bootstrap 95% CI, plus AUROC2 and accuracy.

    Canonical ordering makes the finite seeded resamples reproducible after an
    input permutation, including when confidence values are tied.
    """
    if isinstance(perm, bool) or not isinstance(perm, int) or perm < 1:
        raise ValueError('perm must be a positive integer')
    if isinstance(boot, bool) or not isinstance(boot, int) or boot < 2:
        raise ValueError('boot must be an integer >= 2')
    pairs=sorted(_validated_pairs(pairs))
    rng=random.Random(seed);n=len(pairs);mi=meta_i(pairs,bins)
    if mi is None:return {'n':n,'meta_i':None}
    ys=[y for _,y in pairs];cs=[c for c,_ in pairs];ge=0
    for _ in range(perm):
        rng.shuffle(ys);ge+=meta_i(list(zip(cs,ys)),bins)>=mi
    bs=sorted(meta_i([pairs[rng.randrange(n)] for _ in range(n)],bins) for _ in range(boot))
    return {'n':n,'accuracy':round(sum(int(bool(y)) for _,y in pairs)/n,4),'meta_i':round(mi,4),
            'perm_p':round((ge+1)/(perm+1),4),'ci95':[round(bs[int(.025*boot)],4),round(bs[int(.975*boot)-1],4)],
            'auroc2':None if auroc2(pairs) is None else round(auroc2(pairs),4)}

def abstain_utility(pairs,wrong_cost=1.,abstain_cost=.3,steps=20):
    """Best gain over answering everything: right +1, wrong -wrong_cost, abstain -abstain_cost, abstain below threshold."""
    base=sum(1. if y else -wrong_cost for _,y in pairs);best=(0.,0.)
    for i in range(steps+1):
        t=i/steps;u=sum((1. if y else -wrong_cost) if c>=t else -abstain_cost for c,y in pairs)
        if u-base>best[0]:best=(u-base,t)
    return {'gain':round(best[0],4),'threshold':best[1],'answer_all':round(base,4)}
