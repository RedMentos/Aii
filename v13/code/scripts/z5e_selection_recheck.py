"""WP-Z5e: does the focal selection (attention/coalition) earn its place on the FIXED live path (WP-Z5d context_fit)?

Preregistered in bench-results/z5e-selection-recheck-20261026/PREREGISTRATION.md before the main run.
Same long-session setup as z5_focal_controls.py --session (one session per repetition, effort max, bench mode,
history_turns 0, real organs), with two changes:
  * fresh tasks: repetition i uses utility_bench2.tasks(seed=TASK_SEEDS[i-1]), order shuffled with the same seed;
  * every replay arm gets the same size rule as the fixed live path (fit_arms): if its context would not fit the native
    window, earlier hypotheses are dropped oldest first, then the last layer items (one stays). Size alone no longer decides.
Verdict (selection question, see preregistration): KEEP / SIMPLIFY / NO_GAIN from paired sign tests of the coalition replay
against the simpler arms. FAIL stays FAIL: no rule is changed after the run.
Usage: z5e_selection_recheck.py <installed_home> <out.json> [--reps N] [--limit N]"""
import json
import random
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v13.common import atomic_write
import utility_bench2 as U2
import z5_focal_controls as Z

TASK_SEEDS=(71,72,73,74,75)
SIMPLER=('no_hypotheses','retrieval_only','fixed_slots','full_context')

def fixtures(seed,limit=None):
    fx=U2.tasks(seed)
    if limit:fx=[f for i,f in enumerate(fx) if i%(len(fx)//limit)==0][:limit]
    random.Random(seed).shuffle(fx)
    return fx

def decide(analysis,alpha=.05):
    """Preregistered selection verdict from the paired coalition-replay comparisons (decision arm = coalition replay,
    or coalition_live when replay fidelity < 0.95)."""
    p=analysis['paired'];v=analysis['verdict']
    worse=[a for a in SIMPLER if p.get('coalition_vs_'+a,{}).get('sign_test_p',1)<alpha and p['coalition_vs_'+a]['control_only']>p['coalition_vs_'+a]['coalition_only']]
    nh=p.get('coalition_vs_no_hypotheses',{})
    better_than_none=nh.get('sign_test_p',1)<alpha and nh.get('coalition_only',0)>nh.get('control_only',0)
    if worse:sel='SIMPLIFY'
    elif better_than_none:sel='KEEP'
    else:sel='NO_GAIN'
    best=max(SIMPLER,key=lambda a:analysis['summary'].get(a,{}).get('pass',-1))
    return {'selection':sel,'significantly_worse_than':worse,'better_than_no_hypotheses':better_than_none,
            'best_simpler_arm':best,'replay_fidelity':v['replay_fidelity'],'replay_caveat':v['replay_caveat']}

def main(installed,out,reps=5,limit=None):
    installed=Path(installed).resolve();out=Path(out)
    prev=json.loads(out.read_text()) if out.exists() else {}
    rows,measures,retention=prev.get('rows',[]),prev.get('measures',[]),prev.get('retention',[])
    done={x['rep'] for x in rows}
    for rep in range(1,reps+1):
        if rep in done:continue
        rr,mm,ret=Z.run_rep(installed,rep,fixtures(TASK_SEEDS[rep-1],limit),session_mode=True,fit_arms=True)
        rows+=rr;measures+=mm;retention.append(ret|{'rep':rep})
        a=Z.analyse(rows,measures,retention)
        atomic_write(out,json.dumps({'kind':'WP_Z5E_SELECTION_RECHECK','preregistration':'bench-results/z5e-selection-recheck-20261026/PREREGISTRATION.md',
            'task_seeds':TASK_SEEDS[:reps],'bench_cfg':U2.BENCH_CFG|{'effort':'max','history_turns':0,'context_fit':'active','fit_arms':True},
            'reps_done':sorted({x['rep'] for x in rows}),**a,'selection_verdict':decide(a),'rows':rows,'measures':measures,'retention':retention,
            'claim_limit':'generated English tasks, 5 task seeds, regex on the final answer, lexical retrieval, greedy bench decoding, cloud CPU'},indent=1))
    a=Z.analyse(rows,measures,retention)
    print(json.dumps({'verdict':a['verdict'],'selection_verdict':decide(a)},indent=1))

if __name__=='__main__':
    a=sys.argv[1:];reps=5;lim=None
    if '--reps' in a:i=a.index('--reps');reps=int(a[i+1]);del a[i:i+2]
    if '--limit' in a:i=a.index('--limit');lim=int(a[i+1]);del a[i:i+2]
    main(a[0],a[1],reps,lim)
