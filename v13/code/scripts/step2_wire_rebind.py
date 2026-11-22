"""STEP2 re-binding after WP-W1 (schema key order on the llama-server wire).

Runs the unchanged preregistered STEP2 harness (tests/integration_step2_utility.py,
10 episodes x 7 variants) on one installed home in one of two wire arms:

  w1      live runners.wire_json (keeps schema key order; offers write summary before quotes)
  sorted  runners.wire_json replaced by the pre-W1 sorted serialisation (common.dumps)

Everything else (models, runner, fixtures, scoring, gate) is identical, so the two
cohorts isolate the wire. The harness gate decides PASS/FAIL; `diagnose` adds the
preregistered secondary measurements (earlier-rule transport, action mix). See
docs/proofs/continuation-20261012/step2-wire-rebind/PREREG.md.
"""
import argparse
import json
import re
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from v13 import runners
from v13.common import dumps,atomic_write

ARMS=('w1','sorted')

def set_arm(arm):
    if arm not in ARMS:raise ValueError('arm: '+'|'.join(ARMS))
    if arm=='sorted':runners.wire_json=dumps  # exact pre-W1 request bytes (3316a10 replaced dumps with wire_json)
    return {'arm':arm,'wire_function':runners.wire_json.__module__+'.'+runners.wire_json.__name__}

def prior_budget(fixture):
    m=re.search(r'Budget (\d+) euros',fixture['prior']);return int(m.group(1)) if m else None

def diagnose(report):
    """Secondary, preregistered: does the earlier rule reach C3, and what does C3 decide."""
    fixtures={f['id']:f for f in report['fixtures']};out={}
    for variant in sorted({r['variant'] for r in report['rows']}):
        rows=[r for r in report['rows'] if r['variant']==variant];n=len(rows)
        quote=hypo=0;actions={};exact=0
        for r in rows:
            f=fixtures[r['fixture']];pb=prior_budget(f)
            ctx=json.loads(r['consumer_messages'][1]['content']) if r.get('consumer_messages') else {'analysts':[]}
            if pb is not None and any(f'Budget {pb} euros' in q for a in ctx['analysts'] for q in a['verified_quotes']):quote+=1
            if pb is not None and any(re.search(r'(?<!\d)%d(?!\d)'%pb,dumps(a['hypothesis'])) for a in ctx['analysts']):hypo+=1
            try:act=json.loads(r.get('raw_answer') or '{}').get('action','INVALID')
            except ValueError:act='INVALID'
            actions[act]=actions.get(act,0)+1;exact+=bool(r.get('score',{}).get('exact'))
        out[variant]={'rows':n,'prior_budget_quote_reaches_c3':quote,'prior_budget_in_analyst_hypothesis':hypo,'actions':actions,'exact':exact}
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--installed-home',required=True);p.add_argument('--out',required=True)
    p.add_argument('--arm',required=True,choices=ARMS);p.add_argument('--fixtures',type=int,choices=range(1,11));p.add_argument('--resume',action='store_true')
    a=p.parse_args();arm=set_arm(a.arm)
    import integration_step2_utility as step2
    report=step2.run_locked(a.installed_home,a.out,a.fixtures,a.resume)
    report['wire_arm']=arm;report['wire_diagnosis']=diagnose(report)
    atomic_write(Path(a.out),json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({'arm':a.arm,'status':report['status'],'mean_utility':report.get('paired',{}).get('mean_utility'),'diagnosis':report['wire_diagnosis']},indent=1))

if __name__=='__main__':main()
