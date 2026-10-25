"""Run153: independent source-bound audit of closed Run151 Linux-native C3 evidence.

Read-only; never changes original cohort, labels, Runtime or any V13 gate.
"""
from collections import Counter
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

ARTIFACT_SHA='0f19525d8e8abd62ca328ce752a0e8f8b619ca27ced71a42f3bd5c78d53edbe4'
TASK_SHA='9418de94428bb51a42d4d5e292ab9f5ef5e94acea61382d3f88c1694a7712144'
MODEL_SHA='3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d'
RUNNER_SHA='9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443'
PROMPT_SHA='e2a94802abbfc212fead6e70427ab6ac92b84541aabb762043a8ff29101b980d'
SYSTEM='You are a calculator. Answer each arithmetic question with one integer. You may include the original equation but no extra explanation.'
GATES={'STEP2':'UTILITY_FAIL','B3_L1':'FAIL','Body_JEPA':'UNAVAILABLE','jepa_weight':0,'DS2_H2':'FAIL','V13':'INCOMPLETE'}
QUESTION=re.compile(r'(What is|Calculate|Compute) (-?\d+) (plus|minus|times|divided by) (-?\d+)[?.]')
BARE=re.compile(r'(?:(?:The answer is\s+)|(?:Result:\s*))?(-?\d{1,12})\.?',re.I)
ECHO=re.compile(r'(-?\d{1,6})\s*([+\-*×÷/])\s*(-?\d{1,6})\s*=\s*(-?\d{1,12})\.?')
BOLD_BARE=re.compile(r'\*\*(-?\d{1,12})\*\*')
BOLD_ECHO=re.compile(r'(-?\d{1,6})\s*([+\-*×÷/])\s*(-?\d{1,6})\s*=\s*\*\*(-?\d{1,12})\*\*')
LOG=re.compile(r'RUN151_ROW (\d+) (CORRECT|MISMATCH|ABSTAIN) (CORRECT|MISMATCH|ABSTAIN) (CORRECT|MISMATCH|ABSTAIN) (None|-?\d+)')


def digest(b):return hashlib.sha256(b).hexdigest()
def require(ok,reason):
    if not ok:raise ValueError(reason)


def source(q):
    m=QUESTION.fullmatch(q);require(m is not None,'invalid_question')
    phrase,a,op,b=m.groups();a=int(a);b=int(b)
    truth={'plus':lambda:a+b,'minus':lambda:a-b,'times':lambda:a*b,'divided by':lambda:a//b if b and a%b==0 else None}[op]()
    require(truth is not None,'noninteger_division')
    return phrase,a,op,b,truth


def parse(q,answer,version=3,source_bound=True):
    if not isinstance(answer,str) or len(answer)>256 or any(c in answer for c in '\r\x00\x0b\x0c\x85\u2028\u2029'):
        return None
    if version==2 and '\n' in answer:return None
    t=answer.strip()
    if '\n' in t:return None
    matches=[(BARE.fullmatch(t),'bare'),(ECHO.fullmatch(t),'echo')]
    if version==3:matches.extend([(BOLD_BARE.fullmatch(t),'bold_bare'),(BOLD_ECHO.fullmatch(t),'bold_echo')])
    for m,kind in matches:
        if m is None:continue
        if kind in ('echo','bold_echo') and source_bound:
            _,a,op,b,_=source(q)
            symbol={'plus':'+','minus':'-','times':'*','divided by':'/'}[op]
            actual={'×':'*','÷':'/'}.get(m.group(2),m.group(2))
            if (int(m.group(1)),actual,int(m.group(3)))!=(a,symbol,b):return None
        return int(m.group(4) if kind in ('echo','bold_echo') else m.group(1))
    return None


def audit(data,expected_sha=ARTIFACT_SHA):
    require(digest(data)==expected_sha,'artifact_digest')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        require(sorted(z.namelist())==['RUN151_C3_VARIED_NATIVE_REPORT.json','RUN151_VARIED_NATIVE_RAW.log'],'zip_members')
        report=json.loads(z.read('RUN151_C3_VARIED_NATIVE_REPORT.json'))
        log=z.read('RUN151_VARIED_NATIVE_RAW.log').decode()
    require(report['schema']=='V13_RUN151_C3_VARIED_NATIVE_V1' and report['seed']==15132,'schema_seed')
    require(report['status']=='LINUX_NATIVE_C3_COHORT_EXECUTED' and report['evidence_class']=='LINUX_X86_64_NATIVE_SINGLE_C3','native_status')
    require(report['gates']==GATES and report['age0d_delivery']=='OFF','negative_gates')
    require(report['registered_task_sha256']==TASK_SHA and report['prior_artifact_sha256']=='ddd60c897e1bdc634a40179b67e434097bb1e1999a6a2141372f6272682b9676','registered_source')
    require(report['provenance']['model_sha256']==MODEL_SHA and report['provenance']['runner_archive_sha256']==RUNNER_SHA,'native_provenance')
    require(report['unload']['process_reaped'] is True,'unload')
    require(digest(SYSTEM.encode())==PROMPT_SHA,'prompt')
    rows=report['rows'];require(len(rows)==288,'row_count')
    require([r['id'] for r in rows]==list(range(288)),'row_ids')
    require(len({r['question'] for r in rows})==288,'duplicate_questions')
    tasks=[{k:r[k] for k in ('id','op','phrasing','question','truth')} for r in rows]
    require(digest(json.dumps(tasks,sort_keys=True,separators=(',',':')).encode())==TASK_SHA,'task_digest')
    counts=Counter((r['op'],r['phrasing']) for r in rows)
    require(counts==Counter({(op,ph):24 for op in ('plus','minus','times','divided by') for ph in ('What is','Calculate','Compute')}),'strata')
    rawlines=[m.groups() for line in log.splitlines() if (m:=LOG.fullmatch(line))]
    require(len(rawlines)==288,'raw_log_rows')
    strict_source_labels=[];source_mismatches=[];v3_new=[];statuses=Counter();wrong=[];correct=[]
    for r,line in zip(rows,rawlines):
        phrase,a,op,b,truth=source(r['question'])
        require((r['phrasing'],r['op'],r['truth'])==(phrase,op,str(truth)),'truth')
        require(digest(r['response'].encode())==r['response_sha256'],'response_hash')
        require('error' not in r,'row_error')
        strict=parse(r['question'],r['response'],2,False)
        require(r['label']==(str(strict) if strict is not None else None),'original_label')
        bound=parse(r['question'],r['response'],2,True)
        p2=parse(r['question'],r['response'],2,True)
        p3=parse(r['question'],r['response'],3,True)
        expected2='ABSTAIN' if p2 is None else 'CORRECT' if p2==truth else 'MISMATCH'
        expected3='ABSTAIN' if p3 is None else 'CORRECT' if p3==truth else 'MISMATCH'
        require((r['new_check'],r['v3_check'])==(expected2,expected3),'independent_checker')
        require(line==(str(r['id']),r['new_check'],r['v3_check'],r['old_check'],r['label'] if r['label'] is not None else 'None'),'raw_log_mismatch')
        statuses[('v2',r['new_check'])]+=1;statuses[('v3',r['v3_check'])]+=1
        if strict is not None and bound is None:source_mismatches.append(r['id'])
        if p2 is None and p3 is not None:v3_new.append(r['id'])
        if bound is not None:
            strict_source_labels.append(r['id'])
            (correct if bound==truth else wrong).append(r['id'])
    s=report['summary'];v2=288-statuses['v2','ABSTAIN'];v3=288-statuses['v3','ABSTAIN']
    require((s['v2_supported'],s['v3_supported'],s['v3_only_unadjudicated'])==(v2,v3,sum(r['label'] is None and r['v3_check']!='ABSTAIN' for r in rows)),'summary_coverage')
    require((s['K1'],s['K2'],s['K3'],s['gate'])==('PASS','PASS','PASS','UNVERIFIED'),'original_subgates')
    require(s['label_wrong']==28 and s['label_correct']==217 and s['label_unknown']==43,'original_label_counts')
    return {'schema':'V13_RUN153_INDEPENDENT_NATIVE_AUDIT_V1','source_artifact_sha256':digest(data),
            'evidence_class':'READ_ONLY_SOFTWARE_REAUDIT_OF_RUN151_LINUX_NATIVE','integrity':'PASS',
            'rows':288,'v2_supported':v2,'v3_supported':v3,'v3_only_new_ids':v3_new,
            'original_strict_label_correct':217,'original_strict_label_wrong':28,
            'source_mismatched_strict_label_ids':source_mismatches,
            'source_bound_strict_correct':len(correct),'source_bound_strict_wrong':len(wrong),
            'v3_statuses':{k:statuses['v3',k] for k in ('CORRECT','MISMATCH','ABSTAIN')},
            'K1_original':'PASS_AUTOMATED','K2_original':'PASS_AUTOMATED','K3_original':'PASS',
            'overall_gate':'UNVERIFIED','gates':GATES,
            'limitations':['strict format labels are automated, not human adjudication',
                           'Run151 native was single C3 on Linux, not Redmi or end-to-end V13',
                           '32 v3-only classifications were not labelled by original strict labeler',
                           'source-mismatched echoed equation must be excluded from grounded labels']}


def main():
    p=argparse.ArgumentParser();p.add_argument('--artifact',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();result=audit(a.artifact.read_bytes());a.output.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print('RUN153_AUDIT',result['integrity'],result['rows'],result['overall_gate'])

if __name__=='__main__':main()
