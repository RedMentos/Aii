"""Actual self -> frozen reference -> operator selection -> episodic replay.

The test operator explicitly selects a reference, without asserting its truth.
No generated text or synthetic model response is substituted for inference.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.common import atomic_write,digest
from v13.config import initialize,save_config
from v13.operator import Operator
from v13.resources import device
from v13.runtime import Runtime

def run(installed,out):
    installed=Path(installed).resolve();out=Path(out).resolve()
    report={'status':'RUNNING','device':device(),'stages':{},'checks':{},'reference_truth_validated':False}
    def save():atomic_write(out,json.dumps(report,ensure_ascii=False,indent=2))
    def idle(r):
        end=time.monotonic()+r.cfg['deadline_seconds']+15
        while not r.idle():
            if time.monotonic()>end:r.cancel();raise TimeoutError('Native experience wait')
            time.sleep(.05)
    save();r=None
    with tempfile.TemporaryDirectory(prefix='v13-experience-') as tmp:
        try:
            h=Path(tmp);cfg=initialize(h);cfg.update(observer_mode='off',route_override='simple',answer_tokens=128,history_turns=0);save_config(h,cfg)
            for name in ['models','bin']:shutil.rmtree(h/name);(h/name).symlink_to(installed/name,target_is_directory=True)
            shutil.copyfile(installed/'config/models.json',h/'config/models.json');r=Runtime(h);op=Operator(r)
            report.update(effective_config=dict(r.cfg),models=r.revisions())
            eid=r.submit('Projekt Aurora: Das Budget beträgt 120 Euro. Wie viel ist die Hälfte?');idle(r)
            own=r.last_answer();report['stages']['self']=dict(own);save()
            if own['status']!='FINAL':raise RuntimeError('Self not FINAL')
            own_hash=digest(own['text']);generation=r.store.generation_id
            op.run(':teacher use B1_DETAIL');op.run(':teacher on');op.run(':teacher compare');idle(r)
            teacher=r.store.one("SELECT * FROM messages WHERE event_id=? AND role='teacher' ORDER BY id DESC LIMIT 1",(eid,))
            report['stages']['reference']=dict(teacher) if teacher else None;save()
            if not teacher or teacher['status']!='FINAL':raise RuntimeError('Reference not FINAL')
            report['checks']['self_native']=json.loads(own['metadata'])['runner']['generated_tokens']>0
            report['checks']['reference_native']=json.loads(teacher['metadata'])['runner']['generated_tokens']>0
            report['checks']['reference_not_automatic_memory']=not r.store.rows('SELECT * FROM memories')
            report['checks']['self_first_immutable']=teacher['id']>own['id'] and digest(r.last_answer()['text'])==own_hash
            # A real, non-empty exact character span, selected by this test's operator.
            chosen=op.run(':choose teacher 0:'+str(min(160,len(teacher['text']))))
            selection=r.store.one('SELECT * FROM memories WHERE id=?',(chosen,));report['stages']['selection']=dict(selection);save()
            session=r.session;history=r.store.history(session);memories=r.store.rows('SELECT * FROM memories');dataset=r.memory.experience(eid,session)
            r.close();r=Runtime(h);op=Operator(r)
            report['checks']['selection_survives_restart']=r.session==session and r.store.one('SELECT * FROM memories WHERE id=?',(chosen,))==selection
            report['checks']['dataset_restart_identity']=r.memory.experience(eid,session)==dataset
            exported=json.loads(op.run(':export dataset'));lines=Path(exported['dataset']).read_text().splitlines();item=json.loads(lines[0])
            report['stages']['dataset_export']={'manifest':json.loads(Path(exported['manifest']).read_text()),'record':item}
            report['checks']['export_keeps_native_lanes']=item==dataset and bool(item['lanes']['self']) and bool(item['lanes']['reference']) and item['teacher_truth_authority'] is False
            op.run(':replay 1');idle(r)
            replay=json.loads((h/'exports/replay-last.json').read_text());report['stages']['replay']=replay;save()
            report['checks']['actual_replay_output']=replay['status']=='REPLAY_COMPLETE' and len(replay['rows'])==1 and bool(replay['rows'][0]['output'].strip()) and replay['rows'][0]['native_metrics']['generated_tokens']>0
            report['checks']['no_replay_fact_promotion']=r.store.rows('SELECT * FROM memories')==memories
            report['checks']['chat_unchanged_by_replay']=r.store.history(session)==history
            report['checks']['no_weight_updates']=r.store.generation_id==generation and not r.store.rows('SELECT * FROM updates')
            report['checks']['replay_completed_durable']=r.store.one('SELECT status FROM replay')['status']=='REPLAYED'
            report['checks']['integrity']=not r.store.integrity(True)
            report['status']='EXPERIENCE_REPLAY_PASS' if all(report['checks'].values()) else 'EXPERIENCE_REPLAY_PARTIAL'
        except Exception as exc:report.update(status='INTERRUPTED',error=type(exc).__name__+': '+str(exc))
        finally:
            if r:r.close()
            save()
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--installed-home',required=True);p.add_argument('--out',required=True);a=p.parse_args();r=run(a.installed_home,a.out)
    print(json.dumps({'status':r['status'],'checks':r['checks'],'error':r.get('error')}));sys.exit(0 if r['status']=='EXPERIENCE_REPLAY_PASS' else 2)
