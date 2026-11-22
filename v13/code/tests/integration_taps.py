"""Actual pinned dense-body final-state tap. No injection/training permission."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.common import APP,atomic_write,dumps,digest,file_hash,Cancelled,Limits
from v13.config import initialize
from v13.runtime import Runtime
from v13.resources import device

def main():
    p=argparse.ArgumentParser();p.add_argument('--installed-home',required=True);p.add_argument('--out',required=True);a=p.parse_args();installed=Path(a.installed_home).resolve();out=Path(a.out)
    report={'status':'RUNNING','device':device(),'tap_id':'lfm2.result_norm.final.v1','scope':'independent read-only dense-body prefill, not live private KV or MobileMoE','CAN_LATENT_INJECT':False,'CAN_TRAIN_BODY':False,'checks':{},'rows':[],
            'source_hashes':{str(f.relative_to(APP)):file_hash(f) for f in (APP/'v13').glob('*.py')}}
    def save():atomic_write(out,json.dumps(report,ensure_ascii=False,indent=2))
    with tempfile.TemporaryDirectory(prefix='v13-tap-proof-') as folder:
        h=Path(folder);initialize(h)
        for name in ('models','bin'):shutil.rmtree(h/name);(h/name).symlink_to(installed/name,target_is_directory=True)
        shutil.copyfile(installed/'config/models.json',h/'config/models.json');r=Runtime(h)
        try:
            generation=r.store.generation_id;vectors=[];packets=[]
            for role,text in [('B1_DETAIL','Projekt Aurora: Budget 120 Euro.'),('B1_DETAIL','Projekt Aurora: Budget 120 Euro.'),('B2_GIST','Projekt Borealis: Die Blume ist blau.')]:
                e=r.store.event(r.session,text);packet=r.cognition.tap(role,e,e['source_ref'],time.monotonic()+60);data=r.cognition.read_tap(packet);v=data['vectors'][-1]
                vectors.append(v);packets.append(packet);report['rows'].append({'packet':packet,'last_vector_sha256':digest(dumps(v)),'last_vector_first_eight':v[:8],'last_vector_norm':sum(x*x for x in v)**.5,'unload':r.pool.unload()});save()
            report['checks'].update(actual_native_states=all(x['packet']['shape'][1]==(1024 if x['packet']['tap_id'].startswith('qwen35') else 2048) for x in report['rows']),same_input_repeatable=vectors[0]==vectors[1],different_input_different=vectors[0]!=vectors[2],generation_unchanged=r.store.generation_id==generation)
            r.close();r=Runtime(h)
            report['checks']['restart_exact_feature_reload']=r.cognition.read_tap(packets[0])['vectors'][-1]==vectors[0]
            # Overflow refuses truncation; no fabricated feature packet is stored.
            e=r.store.event(r.session,'Text '*200);before=r.store.one("SELECT COUNT(*) AS n FROM packets WHERE kind='LatentTapPacket'")['n']
            try:r.cognition.tap('B1_DETAIL',e,e['source_ref'],time.monotonic()+60);refused=False
            except Limits:refused=True
            report['checks']['token_budget_refuses']=refused and r.store.one("SELECT COUNT(*) AS n FROM packets WHERE kind='LatentTapPacket'")['n']==before;r.pool.unload()
            ready=threading.Event()
            def cancel_native():
                until=time.monotonic()+10
                while time.monotonic()<until and not ready.is_set():
                    if r.pool.current and r.pool.current.proc:r.cancel_event.set();return
                    time.sleep(.005)
            t=threading.Thread(target=cancel_native);t.start();e=r.store.event(r.session,'Native cancellation fixture.')
            try:r.cognition.tap('B1_DETAIL',e,e['source_ref'],time.monotonic()+60);cancelled=False
            except Cancelled:cancelled=True
            finally:ready.set();t.join();r.cancel_event.clear()
            report['checks']['cancel_reaps_native_process']=cancelled and not r.pool.pids();r.pool.unload()
            # Actual text generation remains usable after switching native modes.
            runner=r.pool.get('C3_LANGUAGE');answer=''.join(runner.generate([{'role':'user','content':'Sag kurz Hallo auf Deutsch.'}],r.cancel_event,time.monotonic()+60,max_tokens=32))
            report['actual_text_after_tap']=answer;report['checks']['text_runner_after_tap']=bool(answer.strip());r.pool.unload()
            report['checks']['integrity']=not r.store.integrity(True)
            report['status']='NATIVE_TAP_PASS' if all(report['checks'].values()) else 'NATIVE_TAP_PARTIAL'
        except Exception as exc:report.update(status='NATIVE_TAP_PARTIAL',error=type(exc).__name__+': '+str(exc))
        finally:r.close();save()
    print(dumps({'status':report['status'],'checks':report['checks'],'error':report.get('error')}));return 0 if report['status']=='NATIVE_TAP_PASS' else 2

if __name__=='__main__':sys.exit(main())
