"""Run131: one pinned registered C3 Linux CPU smoke; never a full V13 proof."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import threading
import time
import traceback

from v13.config import initialize
from v13.models import ModelManager, catalog, download_file
from v13.bootstrap import extract
from v13.runners import LlamaRunner


def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):
            h.update(block)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--home',required=True)
    p.add_argument('--report',required=True)
    a=p.parse_args()
    home=Path(a.home).resolve()
    report=Path(a.report).resolve()
    report.parent.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    result={'schema':'V13_RUN131_NATIVE_C3_SMOKE_V1','evidence_class':'LINUX_X86_64_NATIVE_SINGLE_MODEL',
            'status':'FAIL','no_full_system_claim':True,
            'gates':{'STEP2':'UTILITY_FAIL','B3_L1':'FAIL','Body_JEPA':'UNAVAILABLE','jepa_weight':0,'DS2_H2':'FAIL','V13':'INCOMPLETE'}}
    runner=None
    try:
        cfg=initialize(home)
        cfg=dict(cfg)
        cfg.update(threads=2,context_tokens=1024,answer_tokens=32)
        specs=catalog()
        model_spec=specs['models']['language']
        native_spec=specs['runner']['linux_binaries']['linux-x86_64']
        assert model_spec['revision']=='657e078c94084481950a2d555a941481f715536b'
        assert model_spec['files'][0]['sha256']=='3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d'
        assert native_spec['sha256']=='9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443'
        mm=ModelManager(home)
        mm.install('language',progress=lambda x:print('MODEL_DOWNLOAD',x,flush=True))
        verified=mm.verify(deep=True)
        if not verified['language']['ok']:raise RuntimeError('registered C3 SHA check failed')
        model=mm.path_for('C3_LANGUAGE')
        archive=home/'tmp/llama-b10964-linux-x64.tar.gz'
        download_file(native_spec,archive,progress=lambda x:print('RUNNER_DOWNLOAD',x,flush=True))
        native_dir=home/'bin/b10964'
        extract(archive,native_dir)
        candidates=list(native_dir.rglob('llama-server'))
        if len(candidates)!=1:raise RuntimeError('nonunique native llama-server')
        binary=candidates[0]
        binary.chmod(0o700)
        os.environ['V13_LLAMA_SERVER']=str(binary)
        result['provenance']={'model_id':model_spec['model_id'],'model_revision':model_spec['revision'],
            'model_sha256':sha256(model),'model_bytes':model.stat().st_size,
            'model_license':model_spec['license_id'],'runner_tag':specs['runner']['tag'],
            'runner_archive_sha256':sha256(archive),'runner_archive_bytes':archive.stat().st_size,
            'runner_binary_sha256':sha256(binary)}
        cancel=threading.Event()
        runner=LlamaRunner(home,'C3_LANGUAGE',model,cfg)
        response=''.join(runner.generate([
            {'role':'system','content':'You are a concise assistant. Respond in English.'},
            {'role':'user','content':'Reply with a short greeting.'}],
            cancel,time.monotonic()+150,max_tokens=24,seed=13))
        metrics=dict(runner.last_metrics)
        result['response']={'chars':len(response),'nonempty':bool(response.strip()),
            'generated_tokens':metrics.get('generated_tokens'),
            'ttft_s':metrics.get('ttft_s'),'duration_s':metrics.get('duration_s'),
            'peak_rss_bytes':metrics.get('sampled_peak_rss_bytes'),
            'can_train_body':metrics.get('CAN_TRAIN_BODY'),
            'can_latent_inject':metrics.get('CAN_LATENT_INJECT')}
        if not response.strip():raise RuntimeError('native response empty')
        result['status']='LINUX_NATIVE_SINGLE_C3_PASS'
    except BaseException as e:
        result['error']={'type':type(e).__name__,'message':str(e)[:400]}
        print('RUN131_NATIVE_FAILURE',type(e).__name__,str(e)[:400],flush=True)
        raise
    finally:
        if runner is not None:
            try:result['unload']=runner.unload()
            except BaseException as e:result['unload_error']=type(e).__name__
        result['elapsed_s']=round(time.monotonic()-started,3)
        report.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
        print('RUN131_REPORT',report,'STATUS',result['status'],flush=True)


if __name__=='__main__':main()
