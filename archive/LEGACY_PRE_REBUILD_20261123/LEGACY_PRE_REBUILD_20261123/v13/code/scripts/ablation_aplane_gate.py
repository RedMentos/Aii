"""§99-style ablation without a language model for the §102 UNTESTED_LABEL row MODULE_APLANE (WP-T4 A3 student T2
fallback, thread L, 2026-10-12): does the agreement + retention gate let the student route only while it is reliable?

Real `aplane.student_gate`, `set_student_mode` and `student_fallback` (auto-demotion) on a fresh SQLite store with
real StudentEvaluation packets; only the runtime is a stub (`learner.student_route` returns the student's route).
3000 turns per seed. The teacher path is available with p .90: then the student's route is compared (StudentEvaluation,
agreement = student right). With p .10 the teacher is unavailable and a fallback decides: student route (right with the
student's hidden accuracy) or the scaffold route (right with p .60). Hidden student accuracy rises from .70 to .95 over
the first 500 turns; then two degradations (accuracy .50 for 150 turns each, random non-overlapping starts after turn 800).
A simulated user tries `:aplane student fallback` every 100 turns (refused by the real gate when it does not hold).
Arms (same turns per seed):
  gated        real student_fallback (gate: n >= 50, agreement >= .90, recent 25 not worse than earlier by > .05)
  always       the student always routes on fallback
  never        the scaffold always routes on fallback
  rate_only    same gate without the retention check (agreement window only)
PREREG (fixed before the first run): primary = accuracy on teacher-unavailable turns after turn 100. "helps" only if
gated beats always, never and rate_only in >= 4/5 seeds -> SUPPORTED_SYNTHETIC; some -> PARTIAL; none -> NOT_SUPPORTED.
Claim limit: synthetic agreement process, teacher assumed right, BOOT gate knobs; distillation head and reliance curve untested.
"""
import json
import random
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.ablation99 import SEEDS,_mean,_sd,_store
from v13 import aplane as AP
from v13.contracts import packet

PREREG={'schema':'ABLATION_APLANE_GATE_PREREG_V1','seeds':list(SEEDS),'turns':3000,'p_teacher_available':.90,'scaffold_accuracy':.60,
        'student_accuracy':'.70 -> .95 over 500 turns, then two drops to .50 for 150 turns (starts after 800)','user_promote_every':100,
        'primary':'accuracy on teacher-unavailable turns after turn 100',
        'win_rule':'gated beats always, never and rate_only in >=4/5 seeds -> SUPPORTED_SYNTHETIC; some -> PARTIAL; none -> NOT_SUPPORTED'}
T=3000;P_TEACHER=.9;SCAFFOLD=.6;PROMOTE_EVERY=100;ARMS=('gated','always','never','rate_only')

def world(seed):
    rng=random.Random(seed);drops=[]
    while len(drops)<2:
        s=rng.randint(800,T-150)
        if all(abs(s-d)>=150 for d in drops):drops.append(s)
    out=[]
    for t in range(T):
        acc=.5 if any(d<=t<d+150 for d in drops) else (.7+.25*min(1.,t/500))
        out.append({'teacher':rng.random()<P_TEACHER,'student_right':rng.random()<acc,'scaffold_right':rng.random()<SCAFFOLD})
    return out,drops

def rate_only_gate(store):
    g=_real_gate(store);g['pass']=g['n']>=AP.GATE_N and g['agreement'] is not None and g['agreement']>=AP.GATE_AGREE;return g
_real_gate=AP.student_gate

def run_arm(w,arm):
    turns,_=w;ok=[]
    with tempfile.TemporaryDirectory() as d:
        store,cfg=_store(Path(d));session=store.new_session('ablation');cur={}
        r=SimpleNamespace(store=store,learner=SimpleNamespace(student_route=lambda e:{'route':'detail' if cur['right'] else 'gist'}))
        patch=mock.patch.object(AP,'student_gate',rate_only_gate) if arm=='rate_only' else mock.patch.object(AP,'GATE_N',AP.GATE_N)
        with patch:
            for t,q in enumerate(turns):
                if arm in ('gated','rate_only') and t%PROMOTE_EVERY==0:
                    try:AP.set_student_mode(store,'fallback')
                    except ValueError:pass
                e=store.event(session,f'turn {t}')
                if q['teacher']:
                    p=packet('StudentEvaluation','C2_CONTROL',e['event_id'],store.generation_id,[e['source_ref']],percept_packet_id='pkt_'+e['event_id'],
                             source_ref=e['source_ref'],student_route='detail' if q['student_right'] else 'gist',teacher_route='detail',
                             agreement=q['student_right'],routing_authority=0)
                    store.add_packet('StudentEvaluation',p);continue
                if arm=='always':right=q['student_right']
                elif arm=='never':right=q['scaffold_right']
                else:
                    cur['right']=q['student_right'];fb=AP.student_fallback(r,e,{})
                    right=q['student_right'] if fb else q['scaffold_right']
                if t>=100:ok.append(right)
        store.close()
    return {'primary':round(_mean(ok),5),'fallback_turns':len(ok)}

def run_all(seeds=SEEDS):
    per={s:{a:run_arm(world(s),a) for a in ARMS} for s in seeds}
    wins={a:sum(per[s]['gated']['primary']>per[s][a]['primary'] for s in seeds) for a in ARMS[1:]}
    beat=[a for a,n in wins.items() if n>=4]
    return {'prereg':PREREG,'per_seed':per,'drops':{s:world(s)[1] for s in seeds},'wins_of_5':wins,
            'summary':{a:{'mean':round(_mean([per[s][a]['primary'] for s in seeds]),4),'sd':round(_sd([per[s][a]['primary'] for s in seeds]),4)} for a in ARMS},
            'verdict':'SUPPORTED_SYNTHETIC' if len(beat)==3 else ('PARTIAL' if beat else 'NOT_SUPPORTED'),
            'claim_limit':'synthetic agreement process, teacher assumed right, BOOT gate knobs; distillation head and reliance curve untested'}

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--prereg':
        out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(PREREG,indent=1));sys.exit(0)
    r=run_all();out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=1))
    print(r['verdict'],r['wins_of_5'],r['summary'])
