"""Run136: registered C3 Linux-native answer-visible arithmetic cohort.

Never modifies Runtime or registered cohort; always records partial/failed rows.
No live AGE0d delivery or gate promotion.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import re
import threading
import time

from v13.agi.answer_arithmetic_shadow import evaluate
from v13.config import initialize
from v13.models import ModelManager,catalog,download_file
from v13.bootstrap import extract
from v13.runners import LlamaRunner

SEED=13625
MODEL_SHA='3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d'
RUNNER_SHA='9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443'
OPS=('plus','minus','times','divided by')
SYSTEM="You are a concise assistant. Answer with 'The answer is <number>.' only."
ANSWER=re.compile(r'\s*(?:The answer is\s+)?(?P<num>-?\d{1,9}(?:\.\d{1,4})?)\.?\s*',re.IGNORECASE)


def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()


def tasks():
    rng=random.Random(SEED)
    out=[]
    for op in OPS:
        for _ in range(15):
            a,b=rng.randint(1,30),rng.randint(1,30)
            if op=='plus':truth=a+b
            elif op=='minus':truth=a-b
            elif op=='times':truth=a*b
            else:a*=b;truth=a//b
            out.append({'id':len(out),'op':op,'question':f'What is {a} {op} {b}?','truth':str(truth)})
    return out


def parse_answer(text):
    if not isinstance(text,str):return None
    m=ANSWER.fullmatch(text)
    if m is None:return None
    from decimal import Decimal
    value=Decimal(m.group('num'))
    return '0' if value==0 else format(value.normalize(),'f')


def summarize(rows):
    n=len(rows)
    known=[r for r in rows if r.get('parsed') is not None]
    correct=[r for r in known if r['parsed']==r['truth']]
    wrong=[r for r in known if r['parsed']!=r['truth']]
    fp=sum(r['check']=='MISMATCH' for r in correct)
    detected=sum(r['check']=='MISMATCH' for r in wrong)
    supported=sum(r.get('check') in ('CORRECT','MISMATCH') for r in rows)
    k1='INSUFFICIENT' if len(correct)<10 else ('PASS' if fp/len(correct)<=.10 else 'FAIL')
    k2='INSUFFICIENT' if len(wrong)<10 else ('PASS' if detected/len(wrong)>=.20 else 'FAIL')
    k3='PASS' if n and supported/n>=.30 else 'FAIL'
    return {'n':n,'known_truth_count':len(known),'correct_count':len(correct),'wrong_count':len(wrong),
            'unknown_truth_count':n-len(known),'supported':supported,'abstained':n-supported,
            'false_alarm_numerator':fp,'wrong_detected':detected,
            'false_alarm_rate':None if not correct else fp/len(correct),
            'wrong_detection_rate':None if not wrong else detected/len(wrong),
            'coverage':0 if not n else supported/n,
            'thresholds':{'K1':k1,'K2':k2,'K3':k3},
            'gate':'UNVERIFIED','claim_limit':'REGISTERED_C3_LINUX_NATIVE_NARROW_ARITHMETIC_ONLY'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--home',required=True);p.add_argument('--report',required=True)
    args=p.parse_args();home=Path(args.home).resolve();report=Path(args.report).resolve()
    report.parent.mkdir(parents=True,exist_ok=True)
    result={'schema':'V13_RUN136_C3_AGE0D_NATIVE_V1','evidence_class':'LINUX_X86_64_NATIVE_SINGLE_C3',
            'status':'FAIL','seed':SEED,'rows':[],'gates':{'STEP2':'UTILITY_FAIL','B3_L1':'FAIL',
            'Body_JEPA':'UNAVAILABLE','jepa_weight':0,'DS2_H2':'FAIL','V13':'INCOMPLETE'}}
    runner=None;start=time.monotonic()
    try:
        cfg=dict(initialize(home));cfg.update(threads=2,context_tokens=1024,answer_tokens=48)
        specs=catalog();ms=specs['models']['language'];ns=specs['runner']['linux_binaries']['linux-x86_64']
        assert ms['revision']=='657e078c94084481950a2d555a941481f715536b'
        assert ms['files'][0]['sha256']==MODEL_SHA and ns['sha256']==RUNNER_SHA
        mm=ModelManager(home);mm.install('language',progress=lambda x:print('MODEL_DOWNLOAD',x,flush=True))
        assert mm.verify(deep=True)['language']['ok']
        model=mm.path_for('C3_LANGUAGE')
        archive=home/'tmp/llama-b10964-linux-x64.tar.gz'
        download_file(ns,archive,progress=lambda x:print('RUNNER_DOWNLOAD',x,flush=True))
        native_dir=home/'bin/b10964';extract(archive,native_dir)
        candidates=list(native_dir.rglob('llama-server'))
        if len(candidates)!=1:raise RuntimeError('nonunique llama-server')
        binary=candidates[0];binary.chmod(0o700);os.environ['V13_LLAMA_SERVER']=str(binary)
        result['provenance']={'model_sha256':sha256(model),'model_bytes':model.stat().st_size,
                              'model_revision':ms['revision'],'model_license':ms['license_id'],
                              'runner_archive_sha256':sha256(archive),'runner_binary_sha256':sha256(binary),
                              'runner_tag':specs['runner']['tag']}
        assert result['provenance']['model_sha256']==MODEL_SHA
        assert result['provenance']['runner_archive_sha256']==RUNNER_SHA
        runner=LlamaRunner(home,'C3_LANGUAGE',model,cfg)
        cancel=threading.Event()
        for t in tasks():
            try:
                response=''.join(runner.generate([{'role':'system','content':SYSTEM},
                          {'role':'user','content':t['question']}],cancel,time.monotonic()+45,
                          max_tokens=48,seed=SEED+t['id']))
                check=evaluate(t['question'],response)
                row=dict(t,response=response,response_sha256=hashlib.sha256(response.encode()).hexdigest(),
                         parsed=parse_answer(response),check=check['status'],
                         duration_s=runner.last_metrics.get('duration_s'),
                         ttft_s=runner.last_metrics.get('ttft_s'))
                result['rows'].append(row)
                print('RUN136_ROW',t['id'],row['check'],row['parsed'],flush=True)
            except Exception as exc:
                result['rows'].append(dict(t,error=type(exc).__name__,check='ABSTAIN',parsed=None))
                print('RUN136_ROW_ERROR',t['id'],type(exc).__name__,flush=True)
        result['summary']=summarize(result['rows'])
        result['status']='LINUX_NATIVE_C3_COHORT_EXECUTED' if len(result['rows'])==60 and all('error' not in x for x in result['rows']) else 'PARTIAL_OR_FAILED'
    except BaseException as exc:
        result['error']={'type':type(exc).__name__,'message':str(exc)[:400]}
        print('RUN136_FATAL',type(exc).__name__,str(exc)[:400],flush=True)
        raise
    finally:
        if runner is not None:
            try:result['unload']=runner.unload()
            except Exception as exc:result['unload_error']=type(exc).__name__
        result['elapsed_s']=round(time.monotonic()-start,3)
        report.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
        print('RUN136_REPORT',report,'STATUS',result['status'],flush=True)

if __name__=='__main__':main()
