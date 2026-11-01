"""§99-style ablation without a language model for the §102 UNTESTED_LABEL row MODULE_EPISODIC_ROUTE (WP-U10 §9.1
"second time better", thread L, 2026-10-12): does one human route correction improve the route of the next very similar
request, without leaking to other entities?

Real `episodic_route.for_turn` (mode active) on a fresh SQLite store; corrections are written with the real
`Memory.feedback(event, 'route', value)` exactly as `:feedback route` does. Requests: 12 entities ("Projekt <Name>") x 4
tasks (simple / detail / gist / both) x 3 German paraphrases each. The scaffold route is the task's default; the hidden
true route differs from it for a (entity, task) cell with p .40 (a per-project preference, one of the other routes).
300 requests per seed, uniform cells and paraphrases; whenever the chosen route is wrong the human corrects it with p .50.

Arms (same request stream and correction draws per seed):
  episodic         episodic_route.for_turn, active (entity-aware memory.relevance >= MIN_RELEVANCE .6), else scaffold
  scaffold         the task default only (mode shadow/off)
  no_entity_guard  same, but relevance = plain term Jaccard (no entity check): shows what the entity guard buys
  latest_any       the newest correction of any request, regardless of similarity (recency without matching)
PREREG (fixed before the first run): primary = route accuracy over the second half of the requests. "helps" only if
episodic beats scaffold, no_entity_guard and latest_any in >= 4/5 seeds -> SUPPORTED_SYNTHETIC; some -> PARTIAL;
none -> NOT_SUPPORTED.
Claim limit: synthetic templated German requests, one session, BOOT MIN_RELEVANCE; no consolidation path.
"""
import json
import random
import sys
import tempfile
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.ablation99 import SEEDS,_mean,_sd,_store
from v13 import episodic_route as ER
from v13.memory import Memory,terms

PREREG={'schema':'ABLATION_EPISODIC_ROUTE_PREREG_V1','seeds':list(SEEDS),'requests':300,'entities':12,'tasks':4,'paraphrases':3,
        'p_preference':.40,'p_correct_when_wrong':.50,'primary':'route accuracy over the second half of the requests',
        'win_rule':'episodic beats scaffold, no_entity_guard and latest_any in >=4/5 seeds -> SUPPORTED_SYNTHETIC; some -> PARTIAL; none -> NOT_SUPPORTED'}
N=300;ARMS=('episodic','scaffold','no_entity_guard','latest_any')
NAMES=('Aurora','Borealis','Cassini','Delta','Eos','Fjord','Gaia','Helios','Iris','Juno','Kepler','Lyra')
TASKS={'simple':('Wann startet Projekt {e}?','Wann startet Projekt {e} genau?','Sag mir, wann Projekt {e} startet.'),
       'detail':('Erkläre Projekt {e} genau.','Erkläre Projekt {e} bitte genau.','Erkläre mir Projekt {e} ganz genau.'),
       'gist':('Fasse Projekt {e} kurz zusammen.','Fasse Projekt {e} bitte kurz zusammen.','Fasse mir Projekt {e} kurz zusammen.'),
       'both':('Vergleiche Details und Überblick von Projekt {e}.','Vergleiche bitte Details und Überblick von Projekt {e}.','Vergleiche für Projekt {e} Details und Überblick.')}

def world(seed):
    rng=random.Random(seed);truth={}
    for e in NAMES:
        for t in TASKS:truth[(e,t)]=rng.choice([x for x in ER.ROUTES if x!=t]) if rng.random()<.40 else t
    reqs=[]
    for _ in range(N):
        e=rng.choice(NAMES);t=rng.choice(sorted(TASKS));reqs.append({'text':rng.choice(TASKS[t]).format(e=e),'task':t,'truth':truth[(e,t)],'u':rng.random()})
    return reqs

def jaccard(a,b):
    ta,tb=terms(a),terms(b)
    return len(ta&tb)/len(ta|tb) if ta and tb else 0.

def run_arm(reqs,arm):
    ok=[]
    with tempfile.TemporaryDirectory() as d:
        store,cfg=_store(Path(d));mem=Memory(store,cfg);session=store.new_session('ablation');ER.set_mode(store,'active')
        patch=mock.patch.object(ER,'relevance',jaccard) if arm=='no_entity_guard' else mock.patch.object(ER,'MIN_RELEVANCE',ER.MIN_RELEVANCE)
        with patch:
            for i,q in enumerate(reqs):
                e=store.event(session,q['text']);route=None
                if arm in ('episodic','no_entity_guard'):route,_=ER.for_turn(store,q['text'],session)
                elif arm=='latest_any':
                    m=store.one("SELECT value FROM memories WHERE kind='route' AND active=1 ORDER BY created DESC, rowid DESC LIMIT 1")
                    route=m['value'] if m else None
                route=route or q['task']
                if i>=N//2:ok.append(route==q['truth'])
                if route!=q['truth'] and q['u']<.50:mem.feedback(e['event_id'],'route',q['truth'])
        store.close()
    return {'primary':round(_mean(ok),5)}

def run_all(seeds=SEEDS):
    per={s:{a:run_arm(world(s),a) for a in ARMS} for s in seeds}
    wins={a:sum(per[s]['episodic']['primary']>per[s][a]['primary'] for s in seeds) for a in ARMS[1:]}
    beat=[a for a,n in wins.items() if n>=4]
    return {'prereg':PREREG,'per_seed':per,'wins_of_5':wins,
            'summary':{a:{'mean':round(_mean([per[s][a]['primary'] for s in seeds]),4),'sd':round(_sd([per[s][a]['primary'] for s in seeds]),4)} for a in ARMS},
            'verdict':'SUPPORTED_SYNTHETIC' if len(beat)==3 else ('PARTIAL' if beat else 'NOT_SUPPORTED'),
            'claim_limit':'synthetic templated German requests, one session, BOOT MIN_RELEVANCE; no consolidation path'}

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--prereg':
        out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(PREREG,indent=1));sys.exit(0)
    r=run_all();out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=1))
    print(r['verdict'],r['wins_of_5'],r['summary'])
