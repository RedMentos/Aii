"""Live eligibility extraction (v13/agi/eligibility.read, the prompt ToolStep uses) on the recorded STEP2 quote-context evidence.

Input: the complete STEP2 report of arm `context` (scripts/step2_quote_context.py, 70 rows, real B1/B2 offers with
offer_quote_context_chars=200). Per row the evidence is exactly what the live ToolStep would see: the current source
and the verified analyst quotes C3 received. C3 extracts typed values with EXTRACT_SYSTEM/EXTRACT_SCHEMA, the
deterministic recipe decides. Baseline: the replay through the STEP2 consumer prompt (tool_context.json, same rows).
Preregistration: docs/proofs/continuation-20261021/eligibility-live/PREREG.md. Linux cloud, SHADOW, no gate promotion.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'tests')]
from scripts import calc_tool_ablation as w2
from v13.agi import eligibility as E
from v13.common import atomic_write, digest, dumps, file_hash
from v13.config import initialize, save_config
from v13.runtime import Runtime
from v13.utility import score_decision
import integration_step2_utility as step2

SEED=13;B2_VARIANTS=('b2_only','both_none','both_exact','both_control','prompt_only_dual')

def evidence(row):
    user=json.loads(next(m['content'] for m in row['consumer_messages'] if m['role']=='user'))
    return user['current_source'],[q for a in user.get('analysts',[]) for q in a.get('verified_quotes',[])]

def answer(x,current,quotes):
    d=E.tool(**E.args_from(x,current,quotes))
    return dumps({'project':x['project'],'action':d['action'],'options':d['options']}),d

def run(installed,report_path,out_path):
    report=json.loads(Path(report_path).read_text())
    if report.get('producer_arm',{}).get('arm')!='quote_context_context' or not report.get('all_structural_checks_passed'):raise ValueError('Need the complete context-arm STEP2 report')
    for row in report['rows']:
        if report['row_sha256'][row['fixture']+':'+row['variant']]!=digest(dumps(row)):raise ValueError('Recorded STEP2 row changed')
    fixtures={f['id']:f for f in report['fixtures']};cfg=dict(report['config'])
    out={'schema':'STEP2_ELIGIBILITY_LIVE_V1','status':'RUNNING','source_report_sha256':file_hash(report_path),'seed':SEED,
         'extract_system_sha256':digest(E.EXTRACT_SYSTEM),'extract_schema_sha256':digest(dumps(E.EXTRACT_SCHEMA)),'revision':E.REVISION,
         'installed':step2.installed_artifacts(Path(installed)),'rows':[],'canonical_gate_pass':False,'phone_measured':False}
    home=out_path.with_suffix('.checkpoint')
    if home.exists():shutil.rmtree(home)
    initialize(home);save_config(home,cfg);step2.installed_links(home,Path(installed).resolve());r=Runtime(home)
    try:
        for src in report['rows']:
            current,quotes=evidence(src);f=fixtures[src['fixture']];row={'fixture':src['fixture'],'variant':src['variant'],'quotes':len(quotes)}
            t=time.monotonic()
            try:
                x=E.read(r.pool.get('C3_LANGUAGE'),current,quotes,r.cancel_event,time.monotonic()+cfg['deadline_seconds'])
                row['extracted']=x;row['answer'],d=answer(x,current,quotes);row['rejected']=d['rejected'];row['status']='RECORDED'
            except Exception as exc:row.update(status='ERROR',error_type=type(exc).__name__,error=str(exc)[:300],answer='')
            row['score']=score_decision(row['answer'],f['oracle']) if row['answer'] else {'utility':0.,'exact':False,'field_checks':{}}
            row['elapsed_s']=time.monotonic()-t;out['rows'].append(row);atomic_write(out_path,dumps(out))
            print(dumps({'fixture':row['fixture'],'variant':row['variant'],'status':row['status'],'exact':w2.decision_exact(row['score'])}),flush=True)
    finally:r.close()
    shutil.rmtree(home,ignore_errors=True)
    def act(row):
        try:return json.loads(row['answer']).get('action')
        except (ValueError,AttributeError):return None
    retain=[x for x in out['rows'] if fixtures[x['fixture']]['temporal_mode']=='RETAIN_PRIOR_RULES' and x['variant'] in B2_VARIANTS]
    out['summary']={'decision_exact':sum(w2.decision_exact(x['score']) for x in out['rows']),'rows':len(out['rows']),
                    'wrong_committed':sum(act(x) in ('A','B','NONE') and act(x)!=fixtures[x['fixture']]['oracle']['action'] for x in out['rows']),
                    'retain_b2_exact':sum(w2.decision_exact(x['score']) for x in retain),'retain_b2_rows':len(retain),
                    'per_variant':{v:sum(w2.decision_exact(x['score']) for x in out['rows'] if x['variant']==v) for v in sorted({x['variant'] for x in out['rows']})},
                    'errors':sum(x['status']!='RECORDED' for x in out['rows'])}
    out['installed_unchanged']=out['installed']==step2.installed_artifacts(Path(installed))
    out['status']='RECORDED' if out['installed_unchanged'] and not out['summary']['errors'] else 'STRUCTURAL_FAIL'
    atomic_write(out_path,dumps(out));return out

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--installed-home',type=Path,required=True)
    p.add_argument('--step2-report',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    out=run(a.installed_home,a.step2_report,a.out);print(json.dumps({'status':out['status'],'summary':out['summary']},indent=1))

if __name__=='__main__':main()
