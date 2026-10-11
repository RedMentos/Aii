"""Actual native C2 confidence and explicit route labels in an isolated brain."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.common import APP,atomic_write,dumps,file_hash
from v13.config import initialize,save_config
from v13.runtime import Runtime
from v13.cognition import scaffold_route
from v13.control_calibration_worker import observation
from v13.operator import Operator
from v13.resources import device

def consumer_policy(text,route,info,measured):
    """Evaluate every real attempt, including unavailable/expired native calls."""
    scaffold=scaffold_route(text);native=info.get('native_control')
    if native is None:
        abstention=bool(info.get('control_unavailable') or info.get('executive_control_abstention'))
        return {'policy_ok':route==scaffold and abstention and not info.get('calibrated') and measured is None,
                'native_proposal':None,'native_available':False,'native_abstained':abstention}
    proposal=observation(native)['route'];supported=bool(measured and measured['in_support'])
    accepted=bool(supported and measured['calibrated_confidence']>=.6)
    expected=proposal if scaffold=='simple' and accepted else scaffold
    return {'policy_ok':route==expected and bool(info.get('native_control_rejected'))==(not accepted) and bool(info.get('calibrated'))==supported,
            'native_proposal':proposal,'native_available':True,'native_abstained':not accepted}

def main():
    p=argparse.ArgumentParser();p.add_argument('--installed-home',required=True);p.add_argument('--out',required=True);a=p.parse_args();installed=Path(a.installed_home).resolve();out=Path(a.out)
    report={'status':'RUNNING','device':device(),'scope':'Native route confidence agreement with explicit fixture labels; not semantic truth confidence',
            'source_hashes':{str(f.relative_to(APP)):file_hash(f) for f in (APP/'v13').glob('*.py')},'checks':{},'corpus':[],'native_calls':[]}
    def save():atomic_write(out,json.dumps(report,ensure_ascii=False,indent=2))
    def instrument(r):
        original=r.needle.control
        def measured(text,cancel,deadline):
            start=time.monotonic();attempt={'phase':report.get('phase'),'actual_input':text,'status':'RUNNING','available_budget_s':max(0.,deadline-start)}
            report['native_calls'].append(attempt);save()
            try:
                result=original(text,cancel,deadline);attempt.update(status='FINAL',actual_control=result);return result
            except BaseException as exc:
                attempt.update(status='FAILED',error_type=type(exc).__name__,error=str(exc));raise
            finally:
                attempt.update(duration_s=time.monotonic()-start,native_metrics=dict(r.needle.last_metrics));save()
        r.needle.control=measured
    save()
    with tempfile.TemporaryDirectory(prefix='v13-calibration-') as folder:
        h=Path(folder);initialize(h)
        for name in ('models','bin'):shutil.rmtree(h/name);(h/name).symlink_to(installed/name,target_is_directory=True)
        shutil.copyfile(installed/'config/models.json',h/'config/models.json');r=Runtime(h);instrument(r)
        try:
            r.cfg.update(history_turns=0,observer_mode='off',answer_tokens=24);save_config(h,r.cfg);encoder_hash=file_hash(r.models.path_for('C2_CONTROL'))
            for i in range(32):
                for label,text in (('simple',f'Hallo, guten Tag! Heute ist Besuch Nummer {i+1}.'),('detail',f'Berechne die Hälfte von {100+i*20} Euro.'),
                                   ('gist',f'Fasse kurz zusammen: Gruppe {i+1} pflanzt Bäume, gießt Blumen und pflegt den Garten.'),
                                   ('both',f'Vergleiche Vor- und Nachteile von Bus und Bahn für Projekt {i+1}.')):
                    e=r.store.event(r.session,text);r.memory.feedback(e['event_id'],'route',label,'learn');report['corpus'].append({'input':text,'explicit_label':label,'source_sha256':e['source_ref']['sha256'],'event_id':e['event_id']})
            # Preserve all natural queries and their failed first proposals.
            # Additional explicit operator intent supplies genuine route coverage;
            # neither returned controls nor support thresholds are manufactured.
            for i in range(16):
                tasks=(('simple',f'Hallo Gast {i+1}.'),('detail',f'Berechne die Hälfte von {180+i*10} Euro.'),
                       ('gist',f'Fasse kurz zusammen: Gruppe {i+1} pflanzt Bäume.'),('both',f'Vergleiche Bus und Bahn für Reise {i+1}.'))
                for label,task in tasks:
                    for template in ('Verarbeite diese Anfrage mit Route {route}: {task}','Nutze {route} für diese Anfrage: {task}'):
                        text=template.format(route=label,task=task);e=r.store.event(r.session,text)
                        r.memory.feedback(e['event_id'],'route',label,'learn')
                        report['corpus'].append({'input':text,'explicit_label':label,'source_sha256':e['source_ref']['sha256'],'event_id':e['event_id'],'explicit_processing_intent':True})
            report['corpus_policy']='All 128 original natural requests plus 128 explicit processing-intent requests; no discarded first proposals'
            report['checks']['complete_corpus']=len(report['corpus'])==256
            save();base=r.store.generation_id;r.cfg['learning_mode']='SHADOW_UPDATE';report['phase']='INITIAL_FIT';r.learner.shadow_control_calibration()
            u=r.store.one('SELECT * FROM updates ORDER BY created DESC LIMIT 1');manifest=json.loads(u['manifest']);m=manifest['metrics'];report['update']={'status':u['status'],'manifest':manifest}
            report['checks'].update(actual_native_observations=len(manifest['native_observations'])==256 and len(report['native_calls'])==256,shadow_no_commit=r.store.generation_id==base,
                calibration_gain=m['calibration_pass'],retention=m['retention_pass'],gradient=m['gradient_check'],support=m['held_out_support_pass'],reload=m['checkpoint_reload'],repeat=m['deterministic_repeat']);save()
            if u['status']!='PENDING_APPROVAL':raise RuntimeError('Actual native calibration gate refused candidate; evidence retained')
            r.cfg['learning_mode']='APPROVED_COMMIT';Operator(r).run(':approve '+u['id']);session=r.session;r.close();r=Runtime(h);instrument(r);r.cfg['learning_mode']='APPROVED_COMMIT'
            report['checks']['restart']=r.session==session and r.learner.active('control_calibration') is not None;report['phase']='RUNTIME_CONSUMER'
            # Check the unchanged advisory policy on EVERY source-held-out query.
            # Support is route/confidence coverage, never a text-domain OOD claim.
            report['held_out_consumers']=[]
            for idx in m['partition']['test']:
                text=report['corpus'][idx]['input'];e=r.store.event(r.session,text)
                route,info=r._route(text,e,time.monotonic()+30)
                p=r.store.one("SELECT payload FROM packets WHERE kind='ControlCalibration' AND event_id=? ORDER BY created DESC LIMIT 1",(e['event_id'],))
                measured=json.loads(p['payload'])['prediction'] if p else None
                policy=consumer_policy(text,route,info,measured);proposal=policy['native_proposal']
                report['held_out_consumers'].append({'index':idx,'actual_input':text,'explicit_label':report['corpus'][idx]['explicit_label'],
                    'route':route,'info':info,'measured_calibration':measured,**policy,'native_proposal_agreed':None if proposal is None else proposal==report['corpus'][idx]['explicit_label']})
                save()
            rows=report['held_out_consumers'];report['checks']['consumer_source_held_out']=len(rows)==len(m['partition']['test'])
            report['checks']['actual_route_consumer']=all(x['policy_ok'] for x in rows)
            report['checks']['uncertain_native_abstains']=any(x['info'].get('native_control_rejected') and x['measured_calibration'] and x['measured_calibration']['in_support'] and x['measured_calibration']['calibrated_confidence']<.6 for x in rows)
            report['checks']['confident_native_route_accepted']=any(x['info'].get('source')=='NATIVE_C2_ADVISORY' and x['info'].get('calibrated') for x in rows)
            text=report['corpus'][0]['input'];e=r.store.event(r.session,text);r._turn(e);answer=r.last_answer();meta=json.loads(answer['metadata'])
            report['native_turn']={'status':answer['status'],'actual_output':answer['text'],'metadata':meta}
            report['checks']['actual_final_output']=answer['status']=='FINAL' and bool(answer['text'].strip()) and meta['model_generated']
            # Observe a novel query without presuming it lies outside confidence support.
            novel='Hallo, guten Morgen!';e=r.store.event(r.session,novel);fallback,info=r._route(novel,e,time.monotonic()+30)
            p=r.store.one("SELECT payload FROM packets WHERE kind='ControlCalibration' AND event_id=? ORDER BY created DESC LIMIT 1",(e['event_id'],));measured=json.loads(p['payload'])['prediction'] if p else None
            report['novel_consumer']={'actual_input':novel,'route':fallback,'info':info,'measured_calibration':measured,'text_domain_ood_claim':False}
            report['checks']['measured_novel_policy']=consumer_policy(novel,fallback,info,measured)['policy_ok']
            # Add new source groups so the bounded corpus displaces original rows.
            # Original held-out observations must still be evaluated unchanged.
            report['added_retention_sources']=[]
            for i in range(16):
                for label,task in (('simple',f'Hallo Gast {i+41}.'),('detail',f'Berechne die Hälfte von {340+i*10} Euro.'),('gist',f'Fasse kurz zusammen: Gruppe {i+41} pflanzt Bäume.'),('both',f'Vergleiche Bus und Bahn für Reise {i+41}.')):
                    text=f'Verarbeite diese Anfrage mit Route {label}: {task}';e=r.store.event(r.session,text);r.memory.feedback(e['event_id'],'route',label,'learn')
                    report['added_retention_sources'].append({'input':text,'explicit_label':label,'source_sha256':e['source_ref']['sha256']})
            path=r.learner.active('control_calibration');active_hash=file_hash(path);before=r.store.generation_id;report['phase']='ACTIVE_RETENTION';r.learner.shadow_control_calibration()
            ret=r.store.one('SELECT * FROM updates ORDER BY created DESC LIMIT 1');ret_m=json.loads(ret['manifest']);report['active_retention']={'status':ret['status'],'metrics':ret_m['metrics']}
            report['checks']['second_candidate_parent_unchanged']=r.store.generation_id==before and file_hash(path)==active_hash;report['checks']['active_retention_enforced']=ret_m['metrics']['retention_pass'] or ret['status']=='EVALUATED_FAIL'
            rm=ret_m['metrics'];report['checks']['fixed_old_cases_checked']=rm['retained_test']['n']==len(m['partition']['test']) and bool(rm['retained_test']['per_route'])
            report['checks']['changed_source_corpus']=len(report['added_retention_sources'])==64 and not set(m['source_groups'])<=set(rm['source_groups'])
            report['checks']['old_support_preserved']=rm['retained_support_preserved']
            r.store.rollback(u['id']);e=r.store.event(r.session,text);_,info=r._route(text,e,time.monotonic()+30);report['checks']['rollback_restores_baseline']=not info.get('calibrated') and r.learner.active('control_calibration') is None
            report['checks']['native_weights_unchanged']=file_hash(r.models.path_for('C2_CONTROL'))==encoder_hash;report['checks']['integrity']=not r.store.integrity(True)
            report['status']='CONTROL_CALIBRATION_PASS' if all(report['checks'].values()) else 'CONTROL_CALIBRATION_PARTIAL'
        except Exception as exc:
            report.update(status='CONTROL_CALIBRATION_PARTIAL',error=type(exc).__name__+': '+str(exc));report['worker_logs']=[f.read_text()[-4000:] for f in (h/'shadow').glob('*/worker.log')]
            report['partial_updates']=[{'id':u['id'],'status':u['status'],'manifest':json.loads(u['manifest'])} for u in r.store.rows('SELECT * FROM updates ORDER BY created')];save()
        finally:r.close();save()
    print(dumps({'status':report['status'],'checks':report['checks'],'error':report.get('error')}));return 0 if report['status']=='CONTROL_CALIBRATION_PASS' else 2

if __name__=='__main__':sys.exit(main())
