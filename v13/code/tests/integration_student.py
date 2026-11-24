"""Actual Needle A2 targets, learned A3 raw projection and JEF shadow consumer."""
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

def corpus():
    groups={
        'simple':['Guten Morgen '+str(i)+', wie geht es dir heute?' for i in range(16)],
        'detail':['Berechne die Hälfte von '+str(60+i*20)+' Euro.' for i in range(16)],
        'gist':['Gib eine Zusammenfassung: '+s+'.' for s in ['Pflanzen brauchen Wasser','Bäume brauchen Licht','Blumen brauchen Pflege','Gras braucht Feuchtigkeit','Sträucher benötigen Regen','Kräuter benötigen Sonne','Gärten brauchen Wasser','Wälder brauchen Regen','Rosen benötigen Pflege','Tulpen benötigen Licht','Kakteen brauchen Sonne','Gemüse braucht Wasser','Obstbäume brauchen Licht','Moos braucht Feuchtigkeit','Setzlinge benötigen Regen','Blätter benötigen Sonne']],
        'both':['Vergleiche die Vor- und Nachteile von '+s+'.' for s in ['Solarenergie und Windenergie','Bus und Bahn','Python und Java','Stadt und Land','Fahrrad und Auto','Holz und Stahl','Zug und Flugzeug','Sommer und Winter','Kaffee und Tee','Wald und Wiese','Berg und Meer','Hund und Katze','Buch und Film','Papier und Bildschirm','Garten und Balkon','Sonne und Regen']]}
    return [(label,groups[label][i]) for i in range(16) for label in groups]

def main():
    p=argparse.ArgumentParser();p.add_argument('--installed-home',required=True);p.add_argument('--out',required=True);a=p.parse_args();installed=Path(a.installed_home).resolve();out=Path(a.out)
    report={'status':'RUNNING','device':device(),'scope':'A3 text raw-byte projector + frozen Needle semantic target/reconstruction; T1 JEF shadow, no teacher removal or receiver injection',
            'authority':'Explicit fixture observation/route labels and individual test approvals; teacher features are not facts',
            'source_hashes':{str(f.relative_to(APP)):file_hash(f) for f in (APP/'v13').glob('*.py')},'checks':{}}
    def save():atomic_write(out,json.dumps(report,ensure_ascii=False,indent=2))
    save()
    with tempfile.TemporaryDirectory(prefix='v13-student-') as folder:
        h=Path(folder);initialize(h)
        for name in ('models','bin'):shutil.rmtree(h/name);(h/name).symlink_to(installed/name,target_is_directory=True)
        shutil.copyfile(installed/'config/models.json',h/'config/models.json');r=Runtime(h)
        try:
            encoder_hash=file_hash(r.models.path_for('C2_CONTROL'));r.cfg['learning_mode']='SHADOW_UPDATE';report['corpus']=corpus()
            for label,text in report['corpus']:
                e=r.store.event(r.session,text);r.memory.feedback(e['event_id'],'alignment','observe','learn');r.memory.feedback(e['event_id'],'route',label,'learn')
            base=r.store.generation_id;r.learner.shadow_student();u=r.store.one('SELECT * FROM updates ORDER BY created DESC LIMIT 1');manifest=json.loads(u['manifest']);metrics=manifest.get('metrics',{})
            report['student_update']={'status':u['status'],'manifest':manifest};report['checks']['shadow_no_commit']=r.store.generation_id==base
            report['checks'].update(actual_targets=len(manifest['target_packet_ids'])==64,gradient=metrics.get('gradient_check',False),noncollapse=metrics.get('noncollapse_pass',False),
                                   alignment_gain=metrics.get('alignment_gain',False),reconstruction_gain=metrics.get('reconstruction_gain',False),separate_ablations=metrics.get('separate_ablation_pass',False),
                                   partition=set(metrics.get('train_source_groups',[])).isdisjoint(metrics.get('held_out_source_groups',[])))
            save()
            if u['status']!='PENDING_APPROVAL':raise RuntimeError('A3 candidate failed gate; retained measured metrics')
            r.cfg['learning_mode']='APPROVED_COMMIT';Operator(r).run(':approve '+u['id']);student_hash=file_hash(r.learner.active('a3_student'))
            r.learner.shadow();route=r.store.one('SELECT * FROM updates ORDER BY created DESC LIMIT 1');report['route_update']={'status':route['status'],'manifest':json.loads(route['manifest'])};save()
            if route['status']!='PENDING_APPROVAL':raise RuntimeError('Native route head failed gate')
            Operator(r).run(':approve '+route['id']);report['checks']['route_preserves_student']=file_hash(r.learner.active('a3_student'))==student_hash
            session=r.session;r.close();r=Runtime(h);r.cfg.update(observer_mode='off',history_turns=0,answer_tokens=24,deadline_seconds=120);r.cfg['learning_mode']='APPROVED_COMMIT'
            report['checks']['restart']=r.session==session and set(r.store.components())=={'route','a3_student'}
            evals=[]
            for label,text in (('simple','Guten Morgen 12, wie geht es dir heute?'),('detail','Berechne die Hälfte von 300 Euro.'),('gist','Gib eine Zusammenfassung: Gärten brauchen Wasser.'),('both','Vergleiche die Vor- und Nachteile von Buch und Film.')):
                e=r.store.event(r.session,text);r._turn(e);answer=r.last_answer();meta=json.loads(answer['metadata']);evals.append({'input':text,'expected':label,'status':answer['status'],'actual_output':answer['text'],'route':meta['route']});save()
            report['actual_shadow_consumers']=evals
            shadow=[x['route'].get('student_shadow',{}) for x in evals]
            report['checks']['actual_jef_consumer']=all(x['status']=='FINAL' and x['actual_output'].strip() for x in evals) and all('packet_id' in s for s in shadow)
            report['checks']['no_routing_promotion']=all(s.get('routing_authority')==0 for s in shadow)
            report['checks']['local_route_agreement']=all(s.get('agreement') for s in shadow)
            # Genuine re-collection after restart, using the active checkpoint as
            # retention baseline; a failed candidate must leave it active.
            before=r.store.generation_id;r.learner.shadow_student();ret=r.store.one('SELECT * FROM updates ORDER BY created DESC LIMIT 1');report['retention_update']={'status':ret['status'],'manifest':json.loads(ret['manifest'])}
            report['checks']['retention_no_auto_commit']=r.store.generation_id==before and file_hash(r.learner.active('a3_student'))==student_hash
            measured=report['retention_update']['manifest']['metrics']
            within_limit=all(measured['after'][k]<=measured['before'][k]*(1+r.cfg['retention_max_delta']) for k in ('teacher_mse','reconstruction_mse'))
            report['retention_update']['gate_evidence']={'within_unchanged_limit':within_limit,'limit':r.cfg['retention_max_delta'],
                'relative_changes':{k:measured['after'][k]/measured['before'][k]-1 for k in ('teacher_mse','reconstruction_mse')}}
            report['checks']['retention_measured']=measured['retention_pass']==within_limit
            report['checks']['retention_gate_enforced']=within_limit or (ret['status']=='EVALUATED_FAIL' and not measured['commit_eligible'] and not report['retention_update']['manifest']['commit_eligible'])
            r.store.rollback(route['id']);r.store.rollback(u['id']);report['checks']['rollback_removes_student']=r.learner.student_percept('Berechne die Hälfte von 300 Euro.') is None
            report['checks']['encoder_unchanged']=file_hash(r.models.path_for('C2_CONTROL'))==encoder_hash;report['checks']['integrity']=not r.store.integrity(True)
            report['status']='STUDENT_LIFECYCLE_PASS' if all(report['checks'].values()) else 'STUDENT_LIFECYCLE_PARTIAL'
        except Exception as exc:
            report.update(status='STUDENT_LIFECYCLE_PARTIAL',error=type(exc).__name__+': '+str(exc));report['worker_logs']=[f.read_text()[-4000:] for f in (h/'shadow').glob('*/worker.log')]
        finally:r.close();save()
    print(dumps({'status':report['status'],'checks':report['checks'],'error':report.get('error')}));return 0 if report['status']=='STUDENT_LIFECYCLE_PASS' else 2

if __name__=='__main__':sys.exit(main())
