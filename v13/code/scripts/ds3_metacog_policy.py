"""WP-DS3: calibrated uncertainty chooses answer / recheck with the local tool / say "unsicher" (lab measurement).

Inputs are R4 typed-recipe captures (scripts/r4_typed_recipe.py capture): per task the normal C3 turn (pass1, with the
digit-token logprob features of R4 part 3), the fixed recipe tool result if the BOOT rule proposes one, and the turn
with the exact tool result appended (pass3). Nothing is generated here; the policy is scored on the recorded turns.

Confidence c = exp(digit_min_logprob) of the answer that would be given (1 when it has no digit token). AG9
metacognition is per component (agi/metacog.Metacognition._fit: histogram + pool-adjacent-violators), fitted on dev
captures only: 'no_tool' maps pass1 confidence to P(pass1 correct) on tasks without a tool result, 'after_tool' maps
pass3 confidence to P(pass3 correct) on tasks with one. Policies per task:
  c3_alone        answer pass1
  recipe_always   pass3 when the tool ran, else pass1                       (R4 part 5 winner, no abstention)
  ds3             like recipe_always, but say "unsicher" (abstain) when the calibrated P(correct) of that answer
                  is below T_ABSTAIN (chosen on dev)
Design note: a first draft used one pooled calibrator of the pass1 confidence for both decisions; on dev its best
thresholds were "never abstain" (= recipe_always), because low pass1 confidence sits on the tool tasks the recipe
already fixes. It was replaced by the per-component version before any fresh capture was read.
Scores: correct +1, abstain 0, wrong answer -LAMBDA (a confident wrong answer is worse than saying "unsicher").
  prereg    ds3_metacog_policy.py prereg <dev.json>... <prereg.json>      (choose T_TOOL, T_ABSTAIN on dev only)
  evaluate  ds3_metacog_policy.py evaluate <prereg.json> <fresh.json>... <report.json>
Claim limit: generated English R4 tasks, regex checks, cloud CPU; "unsicher" is scored as an abstention, the model
does not phrase it; no runtime change."""
import hashlib
import json
import math
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.agi.metacog import Metacognition,BINS  # noqa: E402

LAMBDA=1.;LAMBDA_REPORT=2.;FRESH_SEEDS=(31,37)
POLICIES=('c3_alone','recipe_always','ds3')
DECISION=('Fresh seeds 31+37 (120 tasks). H1 calibration: AUROC of c for "final answer wrong" >= .70 and ECE of the dev-fitted '
          'calibrator <= .15. H2 utility: ds3 utility (LAMBDA=1) >= recipe_always + 5 and ds3 wrong answers <= 0.7 x '
          'recipe_always wrong answers, with answered share >= .70. H3 abstention precision: of the abstained tasks >= 60 % '
          'would have been wrong under recipe_always. H4 kept answers: ds3 correct >= recipe_always correct - 6. '
          'DS3_SUPPORTED when H1..H4 all pass, else the failing parts are named. LAMBDA=2 is reported, not judged.')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def conf(turn):
    f=turn['features'];return 1. if not f else min(1.,math.exp(f['digit_min_logprob']))
def final(row):
    """(component, turn) of the answer recipe_always would give."""
    return ('after_tool',row['pass3']) if row['pass3'] is not None else ('no_tool',row['pass1'])
def calibrators(rows):
    pairs={}
    for r in rows:
        comp,t=final(r);pairs.setdefault(comp,[]).append([conf(t),int(t['pass'])])
    return {k:Metacognition._fit(v) for k,v in sorted(pairs.items())}
def cal(tables,comp,c):
    t=tables.get(comp);return 1. if not t else t[min(BINS-1,int(c*BINS))]  # uncalibrated component: never abstain
def decide(row,tables,t_abstain):
    """('answer'|'tool'|'abstain', correct or None)."""
    comp,t=final(row);act='tool' if comp=='after_tool' else 'answer'
    if cal(tables,comp,conf(t))<t_abstain:return 'abstain',None
    return act,t['pass']
def outcomes(rows,policy,tables=None,t_abstain=0.):
    if policy=='c3_alone':return [('answer',r['pass1']['pass']) for r in rows]
    if policy=='recipe_always':return [decide(r,{},0.) for r in rows]
    return [decide(r,tables,t_abstain) for r in rows]
def score(outs,lam=LAMBDA):
    right=sum(o is True for _,o in outs);wrong=sum(o is False for _,o in outs);ab=sum(o is None for _,o in outs)
    return {'correct':right,'wrong':wrong,'abstain':ab,'tool':sum(a=='tool' for a,_ in outs),'answered_share':round((right+wrong)/len(outs),4),
            'utility':round(right-lam*wrong,3),'utility_lambda2':round(right-LAMBDA_REPORT*wrong,3)}
def auroc(scores,labels):
    """P(score of a positive > score of a negative), ties count half; positive = label True."""
    pos=[s for s,l in zip(scores,labels) if l];neg=[s for s,l in zip(scores,labels) if not l]
    if not pos or not neg:return None
    return round(sum((p>n)+.5*(p==n) for p in pos for n in neg)/(len(pos)*len(neg)),4)
def ece(pairs,bins=BINS):
    b={}
    for p,y in pairs:b.setdefault(min(bins-1,int(p*bins)),[]).append((p,y))
    return round(sum(abs(sum(p for p,_ in v)/len(v)-sum(y for _,y in v)/len(v))*len(v) for v in b.values())/len(pairs),4)
def load(paths,seeds_forbidden=()):
    rows=[];shas={}
    for p in paths:
        d=json.loads(Path(p).read_text())
        if d.get('kind')!='V13_R4_TYPED_RECIPE' or len(d['rows'])!=60 or d['task_seed'] in seeds_forbidden:
            raise SystemExit('capture incomplete, wrong kind or a fresh seed used as dev: '+p)
        rows+=d['rows'];shas[str(d['task_seed'])]=sha(p)
    return rows,shas

def prereg(devs,out):
    rows,shas=load(devs,FRESH_SEEDS);tables=calibrators(rows)
    grid=sorted({0.}|{v for t in tables.values() if t for v in t}|{1.01})
    best=max(grid,key=lambda t:(score(outcomes(rows,'ds3',tables,t))['utility'],-t))
    dev={p:score(outcomes(rows,p,tables,best)) for p in POLICIES}
    body={'schema':'v13-ds3-metacog-prereg-v1','created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'dev_sha256':shas,
          'calibrators':tables,'t_abstain':best,'lambda':LAMBDA,'dev':dev,
          'dev_auroc_wrong':auroc([-conf(final(r)[1]) for r in rows],[not final(r)[1]['pass'] for r in rows]),
          'fresh_task_seeds':list(FRESH_SEEDS),'decision_rule':DECISION,'script_sha256':sha(__file__)}
    Path(out).write_text(json.dumps(body,indent=1));print(json.dumps(body,indent=1))

def evaluate(reg_path,fresh,out):
    reg=json.loads(Path(reg_path).read_text())
    if reg['script_sha256']!=sha(__file__):raise SystemExit('script changed since preregistration')
    rows=[];shas={}
    for p in fresh:
        d=json.loads(Path(p).read_text())
        if d['task_seed'] not in FRESH_SEEDS or len(d['rows'])!=60:raise SystemExit('fresh capture incomplete or wrong seed: '+p)
        rows+=d['rows'];shas[str(d['task_seed'])]=sha(p)
    if sorted(shas)!=sorted(map(str,FRESH_SEEDS)):raise SystemExit('need every fresh seed once')
    tables=reg['calibrators'];t=reg['t_abstain']
    res={p:score(outcomes(rows,p,tables,t)) for p in POLICIES}
    au=auroc([-conf(final(r)[1]) for r in rows],[not final(r)[1]['pass'] for r in rows])
    e=ece([(cal(tables,final(r)[0],conf(final(r)[1])),int(final(r)[1]['pass'])) for r in rows])
    ds3=outcomes(rows,'ds3',tables,t);ra=outcomes(rows,'recipe_always')
    ab=[i for i,(a,_) in enumerate(ds3) if a=='abstain'];ab_wrong=sum(ra[i][1] is False for i in ab)
    by_kind={}
    for r,(a,o) in zip(rows,ds3):
        k=r['fixture'].rstrip('0123456789');d=by_kind.setdefault(k,{'answer':0,'tool':0,'abstain':0,'correct':0,'wrong':0})
        d[a]+=1;d['correct']+=o is True;d['wrong']+=o is False
    D,R=res['ds3'],res['recipe_always']
    h={'H1_calibration':{'auroc_wrong':au,'ece':e,'pass':au is not None and au>=.70 and e<=.15},
       'H2_utility':{'ds3':D['utility'],'recipe_always':R['utility'],'ds3_wrong':D['wrong'],'recipe_wrong':R['wrong'],
                     'answered_share':D['answered_share'],
                     'pass':D['utility']>=R['utility']+5 and D['wrong']<=.7*R['wrong'] and D['answered_share']>=.70},
       'H3_abstain_precision':{'abstained':len(ab),'would_be_wrong':ab_wrong,'share':round(ab_wrong/len(ab),4) if ab else None,
                               'pass':bool(ab) and ab_wrong/len(ab)>=.6},
       'H4_kept_answers':{'ds3_correct':D['correct'],'recipe_correct':R['correct'],'pass':D['correct']>=R['correct']-6}}
    fails=[k for k,v in h.items() if not v['pass']]
    body={'prereg_sha256':sha(reg_path),'fresh_sha256':shas,'policies':res,'hypotheses':h,'ds3_by_kind':by_kind,
          'verdict':'DS3_SUPPORTED' if not fails else 'NOT_SUPPORTED: '+', '.join(fails),'phone_measured':False,'runtime_changed':False}
    Path(out).write_text(json.dumps(body,indent=1));print(json.dumps(body,indent=1))

if __name__=='__main__':
    a=sys.argv[1:]
    if a[0]=='prereg':prereg(a[1:-1],a[-1])
    else:evaluate(a[1],a[2:-1],a[-1])
