"""Run154: digest-bound comparison of two serialized, unplanned Run151 native executions.

No model execution. Preserve nonidentical outputs and failed/partial results;
never infer deterministic repeat or V13 completion from paired aggregate passes.
"""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import zipfile

from scripts.age0d_run151_independent_audit_run153 import source,parse,digest,GATES,TASK_SHA,MODEL_SHA,RUNNER_SHA

FIRST='0f19525d8e8abd62ca328ce752a0e8f8b619ca27ced71a42f3bd5c78d53edbe4'
SECOND='fb0cc7d8370437a29d49fdbdabe5b8bbc32a5445ee3db55e295f701bfaec30da'


def require(ok,code):
    if not ok:raise ValueError(code)


def load(data,sha):
    require(digest(data)==sha,'artifact_hash')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        require(sorted(z.namelist())==['RUN151_C3_VARIED_NATIVE_REPORT.json','RUN151_VARIED_NATIVE_RAW.log'],'zip_members')
        report=json.loads(z.read('RUN151_C3_VARIED_NATIVE_REPORT.json'))
        log=z.read('RUN151_VARIED_NATIVE_RAW.log').decode()
    require(report['schema']=='V13_RUN151_C3_VARIED_NATIVE_V1' and report['seed']==15132,'schema_seed')
    require(report['status']=='LINUX_NATIVE_C3_COHORT_EXECUTED' and report['unload']['process_reaped'] is True,'native_status')
    require(report['gates']==GATES and report['age0d_delivery']=='OFF','gates')
    require(report['registered_task_sha256']==TASK_SHA,'registered_task')
    require(report['provenance']['model_sha256']==MODEL_SHA and report['provenance']['runner_archive_sha256']==RUNNER_SHA,'provenance')
    rows=report['rows'];require(len(rows)==288 and [r['id'] for r in rows]==list(range(288)),'rows')
    tasks=[{k:r[k] for k in ('id','op','phrasing','question','truth')} for r in rows]
    require(digest(json.dumps(tasks,sort_keys=True,separators=(',',':')).encode())==TASK_SHA,'task_digest')
    for r in rows:
        _,_,_,_,truth=source(r['question']);require(str(truth)==r['truth'],'truth')
        require(digest(r['response'].encode())==r['response_sha256'],'response_hash')
        require('error' not in r,'row_error')
        label=parse(r['question'],r['response'],3,True)
        expected='ABSTAIN' if label is None else 'CORRECT' if label==truth else 'MISMATCH'
        require(r['v3_check']==expected,'v3_status')
    require(sum(line.startswith('RUN151_ROW ') for line in log.splitlines())==288,'raw_log_count')
    require(report['summary']['gate']=='UNVERIFIED','summary_gate')
    return report


def compare(a,b,first_sha=FIRST,second_sha=SECOND):
    require(first_sha!=second_sha,'not_independent_artifacts')
    x=load(a,first_sha);y=load(b,second_sha)
    require(x['registered_task_sha256']==y['registered_task_sha256'],'different_tasks')
    require(x['provenance']['model_sha256']==y['provenance']['model_sha256'] and x['provenance']['runner_archive_sha256']==y['provenance']['runner_archive_sha256'],'different_models')
    transitions=Counter();byop=Counter();different=[];same=0
    for left,right in zip(x['rows'],y['rows']):
        require((left['id'],left['question'],left['truth'])==(right['id'],right['question'],right['truth']),'row_alignment')
        transitions[(left['v3_check'],right['v3_check'])]+=1
        if left['response_sha256']==right['response_sha256']:same+=1
        else:different.append(left['id']);byop[left['op']]+=1
    status_diff=sum(n for (a,b),n in transitions.items() if a!=b)
    return {'schema':'V13_RUN154_SERIALIZED_NATIVE_REPLICATION_V1',
            'first_artifact_sha256':first_sha,'second_artifact_sha256':second_sha,
            'evidence_class':'READ_ONLY_SOFTWARE_COMPARISON_OF_TWO_LINUX_NATIVE_C3_RUNS',
            'rows':288,'response_identical':same,'response_different':288-same,
            'different_response_ids':different,'different_by_operation':dict(sorted(byop.items())),
            'v3_status_changed':status_diff,
            'v3_transition_counts':{f'{a}->{b}':n for (a,b),n in sorted(transitions.items())},
            'first_v3_supported':x['summary']['v3_supported'],'second_v3_supported':y['summary']['v3_supported'],
            'first_subgates':{k:x['summary'][k] for k in ('K1','K2','K3')},
            'second_subgates':{k:y['summary'][k] for k in ('K1','K2','K3')},
            'deterministic_repeat':same==288,'overall_gate':'UNVERIFIED','gates':GATES,
            'limitations':['second execution was an unplanned serialized duplicate, not a preregistered independent seed',
                           'fixed sampling seeds did not guarantee byte-identical native responses',
                           'two Linux single-C3 runs are not Redmi or whole V13 utility',
                           'automated labels do not replace human adjudication']}


def main():
    p=argparse.ArgumentParser();p.add_argument('--first',type=Path,required=True);p.add_argument('--second',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=compare(a.first.read_bytes(),a.second.read_bytes());a.output.write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
    print('RUN154_REPLICATION',r['response_identical'],'/',r['rows'],'status_changes',r['v3_status_changed'],'GATE',r['overall_gate'])

if __name__=='__main__':main()
