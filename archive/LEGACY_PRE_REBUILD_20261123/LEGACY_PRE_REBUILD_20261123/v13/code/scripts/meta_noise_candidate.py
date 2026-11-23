"""Isolated candidate (thread L, 2026-10-12) after the META ablation in `ablation_homeo_meta.py` (PARTIAL: noise reopens
plasticity, the second noisy phase has the highest P). `neuromod.py` is not changed here.

Candidate META rule (mirrors `age_plasticity_policy=noise_aware`, same BOOT constants NOISE_EMA .2, NOISE_K 2,
NOISE_REF .05, NOISE_MIN_N 4 from v13/age.py): the path tracks a noise estimate = EMA of |window error - previous
window error| (winsorized at K x estimate once warm). The reopen terms of the unchanged `Neuromod.meta_rule` are then
damped by 1 / (1 + noise / NOISE_REF), and a failing window whose error rise lies inside K x noise is not counted as a
repeated failure; a window counts as novel only if its jump also exceeds K x noise. Stability and saturation unchanged.

PREREG (fixed before the first run), test seeds 13-17:
  noisy stream  = the ablation's META stream (learn -> noisy -> shift -> noisy2)
  clean stream  = same phases and target shift, label noise .1 everywhere (the candidate must not cost when clean)
  PASS only if
    (a) noisy: candidate beats current v13 rule in >= 4/5 seeds,
    (b) noisy: candidate beats fixed_conservative (P .45) and fixed_matched (same mean P) in >= 4/5 seeds each,
    (c) clean: candidate worse than current v13 in at most 1/5 seeds.
  Otherwise FAIL. Primary metric as in the ablation (mean parameter error from the first noisy phase on).
Claim limit: synthetic NLMS learner, harness features, BOOT constants.
"""
import json
import random
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v13.ablation99 import SEEDS,_vec,_dot,_nlms,_err,_mean
from v13.neuromod import Neuromod
from v13.age import NOISE_EMA,NOISE_K,NOISE_REF,NOISE_MIN_N
import ablation_homeo_meta as HM

PREREG={'schema':'META_NOISE_CANDIDATE_PREREG_V1','test_seeds':list(SEEDS),'constants':{'NOISE_EMA':NOISE_EMA,'NOISE_K':NOISE_K,'NOISE_REF':NOISE_REF,'NOISE_MIN_N':NOISE_MIN_N},
        'streams':{'noisy':'ablation META stream','clean':'same phases, label noise .1'},
        'pass':['noisy: candidate < v13 in >=4/5','noisy: candidate < fixed_conservative and < fixed_matched in >=4/5 each','clean: candidate > v13 in <=1/5']}

def clean_stream(seed):
    rng=random.Random(seed);w=_vec(rng);w2=_vec(rng);out=[]
    for t in range(HM.M_PHASES[-1][1]):
        phase=next(p for a,b,p in HM.M_PHASES if a<=t<b);true=w if phase in ('learn','noisy') else w2
        x=[rng.gauss(0,1) for _ in range(HM.DIM)];out.append({'t':t,'phase':phase,'x':x,'y':_dot(true,x)+rng.gauss(0,.1),'w':true})
    return out

def candidate_rule(f,noise):
    damp=1/(1+noise/NOISE_REF)
    g=dict(f,novelty=f['novelty']*damp,repeated_errors=f['repeated_errors']*damp)
    return Neuromod.meta_rule(g)

def run_candidate(stream):
    """Same harness as ablation_homeo_meta.run_meta; only the noise estimate and the candidate rule are new."""
    theta=[0.]*HM.DIM;errs={p:[] for *_,p in HM.M_PHASES};win=[];prev=None;passes=0;fails=0;novel=0.;level=0.;ps=[];nz={'mad':0.,'n':0}
    f={'stability':0.,'novelty':0.,'repeated_errors':0.,'saturation':0.,'error_level':0.,'modulator':0.}
    for ev in stream:
        noise=nz['mad'] if nz['n']>=NOISE_MIN_N else 0.
        p=candidate_rule(f,noise);ps.append(p);theta=_nlms(theta,ev['x'],ev['y'],HM.LR*p);e=_err(theta,ev['w']);errs[ev['phase']].append(e);win.append(e)
        if (ev['t']+1)%HM.WINDOW==0:
            err=_mean(win);win=[];band=NOISE_K*nz['mad'] if nz['n']>=NOISE_MIN_N else 0.
            if prev is not None:
                dev=abs(err-prev)
                if nz['n']>=NOISE_MIN_N:dev=min(dev,band)
                nz['mad']=dev if nz['n']==0 else (1-NOISE_EMA)*nz['mad']+NOISE_EMA*dev;nz['n']+=1
            rise=err-prev if prev is not None else 0.
            novel=1. if prev is not None and err>2*prev and err>.05 and rise>band else 0.
            ok=prev is None or err<=prev*1.1+.02 or rise<=band;passes=passes+1 if ok and err<.1 else 0;fails=0 if ok else fails+1
            level=.8*level+.2*min(1.,err);prev=err
            f={'stability':1. if passes>=3 else (.5 if passes>=1 else 0.),'novelty':novel,'repeated_errors':min(1.,fails/3),
               'saturation':.5*(1-level),'error_level':level,'modulator':0.}
    post=errs['noisy']+errs['shift']+errs['noisy2']
    return {'primary':round(_mean(post),5),'mean_p':round(_mean(ps),5),
            'mean_p_phase':{k:round(_mean([ps[i] for i,ev in enumerate(stream) if ev['phase']==k]),4) for *_,k in HM.M_PHASES}}

def run():
    res={}
    for name,mk in (('noisy',HM.meta_stream),('clean',clean_stream)):
        res[name]={}
        for s in SEEDS:
            st=mk(s);v=HM.run_meta(st,'v13')
            res[name][s]={'candidate':run_candidate(st),'v13':v,'fixed_conservative':HM.run_meta(st,'fixed_conservative'),'fixed_matched':HM.run_meta(st,'fixed_matched',v['mean_p'])}
    P=lambda n,s,a:res[n][s][a]['primary']
    ca=sum(P('noisy',s,'candidate')<P('noisy',s,'v13') for s in SEEDS)
    cb={a:sum(P('noisy',s,'candidate')<P('noisy',s,a) for s in SEEDS) for a in ('fixed_conservative','fixed_matched')}
    cc=sum(P('clean',s,'candidate')>P('clean',s,'v13') for s in SEEDS)
    means={n:{a:round(_mean([P(n,s,a) for s in SEEDS]),5) for a in ('candidate','v13','fixed_conservative','fixed_matched')} for n in res}
    return {'prereg':PREREG,'test':res,'means':means,'criteria':{'noisy_beats_v13':ca,'noisy_beats_fixed':cb,'clean_worse_than_v13':cc},
            'verdict':'PASS' if ca>=4 and all(v>=4 for v in cb.values()) and cc<=1 else 'FAIL',
            'claim_limit':'synthetic NLMS learner, harness features, BOOT constants; isolated candidate, neuromod.py unchanged'}

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--prereg':
        out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(PREREG,indent=1));sys.exit(0)
    r=run();out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=1))
    print(r['verdict'],r['criteria']);print(json.dumps(r['means']))
