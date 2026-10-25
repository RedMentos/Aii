"""Run151 preregistered fresh C3 native varied-language AGE0d SHADOW holdout.

No runtime/learning rights changes. Independent format labels are bounded, not
human labels; negative/partial evidence is retained and never promoted.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import random
import re
import threading
import time
import zipfile

from v13.agi.answer_arithmetic_shadow_v2 import evaluate as check_v2
from v13.agi.answer_arithmetic_shadow_v3 import evaluate as check_v3
from v13.agi.answer_arithmetic_shadow import evaluate as check_old
from v13.config import initialize
from v13.models import ModelManager,catalog,download_file
from v13.bootstrap import extract
from v13.runners import LlamaRunner

SEED=15132
TASK_SHA='9418de94428bb51a42d4d5e292ab9f5ef5e94acea61382d3f88c1694a7712144'
PRIOR_SHA='ddd60c897e1bdc634a40179b67e434097bb1e1999a6a2141372f6272682b9676'
MODEL_SHA='3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d'
RUNNER_SHA='9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443'
EXCLUDED_PRIOR={'What is 504 divided by 18?', 'What is 96 times 78?'}
SYSTEM='You are a calculator. Answer each arithmetic question with one integer. You may include the original equation but no extra explanation.'
GATES={'STEP2':'UTILITY_FAIL','B3_L1':'FAIL','Body_JEPA':'UNAVAILABLE','jepa_weight':0,'DS2_H2':'FAIL','V13':'INCOMPLETE'}
LABEL_BARE=re.compile(r'\s*(?:The answer is\s+|Result:\s*)?(?P<n>-?\d{1,12})\.?\s*',re.I)
LABEL_ECHO=re.compile(r'\s*-?\d{1,6}\s*[+\-*×÷/]\s*-?\d{1,6}\s*=\s*(?P<n>-?\d{1,12})\.?\s*')


def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()


def tasks():
    rng=random.Random(SEED);out=[];seen=set()
    for op in ('plus','minus','times','divided by'):
        for phrasing in ('What is','Calculate','Compute'):
            while sum(x['op']==op and x['phrasing']==phrasing for x in out)<24:
                a,b=rng.randint(10,99),rng.randint(10,99)
                if op=='plus':truth=a+b
                elif op=='minus':truth=a-b
                elif op=='times':truth=a*b
                else:
                    b=rng.randint(2,30);truth=rng.randint(2,30);a=b*truth
                q=f'{phrasing} {a} {op} {b}{"?" if phrasing=="What is" else "."}'
                if q in seen or q in EXCLUDED_PRIOR:continue
                seen.add(q);out.append({'id':len(out),'op':op,'phrasing':phrasing,'question':q,'truth':str(truth)})
    return out


def label_answer(answer):
    """Independent broad exact-output numeric label, NOT a human adjudication."""
    if not isinstance(answer,str) or len(answer)>256 or '\n' in answer or '\r' in answer:return None
    m=LABEL_BARE.fullmatch(answer) or LABEL_ECHO.fullmatch(answer)
    return None if m is None else str(int(m['n']))


def summarize(rows):
    known=[r for r in rows if r.get('label') is not None]
    correct=[r for r in known if r['label']==r['truth']]
    wrong=[r for r in known if r['label']!=r['truth']]
    n=len(rows);complete=n==288 and all('error' not in r for r in rows)
    fp_v2=sum(r['new_check']=='MISMATCH' for r in correct)
    fp_v3=sum(r['v3_check']=='MISMATCH' for r in correct)
    detected_v2=sum(r['new_check']=='MISMATCH' for r in wrong)
    detected_v3=sum(r['v3_check']=='MISMATCH' for r in wrong)
    v2=sum(r['new_check'] in ('CORRECT','MISMATCH') for r in rows)
    v3=sum(r['v3_check'] in ('CORRECT','MISMATCH') for r in rows)
    return {'n':n,'labelable':len(known),'label_correct':len(correct),'label_wrong':len(wrong),
            'label_unknown':n-len(known),'v2_supported':v2,'v3_supported':v3,
            'old_supported':sum(r['old_check'] in ('CORRECT','MISMATCH') for r in rows),
            'v3_only_unadjudicated':sum(r['label'] is None and r['v3_check']!='ABSTAIN' for r in rows),
            'false_alarms_v2':fp_v2,'false_alarms_v3_strict_labels':fp_v3,
            'wrong_detected_v2':detected_v2,'wrong_detected_v3':detected_v3,
            'coverage_v2':v2/n if n else 0,'coverage_v3':v3/n if n else 0,
            'coverage_delta_pp':100*(v3-v2)/n if n else 0,
            'K1':'INSUFFICIENT' if not complete or len(correct)<50 else ('PASS' if fp_v3/len(correct)<=.02 else 'FAIL'),
            'K2':'INSUFFICIENT' if not complete or len(wrong)<10 else ('PASS' if detected_v3/len(wrong)>=.80 else 'FAIL'),
            'K3':'PASS' if complete and v3/n>=.30 and (v3-v2)/n>=.05 else 'FAIL',
            'per_phrasing':{p:{'n':sum(r['phrasing']==p for r in rows),
                               'v3_supported':sum(r['phrasing']==p and r['v3_check']!='ABSTAIN' for r in rows)}
                            for p in ('What is','Calculate','Compute')},
            'original_run147_K2':'INSUFFICIENT',
            'claim_limit':'AUTOMATED_STRICT_FORMAT_LABELS_V3_ONLY_UNADJUDICATED_NO_LIVE_DELIVERY',
            'gate':'UNVERIFIED'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--home',required=True);p.add_argument('--report',required=True);p.add_argument('--prior-zip',required=True)
    args=p.parse_args();home=Path(args.home).resolve();report=Path(args.report).resolve()
    report.parent.mkdir(parents=True,exist_ok=True)
    result={'schema':'V13_RUN151_C3_VARIED_NATIVE_V1','evidence_class':'LINUX_X86_64_NATIVE_SINGLE_C3',
            'status':'FAIL','seed':SEED,'rows':[],'gates':GATES,'age0d_delivery':'OFF'}
    runner=None;start=time.monotonic()
    try:
        planned=tasks()
        assert hashlib.sha256(json.dumps(planned,sort_keys=True,separators=(',',':')).encode()).hexdigest()==TASK_SHA
        assert sha256(args.prior_zip)==PRIOR_SHA
        with zipfile.ZipFile(args.prior_zip) as z:
            prior=json.loads(z.read('RUN147_C3_VARIED_NATIVE_REPORT.json'))
        assert len(prior['rows'])==96 and not ({t['question'] for t in planned}&{t['question'] for t in prior['rows']})
        result['registered_task_sha256']=TASK_SHA
        result['prior_artifact_sha256']=PRIOR_SHA
        cfg=dict(initialize(home));cfg.update(threads=2,context_tokens=1024,answer_tokens=48)
        specs=catalog();ms=specs['models']['language'];ns=specs['runner']['linux_binaries']['linux-x86_64']
        assert ms['revision']=='657e078c94084481950a2d555a941481f715536b'
        assert ms['files'][0]['sha256']==MODEL_SHA and ns['sha256']==RUNNER_SHA
        mm=ModelManager(home);mm.install('language',progress=lambda x:print('MODEL_DOWNLOAD',x,flush=True))
        assert mm.verify(deep=True)['language']['ok']
        model=mm.path_for('C3_LANGUAGE');archive=home/'tmp/llama-b10964-linux-x64.tar.gz'
        download_file(ns,archive,progress=lambda x:print('RUNNER_DOWNLOAD',x,flush=True))
        native_dir=home/'bin/b10964';extract(archive,native_dir)
        binaries=list(native_dir.rglob('llama-server'))
        if len(binaries)!=1:raise RuntimeError('nonunique llama-server')
        binary=binaries[0];binary.chmod(0o700);os.environ['V13_LLAMA_SERVER']=str(binary)
        result['provenance']={'model_sha256':sha256(model),'model_revision':ms['revision'],
                              'model_license':ms['license_id'],'runner_archive_sha256':sha256(archive),
                              'runner_binary_sha256':sha256(binary),'runner_tag':specs['runner']['tag']}
        assert result['provenance']['model_sha256']==MODEL_SHA
        assert result['provenance']['runner_archive_sha256']==RUNNER_SHA
        runner=LlamaRunner(home,'C3_LANGUAGE',model,cfg);cancel=threading.Event()
        for t in planned:
            try:
                response=''.join(runner.generate([{'role':'system','content':SYSTEM},
                        {'role':'user','content':t['question']}],cancel,time.monotonic()+45,
                        max_tokens=48,seed=SEED+t['id']))
                v2=check_v2(t['question'],response);v3=check_v3(t['question'],response);old=check_old(t['question'],response)
                row=dict(t,response=response,response_sha256=hashlib.sha256(response.encode()).hexdigest(),
                         label=label_answer(response),new_check=v2['status'],v3_check=v3['status'],old_check=old['status'],
                         duration_s=runner.last_metrics.get('duration_s'),ttft_s=runner.last_metrics.get('ttft_s'))
                result['rows'].append(row)
                print('RUN151_ROW',t['id'],row['new_check'],row['v3_check'],row['old_check'],row['label'],flush=True)
            except Exception as exc:
                result['rows'].append(dict(t,error=type(exc).__name__,label=None,
                                          new_check='ABSTAIN',v3_check='ABSTAIN',old_check='ABSTAIN'))
                print('RUN151_ROW_ERROR',t['id'],type(exc).__name__,flush=True)
        result['summary']=summarize(result['rows'])
        result['status']='LINUX_NATIVE_C3_COHORT_EXECUTED' if len(result['rows'])==288 and all('error' not in r for r in result['rows']) else 'PARTIAL_OR_FAILED'
    except BaseException as exc:
        result['error']={'type':type(exc).__name__,'message':str(exc)[:400]}
        print('RUN151_FATAL',type(exc).__name__,str(exc)[:400],flush=True)
        raise
    finally:
        if runner is not None:
            try:
                result['unload']=runner.unload()
                if result['unload'].get('process_reaped') is not True:result['status']='PARTIAL_OR_FAILED'
            except Exception as exc:
                result['unload_error']=type(exc).__name__;result['status']='PARTIAL_OR_FAILED'
        result['elapsed_s']=round(time.monotonic()-start,3)
        report.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
        print('RUN151_REPORT',report,'STATUS',result['status'],flush=True)

if __name__=='__main__':main()
