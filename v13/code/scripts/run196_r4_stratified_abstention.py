#!/usr/bin/env python3
"""Run196: conservative by-kind deployment veto for retrospective R4 abstention.

No native model execution and no runtime import. Threshold is read from the
sealed Run195 prereg; this checks known seed11 as a negative control, NOT a
fresh validation. Future unseen heldout with model/source hashes is required.
"""
import argparse
import json
import math
from pathlib import Path
from scripts import run195_r4_selective_abstention as R

SCHEMA='V13_RUN196_STRATIFIED_ABSTENTION_V1'
KINDS=('summary','long','notes','compare')
MAX_ERROR=.30
MIN_KIND_COVERAGE=.50
MIN_KIND_ANSWERED=5


def fixture_kind(row):
    name=row['fixture']
    kind=next((k for k in KINDS if name.startswith(k) and name[len(k):].isdigit()),None)
    if kind is None:raise ValueError('UNREGISTERED_FIXTURE_KIND')
    return kind


def evaluate_strata(rows,threshold):
    if type(threshold) not in (int,float) or not math.isfinite(threshold):
        raise ValueError('THRESHOLD_INVALID')
    if len(rows)!=60 or len({r['fixture'] for r in rows})!=60:
        raise ValueError('FIXTURE_COHORT_INVALID')
    groups={k:[] for k in KINDS}
    for row in rows:groups[fixture_kind(row)].append(row)
    if any(len(groups[k])!=15 for k in KINDS):
        raise ValueError('FIXTURE_STRATIFICATION_INVALID')
    per={};fail=[]
    for k in KINDS:
        m=R.metrics(groups[k],threshold)
        risk=m['selective_error_rate'];coverage=m['coverage']
        reasons=[]
        if m['answered']<MIN_KIND_ANSWERED:reasons.append('TOO_FEW_ANSWERS')
        if coverage<MIN_KIND_COVERAGE:reasons.append('COVERAGE_TOO_LOW')
        if risk is None or risk>MAX_ERROR:reasons.append('SELECTIVE_ERROR_TOO_HIGH')
        per[k]=dict(m,reasons=reasons)
        if reasons:fail.append({'kind':k,'reasons':reasons})
    total=R.metrics(rows,threshold)
    return {'schema':SCHEMA,'threshold':threshold,'per_kind':per,'total':total,
            'deployment_supported':not fail,'failures':fail,
            'production_authority':0,'canonical_gate_pass':False,
            'evidence_class':'OFFLINE_REPLAY_EXISTING_LINUX_NATIVE_C3_CAPTURE',
            'native_inference_this_run':False,'redmi_measured':False,
            'holdout_blind':False,'claim_limit':'No live abstention authority from retrospective replay.'}


def replay(prereg_path,report_path,capture_path):
    reg=json.loads(Path(prereg_path).read_text())
    report=json.loads(Path(report_path).read_text())
    if (R.sha(prereg_path)!=report.get('prereg_sha256')
            or reg.get('schema')!=R.SCHEMA or reg.get('phase')!='PREREGISTERED'
            or reg.get('script_sha256')!=R.sha(R.__file__)
            or report.get('phase')!='RETROSPECTIVE_EVALUATION'
            or report.get('fresh_capture_sha256')!=R.FRESH_SHA
            or report.get('threshold')!=reg.get('threshold')):
        raise ValueError('FROZEN_REPLAY_LINEAGE_INVALID')
    rows=R.load_capture(capture_path,R.FRESH_SEED,R.FRESH_SHA)
    result=evaluate_strata(rows,reg['threshold'])
    if result['total']!=report.get('metrics'):
        raise ValueError('FROZEN_REPLAY_TOTAL_MISMATCH')
    return result


def main():
    ap=argparse.ArgumentParser()
    for name in ('prereg','report','capture','output'):ap.add_argument(name,type=Path)
    a=ap.parse_args()
    result=replay(a.prereg,a.report,a.capture)
    R.write_once(a.output,result)
    print(json.dumps({'deployment_supported':result['deployment_supported'],
                      'failures':result['failures'],'production_authority':0},sort_keys=True))


if __name__=='__main__':main()
