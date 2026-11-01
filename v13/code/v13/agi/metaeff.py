"""WP-FS3 metacognitive efficiency (BP6 measure): how well does confidence separate right from wrong answers.

Model-free: normalised mutual information meta_I = I(correct; confidence bin) / H(correct), in [0,1], plus the
type-2 AUROC, a permutation null and a bootstrap CI. Idea after Cacioli, arXiv 2603.25112 (meta-I_2r); the exact
binning and normalisation of the paper were NOT verified here (only the abstract was read), so this is our own
variant and reported as `meta_i`, not as the paper's number. ECE stays reported next to it, never replaced.
abstain_utility() gives the payoff of "say I don't know below a confidence threshold", the quantity meta_i should predict.
"""
import math,random

def _h(p):return 0. if p<=0 or p>=1 else -(p*math.log2(p)+(1-p)*math.log2(1-p))

def meta_i(pairs,bins=5):
    """pairs: [(confidence 0..1, correct 0/1)]. Equal-count bins so a skewed confidence scale does not hide signal."""
    n=len(pairs)
    if n<2:return None
    k=sum(int(bool(y)) for _,y in pairs);hy=_h(k/n)
    if hy==0:return 0.  # all right or all wrong: confidence has nothing to separate
    s=sorted(pairs,key=lambda t:t[0]);b=max(1,min(bins,n));cells=[s[i*n//b:(i+1)*n//b] for i in range(b)]
    hyc=sum(len(c)/n*_h(sum(int(bool(y)) for _,y in c)/len(c)) for c in cells if c)
    return max(0.,(hy-hyc)/hy)

def auroc2(pairs):
    """P(confidence of a right answer > confidence of a wrong one), ties count half. None if one class is missing."""
    pos=[c for c,y in pairs if y];neg=[c for c,y in pairs if not y]
    if not pos or not neg:return None
    return sum((p>q)+.5*(p==q) for p in pos for q in neg)/(len(pos)*len(neg))

def report(pairs,bins=5,perm=500,boot=300,seed=0):
    """meta_i with permutation null (p-value) and bootstrap 95% CI, plus AUROC2 and accuracy."""
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
