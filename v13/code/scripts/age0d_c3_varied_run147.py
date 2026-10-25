"""Run147 preregistered fresh C3 native varied-language AGE0d SHADOW holdout.

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

from v13.agi.answer_arithmetic_shadow_v2 import evaluate as check_new
from v13.agi.answer_arithmetic_shadow import evaluate as check_old
from v13.config import initialize
from v13.models import ModelManager,catalog,download_file
from v13.bootstrap import extract
from v13.runners import LlamaRunner

SEED=14725
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
            while sum(x['op']==op and x['phrasing']==phrasing for x in out)<8:
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
    fp=sum(r['new_check']=='MISMATCH' for r in correct)
    detected=sum(r['new_check']=='MISMATCH' for r in wrong)
    supported=sum(r['new_check'] in ('CORRECT','MISMATCH') for r in rows)
    n=len(rows)
    complete=n==96 and all('error' not in r for r in rows)
    return {'n':n,'labelable':len(known),'label_correct':len(correct),'label_wrong':len(wrong),
            'label_unknown':n-len(known),'new_supported':supported,
            'old_supported':sum(r['old_check'] in ('CORRECT','MISMATCH') for r in rows),
            'false_alarms':fp,'wrong_detected':detected,
            'false_alarm_rate':None if not correct else fp/len(correct),
            'wrong_detect_rate':None if not wrong else detected/len(wrong),
            'coverage':0 if not n else supported/n,
            'K1':'INSUFFICIENT' if not complete or len(correct)<10 else ('PASS' if fp/len(correct)<=.10 else 'FAIL'),
            'K2':'INSUFFICIENT' if not complete or len(wrong)<10 else ('PASS' if detected/len(wrong)>=.20 else 'FAIL'),
            'K3':'PASS' if complete and supported/n>=.30 else 'FAIL',
            'per_phrasing':{p:{'n':sum(r['phrasing']==p for r in rows),
                               'supported':sum(r['phrasing']==p and r['new_check']!='ABSTAIN' for r in rows)}
                            for p in ('What is','Calculate','Compute')},
            'claim_limit':'AUTOMATED_FORMAT_LABELS_NARROW_ARITHMETIC_NO_LIVE_DELIVERY',
            'gate':'UNVERIFIED'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--home',required=True);p.add_argument('--report',required=True)
    args=p.parse_args();home=Path(args.home).resolve();report=Path(args.report).resolve()
    report.parent.mkdir(parents=True,exist_ok=True)
    result={'schema':'V13_RUN147_C3_VARIED_NATIVE_V1','evidence_class':'LINUX_X86_64_NATIVE_SINGLE_C3',
            'status':'FAIL','seed':SEED,'rows':[],'gates':GATES,'age0d_delivery':'OFF'}
    runner=None;start=time.monotonic()
    try:
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
        for t in tasks():
            try:
                response=''.join(runner.generate([{'role':'system','content':SYSTEM},
                        {'role':'user','content':t['question']}],cancel,time.monotonic()+45,
                        max_tokens=48,seed=SEED+t['id']))
                new=check_new(t['question'],response);old=check_old(t['question'],response)
                row=dict(t,response=response,response_sha256=hashlib.sha256(response.encode()).hexdigest(),
                         label=label_answer(response),new_check=new['status'],old_check=old['status'],
                         duration_s=runner.last_metrics.get('duration_s'),ttft_s=runner.last_metrics.get('ttft_s'))
                result['rows'].append(row)
                print('RUN147_ROW',t['id'],row['new_check'],row['old_check'],row['label'],flush=True)
            except Exception as exc:
                result['rows'].append(dict(t,error=type(exc).__name__,label=None,
                                          new_check='ABSTAIN',old_check='ABSTAIN'))
                print('RUN147_ROW_ERROR',t['id'],type(exc).__name__,flush=True)
        result['summary']=summarize(result['rows'])
        result['status']='LINUX_NATIVE_C3_COHORT_EXECUTED' if len(result['rows'])==96 and all('error' not in r for r in result['rows']) else 'PARTIAL_OR_FAILED'
    except BaseException as exc:
        result['error']={'type':type(exc).__name__,'message':str(exc)[:400]}
        print('RUN147_FATAL',type(exc).__name__,str(exc)[:400],flush=True)
        raise
    finally:
        if runner is not None:
            try:result['unload']=runner.unload()
            except Exception as exc:result['unload_error']=type(exc).__name__
        result['elapsed_s']=round(time.monotonic()-start,3)
        report.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
        print('RUN147_REPORT',report,'STATUS',result['status'],flush=True)

if __name__=='__main__':main()
