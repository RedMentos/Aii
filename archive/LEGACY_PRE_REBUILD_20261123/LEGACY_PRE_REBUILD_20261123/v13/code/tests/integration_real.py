"""Opt-in real-weight test. Nothing in this file mocks inference.
Run: python tests/integration_real.py --installed-home ~/v13 --out proof.json
Creates an isolated brain; reads installed immutable models/binaries.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.config import initialize,save_config
from v13.runtime import Runtime
from v13.common import APP,dumps,atomic_write,digest,file_hash
from v13.resources import device

def wait(r,timeout=120):
    end=time.monotonic()+timeout
    while not r.idle() and time.monotonic()<end:time.sleep(.025)
    if not r.idle():r.cancel();raise RuntimeError('Test wait timeout')
def ask(r,text):
    r.submit(text);wait(r);m=r.last_answer();return {'text':m['text'],'status':m['status'],'metadata':json.loads(m['metadata'])}
def main():
    p=argparse.ArgumentParser();p.add_argument('--installed-home',required=True);p.add_argument('--out',required=True);a=p.parse_args();installed=Path(a.installed_home).resolve();report={'device':device(),'uses_real_weights':True,'history_turns':0,'phone_measured':device()['android'],'source_hashes':{str(p.relative_to(APP)):file_hash(p) for p in list((APP/'v13').glob('*.py'))+[Path(__file__).resolve()]}}
    with tempfile.TemporaryDirectory(prefix='v13-real-') as d:
        h=Path(d);cfg=initialize(h);cfg.update(observer_mode='off',route_override='detail',history_turns=0,answer_tokens=128);save_config(h,cfg)
        for name in ['models','bin']:shutil.rmtree(h/name);(h/name).symlink_to(installed/name,target_is_directory=True)
        shutil.copyfile(installed/'config/models.json',h/'config/models.json');r=Runtime(h)
        try:
            q='Welches Budget hat Projekt Aurora? Sag nur den Betrag, falls er bekannt ist.'
            report['before']=ask(r,q);generation=r.store.generation_id;mem=r.memory.feedback(r.last_answer()['event_id'],'fact','Das Budget von Projekt Aurora beträgt 120 Euro. Es gelten weiterhin die Vorgaben: nur lokal, keine Cloud.')
            sid=r.session;r.close();r=Runtime(h);report['restart_same_session']=r.session==sid
            query='Welches Budget hat Projekt Aurora? Nenne auch die Hälfte des Budgets.';report['after_restart']=ask(r,query)
            report['unrelated_project']=ask(r,'Welches Budget hat Projekt Borealis? Sag nur den Betrag, falls er bekannt ist.')
            r.cfg['memory_top_k']=0;report['memory_ablation']=ask(r,query);r.cfg['memory_top_k']=3
            report['generation_unchanged']=generation==r.store.generation_id
            r.cfg.update(route_override='simple',answer_tokens=1024);r.submit('Schreibe eine lange Geschichte über einen Roboter, mindestens 1000 Wörter.');end=time.monotonic()+35
            while time.monotonic()<end:
                m=r.store.one("SELECT * FROM messages WHERE session_id=? AND role='assistant' ORDER BY id DESC LIMIT 1",(r.session,))
                if m and m['status']=='STREAMING' and len(m['text'])>30:break
                time.sleep(.02)
            start=time.monotonic();r.cancel();wait(r);m=r.last_answer();partial=m['text'];mid=m['id'];report['cancel']={'status':m['status'],'characters':len(partial),'text':partial,'stop_s':time.monotonic()-start,'runner':json.loads(m['metadata']).get('runner',{}),'native_process_stopped':not r.pool.pids()}
            r.close();r=Runtime(h);saved=r.store.one('SELECT * FROM messages WHERE id=?',(mid,));report['cancel']['restart_preserved']=saved['text']==partial and saved['status']=='CANCELLED'
            r.cfg.update(observer_mode='off',route_override='simple',deadline_seconds=.01);report['deadline']=ask(r,'Erkläre die Relativitätstheorie.')
            report['integrity_errors']=r.store.integrity(True)
            report['checks']={'restart':report['restart_same_session'],'actual_first_model_output':report['before']['metadata']['model_generated'],'correction_used':mem in report['after_restart']['metadata']['memory_ids'],'new_computation':('120' in report['after_restart']['text'] and '60' in report['after_restart']['text']),'no_cross_project_retrieval':not report['unrelated_project']['metadata']['memory_ids'],'ablation_no_retrieval':not report['memory_ablation']['metadata']['memory_ids'],'ablation_loses_budget':not ('120' in report['memory_ablation']['text'] and '60' in report['memory_ablation']['text']),'record_only_no_weights':report['generation_unchanged'],'cancel_persisted':report['cancel']['restart_preserved'],'deadline_has_output':report['deadline']['status']=='DEADLINE' and bool(report['deadline']['text']),'integrity':not report['integrity_errors']}
            report['checks']['cancel_runner_status']=report['cancel']['runner'].get('status')=='CANCELLED';report['checks']['cancel_native_process_stopped']=report['cancel']['native_process_stopped']
            report['all_passed']=all(report['checks'].values())
        finally:r.close()
    atomic_write(Path(a.out),json.dumps(report,ensure_ascii=False,indent=2));print(dumps(report['checks']));return 0 if report['all_passed'] else 1
if __name__=='__main__':sys.exit(main())
