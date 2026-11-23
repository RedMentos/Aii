"""§99-style ablation without a language model for the §102 UNTESTED_LABEL row MODULE_WORKSPACE_LEARN (WP-U8 L3-B4,
thread L, 2026-10-12): does the learned per-kind hold multiplier reduce restore losses of a capacity-limited workspace?

Real `workspace_learn.observe` / `decay_factor` / `set_mode` on a fresh SQLite store; the workspace around it is harness
code that mirrors `focal.Workspace` (per-turn decay x BOOT turn_decay .6 x hold multiplier, capped at the slot's previous
decay; drop below .05; keep the highest-decay slots up to CAPACITY).
Each turn brings 3 new items (kind B1_DETAIL / B2_GIST / MEMORY, uniform). An item is needed again in each later turn
with a hidden kind probability (MEMORY .45, B1_DETAIL .20, B2_GIST .04) for up to 8 turns. A needed old item still in the
workspace is a useful hold (ACTIVE again); a needed old item no longer held is a restore loss (re-fetched fresh, as the
real loop does). Held items that are not needed are wasted holds.

Arms (same item stream per seed):
  learned      mode ACTIVE (explicit human): decay x learned multiplier per kind
  shadow       mode SHADOW (default): multiplier 1 (fixed BOOT decay); the loop still learns, unused
  shuffled     the learned multipliers of this turn assigned to the wrong kinds (rotation)
  hold_all     every kind gets the maximum multiplier 1.5 (blindly hold longer)
PREREG (fixed before the first run): primary = restore losses in the second half of the turns (lower is better).
"helps" only if learned beats every control in >= 4/5 seeds -> SUPPORTED_SYNTHETIC; some -> PARTIAL; none -> NOT_SUPPORTED.
Claim limit: synthetic reuse statistics per kind, harness workspace, BOOT knobs.
"""
import json
import random
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.ablation99 import SEEDS,_mean,_sd,_store
from v13 import workspace_learn as W

PREREG={'schema':'ABLATION_WORKSPACE_HOLD_PREREG_V1','seeds':list(SEEDS),'turns':400,'capacity':6,
        'reuse_per_turn':{'MEMORY':.45,'B1_DETAIL':.20,'B2_GIST':.04},'horizon_turns':8,
        'primary':'restore losses in the second half of the turns (lower is better)',
        'win_rule':'learned beats shadow, shuffled and hold_all in >=4/5 seeds -> SUPPORTED_SYNTHETIC; some -> PARTIAL; none -> NOT_SUPPORTED'}
KINDS=('B1_DETAIL','B2_GIST','MEMORY');REUSE=PREREG['reuse_per_turn'];HORIZON=8;TURNS=400;CAPACITY=6;NEW=3
TURN_DECAY=.6;DROP=.05
ARMS=('learned','shadow','shuffled','hold_all')

def stream(seed):
    """Per turn: new items (id, kind) and the set of old item ids needed again this turn."""
    rng=random.Random(seed);items={};turns=[];nid=0
    for t in range(TURNS):
        new=[]
        for _ in range(NEW):
            nid+=1;k=rng.choice(KINDS);iid=f'i{nid}';items[iid]=(k,t);new.append(iid)
        need={i for i,(k,t0) in items.items() if t0<t<=t0+HORIZON and rng.random()<REUSE[k]}
        turns.append({'new':new,'need':need})
    return {i:k for i,(k,_) in items.items()},turns

def run_arm(st,arm):
    kind,turns=st
    with tempfile.TemporaryDirectory() as d:
        store,cfg=_store(Path(d))
        if arm=='learned':W.set_mode(store,'ACTIVE','EXPLICIT_HUMAN')
        held={};old_slots=[];restores=0;wasted=0;useful=0;half=TURNS//2;mults=[]
        for t,tr in enumerate(turns):
            learned={k:W.multiplier(W._load(store)[0]['kinds'].get(k)) for k in KINDS}
            if arm=='learned':hold={k:W.decay_factor(store,k) for k in KINDS}
            elif arm=='shadow':hold={k:1. for k in KINDS}
            elif arm=='shuffled':hold={k:learned[KINDS[(i+1)%3]] for i,k in enumerate(KINDS)}
            else:hold={k:W.MULT_MAX for k in KINDS}
            mults.append(hold)
            # load: decay the held slots (focal.Workspace.load)
            for i,s in list(held.items()):
                s['decay']=min(s['decay'],s['decay']*TURN_DECAY*hold[kind[i]]);s['turns']+=1
                if s['decay']<DROP:del held[i]
            active=[];rest=[]
            for i,s in held.items():
                on=i in tr['need'];x={'payload_ref':i,'source_kind':kind[i],'state_type':'ACTIVE' if on else 'REACTIVATABLE','turns_retained':s['turns']}
                (active if on else rest).append(x)
                if t>=half:useful+=on;wasted+=not on
            for i in tr['need']:
                if i not in held:
                    active.append({'payload_ref':i,'source_kind':kind[i],'state_type':'ACTIVE','turns_retained':0});held[i]={'decay':1.,'turns':0}
                    if t>=half:restores+=1
            for i in tr['new']:
                active.append({'payload_ref':i,'source_kind':kind[i],'state_type':'ACTIVE','turns_retained':0});held[i]={'decay':1.,'turns':0}
            keep=sorted(held,key=lambda i:(-held[i]['decay'],i))[:CAPACITY]
            held={i:held[i] for i in keep}
            kept=[{'payload_ref':i,'source_kind':kind[i]} for i in keep]
            W.observe(store,active,rest,kept,old_slots);old_slots=kept
        final={k:W.multiplier(W._load(store)[0]['kinds'].get(k)) for k in KINDS}
        store.close()
    return {'primary':restores,'useful_holds':useful,'wasted_holds':wasted,'final_learned_multiplier':final,
            'mean_hold_second_half':{k:round(_mean([m[k] for m in mults[TURNS//2:]]),4) for k in KINDS}}

def run_all(seeds=SEEDS):
    per={s:{a:run_arm(stream(s),a) for a in ARMS} for s in seeds}
    wins={a:sum(per[s]['learned']['primary']<per[s][a]['primary'] for s in seeds) for a in ARMS if a!='learned'}
    beat=[a for a,n in wins.items() if n>=4]
    summ={a:{k:{'mean':round(_mean([per[s][a][k] for s in seeds]),3),'sd':round(_sd([per[s][a][k] for s in seeds]),3)} for k in ('primary','useful_holds','wasted_holds')} for a in ARMS}
    return {'prereg':PREREG,'per_seed':per,'summary':summ,'wins_of_5':wins,
            'verdict':'SUPPORTED_SYNTHETIC' if len(beat)==len(wins) else ('PARTIAL' if beat else 'NOT_SUPPORTED'),
            'claim_limit':'synthetic reuse statistics per kind, harness workspace mirroring focal.Workspace, BOOT knobs'}

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--prereg':
        out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(PREREG,indent=1));sys.exit(0)
    r=run_all();out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=1))
    print(r['verdict'],r['wins_of_5'])
    for a,v in r['summary'].items():print(' ',a,{k:x['mean'] for k,x in v.items()})
