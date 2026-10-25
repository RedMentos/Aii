"""Read-only independent diagnostic of registered Run142 C3 answers.

This is a post-hoc *audit*, never a new AGE0d gate or live checker.
Reject mismatched source bytes, provenance, task arithmetic or response hashes.
"""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

SOURCE_COMMIT = '2ba3688039ac6368f6cb8c0130dcaaa5dcb5d6ee'
MODEL_SHA = '3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d'
RUNNER_SHA = '9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443'
EXPECTED_GATES = {'STEP2':'UTILITY_FAIL','B3_L1':'FAIL','Body_JEPA':'UNAVAILABLE',
                  'jepa_weight':0,'DS2_H2':'FAIL','V13':'INCOMPLETE'}
QUESTION = re.compile(r'What is (?P<a>\d{1,5}) (?P<op>plus|minus|times|divided by) (?P<b>\d{1,5})\?\Z')
NUMBER = r'-?\d{1,9}'
BARE = re.compile(rf'(?:The answer is\s+)?(?P<result>{NUMBER})\.?\Z', re.I)
ECHO = re.compile(rf'(?P<a>\d{{1,5}})\s*(?P<op>[+\-*×÷/])\s*(?P<b>\d{{1,5}})\s*=\s*(?P<result>{NUMBER})\Z')
OPS = {'plus':'+','minus':'-','times':'*','divided by':'/'}
ALIASES = {'+':'+','-':'-','*':'*','×':'*','/':'/','÷':'/'}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def expected(question):
    m = QUESTION.fullmatch(question)
    if m is None:
        raise ValueError('unsupported source question')
    a,b = int(m['a']),int(m['b'])
    op = OPS[m['op']]
    if op == '+': truth = a+b
    elif op == '-': truth = a-b
    elif op == '*': truth = a*b
    else:
        if b == 0 or a%b: raise ValueError('non-exact division')
        truth = a//b
    return a,b,op,str(truth),m['op']


def parse_strict_answer(question, answer):
    """Independent exact-expression diagnostic; rejects prose and ambiguous output."""
    if not isinstance(answer,str) or len(answer)>256 or '\n' in answer or '\r' in answer:
        return None
    a,b,op,truth,kind = expected(question)
    answer=answer.strip()
    m=BARE.fullmatch(answer)
    if m:
        return str(int(m['result']))
    m=ECHO.fullmatch(answer)
    if not m or (int(m['a']),int(m['b']),ALIASES[m['op']])!=(a,b,op):
        return None
    return str(int(m['result']))


def audit(report, raw_sha):
    if report.get('schema')!='V13_RUN142_C3_AGE0D_NATIVE_V1': raise ValueError('wrong schema')
    if report.get('evidence_class')!='LINUX_X86_64_NATIVE_SINGLE_C3': raise ValueError('wrong evidence class')
    if report.get('status')!='LINUX_NATIVE_C3_COHORT_EXECUTED': raise ValueError('incomplete native run')
    if report.get('seed')!=14225 or report.get('gates')!=EXPECTED_GATES: raise ValueError('seed/gates mismatch')
    prov=report.get('provenance',{})
    if prov.get('model_sha256')!=MODEL_SHA or prov.get('runner_archive_sha256')!=RUNNER_SHA:
        raise ValueError('registered provenance mismatch')
    rows=report.get('rows')
    if not isinstance(rows,list) or len(rows)!=80: raise ValueError('missing rows')
    seen=set(); out=[]; statuses=Counter(); diagnostics=Counter(); ops=Counter()
    for row in rows:
        if not isinstance(row,dict) or type(row.get('id')) is not int or row['id'] in seen:
            raise ValueError('duplicate/invalid row id')
        seen.add(row['id'])
        if row['id']<0 or row['id']>=80 or 'error' in row: raise ValueError('bad/failed row')
        a,b,op,truth,kind=expected(row.get('question'))
        if row.get('op')!=kind or row.get('truth')!=truth: raise ValueError('question/truth mismatch')
        if row.get('response_sha256')!=sha256(row.get('response','').encode('utf-8')):
            raise ValueError('response hash mismatch')
        status=row.get('check')
        if status not in ('CORRECT','MISMATCH','ABSTAIN'): raise ValueError('invalid original status')
        parsed=parse_strict_answer(row['question'],row['response'])
        verdict='ABSTAIN' if parsed is None else ('CORRECT' if parsed==truth else 'MISMATCH')
        statuses[status]+=1; diagnostics[verdict]+=1; ops[kind]+=1
        out.append({'id':row['id'],'op':kind,'original':status,'diagnostic':verdict,
                    'claimed':parsed,'truth':truth,'response_sha256':row['response_sha256']})
    if seen!=set(range(80)) or ops!={'plus':10,'minus':20,'times':40,'divided by':10}:
        raise ValueError('registered task structure mismatch')
    recovered=[r for r in out if r['original']=='ABSTAIN' and r['diagnostic']!='ABSTAIN']
    conflicts=[r for r in out if r['original'] in ('CORRECT','MISMATCH') and r['diagnostic'] not in (r['original'],)]
    return {'schema':'V13_RUN143_READONLY_RUN142_AUDIT_V1','source_commit':SOURCE_COMMIT,
            'source_report_sha256':raw_sha,'evidence_class':'POSTHOC_SOFTWARE_AUDIT_OF_LINUX_NATIVE_OUTPUT',
            'original_statuses':dict(statuses),'diagnostic_statuses':dict(diagnostics),
            'original_abstains_with_strict_diagnostic':len(recovered),
            'original_supported_disagreement':len(conflicts),
            'recovered_ids':[r['id'] for r in recovered],
            'conflict_ids':[r['id'] for r in conflicts],
            'per_operation':{op:{k:sum(r['op']==op and r['diagnostic']==k for r in out)
                              for k in ('CORRECT','MISMATCH','ABSTAIN')}
                             for op in ('plus','minus','times','divided by')},
            'rows':out,'gates':EXPECTED_GATES,'age0d_delivery':'OFF',
            'gate':'UNVERIFIED','claim_limit':'POSTHOC_FORMAT_DIAGNOSTIC_NOT_PREREGISTERED_K1_K2_K3'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--report',type=Path,required=True)
    p.add_argument('--expected-sha256',required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    data=a.report.read_bytes(); digest=sha256(data)
    if digest!=a.expected_sha256: raise SystemExit('REFUSED_UNBOUND_SOURCE_SHA256')
    result=audit(json.loads(data),digest)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},sort_keys=True))


if __name__=='__main__': main()
