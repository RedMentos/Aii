#!/usr/bin/env python3
"""§85.1 G-B-TIMESCALE-DIVERGENCE-001 measurement (WP-V4).

Runs the existing STEP2 ablation (b1_only, b2_only, both_*) once per B2 control:

  same_model_same_policy   B2 = B1 body, B1 prompt/window, no earlier context
  same_model_prompt_only   B2 = B1 body, gist prompt only
  shared_body_dual_state   B2 = B1 body, gist prompt + long window + earlier context
  two_body                 B2 = own body (Qwen3.5-0.8B), full gist policy

and scores every row with the task-bound assertions (analyze_step2_proof.task_score).
The gate needs (a) the combination beating the best single body and (b) two_body
beating every same-model control. Small fixture sets are diagnostic only; this script
never promotes a gate or changes the installed configuration.
"""
import argparse,importlib.util,json,sys
from pathlib import Path

APP=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(APP),str(APP/'tests')]
from v13.common import atomic_write
from v13.models import B2_CONTROLS

def _load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def scorable(proof):
    """Single-body rows often fail only 'expected_roles' (background observers add the other
    body's offer after the answer). The answer itself is still that route's answer, so for
    task scoring such rows count; every other failed check still excludes the row."""
    out=json.loads(json.dumps(proof))
    for r in out.get('rows',[]):
        failed={k for k,v in (r.get('checks') or {}).items() if not v}
        if r.get('status')=='CHECKS_PARTIAL' and failed=={'expected_roles'}:r['status']='CHECKS_PASS';r['scored_despite']='expected_roles'
    return out

def summarize(by_control):
    """by_control: {control: analyze_step2_proof.analyze(...) output}."""
    rows={}
    for control,analysis in by_control.items():
        both=[f['best_both_task_fraction'] for f in analysis['fixtures'] if f.get('best_both_task_fraction') is not None]
        single=[f['best_single_task_fraction'] for f in analysis['fixtures'] if f.get('best_single_task_fraction') is not None]
        rows[control]={'mean_both_task_fraction':sum(both)/len(both) if both else None,
                       'mean_best_single_task_fraction':sum(single)/len(single) if single else None,
                       'task_bound_positive_fixtures':[f['id'] for f in analysis['fixtures'] if f.get('task_bound_positive_combination_signal')]}
    two=rows.get('two_body',{}).get('mean_both_task_fraction')
    controls=[rows[c]['mean_both_task_fraction'] for c in rows if c!='two_body']
    combination=two is not None and rows['two_body']['mean_best_single_task_fraction'] is not None and two>rows['two_body']['mean_best_single_task_fraction']
    beats=two is not None and controls and all(x is not None and two>x for x in controls)
    shared=rows.get('shared_body_dual_state',{}).get('mean_both_task_fraction')
    return {'controls':rows,'combination_beats_single':bool(combination),'two_body_beats_all_controls':bool(beats),
            'cheaper_shared_body_is_enough':shared is not None and two is not None and shared>=two,
            'diagnostic_signal':bool(combination and beats),'gate_promotion':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--installed-home',required=True);p.add_argument('--out-dir',required=True)
    p.add_argument('--controls',nargs='*',default=list(B2_CONTROLS));p.add_argument('--lang',nargs='*',default=['en']);p.add_argument('--reanalyze',action='store_true',help='score existing <control>.json files without new runs')
    a=p.parse_args();out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True)
    step2=_load('integration_step2',APP/'tests/integration_step2.py');analyzer=_load('analyze_step2',APP/'scripts/analyze_step2_proof.py')
    analyses={}
    for control in a.controls:
        if control not in B2_CONTROLS:raise SystemExit('unknown control '+control)
        proof=json.loads((out/(control+'.json')).read_text()) if a.reanalyze else step2.run(a.installed_home,out/(control+'.json'),1,control,tuple(a.lang))
        analyses[control]=analyzer.analyze(scorable(proof));atomic_write(out/(control+'.analysis.json'),json.dumps(analyses[control],indent=2,ensure_ascii=False))
    report={'proof_kind':'B_TIMESCALE_DIVERGENCE_CONTROLS','gate':'G-B-TIMESCALE-DIVERGENCE-001','languages':a.lang,**summarize(analyses),
            'claim_limits':['Few fixtures, lexical task assertions; diagnostic only.','Linux x86 timing is not Redmi timing.']}
    atomic_write(out/'timescale-gate.json',json.dumps(report,indent=2,ensure_ascii=False));print(json.dumps({k:report[k] for k in ('combination_beats_single','two_body_beats_all_controls','cheaper_shared_body_is_enough','diagnostic_signal')}))
    return 0
if __name__=='__main__':sys.exit(main())
