#!/usr/bin/env python3
"""WP-N7 / R6 measurement: re-prefill cost of the legacy context layout vs. the Context OS `stable_prefix` layout.

Needs a prepared V13_HOME with real models (e.g. after `cloud_bench.sh --smoke`). For each role it
1. probes the chat template (consecutive user messages kept in order? G6B capability),
2. replays the same scripted multi-turn conversation twice (legacy, stable_prefix) with changing volatile context,
3. records llama.cpp timings per turn (prompt_n = tokens re-prefilled, cache_n = tokens reused, prompt_ms).
Writes one JSON report. Fixed assistant replies keep both runs identical apart from the layout.

  V13_HOME=/tmp/v13-bench/home python3 scripts/context_cache_bench.py --roles C3_LANGUAGE B2_GIST --out report.json
"""
import argparse
import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.runtime import Runtime  # noqa: E402
from v13 import context_os as C  # noqa: E402
from v13.common import dumps  # noqa: E402

TURNS=[('My sister Lena lives in Graz and works as a nurse.','Noted: Lena lives in Graz and works as a nurse.'),
       ('Her shift starts at 06:30 on weekdays.','Got it, her weekday shift starts at 06:30.'),
       ('What city does Lena live in?','Lena lives in Graz.'),
       ('Remind me of her shift start.','Her weekday shift starts at 06:30.'),
       ('Suggest a short birthday message for her.','Happy birthday, Lena! Thank you for all the care you give.'),
       ('Make it a bit warmer.','Happy birthday, dear Lena! Your kindness lights up every room.')]

def run(r,role,layout,cancel):
    c=C.ContextOS(r.store,r.cfg);c.set_layout(layout)
    if layout!='legacy':c.set_capability(role,'consecutive_user',True,'bench_forced')
    runner=r.pool.get(role);stable='You are a concise assistant. Answer in one sentence.'
    # flush slot 0 so both layouts start cold
    list(runner.generate([{'role':'user','content':'flush '+layout}],cancel,time.monotonic()+120,max_tokens=1))
    hist=[];out=[]
    for i,(q,a) in enumerate(TURNS):
        e=r.store.event(r.session,q)['event_id']
        vol=[('ACTIVE_VIEW','\nRelevant memories: ',[{'topic':'turn','correction':'memory snapshot %d'%i}]),
             ('LATENT_STATE','\nTask context: ',{'turn':i,'open_questions':i%2})]
        plan=c.plan(e,role,stable,vol,hist,q)
        msgs=plan['planned']
        t0=time.monotonic();said=''.join(runner.generate(msgs,cancel,time.monotonic()+180,max_tokens=24));dt=time.monotonic()-t0
        tm=runner.last_metrics.get('timings',{})
        out.append({'turn':i,'prompt_tokens':runner.last_metrics.get('prompt_tokens'),'prompt_n':tm.get('prompt_n'),'cache_n':tm.get('cache_n'),
                    'prompt_ms':tm.get('prompt_ms'),'wall_s':round(dt,3),'est_reused_chars':plan['plan']['cache']['est_reused_chars_planned'],
                    'layout':plan['plan']['layout'],'fallback':plan['plan']['cache']['fallback_reason']})
        hist+=[{'event_id':e,'role':'user','text':q},{'event_id':e,'role':'assistant','text':said or a}]  # committed answer = what the body said
    tot=lambda k:sum(x[k] or 0 for x in out[1:])  # turn 0 is cold in both layouts
    return {'turns':out,'reprefill_tokens_after_turn0':tot('prompt_n'),'reused_tokens_after_turn0':tot('cache_n'),'prompt_ms_after_turn0':round(tot('prompt_ms'),1)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--roles',nargs='+',default=['C3_LANGUAGE']);ap.add_argument('--out',required=True)
    a=ap.parse_args();import os
    r=Runtime(Path(os.environ['V13_HOME']));cancel=threading.Event();report={'created':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'roles':{}}
    try:
        for role in a.roles:
            try:
                runner=r.pool.get(role);probe=C.probe_template(runner,cancel,time.monotonic()+180)
                res={'model':runner.model.name,'template_probe':probe}
                for layout in ('legacy','stable_prefix','append_only'):res[layout]=run(r,role,layout,cancel)
                lg=res['legacy']
                for lay in ('stable_prefix','append_only'):res['reprefill_saved_'+lay]=round(1-res[lay]['reprefill_tokens_after_turn0']/lg['reprefill_tokens_after_turn0'],4) if lg['reprefill_tokens_after_turn0'] else None
            except Exception as exc:res={'error':type(exc).__name__+': '+str(exc)[:300]}
            report['roles'][role]=res;print(role,dumps({k:v for k,v in res.items() if k not in {'legacy','stable_prefix','append_only'}}),flush=True)
    finally:
        r.close()
    Path(a.out).write_text(json.dumps(report,indent=1,ensure_ascii=False))

if __name__=='__main__':main()
