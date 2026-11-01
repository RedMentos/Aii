#!/usr/bin/env python3
"""WP-BP8: Age reopening with an independent noise signal. Software-only (see docs/BP8_AGE_REOPEN.md, preregistered before the run).
  PYTHONPATH=. python3 scripts/bp8_age_reopen.py --out bench-results/bp8-age-reopen-20261027 --seeds 401,402,403,404,405
"""
import argparse,json,math,random,sys,tempfile
from pathlib import Path
from v13 import ablation99 as A
from v13.age import AgeControl

WINDOW=A.WINDOW;PROBE=24;ARMS=('boot','stable_reopen','noise_mad','noise_indep','no_reopen','fixed_conservative','fixed_permissive')
LABEL_NOISE={'learn':.1,'noisy':1.,'shift':.1}

def measure(theta,w,phase,rng):
    """Competence from two independent replicate halves of a probe set; returns (competence, noise_signal)."""
    halves=[]
    for _ in range(2):
        res=[];ys=[]
        for _ in range(PROBE//2):
            x=[rng.gauss(0,1) for _ in range(A.DIM)];y=A._dot(w,x)+rng.gauss(0,LABEL_NOISE[phase])
            res.append((A._dot(theta,x)-y)**2);ys.append(y*y)
        halves.append(max(0.,1-A._mean(res)/max(1e-9,A._mean(ys))))
    return (halves[0]+halves[1])/2,abs(halves[0]-halves[1])/2

def run(stream,arm,home,seed):
    rng=random.Random(seed*7+1);ctl=None
    if arm in ('boot','stable_reopen','noise_mad','noise_indep','no_reopen'):
        store,cfg=A._store(Path(home));cfg['user_stage_cap']=5
        cfg['age_plasticity_policy']={'stable_reopen':'stable_reopen','noise_mad':'noise_aware','noise_indep':'noise_aware'}.get(arm,'boot');ctl=AgeControl(store,cfg,build_ceiling=5)
    theta=[0.]*A.DIM;errs={'learn':[],'noisy':[],'shift':[]};trace=[];prev=None;prev_theta=list(theta);fails=0;novel=True;win=[];stage_prev=0;false_dem=0
    for ev in stream:
        p=ctl.plasticity('language',novel_domain=novel,repeated_errors=0 if arm=='no_reopen' else fails) if ctl else A.FIXED[arm]
        theta=A._nlms(theta,ev['x'],ev['y'],A.LR0*.6*p);e=A._err(theta,ev['w']);errs[ev['phase']].append(e);win.append(e);trace.append((ev['t'],ev['phase'],e))
        if (ev['t']+1)%WINDOW==0:
            err=A._mean(win);win=[];comp,nsig=measure(theta,ev['w'],ev['phase'],rng)
            novel=prev is not None and err>2*prev and err>.1;passed=prev is None or err<=prev*1.1+.02;fails=0 if passed else fails+1
            if ctl:
                drift=math.sqrt(sum((a-b)**2 for a,b in zip(theta,prev_theta)))/max(1e-9,math.sqrt(A._dot(theta,theta)))
                m={'experience':ev['t']+1,'competence':comp,'stability':max(0.,1-drift),'retention':comp,'calibration':.8,'memory_health':.97,'safe_self_control':.999,'regression_pass':passed}
                if arm=='noise_indep':m['noise_signal']=nsig
                ctl.record('language',m,evidence_id='bp8-%d-%s'%(ev['t'],arm))
                st=ctl.state()[0]['capabilities']['language']['stage']
                if st<stage_prev and ev['phase']=='noisy':false_dem+=1
                stage_prev=st
            prev=err;prev_theta=list(theta)
    if ctl:ctl.s.close()
    shift_start=1000;rec=next((t-shift_start for t,ph,e in trace if ph=='shift' and e<.1),500)
    return {'noisy_err':A._mean(errs['noisy']),'shift_err':A._mean(errs['shift']),'learn_err':A._mean(errs['learn']),'recovery_steps':rec,'false_demotions_noisy':false_dem}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--seeds',default='401,402,403,404,405');a=ap.parse_args()
    seeds=[int(x) for x in a.seeds.split(',')];res={arm:[] for arm in ARMS}
    for s in seeds:
        st=A.age_stream(s)
        for arm in ARMS:
            with tempfile.TemporaryDirectory() as d:res[arm].append(run(st,arm,d,s))
    mean=lambda arm,k:A._mean([r[k] for r in res[arm]])
    Aa,B,C='noise_indep','boot','noise_mad'
    crit={'1_noisy_err_le_0.85_boot':(mean(Aa,'noisy_err'),.85*mean(B,'noisy_err')),
          '2_shift_err_le_1.10_boot':(mean(Aa,'shift_err'),1.10*mean(B,'shift_err')),
          '3_recovery_le_1.25_boot':(mean(Aa,'recovery_steps'),1.25*mean(B,'recovery_steps')),
          '4_false_demotions_le_min_boot_mad':(mean(Aa,'false_demotions_noisy'),min(mean(B,'false_demotions_noisy'),mean(C,'false_demotions_noisy'))),
          '5_shift_err_le_noise_mad':(mean(Aa,'shift_err'),mean(C,'shift_err')),
          '6a_noisy_err_le_fixed_conservative':(mean(Aa,'noisy_err'),mean('fixed_conservative','noisy_err')),
          '6b_shift_err_le_1.25_fixed_permissive':(mean(Aa,'shift_err'),1.25*mean('fixed_permissive','shift_err'))}
    out={k:{'value':round(v,4),'limit':round(l,4),'pass':v<=l} for k,(v,l) in crit.items()}
    verdict='BP8_AGE_REOPEN_SOFTWARE_PASS' if all(c['pass'] for c in out.values()) else 'BP8_AGE_REOPEN_SOFTWARE_FAIL'
    summary={arm:{k:round(mean(arm,k),4) for k in res[arm][0]} for arm in ARMS}
    o=Path(a.out);o.mkdir(parents=True,exist_ok=True);(o/'result.json').write_text(json.dumps({'verdict':verdict,'criteria':out,'summary':summary,'runs':res},indent=1,sort_keys=True))
    print(verdict);print(json.dumps(out,indent=1));print(json.dumps(summary,indent=1))
if __name__=='__main__':sys.exit(main())
