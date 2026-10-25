"""Run148: independent, read-only audit of Run147 closed Linux-native C3 ZIP.

No Runtime imports, no model calls, no changes to pre-registered cohort or gates.
A passing integrity audit does not establish a human-labelled false-alarm rate.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import zipfile

ARTIFACT_SHA = 'ddd60c897e1bdc634a40179b67e434097bb1e1999a6a2141372f6272682b9676'
MODEL_SHA = '3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d'
RUNNER_SHA = '9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443'
TASK_SHA = '3fc7e9da001e9851163813e758aacb31d5fb4d293e5bce78da1fe46b2c864836'
PROMPT_SHA = 'e2a94802abbfc212fead6e70427ab6ac92b84541aabb762043a8ff29101b980d'
SYSTEM = 'You are a calculator. Answer each arithmetic question with one integer. You may include the original equation but no extra explanation.'
GATES = {'STEP2':'UTILITY_FAIL','B3_L1':'FAIL','Body_JEPA':'UNAVAILABLE','jepa_weight':0,'DS2_H2':'FAIL','V13':'INCOMPLETE'}
Q = re.compile(r'(What is|Calculate|Compute)\s+(-?\d+)\s+(plus|minus|times|divided by)\s+(-?\d+)[?.]')
BARE = re.compile(r'\s*(?:(?:the answer is\s+)|(?:result:\s*))?(-?\d{1,12})\.?\s*', re.I)
ECHO = re.compile(r'\s*(-?\d{1,6})\s*([+\-*×÷/])\s*(-?\d{1,6})\s*=\s*(-?\d{1,12})\.?\s*')
LOG = re.compile(r'^RUN147_ROW (\d+) (CORRECT|MISMATCH|ABSTAIN) (CORRECT|MISMATCH|ABSTAIN) (None|-?\d+)$')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check(condition, code):
    if not condition:
        raise ValueError(code)


def arithmetic(question):
    m = Q.fullmatch(question)
    check(m is not None, 'invalid_question')
    phrase,a,op,b = m.groups();a=int(a);b=int(b)
    if op=='plus': n=a+b
    elif op=='minus': n=a-b
    elif op=='times': n=a*b
    else:
        check(b!=0 and a%b==0, 'noninteger_division');n=a//b
    return phrase,op,a,b,n


def independent_label(answer):
    if not isinstance(answer,str) or len(answer)>256 or '\n' in answer or '\r' in answer:return None
    m=BARE.fullmatch(answer)
    if m:return str(int(m.group(1)))
    m=ECHO.fullmatch(answer)
    return str(int(m.group(4))) if m else None


def independent_checker(question,answer):
    if not isinstance(answer,str) or len(answer)>256 or any(c in answer for c in '\n\r\x00'):
        return 'ABSTAIN'
    _,op,a,b,truth=arithmetic(question)
    label=independent_label(answer)
    if label is None:return 'ABSTAIN'
    m=ECHO.fullmatch(answer)
    if m:
        sym={'plus':'+','minus':'-','times':'*','divided by':'/'}[op]
        normalized={'×':'*','÷':'/'}.get(m.group(2),m.group(2))
        if (int(m.group(1)),normalized,int(m.group(3)))!=(a,sym,b):return 'ABSTAIN'
    return 'CORRECT' if int(label)==truth else 'MISMATCH'


def audit_zip(data, expected_sha=ARTIFACT_SHA):
    from io import BytesIO
    check(sha(data)==expected_sha,'artifact_digest_mismatch')
    with zipfile.ZipFile(BytesIO(data)) as z:
        names=z.namelist()
        check(sorted(names)==['RUN147_C3_VARIED_NATIVE_REPORT.json','RUN147_VARIED_NATIVE_RAW.log'], 'unexpected_zip_members')
        check(all(not x.flag_bits & 1 for x in z.infolist()),'encrypted_member')
        report=json.loads(z.read(names[0] if names[0].endswith('.json') else 'RUN147_C3_VARIED_NATIVE_REPORT.json'))
        log=z.read('RUN147_VARIED_NATIVE_RAW.log').decode('utf-8')
    check(report['schema']=='V13_RUN147_C3_VARIED_NATIVE_V1','schema')
    check(report['status']=='LINUX_NATIVE_C3_COHORT_EXECUTED','native_status')
    check(report['evidence_class']=='LINUX_X86_64_NATIVE_SINGLE_C3','evidence_class')
    check(report['seed']==14725,'seed')
    check(report['gates']==GATES and report['age0d_delivery']=='OFF','negative_gates')
    p=report['provenance']
    check(p['model_sha256']==MODEL_SHA and p['runner_archive_sha256']==RUNNER_SHA,'native_hashes')
    check(p['model_revision']=='657e078c94084481950a2d555a941481f715536b' and p['runner_tag']=='b10964','native_revision')
    check(report.get('unload',{}).get('process_reaped') is True,'native_unload')
    rows=report['rows'];check(len(rows)==96,'row_count')
    check([r['id'] for r in rows]==list(range(96)),'row_id_order')
    check(len({r['question'] for r in rows})==96,'question_uniqueness')
    check(not any('error' in r for r in rows),'row_error')
    check(sha(json.dumps([{k:r[k] for k in ('id','op','phrasing','question','truth')} for r in rows],sort_keys=True,separators=(',',':')).encode())==TASK_SHA,'registered_task_digest')
    check(sha(SYSTEM.encode())==PROMPT_SHA,'registered_prompt_digest')
    counts=Counter((r['op'],r['phrasing']) for r in rows)
    check(counts==Counter({(op,ph):8 for op in ('plus','minus','times','divided by') for ph in ('What is','Calculate','Compute')}),'strata')
    statuses=Counter(); unknown=[]; wrong=[]; correct=[]
    for r in rows:
        phrase,op,a,b,truth=arithmetic(r['question'])
        check(r['phrasing']==phrase and r['op']==op and r['truth']==str(truth),'source_truth')
        check(sha(r['response'].encode())==r['response_sha256'],'response_digest')
        label=independent_label(r['response'])
        check(label==r['label'],'independent_label_disagreement')
        check(independent_checker(r['question'],r['response'])==r['new_check'],'independent_checker_disagreement')
        check(r['new_check'] in ('CORRECT','MISMATCH','ABSTAIN') and r['old_check'] in ('CORRECT','MISMATCH','ABSTAIN'),'invalid_status')
        check(isinstance(r['duration_s'],(int,float)) and r['duration_s']>=0,'duration')
        check(isinstance(r['ttft_s'],(int,float)) and r['ttft_s']>=0,'ttft')
        statuses[r['new_check']]+=1
        if label is None:unknown.append(r['id'])
        elif label==r['truth']:correct.append(r['id'])
        else:wrong.append(r['id'])
    lines=[m.groups() for line in log.splitlines() if (m:=LOG.fullmatch(line))]
    check(len(lines)==96,'raw_log_count')
    for r,line in zip(rows,lines):
        check(line==(str(r['id']),r['new_check'],r['old_check'],r['label'] if r['label'] is not None else 'None'),'raw_log_disagreement')
    check('RUN147_REPORT ' in log and 'STATUS LINUX_NATIVE_C3_COHORT_EXECUTED' in log,'raw_log_terminal')
    summary=report['summary']
    check(summary['n']==96 and summary['label_correct']==len(correct) and summary['label_wrong']==len(wrong) and summary['label_unknown']==len(unknown),'summary_denominators')
    check(summary['new_supported']==96-statuses['ABSTAIN'],'summary_coverage')
    check(summary['K1']=='PASS' and summary['K2']=='INSUFFICIENT' and summary['K3']=='PASS' and summary['gate']=='UNVERIFIED','summary_gates')
    check(summary['false_alarms']==sum(rows[i]['new_check']=='MISMATCH' for i in correct),'false_alarm_count')
    check(summary['wrong_detected']==sum(rows[i]['new_check']=='MISMATCH' for i in wrong),'wrong_detect_count')
    return {'schema':'V13_RUN148_INDEPENDENT_AUDIT_V1','source_artifact_sha256':sha(data),
            'source_commit':'af8b88b35fd1cf32f0c6895d27ff956e28e9ab5e',
            'evidence_class':'READ_ONLY_CROSS_HOST_AUDIT_OF_LINUX_NATIVE',
            'integrity':'PASS','rows':96,'correct_format_label':len(correct),'wrong_format_label':len(wrong),
            'unknown_format_label':len(unknown),'unknown_ids':unknown,'wrong_ids':wrong,
            'new_checker_status':dict(statuses),'original_K1':'PASS','original_K2':'INSUFFICIENT','original_K3':'PASS',
            'overall_gate':'UNVERIFIED','gates':GATES,
            'limitations':['format labels are automated, not human adjudication',
                           'posthoc audit is not a fresh prospective cohort',
                           'unknown formats are not independently adjudicated',
                           'no Redmi evidence; no learning or live delivery']}


def main():
    p=argparse.ArgumentParser();p.add_argument('--artifact',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); result=audit_zip(a.artifact.read_bytes());a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print('RUN148_AUDIT',result['integrity'],result['rows'],result['overall_gate'])

if __name__=='__main__':main()
