"""Real causal native-state pairs; no synthetic latent targets or body update."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.common import APP,atomic_write,dumps,file_hash
from v13.config import initialize
from v13.runtime import Runtime
from v13.operator import Operator
from v13.resources import device

def main():
    p=argparse.ArgumentParser();p.add_argument('--installed-home',required=True);p.add_argument('--out',required=True);p.add_argument('--role',choices=['B1_DETAIL','B2_GIST'],default='B1_DETAIL');a=p.parse_args();installed=Path(a.installed_home).resolve();out=Path(a.out)
    report={'status':'RUNNING','device':device(),'role':a.role,'scope':'external predictor/projector and stop-gradient target EMA over actual dense-body final states; no sparse body training or injection',
            'labels':'explicit fixture observation permissions; native states are measurements, not semantic truth','checks':{},'source_hashes':{str(f.relative_to(APP)):file_hash(f) for f in (APP/'v13').glob('*.py')}}
    def save():atomic_write(out,json.dumps(report,ensure_ascii=False,indent=2))
    save()
    with tempfile.TemporaryDirectory(prefix='v13-predictor-') as folder:
        h=Path(folder);initialize(h)
        for name in ('models','bin'):shutil.rmtree(h/name);(h/name).symlink_to(installed/name,target_is_directory=True)
        shutil.copyfile(installed/'config/models.json',h/'config/models.json');r=Runtime(h)
        try:
            report['inputs']=[]
            for i in range(16):
                text=f'Projekt Atlas hat ein Budget von {100+i*20} Euro. Davon sind {20+i*10} Euro reserviert. Der Rest bleibt als Reserve im Projekt.'
                e=r.store.event(r.session,text);r.memory.feedback(e['event_id'],'prediction','observe','learn');report['inputs'].append(text)
            before=r.store.generation_id;body_hash=file_hash(r.models.path_for(a.role));r.cfg['learning_mode']='SHADOW_UPDATE';report['result']=r.learner.shadow_predictor(a.role)
            u=r.store.one('SELECT * FROM updates ORDER BY created DESC LIMIT 1');manifest=json.loads(u['manifest']);report['update']={'status':u['status'],'manifest':manifest};save()
            metrics=manifest['metrics'];report['checks'].update(causal_prefix=manifest['causal_prefix_proof']['pass'],actual_tap_count=len(manifest['tap_packet_ids'])==16,
                shadow_no_commit=before==r.store.generation_id,gradient=metrics['gradient_check'],target_ema_changed=metrics['target_changed'],noncollapse=metrics['noncollapse_pass'],heldout_ablation=metrics['predictive_ablation_pass'],retention=metrics['retention_pass'])
            if u['status']=='PENDING_APPROVAL':
                r.cfg['learning_mode']='APPROVED_COMMIT';Operator(r).run(':approve '+u['id']);session=r.session;r.close();r=Runtime(h)
                e=r.store.event(r.session,'Projekt Atlas hat ein Budget von 460 Euro. Davon sind 200 Euro reserviert. Der Rest bleibt als Reserve im Projekt.')
                tap=r.cognition.tap(a.role,e,e['source_ref'],time.monotonic()+90);report['actual_prediction_after_restart']=tap.get('local_prediction')
                prediction=tap.get('local_prediction') or {};report['checks']['restart_consumes_predictor']=r.session==session and len(prediction.get('future_latent_prediction',[]))==16 and prediction.get('observed_pair_count',0)>0
                report['checks']['no_receiver_authority']=tap['receiver_injection_authority']==0 and prediction.get('receiver_injection') is False
                r.store.rollback(u['id']);report['checks']['rollback_removes_consumer']=r.learner.predict_states(a.role,r.cognition.read_tap(tap)['vectors']) is None
            else:report['checks']['activation_gate_passed']=False
            report['checks']['body_unchanged']=file_hash(r.models.path_for(a.role))==body_hash;report['checks']['integrity']=not r.store.integrity(True)
            report['status']='PREDICTOR_LIFECYCLE_PASS' if all(report['checks'].values()) else 'PREDICTOR_LIFECYCLE_PARTIAL'
        except Exception as exc:
            report.update(status='PREDICTOR_LIFECYCLE_PARTIAL',error=type(exc).__name__+': '+str(exc));report['worker_logs']=[p.read_text()[-3000:] for p in (h/'shadow').glob('*/worker.log')]
        finally:r.close();save()
    print(dumps({'status':report['status'],'checks':report['checks'],'error':report.get('error')}));return 0 if report['status']=='PREDICTOR_LIFECYCLE_PASS' else 2

if __name__=='__main__':sys.exit(main())
