#!/usr/bin/env python3
"""WP-BP7: six simulated weeks of memory use with nightly sleep. Software-only and synthetic (no model).

Preregistered in docs/BP7_SLEEP_CONSOLIDATION.md (committed before the first run). Arms: recon off vs active; Sleep-D checklist
off vs active on the nightly weight-update batch. Output: JSON + the criteria verdicts. Usage:
  PYTHONPATH=. python3 scripts/bp7_weeks_sim.py --out bench-results/bp7-weeks-sim-20261027 --seeds 301,302,303
"""
import argparse,hashlib,json,random,sys,tempfile
from pathlib import Path
from v13.runtime import Runtime
from v13.reconsolidation import Reconsolidation,DAY
from v13.ssgm import Checklist,private_hits
from v13.dream_policy import policy_items,fact_paraphrase_items,audit
from v13.agi.weights import WeightConsolidation

WEEKS=6;QUERIES=20;VERDICT_RATE=.3;T0=1_800_000_000.
PAIRS=12;UNIQUE=12;PRIVATE=[('Kontakt Anna Mail','anna.kern@example.org'),('Kontakt Ben Telefon','+49 170 5551234'),('Zugang Server Schluessel','sk-abcd1234efgh5678'),
                            ('Konto Bank','DE89 3704 0044 0532 0130 00'),('Notiz Passwort','passwort: hunter2-tiger'),('Kontakt Cem Mail','cem.arda@example.net')]

def run_arm(seed,recon_mode,checklist_mode,home):
    rng=random.Random(seed)  # all draws are arm-independent: same questions, same verdict propensity, same truth
    r=Runtime(Path(home));r.sleep.cycle.set_policy('enabled','off')
    clock=[T0];Reconsolidation.default_clock=staticmethod(lambda:clock[0])
    r.cfg.update(reconsolidation=recon_mode,sleep_d_checklist=checklist_mode,memory_threshold=.1)
    def add(q,v):
        e=r.store.event(r.session,q);mid=r.memory.feedback(e['event_id'],'fact',v,'learn')
        with r.store.tx() as c:c.execute('UPDATE memories SET created=? WHERE id=?',(clock[0],mid))
        return mid
    truth={};pair_q={};uniq_q={};order=[]
    for i in range(PAIRS):
        base=f'Projekt Pair{i} Budget';a,b=base+' Plan?',base+' Notiz?'
        first,second=(a,b) if rng.random()<.5 else (b,a)  # which entry is newer is random
        add(first,f'wert-{i}-erste');clock[0]+=1;add(second,f'wert-{i}-zweite');clock[0]+=1
        want=rng.choice([a,b]);pair_q[base]=want
    for i in range(UNIQUE):
        q=f'Projekt Solo{i} Vertrag?';add(q,f'solo-wert-{i}');uniq_q[f'Projekt Solo{i} Vertrag']=q;clock[0]+=1
    for k,v in PRIVATE:add(k+'?',v);clock[0]+=1
    def current():
        return {m['key_text']:(m['id'],m['value']) for m in r.store.rows("SELECT id,key_text,value FROM memories WHERE active=1")}
    corrections={7:('Projekt Solo0 Vertrag?','solo-neu-0'),21:('Projekt Solo1 Vertrag?','solo-neu-1')}
    # ids are random per run, so the hash covers content only
    snapshot=lambda:hashlib.sha256(json.dumps(sorted((m['key_text'],m['value'],m['active']) for m in r.store.rows('SELECT key_text,value,active FROM memories')),sort_keys=True).encode()).hexdigest()
    rows=[];staged_private=staged_leak=policy_in=policy_kept=0;stale=0
    for day in range(WEEKS*7):
        clock[0]=T0+day*DAY
        if day in corrections:
            q,v=corrections[day];add(q,v)
        cur=current();pair_hit=[0,0];uniq_hit=[0,0]
        for n in range(QUERIES):
            kind='pair' if rng.random()<.55 else 'uniq';propensity=rng.random()<VERDICT_RATE
            if kind=='pair':base=rng.choice(sorted(pair_q));q=base;want_key=pair_q[base]
            else:base=rng.choice(sorted(uniq_q));q=base;want_key=uniq_q[base]
            got=r.memory.recall(q,r.session,top_k=3)
            want=cur.get(want_key)
            hit=bool(got) and want is not None and got[0]['id']==want[0]
            if got and any(g['key_text'] in cur and cur[g['key_text']][1]!=g['value'] for g in got):stale+=1
            (pair_hit if kind=='pair' else uniq_hit)[0]+=int(hit);(pair_hit if kind=='pair' else uniq_hit)[1]+=1
            if propensity and got:
                e=r.store.event(r.session,q+' [urteil]')
                for g in got:
                    label='relevant' if want and g['id']==want[0] else 'irrelevant'
                    fid=r.memory.retrieval_feedback(e['event_id'],g['id'],label)
                    with r.store.tx() as c:c.execute('UPDATE feedback SET created=? WHERE id=?',(clock[0]+n,fid))
        # night: reconsolidation + the weight-update batch (memories + dreams) through the checklist
        Reconsolidation(r.store,r.cfg).sleep()
        mems=[m for m in r.store.rows("SELECT id,key_text,value FROM memories WHERE active=1")]
        cands=WeightConsolidation(r.store,r.cfg).candidates(require_replay_pass=False,cap=False)
        dreams=fact_paraphrase_items(rng.sample(mems,4),seed*1000+day)+policy_items(4,seed*1000+day)
        kept,rep=Checklist(r.store,r.cfg).run(cands+dreams)
        staged_private+=sum(1 for i in kept if private_hits((i.get('prompt') or '')+' '+(i.get('target') or '')))
        staged_leak+=sum(1 for i in kept if i.get('kind')=='dream_para')
        policy_in+=4;policy_kept+=sum(1 for i in kept if i.get('kind')=='dream_policy')
        rows.append({'day':day,'pair':pair_hit,'uniq':uniq_hit})
    w=Reconsolidation(r.store,r.cfg).weights(T0+WEEKS*7*DAY)
    sums=lambda sel,days:(sum(x[sel][0] for x in days),sum(x[sel][1] for x in days))
    per_week=[]
    for wk in range(WEEKS):
        d=rows[wk*7:(wk+1)*7];ph,pn=sums('pair',d);uh,un=sums('uniq',d)
        per_week.append({'week':wk+1,'pair_hit1':ph/pn if pn else None,'uniq_hit1':uh/un if un else None})
    last=rows[(WEEKS-2)*7:];ph,pn=sums('pair',last);uh,un=sums('uniq',last)
    out={'seed':seed,'recon':recon_mode,'checklist':checklist_mode,'per_week':per_week,'pair_hit1_w56':ph/pn,'uniq_hit1_w56':uh/un,'stale_returns':stale,
         'staged_private':staged_private,'staged_fact_leak':staged_leak,'policy_in':policy_in,'policy_kept':policy_kept,
         'weight_min':min(w.values()) if w else 1.,'weight_max':max(w.values()) if w else 1.,
         'review_list':[x['memory_id'] for x in Reconsolidation(r.store,r.cfg).review_list(T0+WEEKS*7*DAY)],
         'memory_hash':snapshot()}
    r.close();return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--seeds',default='301,302,303');a=ap.parse_args()
    seeds=[int(x) for x in a.seeds.split(',')];res=[]
    for s in seeds:
        for recon,ck in (('off','active'),('active','active'),('off','off')):
            with tempfile.TemporaryDirectory() as d:res.append(run_arm(s,recon,ck,d))
    by=lambda recon,ck:[x for x in res if x['recon']==recon and x['checklist']==ck]
    mean=lambda xs:sum(xs)/len(xs)
    A=by('off','active');B=by('active','active');C=by('off','off')
    crit={}
    gain=mean([b['pair_hit1_w56']-a['pair_hit1_w56'] for a,b in zip(A,B)])
    crit['1_pair_gain_ge_0.05']={'value':round(gain,4),'pass':gain>=.05}
    loss=mean([a['uniq_hit1_w56']-b['uniq_hit1_w56'] for a,b in zip(A,B)])
    crit['2_unique_loss_le_0.02']={'value':round(loss,4),'pass':loss<=.02}
    crit['3_stale_zero']={'value':sum(x['stale_returns'] for x in A+B),'pass':sum(x['stale_returns'] for x in A+B)==0}
    # criterion 4: recon must not rewrite memory rows: compare memory hash of arm A (no recon) and B (recon active) per seed
    same=all(a['memory_hash']==b['memory_hash'] for a,b in zip(A,B))
    crit['4_memory_unchanged_by_recon']={'value':same,'pass':same}
    p_on=sum(x['staged_private']+x['staged_fact_leak'] for x in A+B);p_off=min(sum(x['staged_private'] for x in C),sum(x['staged_fact_leak'] for x in C))
    crit['5_checklist_blocks_and_control_bites']={'value':{'active_leaks':p_on,'off_private':sum(x['staged_private'] for x in C),'off_fact_leak':sum(x['staged_fact_leak'] for x in C)},'pass':p_on==0 and p_off>0}
    keep=min(x['policy_kept']/x['policy_in'] for x in A+B)
    crit['6_policy_items_kept_ge_0.95']={'value':round(keep,4),'pass':keep>=.95}
    wmin=min(x['weight_min'] for x in B);wmax=max(x['weight_max'] for x in B)
    crit['7_weights_in_range']={'value':[round(wmin,4),round(wmax,4)],'pass':wmin>.5 and wmax<1.5}
    verdict='BP7_WEEKS_SIM_PASS' if all(c['pass'] for c in crit.values()) else 'BP7_WEEKS_SIM_FAIL'
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    (out/'result.json').write_text(json.dumps({'verdict':verdict,'criteria':crit,'runs':res},indent=1,sort_keys=True))
    print(verdict);print(json.dumps(crit,indent=1))
if __name__=='__main__':sys.exit(main())
