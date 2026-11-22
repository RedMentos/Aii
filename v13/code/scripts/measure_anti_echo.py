#!/usr/bin/env python3
"""WP-V3 measurement: C3 'anti_echo' (v4 §65 decoder) versus 'legacy' sampling.

Same installed C3 model, same prompts, same seed; only `c3_sampling` differs. Every
answer is scored with guards.turn_metrics (query echo, repetition, type/token ratio,
min_new) and the benchmark's lexical checks. Diagnostic only; nothing is promoted.
"""
import argparse,importlib.util,json,sys,threading,time
from pathlib import Path

APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
from v13.config import initialize
from v13.common import atomic_write
from v13.models import ModelManager
from v13.runners import LlamaRunner
from v13.guards import turn_metrics
from v13.prompts import text as prompt_text

OPEN=[  # open questions where small models tend to echo the question back
 ('open_memory','Explain in two sentences how a local assistant can remember corrections.'),
 ('open_plan','What are three steps to plan a small garden on a balcony?'),
 ('open_compare','Compare trains and buses for a 50 km daily commute.'),
 ('open_why','Why does a phone get warm when it runs a language model?'),
]

def main():
    p=argparse.ArgumentParser();p.add_argument('--installed-home',required=True);p.add_argument('--out',required=True);p.add_argument('--lang',default='en');a=p.parse_args()
    home=Path(a.installed_home);base=initialize(home)|{'answer_language':a.lang}
    bench=importlib.util.spec_from_file_location('b',APP/'scripts/benchmark_c3.py');b=importlib.util.module_from_spec(bench);bench.loader.exec_module(b)
    cases=[(f['id'],f['system'],f['user'],f) for f in b.FIXTURES if f.get('lang','de')==a.lang]+[(i,prompt_text(base,'system'),q,{}) for i,q in OPEN]
    model=ModelManager(home).path_for('C3_LANGUAGE');report={'proof_kind':'C3_ANTI_ECHO_COMPARISON','model':model.name,'lang':a.lang,'modes':{}}
    for mode in ('legacy','anti_echo'):
        cfg=base|{'c3_sampling':mode};runner=LlamaRunner(home,'C3_LANGUAGE',model,cfg);rows=[]
        try:
            for cid,system,user,fx in cases:
                out=''.join(runner.generate([{'role':'system','content':system},{'role':'user','content':user}],threading.Event(),time.monotonic()+120,128,seed=13))
                m=turn_metrics(out,user);rows.append({'id':cid,'output':out,'metrics':m,'checks':b.lexical_checks(out,fx) if fx else {}})
        finally:runner.unload()
        n=len(rows);mean=lambda k:sum(float(r['metrics'][k]) for r in rows)/n
        report['modes'][mode]={'rows':rows,'mean_query_echo':mean('query_echo'),'mean_repetition_rate':mean('repetition_rate'),
            'mean_type_token_ratio':mean('type_token_ratio'),'below_min_new':sum(r['metrics']['below_min_new'] for r in rows),
            'checks_passed':sum(all(r['checks'].values()) for r in rows if r['checks']),'checked':sum(1 for r in rows if r['checks'])}
    atomic_write(Path(a.out),json.dumps(report,indent=2,ensure_ascii=False))
    print(json.dumps({m:{k:v for k,v in r.items() if k!='rows'} for m,r in report['modes'].items()},indent=1))
if __name__=='__main__':main()
