#!/usr/bin/env python3
"""WP-DS3: retrospective selective abstention on frozen Linux-native C3 outputs.

Uses the already recorded R4 seed7/seed11 captures; no model is called.
Seed11 aggregate findings were published on 2026-10-12, so this is NOT a
new blind heldout proof. The rule is fixed from seed7 before this script
inspects seed11; no runtime/answer policy or Age authority is changed.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

SCHEMA='V13_RUN195_SELECTIVE_ABSTENTION_V1'
FEATURE='digit_min_logprob'
TRAIN_SHA='5095bae1ce531aca4b72b292c4d9a1ac9d1138b8a4a3dca84f8c2d86f7607cf5'
FRESH_SHA='96efd0d65bdb13005336661e0cb09fc7d1f41a1e62ec77c0b512ebf74078b5a1'
MIN_COVERAGE=.70
FRESH_SEED=11
RULE='Fresh coverage >= 70%, selective error rate <= 20%, and at least 10 percentage points below raw C3 error rate.'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_capture(path,seed,expected_sha):
    if sha(path)!=expected_sha:raise ValueError('CAPTURE_SHA256_MISMATCH')
    doc=json.loads(Path(path).read_text())
    if doc.get('kind')!='V13_R4_C3_UNCERTAINTY_CAPTURE' or doc.get('task_seed')!=seed:
        raise ValueError('CAPTURE_IDENTITY_MISMATCH')
    rows=doc.get('rows')
    if not isinstance(rows,list) or len(rows)!=60:raise ValueError('CAPTURE_INCOMPLETE')
    ids=set()
    for row in rows:
        if not isinstance(row,dict) or not isinstance(row.get('fixture'),str) or row['fixture'] in ids:
            raise ValueError('CAPTURE_FIXTURE_INVALID')
        ids.add(row['fixture'])
        if type(row.get('pass')) is not bool or row.get('answer_stream_matches_output') is not True:
            raise ValueError('CAPTURE_LABEL_OR_STREAM_INVALID')
        if not isinstance(row.get('tokens'),list) or not isinstance(row.get('features'),dict):
            raise ValueError('CAPTURE_TOKENS_MISSING')
        for t in row['tokens']:
            if (not isinstance(t,dict) or not isinstance(t.get('token'),str)
                    or type(t.get('logprob')) not in (int,float) or not math.isfinite(t['logprob'])):
                raise ValueError('CAPTURE_TOKEN_INVALID')
        lp=row['features'].get(FEATURE)
        if type(lp) not in (int,float) or not math.isfinite(lp):
            raise ValueError('CAPTURE_FEATURE_INVALID')
    return rows


def uncertainty(row):
    """Larger means less certain; no numeric token means abstain (not score 0)."""
    if not any(any(ch.isdigit() for ch in t['token']) for t in row['tokens']):
        return math.inf
    lp=row['features'][FEATURE]
    return -lp if math.isfinite(lp) and lp<=0 else math.inf


def metrics(rows,threshold):
    if type(threshold) not in (int,float) or not math.isfinite(threshold):
        raise ValueError('THRESHOLD_INVALID')
    selected=[r for r in rows if uncertainty(r)<=threshold]
    n=len(rows);answered=len(selected)
    correct=sum(r['pass'] for r in selected);wrong=answered-correct
    base_correct=sum(r['pass'] for r in rows);base_wrong=n-base_correct
    return {'n':n,'answered':answered,'abstained':n-answered,
            'correct_answered':correct,'wrong_answered':wrong,
            'coverage':answered/n,'selective_error_rate':wrong/answered if answered else None,
            'raw_c3_correct':base_correct,'raw_c3_wrong':base_wrong,
            'raw_c3_error_rate':base_wrong/n,
            'correct_abstained':base_correct-correct,
            'wrong_abstained':base_wrong-wrong}


def choose_threshold(rows,min_coverage=MIN_COVERAGE):
    if not 0<min_coverage<=1:raise ValueError('COVERAGE_TARGET_INVALID')
    thresholds=sorted({uncertainty(r) for r in rows if math.isfinite(uncertainty(r))})
    eligible=[]
    for t in thresholds:
        m=metrics(rows,t)
        if m['coverage']>=min_coverage:
            eligible.append((m['selective_error_rate'],-m['coverage'],t,m))
    if not eligible:raise ValueError('NO_THRESHOLD_MEETS_COVERAGE')
    risk,neg_coverage,threshold,m=min(eligible,key=lambda x:x[:3])
    return threshold,m


def prereg(train_path):
    rows=load_capture(train_path,7,TRAIN_SHA)
    threshold,m=choose_threshold(rows)
    return {'schema':SCHEMA,'phase':'PREREGISTERED','feature':FEATURE,
            'train_capture_sha256':TRAIN_SHA,'fresh_capture_sha256':FRESH_SHA,
            'script_sha256':sha(__file__),'train_seed':7,'fresh_seed':FRESH_SEED,
            'min_coverage':MIN_COVERAGE,'threshold':threshold,'train_metrics':m,
            'decision_rule':RULE,'holdout_blind':False,
            'known_prior_seed11_summary':True,'production_authority':0}


def evaluate(reg_path,fresh_path):
    reg=json.loads(Path(reg_path).read_text())
    if (reg.get('schema')!=SCHEMA or reg.get('phase')!='PREREGISTERED'
            or reg.get('script_sha256')!=sha(__file__) or reg.get('feature')!=FEATURE
            or reg.get('train_capture_sha256')!=TRAIN_SHA
            or reg.get('fresh_capture_sha256')!=FRESH_SHA
            or reg.get('fresh_seed')!=FRESH_SEED or reg.get('min_coverage')!=MIN_COVERAGE
            or reg.get('decision_rule')!=RULE):
        raise ValueError('PREREGISTRATION_CHANGED')
    t=reg.get('threshold')
    if type(t) not in (int,float) or not math.isfinite(t):
        raise ValueError('PREREGISTERED_THRESHOLD_INVALID')
    rows=load_capture(fresh_path,FRESH_SEED,FRESH_SHA)
    m=metrics(rows,t)
    risk=m['selective_error_rate']
    supported=(m['coverage']>=MIN_COVERAGE and risk is not None and risk<=.20
               and m['raw_c3_error_rate']-risk>=.10)
    return {'schema':SCHEMA,'phase':'RETROSPECTIVE_EVALUATION','prereg_sha256':sha(reg_path),
            'fresh_capture_sha256':FRESH_SHA,'threshold':t,'metrics':m,
            'verdict':'SELECTIVE_RISK_SUPPORTED_RETROSPECTIVE' if supported else 'NOT_SUPPORTED',
            'evidence_class':'OFFLINE_REPLAY_OF_EXISTING_LINUX_NATIVE_C3_OUTPUTS',
            'native_inference_this_run':False,'redmi_measured':False,'holdout_blind':False,
            'production_authority':0,'canonical_gate_pass':False,
            'claim_limit':'Abstention reduces coverage; no new answer quality or AGI proof.'}


def write_once(path,doc):
    path=Path(path)
    if path.exists():raise ValueError('REFUSE_OVERWRITE_PROOF')
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,
                                     prefix='.partial-',delete=False) as stream:
        temp=Path(stream.name)
        json.dump(doc,stream,indent=2,sort_keys=True,allow_nan=False)
        stream.write('\n');stream.flush();os.fsync(stream.fileno())
    try:
        if path.exists():raise ValueError('REFUSE_OVERWRITE_PROOF')
        os.link(temp,path)
    finally:
        temp.unlink(missing_ok=True)
    fd=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=('prereg','evaluate'))
    ap.add_argument('first',type=Path);ap.add_argument('second',type=Path)
    ap.add_argument('third',nargs='?',type=Path);args=ap.parse_args()
    if args.phase=='prereg':
        if args.third is not None:ap.error('prereg takes train.json output.json')
        doc=prereg(args.first);out=args.second
    else:
        if args.third is None:ap.error('evaluate takes prereg.json fresh.json output.json')
        doc=evaluate(args.first,args.second);out=args.third
    write_once(out,doc)
    print(json.dumps({'phase':doc['phase'],'verdict':doc.get('verdict'),
                      'out':str(out),'production_authority':0},sort_keys=True))


if __name__=='__main__':main()
