"""Run316 immutable 5-case C3 native correction/forget cohort, resumable raw receipts.

One controlled native C3 route per case; fixture mode is never native proof.
Semantic utility failures are recorded, not converted to test harness success.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from native_second_turn_probe_run315 import probe as one_probe
import native_second_turn_probe_run315 as P
from v13.common import atomic_write,dumps

CASES=(
    {'id':'ASTER','question':'What is the exact calibration code for fictional Project RUN316-ASTER?','code':'59217'},
    {'id':'BERYL','question':'What is the exact entry passcode for fictional Project RUN316-BERYL?','code':'80426'},
    {'id':'CEDAR','question':'What is the exact docking bay number for fictional Project RUN316-CEDAR?','code':'27615'},
    {'id':'DELTA','question':'What is the exact maintenance ticket number for fictional Project RUN316-DELTA?','code':'94531'},
    {'id':'ECHO','question':'What is the exact color-key code for fictional Project RUN316-ECHO?','code':'61872'},
)
COHORT_SHA256='a5c990124a088f7968882ca269352bce2f0635acbf03e1685e473e5f23895ce7'
EXPECTED_C3_SHA256='3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d'


def registry_sha():
    b=json.dumps(list(CASES),sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
    return hashlib.sha256(b).hexdigest()


def file_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def summarize(report):
    done=report['cases'];n=len(CASES)
    def count(fn):return sum(bool(fn(x)) for x in done)
    metrics={
        'cases_attempted':len(done),'denominator':n,
        'integration_count':count(lambda x:x.get('integration_pass')),
        'utility_count':count(lambda x:x.get('utility_pass')),
        'second_exact_count':count(lambda x:x.get('utility',{}).get('second_exact')),
        'observed_improvement_count':count(lambda x:x.get('utility',{}).get('observed_improvement')),
        'post_forget_nonretention_count':count(lambda x:x.get('utility',{}).get('forget_output_nonretention')),
        'errors':count(lambda x:x.get('status')=='ERROR'),
    }
    for key in ('integration','utility','second_exact','observed_improvement','post_forget_nonretention'):
        metrics[key+'_rate']=round(metrics[key+'_count']/n,4)
    report['metrics']=metrics
    if len(done)==n:
        report['status']='COMPLETE' if metrics['integration_count']==n and not metrics['errors'] else 'INTEGRATION_FAIL'
        report['evidence_capture_pass']=report['status']=='COMPLETE'
    else:
        report['status']='PARTIAL';report['evidence_capture_pass']=False
    return report


def run(out_dir,models_from=None,native=True,timeout=140):
    out_dir=Path(out_dir);out_dir.mkdir(parents=True,exist_ok=True)
    if registry_sha()!=COHORT_SHA256:raise ValueError('Frozen Run316 cohort registry hash mismatch')
    aggregate=out_dir/'RUN316_COHORT.json'
    if aggregate.exists():
        report=json.loads(aggregate.read_text())
        if report.get('cohort_sha256')!=COHORT_SHA256 or report.get('native')!=native:
            raise ValueError('Run316 resume identity mismatch')
        for i,item in enumerate(report.get('cases',[])):
            if i>=len(CASES) or item.get('case_id')!=CASES[i]['id']:
                raise ValueError('Run316 resume case order mismatch')
            path=out_dir/('RUN316_'+item['case_id']+'.json')
            if not path.is_file() or file_sha(path)!=item.get('raw_sha256'):
                raise ValueError('Run316 resume raw case bytes changed')
    else:
        report={'schema':'V13_RUN316_C3_COHORT_V1','native':bool(native),
                'evidence_level':'LINUX_NATIVE_C3' if native else 'FIXTURE_ONLY',
                'cohort_sha256':COHORT_SHA256,'expected_c3_sha256':EXPECTED_C3_SHA256,
                'case_order':[x['id'] for x in CASES],'cases':[],
                'gates':dict(P.GATES),
                'claim_limit':'5 fixed synthetic C3 prompts, no weight learning, Redmi, JEPA or broad reliability claim'}
    def save():atomic_write(aggregate,(dumps(summarize(report))+'\n').encode())
    save()
    original_question,original_code=P.QUESTION,P.CODE
    try:
        for case in CASES[len(report['cases']):]:
            P.QUESTION=case['question'];P.CODE=case['code']
            case_file=out_dir/('RUN316_'+case['id']+'.json')
            if case_file.exists():raise ValueError('Unregistered existing Run316 case file; refuse overwrite')
            try:
                result=one_probe(out_dir/('home-'+case['id']),models_from,case_file,native=native,timeout=timeout)
            except Exception as exc:
                if not case_file.exists():
                    atomic_write(case_file,(dumps({'status':'ERROR','error':type(exc).__name__})+'\n').encode())
                result=json.loads(case_file.read_text())
            model=result.get('model') or {}
            if native and model.get('sha256') not in (None,EXPECTED_C3_SHA256):
                result['integration_pass']=False
                result['status']='ERROR'
            report['cases'].append({
                'case_id':case['id'],'status':result.get('status'),'raw_sha256':file_sha(case_file),
                'integration_pass':bool(result.get('integration_pass')),
                'utility_pass':bool(result.get('utility_pass')),
                'utility':result.get('utility',{}),
                'native_stages':len(result.get('stages',[])),
                'model_sha256':model.get('sha256'),
            })
            save()
        return report
    finally:
        P.QUESTION,P.CODE=original_question,original_code
        save()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out-dir',required=True);ap.add_argument('--models-from')
    ap.add_argument('--fixture',action='store_true');ap.add_argument('--timeout',type=int,default=140)
    args=ap.parse_args()
    report=run(args.out_dir,args.models_from,native=not args.fixture,timeout=args.timeout)
    print(dumps({'status':report['status'],'native':report['native'],'metrics':report['metrics']}))
    if not report['evidence_capture_pass']:raise SystemExit(2)

if __name__=='__main__':main()
