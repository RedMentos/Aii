"""§99-style ablation without a language model for the §102 UNTESTED_LABEL row MODULE_ATTENTION (thread L, 2026-10-12):
does the learned §4B.4 usefulness prior improve F1 admission under the event budget?

Real `attention.Attention` on a fresh SQLite store (requests, admission, outcomes and the per (reason,target) prior are
the unchanged module). Each event files 8 AttentionRequests with random target/reason; the budget grants 3. Every granted
request gets an outcome = hidden usefulness of its (reason,target) key + noise, reported through `Attention.outcome`
(as the runtime does). Hidden key means are drawn uniformly from [-1, 1] per seed and never shown to the module.

Arms (same request stream per seed):
  scaffold        mode SHADOW (default): rank by priority x target gain; the prior is learned but not used
  learned_active  mode ACTIVE (explicit human switch): the learned prior shifts the score by at most LEARNED_MAX
  random          random grant order (same budget)
  oracle          rank by the hidden key mean (upper bound, not a control the module can beat)
Streams: `blind` (priority uniform, carries no information) and `informed` (priority = .5 + .25 x hidden mean + noise).

PREREG (fixed before the first run): primary = mean hidden usefulness of granted requests over the second half of the
events. "Learned prior helps" only if learned_active beats scaffold in >= 4/5 seeds on BOTH streams; PARTIAL if on one;
NOT_SUPPORTED otherwise. Random and oracle are reported for scale. Claim limit: synthetic request stream, BOOT knobs.
"""
import json
import random
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.ablation99 import SEEDS,_mean,_sd,_store
from v13 import attention as A

PREREG={'schema':'ABLATION_ATTENTION_PRIOR_PREREG_V1','seeds':list(SEEDS),'events':300,'requests_per_event':8,'grants_per_event':3,
        'primary':'mean hidden usefulness of granted requests, second half of events','streams':['blind','informed'],
        'win_rule':'learned_active > scaffold in >=4/5 seeds on both streams -> SUPPORTED_SYNTHETIC; one stream -> PARTIAL; else NOT_SUPPORTED'}
EVENTS=300;PER=8;COST=64;BUDGET=3*COST;NOISE=.3
ARMS=('scaffold','learned_active','random','oracle')
REQ_TARGETS=('A_SOURCE','B1','B2','MEMORY','WORLD','TOOL','SELF');REQ_REASONS=A.REASONS

def stream(seed,kind):
    rng=random.Random(seed);means={(r,t):rng.uniform(-1,1) for r in REQ_REASONS for t in REQ_TARGETS};out=[]
    for _ in range(EVENTS):
        reqs=[]
        for _ in range(PER):
            r=rng.choice(REQ_REASONS);t=rng.choice(REQ_TARGETS);m=means[(r,t)]
            pr=rng.random() if kind=='blind' else min(1.,max(0.,.5+.25*m+rng.gauss(0,.15)))
            reqs.append({'reason':r,'target':t,'priority':pr,'outcome':max(-1.,min(1.,m+rng.gauss(0,NOISE)))})
        out.append(reqs)
    return means,out

def run_arm(st,arm,seed):
    means,events=st;rng=random.Random(seed*7+1)
    with tempfile.TemporaryDirectory() as d:
        store,cfg=_store(Path(d));att=A.Attention(store)
        if arm=='learned_active':att.set_mode('ACTIVE','EXPLICIT_HUMAN')
        session=store.new_session('ablation');got=[]
        for i,reqs in enumerate(events):
            e=store.event(session,f'event {i}');eid=e['event_id']
            if arm in ('random','oracle'):
                order=list(range(len(reqs)))
                if arm=='random':rng.shuffle(order)
                else:order.sort(key=lambda j:-means[(reqs[j]['reason'],reqs[j]['target'])])
                granted=order[:BUDGET//COST]
                if i>=EVENTS//2:got+=[means[(reqs[j]['reason'],reqs[j]['target'])] for j in granted]
                continue
            packets=[att.request(eid,'JEF',q['target'],q['reason'],priority=q['priority'],budget=COST) for q in reqs]
            resp=att.admit(eid,packets,budget=BUDGET)
            byid={p['packet_id']:q for p,q in zip(packets,reqs)}
            for rs in resp:
                if rs['status']!='GRANTED':continue
                q=byid[rs['request_packet_id']];att.outcome(rs['packet_id'],q['outcome'])
                if i>=EVENTS//2:got.append(means[(q['reason'],q['target'])])
        store.close()
    return {'primary':round(_mean(got),5),'granted':len(got)}

def run_all(seeds=SEEDS):
    res={}
    for kind in PREREG['streams']:
        per={}
        for s in seeds:
            st=stream(s,kind);per[s]={a:run_arm(st,a,s) for a in ARMS}
        wins=sum(per[s]['learned_active']['primary']>per[s]['scaffold']['primary'] for s in seeds)
        res[kind]={'per_seed':per,'learned_beats_scaffold_of_5':wins,
                   'summary':{a:{'mean':round(_mean([per[s][a]['primary'] for s in seeds]),5),'sd':round(_sd([per[s][a]['primary'] for s in seeds]),5)} for a in ARMS}}
    ok=[k for k in res if res[k]['learned_beats_scaffold_of_5']>=4]
    return {'prereg':PREREG,'streams':res,'verdict':'SUPPORTED_SYNTHETIC' if len(ok)==2 else ('PARTIAL' if ok else 'NOT_SUPPORTED'),
            'claim_limit':'synthetic request stream, hidden usefulness per (reason,target), BOOT knobs (LEARNED_MAX, POLICY_RATE)'}

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--prereg':
        out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(PREREG,indent=1));sys.exit(0)
    r=run_all();out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=1))
    print(r['verdict'])
    for k,v in r['streams'].items():print(k,v['learned_beats_scaffold_of_5'],{a:x['mean'] for a,x in v['summary'].items()})
