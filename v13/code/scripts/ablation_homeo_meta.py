"""§99-style ablations without a language model for two §102 UNTESTED_LABEL rows (thread L, 2026-10-12):

  Metaplasticity helps  (F7_MEASURED_PLASTICITY / neuromod META, §16.1, §68)
      P = Neuromod.meta_rule(features) scales the step size of one NLMS learner
      vs  fixed permissive P=1, fixed conservative P=.45, fixed P at the V13 run's mean P (budget matched),
          V13 without the novelty term, V13 without the repeated-failure term.
  Homeostasis helps     (MODULE_HOMEOSTASIS / WP-U2 homeostasis.regulate, §16.2, §68)
      per-path gain from homeostasis.regulate once per "night" (every NIGHT events) scales each path's step size
      vs  no regulation (gain 1), direct equalisation (gain = fair share / share, bounded, no slow move),
          random gains (the V13 run's gain values shuffled across paths each night), V13 without dead-path reopen,
          V13 without dominant-path inhibition.

Both drive the real, unchanged pure functions (`Neuromod.meta_rule`, `homeostasis.regulate`); only the feature
bookkeeping around them is harness code (documented below). Streams are open-loop and identical for all arms of a seed.
PREREG (fixed before the first run, see PREREG below): a mechanism "helps" only if it beats every control on the
primary metric in >= 4 of 5 seeds; otherwise the verdict is PARTIAL (beats some) or NOT_SUPPORTED (beats none).
Claim limit: synthetic stream, linear NLMS learners (dim 4), no language model, BOOT knob values; says nothing about
real-model learning quality.
"""
import contextlib
import json
import math
import random
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.ablation99 import DIM,SEEDS,_vec,_dot,_nlms,_err,_mean,_sd
from v13.neuromod import Neuromod
from v13 import homeostasis as H

PREREG={'schema':'ABLATION_HOMEO_META_PREREG_V1','seeds':list(SEEDS),'win_rule':'v13 primary metric lower than control in >=4/5 seeds, for every control',
        'verdicts':{'SUPPORTED_SYNTHETIC':'beats every control','PARTIAL':'beats at least one control','NOT_SUPPORTED':'beats none'},
        'meta':{'primary':'mean per-step parameter error over the noisy and shift phases','secondary':['phase errors','final error','mean P']},
        'homeostasis':{'primary':'mean over paths of the time-averaged parameter error after the pre-phase','secondary':['dominant-path error','revived-path recovery error','final error']}}

# --- metaplasticity -------------------------------------------------------------------------------------------------
LR=.3;WINDOW=25
M_PHASES=((0,300,'learn'),(300,900,'noisy'),(900,1200,'shift'),(1200,1500,'noisy2'))
META_ARMS=('v13','fixed_permissive','fixed_conservative','fixed_matched','v13_no_novelty','v13_no_repeated')

def meta_stream(seed):
    rng=random.Random(seed);w=_vec(rng);w2=_vec(rng);out=[]
    for t in range(M_PHASES[-1][1]):
        phase=next(p for a,b,p in M_PHASES if a<=t<b);true=w if phase in ('learn','noisy') else w2
        x=[rng.gauss(0,1) for _ in range(DIM)]
        y=_dot(true,x)+rng.gauss(0,1. if phase.startswith('noisy') else .1)
        out.append({'t':t,'phase':phase,'x':x,'y':y,'w':true})
    return out

def run_meta(stream,arm,matched=None):
    """Harness features per window (the real module derives them from LearningTrace/PlasticityState packets):
    stability   1 after 3 consecutive passing windows with low error (stable+tag), .5 after one, else 0
    novelty     1 for one window after the window error more than doubles (surprise), else 0
    repeated    consecutive failing windows / 3, capped at 1 (retention failures)
    saturation  activation rate (here .5: the path is active every other event on average) x (1 - error level)
    error_level EMA of the window error, clamped to [0,1]"""
    theta=[0.]*DIM;errs={p:[] for *_,p in M_PHASES};win=[];prev=None;passes=0;fails=0;novel=0.;level=0.;ps=[]
    f={'stability':0.,'novelty':0.,'repeated_errors':0.,'saturation':0.,'error_level':0.,'modulator':0.}
    for ev in stream:
        if arm=='fixed_permissive':p=1.
        elif arm=='fixed_conservative':p=.45
        elif arm=='fixed_matched':p=matched
        else:
            g=dict(f)
            if arm=='v13_no_novelty':g['novelty']=0.
            if arm=='v13_no_repeated':g['repeated_errors']=0.
            p=Neuromod.meta_rule(g)
        ps.append(p);theta=_nlms(theta,ev['x'],ev['y'],LR*p);e=_err(theta,ev['w']);errs[ev['phase']].append(e);win.append(e)
        if (ev['t']+1)%WINDOW==0:
            err=_mean(win);win=[]
            novel=1. if prev is not None and err>2*prev and err>.05 else 0.
            ok=prev is None or err<=prev*1.1+.02;passes=passes+1 if ok and err<.1 else 0;fails=0 if ok else fails+1
            level=.8*level+.2*min(1.,err);prev=err
            f={'stability':1. if passes>=3 else (.5 if passes>=1 else 0.),'novelty':novel,'repeated_errors':min(1.,fails/3),
               'saturation':.5*(1-level),'error_level':level,'modulator':0.}
    post=errs['noisy']+errs['shift']+errs['noisy2']
    return {'primary':round(_mean(post),5),'phase_error':{k:round(_mean(v),5) for k,v in errs.items()},
            'final_error':round(_err(theta,stream[-1]['w']),5),'mean_p':round(_mean(ps),5),
            'mean_p_phase':{k:round(_mean([ps[i] for i,ev in enumerate(stream) if ev['phase']==k]),4) for *_,k in M_PHASES}}

# --- homeostasis ----------------------------------------------------------------------------------------------------
PATHS=('p0','p1','p2','p3','p4','p5');DOMINANT='p0';REVIVED='p5';NIGHT=100;LR_H=.3;NOISE_H=.6
H_PHASES=((0,300,'pre'),(300,1100,'skewed'),(1100,1500,'revived'))
HOMEO_ARMS=('v13','none','equalize','random_gains','v13_no_reopen','v13_no_dominant')

def homeo_stream(seed):
    """pre: all six paths uniform (all learn); skewed: p0 gets 60 %, p5 silent while its target drifts at t=700;
    revived: p5 back at 30 %. Label noise sd .6 on every path (noise punishes over-plastic, over-used paths)."""
    rng=random.Random(seed);w={p:_vec(rng) for p in PATHS};w5b=_vec(rng);out=[]
    for t in range(H_PHASES[-1][1]):
        phase=next(p for a,b,p in H_PHASES if a<=t<b)
        if t==700:w[REVIVED]=w5b
        if phase=='pre':share={p:1. for p in PATHS}
        elif phase=='skewed':share={DOMINANT:.6,**{p:.1 for p in PATHS[1:5]},REVIVED:0.}
        else:share={DOMINANT:.3,**{p:.1 for p in PATHS[1:5]},REVIVED:.3}
        r=rng.random()*sum(share.values());path=PATHS[-1]
        for path in PATHS:
            r-=share[path]
            if r<=0:break
        x=[rng.gauss(0,1) for _ in range(DIM)];out.append({'t':t,'phase':phase,'path':path,'x':x,'y':_dot(w[path],x)+rng.gauss(0,NOISE_H),'w':{k:list(v) for k,v in w.items()}})
    return out

@contextlib.contextmanager
def _home(**kw):
    old=dict(H.HOME);H.HOME.update(kw)
    try:yield
    finally:H.HOME.clear();H.HOME.update(old)

def run_homeo(stream,arm,rng_seed=0,gain_pool=None):
    """Harness bookkeeping per night: activations = cumulative touches per path (neuromod snapshot), updates = touches
    since the previous night (each touch is one shadow update), useful = paths whose error was < .25 at an earlier night
    (stands in for tagged/stable/confirmed). The gains feed the step size directly (homeostasis ACTIVE)."""
    rng=random.Random(rng_seed);theta={p:[0.]*DIM for p in PATHS};gains={p:1. for p in PATHS};acts={p:0 for p in PATHS};upd={p:0 for p in PATHS}
    prev=None;useful=set();track={p:[] for p in PATHS};dom=[];rev=[];used=[]
    for ev in stream:
        p=ev['path'];acts[p]+=1;upd[p]+=1
        theta[p]=_nlms(theta[p],ev['x'],ev['y'],LR_H*gains[p])
        cur={q:_err(theta[q],ev['w'][q]) for q in PATHS}
        if ev['phase']!='pre':
            for q in PATHS:track[q].append(cur[q])
            if ev['phase']=='skewed':dom.append(cur[DOMINANT])
            if ev['phase']=='revived' and ev['t']<H_PHASES[2][0]+150:rev.append(cur[REVIVED])
        if (ev['t']+1)%NIGHT==0:
            snap={'activations':dict(acts),'useful':sorted(useful)}
            if arm in ('v13','v13_no_reopen','v13_no_dominant','random_gains'):
                kw={'dominant_path_inhibition':0.} if arm=='v13_no_dominant' else {}
                if arm=='v13_no_reopen':snap['useful']=[]
                with _home(**kw):rep=H.regulate(prev,snap,gains,upd,{})
                new={q:rep['paths'][q]['gain'] for q in PATHS}
                if arm=='random_gains':
                    vals=list((gain_pool or {}).get(ev['t'],new.values()));rng.shuffle(vals);new=dict(zip(PATHS,vals))
                gains=new
            elif arm=='equalize':
                d={q:acts[q]-(prev or {}).get('activations',{}).get(q,0) for q in PATHS};tot=sum(d.values());n=sum(1 for v in d.values() if v)
                gains={q:min(H.GAIN_MAX,max(H.GAIN_MIN,(1/n)/(d[q]/tot))) if d[q] and tot and n else 1. for q in PATHS}
            used.append((ev['t'],[gains[q] for q in PATHS]))
            useful|={q for q in PATHS if cur[q]<.25};prev=snap;upd={q:0 for q in PATHS}
    return {'primary':round(_mean([_mean(v) for v in track.values()]),5),'dominant_error_skewed':round(_mean(dom),5),
            'revived_recovery_error':round(_mean(rev),5),'final_error':round(_mean([_err(theta[q],stream[-1]['w'][q]) for q in PATHS]),5),
            'gains_by_night':{t:g for t,g in used}}

# --- driver ---------------------------------------------------------------------------------------------------------
def _verdict(per_seed,arms,v='v13'):
    wins={a:sum(1 for s in per_seed if per_seed[s][v]['primary']<per_seed[s][a]['primary']) for a in arms if a!=v}
    beat=[a for a,n in wins.items() if n>=4]
    return {'wins_of_5':wins,'verdict':'SUPPORTED_SYNTHETIC' if len(beat)==len(wins) else ('PARTIAL' if beat else 'NOT_SUPPORTED'),'beats':beat}

def _summary(per_seed,arms):
    keys=[k for k,v in next(iter(per_seed.values()))['v13'].items() if isinstance(v,(int,float))]
    return {a:{k:{'mean':round(_mean([per_seed[s][a][k] for s in per_seed]),5),'sd':round(_sd([per_seed[s][a][k] for s in per_seed]),5)} for k in keys} for a in arms}

def run_all(seeds=SEEDS):
    meta={};homeo={}
    for s in seeds:
        st=meta_stream(s);row={'v13':run_meta(st,'v13')}
        for a in META_ARMS[1:]:row[a]=run_meta(st,a,matched=row['v13']['mean_p'])
        meta[s]=row
        hs=homeo_stream(s);row={'v13':run_homeo(hs,'v13')}
        pool={int(t):g for t,g in row['v13']['gains_by_night'].items()}
        for a in HOMEO_ARMS[1:]:row[a]=run_homeo(hs,a,rng_seed=s,gain_pool=pool)
        homeo[s]=row
    return {'prereg':PREREG,'seeds':list(seeds),
            'meta':{'arms':META_ARMS,'per_seed':meta,'summary':_summary(meta,META_ARMS),**_verdict(meta,META_ARMS)},
            'homeostasis':{'arms':HOMEO_ARMS,'per_seed':homeo,'summary':_summary(homeo,HOMEO_ARMS),**_verdict(homeo,HOMEO_ARMS)},
            'claim_limit':'synthetic open-loop streams, linear NLMS learners (dim 4), no language model, BOOT knob values'}

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--prereg':
        out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(PREREG,indent=1));sys.exit(0)
    out=Path(sys.argv[1]);r=run_all();out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=1))
    for part in ('meta','homeostasis'):
        print(part,r[part]['verdict'],r[part]['wins_of_5'])
        for a,v in r[part]['summary'].items():print(' ',a,{k:x['mean'] for k,x in v.items()})
