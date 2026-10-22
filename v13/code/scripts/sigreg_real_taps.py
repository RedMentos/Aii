"""WP-S4 rest: EMA vs. SIGReg vs. both on actual native B1 token states.

The unchanged runtime worker `v13.predictor_worker.train` is called on real
per-token final states of B1 LFM2.5-1.2B (llama.cpp b10964, pooling none),
captured by Thread J for B3-L1 attempt 3 (`bench-results/b3-l1-v3-20261012/
states.npz`, 600 synthetic hand-over notes). Pairs follow `learning.py`
exactly: context token i, future token i+2, i = 3, 6, 9, ...; one source group
per note. Only the anti-collapse mode differs inside a fold.

Subcommands:
  smoke   dev notes 0..79 only, never used by the preregistered arms
  prereg  freeze arms, data/code hashes and decision rule before any test run
  run     execute the preregistered arms (resumable, hash-checked)
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.common import APP,atomic_write,dumps,file_hash
from v13.config import KNOBS
from v13 import predictor_worker as PW

DATA=APP.parent/'bench-results/b3-l1-v3-20261012/states.npz'
DATA_SHA256='df80c17b7eaaa01adf0c8690b8a343f65818d67e55e71644cd68f6208dc587d2'
DEV_NOTES=range(0,80)
SPLIT_SEED=20261012
MODES=('ema','sigreg','both')
REGIMES={'R16':16,'R64':64}
FOLDS=5
SHRINK=.02
RUNTIME={k:KNOBS[k][0] for k in ('predictor_lr','ema_decay','max_update_norm','retention_max_delta','predictor_steps')}
# Knob maxima from v13/config.py: the largest budget the runtime would ever allow.
STRESS=RUNTIME|{'predictor_lr':KNOBS['predictor_lr'][3],'max_update_norm':KNOBS['max_update_norm'][3],'predictor_steps':KNOBS['predictor_steps'][3]}
BUDGETS={'runtime':RUNTIME,'stress':STRESS}
SIGREG={'sigreg_weight':1.,'sigreg_projections':32}
DECISION=('Separately per budget. A mode M in {sigreg,both} BEATS_EMA when, over both regimes x 5 folds (10 runs): '
 '(1) healthy start: commit_eligible(M) >= 8 and >= commit_eligible(ema); median held-out prediction_mse/copy_baseline_mse of M <= that of ema; '
 'median in-batch retrieval top-1 of M >= that of ema; (2) shrunk start: noncollapse_pass(M) >= 8 and > noncollapse_pass(ema). '
 'If both qualify, the lower healthy median ratio wins. The runtime default changes from ema only if a mode BEATS_EMA on the runtime budget; '
 'a stress-only win is recorded as a hint, not a default change. Otherwise DEFAULT_STAYS_EMA. No other outcome changes code.')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load():
    if sha(DATA)!=DATA_SHA256:raise SystemExit('states.npz hash differs from the bound capture')
    with np.load(DATA,allow_pickle=False) as z:return z['Hs'],z['Ms']

def pairs(H,M,notes):
    contexts=[];futures=[];groups=[]
    for n in notes:
        v=H[n,:int(M[n].sum())].astype(np.float64)
        # Same pair rule as learning.Learner.shadow_predictor.
        for index in range(3,len(v)-2,3):contexts.append(v[index]);futures.append(v[index+2]);groups.append(f'note-{n}')
    return np.asarray(contexts),np.asarray(futures),groups

def folds():
    order=np.random.default_rng(SPLIT_SEED).permutation(np.arange(DEV_NOTES.stop,600)).tolist();out={};pos=0
    for regime,size in REGIMES.items():
        out[regime]=[sorted(order[pos+k*size:pos+(k+1)*size]) for k in range(FOLDS)];pos+=FOLDS*size
    return out

def initial(dim,seed):
    # Exactly the projector train() draws for this seed.
    return np.linalg.qr(np.random.default_rng(seed).normal(size=(dim,16)))[0]

def retrieval(x,y,checkpoint):
    """Scale-free check comparable across modes: is the prediction nearest to its own future among held-out rows."""
    with np.load(checkpoint,allow_pickle=False) as z:p=z['projector'];q=z['predictor'];t=z['target']
    def top1(a,b):
        a=a/np.maximum(np.linalg.norm(a,axis=1,keepdims=True),1e-12);b=b/np.maximum(np.linalg.norm(b,axis=1,keepdims=True),1e-12)
        return float(np.mean(np.argmax(a@b.T,axis=1)==np.arange(len(a))))
    actual=y@t;return {'prediction_top1':top1((x@p)@q,actual),'copy_top1':top1(x@t,actual),'chance':1/len(x)}

def one(x,y,groups,cfg,start,folder):
    inp={'config':cfg,'context_states':x,'future_states':y,'source_groups':groups,'active_checkpoint':None}
    if start=='shrunk':
        p=initial(x.shape[1],cfg['seed'])*SHRINK;ck=Path(folder)/'shrunk.npz'
        np.savez(ck,projector=p,predictor=np.eye(16),target=p,anchor=p,horizon=np.asarray(2));inp['active_checkpoint']=str(ck)
    m=PW.train(inp,folder)
    order=list(dict.fromkeys(groups));held=order[-max(3,len(order)//4):];vi=np.isin(np.asarray(groups),held)
    xn=PW.normalize(x[vi]);yn=PW.normalize(y[vi]);a=m['after'];b=m['before']
    return {'commit_eligible':m['commit_eligible'],'noncollapse_pass':m['noncollapse_pass'],'predictive_ablation_pass':m['predictive_ablation_pass'],
            'retention_pass':m['retention_pass'],'gradient_check':m['gradient_check'],'deterministic_repeat':m['deterministic_repeat'],'checkpoint_reload':m['checkpoint_reload'],
            'train_pairs':m['train_pairs'],'held_out_pairs':m['held_out_pairs'],
            'ratio_copy':a['prediction_mse']/max(a['copy_baseline_mse'],1e-300),'ratio_shuffled':a['prediction_mse']/max(a['shuffled_target_mse'],1e-300),
            'before':{k:b[k] for k in ('prediction_mse','copy_baseline_mse','target_std_mean','effective_rank')}|{'context_isotropy':b['context_embedding']['isotropy']},
            'after':{k:a[k] for k in ('prediction_mse','copy_baseline_mse','shuffled_target_mse','target_std_mean','target_std_ratio','effective_rank','predicted_std_mean')}
                   |{'context_isotropy':a['context_embedding']['isotropy'],'context_participation_rank':a['context_embedding']['participation_rank'],
                     'target_isotropy':a['target_embedding']['isotropy'],'target_participation_rank':a['target_embedding']['participation_rank']},
            'retrieval':retrieval(xn,yn,Path(folder)/'candidate.npz'),'telemetry_last':m['history']['collapse_telemetry'][-1],'duration_s':m['duration_s']}

def arms():
    out=[]
    for budget in BUDGETS:
        for regime in REGIMES:
            for fold in range(FOLDS):
                for start in ('healthy','shrunk'):
                    for mode in MODES:out.append(f'{budget}/{regime}/f{fold}/{start}/{mode}')
    return out

def config(budget,fold,mode):return dict(BUDGETS[budget])|SIGREG|{'seed':fold+1,'predictor_regularizer':mode}

def code_hashes():
    return {str(p.relative_to(APP)):file_hash(p) for p in (Path(__file__).resolve(),APP/'v13/predictor_worker.py',APP/'v13/config.py')}

def summarize(results):
    def med(v):return float(np.median(v)) if v else None
    out={};decision={}
    for budget in BUDGETS:
        table={}
        for mode in MODES:
            rows={s:[r for k,r in results.items() if k.startswith(budget+'/') and k.endswith(f'/{s}/{mode}')] for s in ('healthy','shrunk')}
            table[mode]={s:{'runs':len(r),'commit_eligible':sum(x['commit_eligible'] for x in r),'noncollapse_pass':sum(x['noncollapse_pass'] for x in r),
                            'predictive_ablation_pass':sum(x['predictive_ablation_pass'] for x in r),'retention_pass':sum(x['retention_pass'] for x in r),
                            'median_ratio_copy':med([x['ratio_copy'] for x in r]),'median_top1':med([x['retrieval']['prediction_top1'] for x in r]),
                            'median_copy_top1':med([x['retrieval']['copy_top1'] for x in r]),'median_target_std':med([x['after']['target_std_mean'] for x in r]),
                            'median_context_isotropy':med([x['after']['context_isotropy'] for x in r])} for s,r in rows.items()}
        ok=[]
        if all(table[m]['healthy']['runs']==FOLDS*len(REGIMES) for m in MODES):
            e=table['ema']
            for m in ('sigreg','both'):
                h=table[m]['healthy'];s=table[m]['shrunk']
                if (h['commit_eligible']>=8 and h['commit_eligible']>=e['healthy']['commit_eligible'] and h['median_ratio_copy']<=e['healthy']['median_ratio_copy']
                    and h['median_top1']>=e['healthy']['median_top1'] and s['noncollapse_pass']>=8 and s['noncollapse_pass']>e['shrunk']['noncollapse_pass']):ok.append(m)
            ok.sort(key=lambda m:table[m]['healthy']['median_ratio_copy'])
            decision[budget]=('BEATS_EMA:'+ok[0]) if ok else 'EMA_NOT_BEATEN'
        else:decision[budget]='INCOMPLETE'
        out[budget]=table
    verdict=('CHANGE_DEFAULT_TO_'+decision['runtime'].split(':')[1].upper()) if decision.get('runtime','').startswith('BEATS_EMA') else \
            'INCOMPLETE' if 'INCOMPLETE' in decision.values() else 'DEFAULT_STAYS_EMA'
    return {'tables':out,'per_budget':decision,'verdict':verdict}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('cmd',choices=['smoke','prereg','run']);ap.add_argument('--out',type=Path,default=APP/'docs/proofs/continuation-20261012/sigreg-real-taps');a=ap.parse_args()
    H,M=load();a.out.mkdir(parents=True,exist_ok=True);prereg=a.out/'preregistration.json'
    if a.cmd=='smoke':
        x,y,g=pairs(H,M,DEV_NOTES[:16]);res={}
        for mode in MODES:
            with tempfile.TemporaryDirectory() as t:s=time.monotonic();res[mode]=one(x,y,g,config('runtime',0,mode),'healthy',t);res[mode]['wall_s']=time.monotonic()-s
        print(dumps({m:{k:r[k] for k in ('commit_eligible','ratio_copy','retrieval','wall_s')} for m,r in res.items()}));return 0
    if a.cmd=='prereg':
        if prereg.exists():raise SystemExit('preregistration exists; never overwrite')
        body={'package':'WP-S4 rest: SIGReg vs EMA on actual native taps','created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
              'data':{'path':str(DATA.relative_to(APP.parent)),'sha256':DATA_SHA256,'source':'B1 LFM2.5-1.2B per-token final states, llama.cpp b10964 /embeddings pooling none, Thread J b3_l1_v3_bench.py',
                      'pair_rule':'learning.py: context i, future i+2, i=3,6,9..; group=note','dev_notes_excluded':[DEV_NOTES.start,DEV_NOTES.stop]},
              'split_seed':SPLIT_SEED,'folds':folds(),'budgets':BUDGETS,'sigreg':SIGREG,'shrunk_scale':SHRINK,'modes':MODES,'arms':arms(),
              'worker':'v13.predictor_worker.train unchanged (held-out = last quarter of groups, its own commit gates)','code_sha256':code_hashes(),'decision_rule':DECISION}
        atomic_write(prereg,json.dumps(body,indent=1));print(hashlib.sha256(prereg.read_bytes()).hexdigest());return 0
    reg=json.loads(prereg.read_text())
    if reg['code_sha256']!=code_hashes() or reg['folds']!=folds():raise SystemExit('code or folds differ from preregistration')
    path=a.out/'results.json';state=json.loads(path.read_text()) if path.exists() else {'preregistration_sha256':sha(prereg),'results':{}}
    for arm in reg['arms']:
        if arm in state['results']:continue
        budget,regime,fold,start,mode=arm.split('/');x,y,g=pairs(H,M,reg['folds'][regime][int(fold[1:])])
        with tempfile.TemporaryDirectory() as t:state['results'][arm]=one(x,y,g,config(budget,int(fold[1:]),mode),start,t)
        state['summary']=summarize(state['results']);atomic_write(path,json.dumps(state,indent=1));print(arm,state['results'][arm]['commit_eligible'],round(state['results'][arm]['ratio_copy'],4),flush=True)
    print(dumps(state['summary']['per_budget']),state['summary']['verdict']);return 0

if __name__=='__main__':sys.exit(main())
