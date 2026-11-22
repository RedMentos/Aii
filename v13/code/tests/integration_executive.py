"""Actual no-B C1/C2/C3 continuation; no semantic task completion claim."""
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
from v13.operator import Operator
from v13.resources import device
from v13.proofs import archive_previous,audit_event

def run(installed,out):
    installed=Path(installed).resolve();out=Path(out).resolve();archive_previous(out)
    report={'schema':'V13_EXPLICIT_EXECUTIVE_PROOF_V1','status':'RUNNING','device':device(),'phone_measured':device()['android'],'checks':{},'turns':[],
        'source_hashes':{str(p.relative_to(APP)):file_hash(p) for p in list((APP/'v13').glob('*.py'))+[Path(__file__).resolve()]},
        'claim_limits':['Actual unchanged native C2 query and actual C3 output, no B manifest in this test home.',
                        'Explicit structured task continuity and exact provenance; no native KV persistence or learned executive body.',
                        'Native wording is recorded; fluent answers do not prove task completion or truthful self reports.',
                        'Fixture task is explicitly authored by the test operator. No Android sustained or energy proof inferred from Linux.']}
    def save():atomic_write(out,json.dumps(report,ensure_ascii=False,indent=2))
    save();r=None
    with tempfile.TemporaryDirectory(prefix='v13-executive-') as folder:
        home=Path(folder);cfg=initialize(home);cfg.update(observer_mode='off',route_override='auto',history_turns=0,answer_tokens=64);save_config(home,cfg)
        for name in ('models','bin'):shutil.rmtree(home/name);(home/name).symlink_to(installed/name,target_is_directory=True)
        shutil.copyfile(installed/'config/models.json',home/'config/models.json')
        try:
            r=Runtime(home);op=Operator(r);r.models.installed.pop('body',None);r.models.installed.pop('gist',None);r.models.save()
            report['model_revisions']=r.revisions();hashes={role:file_hash(r.models.path_for(role)) for role in ('C3_LANGUAGE','C2_CONTROL')}
            def ask(name,text):
                eid=r.submit(text);end=time.monotonic()+r.cfg['deadline_seconds']+20
                while not r.idle():
                    if time.monotonic()>end:r.cancel();raise TimeoutError('Executive native turn deadline')
                    time.sleep(.025)
                audit=audit_event(r.store,eid);report['turns'].append({'name':name,'audit':audit});save();return audit
            first=ask('actual_native_control_and_report','Hallo. Wie kann ich dir eine Frage stellen?')
            route=first['output_metadata']['route'];context=json.loads(r.store.one("SELECT payload FROM packets WHERE event_id=? AND kind='ExecutiveControlContext'",(first['event_id'],))['payload'])
            report['control_context']=context
            report['checks']['actual_native_control']=bool(route.get('native_control')) and route.get('executive_control_policy')=='LOCAL_PROCESSING_ONLY' and context['compact_view']['raw_query']=='Hallo. Wie kann ich dir eine Frage stellen?'
            report['checks']['first_actual_c3']=all(first['checks'].values()) and first['output_metadata'].get('runner',{}).get('role')=='C3_LANGUAGE'
            task=json.loads(op.run(':task set Prüfe das Budget von Projekt Aurora.'));task_ref=task['active_task']['source_ref'];report['operator_task']=task['active_task'];save()
            r.cfg['route_override']='simple';save_config(home,r.cfg)
            second=ask('structured_task_and_native_report','Welche Aufgabe steht im expliziten Kontext? Antworte kurz.')
            view=r.executive.view(r.session);report['executive_after_report']=view;refs=second['output_metadata'].get('context_source_refs',[])
            report['checks']['second_actual_c3']=all(second['checks'].values()) and second['output_metadata'].get('runner',{}).get('role')=='C3_LANGUAGE'
            report['checks']['task_source_consumed_in_native_context']=task_ref in refs and view['active_task']['exact_task']=='Prüfe das Budget von Projekt Aurora.'
            report['checks']['semantic_completion_not_inferred']=view['active_task']['status']=='REPORTED_UNCONFIRMED' and view['uncertainty']['semantic_confidence'] is None
            report['checks']['actual_action_and_corollary_bound']=view['current_action_intent']['corollary_packet_id'] in {x['packet_id'] for x in [json.loads(p['payload']) for p in r.store.rows("SELECT payload FROM packets WHERE kind='CorollaryCopy' AND event_id=?",(second['event_id'],))]}
            report['checks']['body_not_required']=not {'body','gist'}&set(r.models.installed) and not r.store.rows("SELECT id FROM packets WHERE kind='OfferPacket'")
            session=r.session;state=r.store.state('C1_EXEC:'+session);r.close();r=Runtime(home);op=Operator(r)
            report['checks']['restart_state_exact']=r.session==session and r.store.state('C1_EXEC:'+session)==state
            forced=op.run(':force-report');report['forced_idle_report']=forced;report['checks']['forced_best_actual_output']=second['output'] in forced and 'CURRENT_OUTPUT_SNAPSHOT' in forced
            report['checks']['no_weight_updates']=not r.store.rows('SELECT id FROM updates') and all(file_hash(r.models.path_for(role))==h for role,h in hashes.items())
            report['checks']['integrity']=not r.store.integrity(True)
            report['status']='EXECUTIVE_CONTINUITY_PASS' if all(report['checks'].values()) else 'EXECUTIVE_CONTINUITY_PARTIAL';save()
        except Exception as exc:report.update(status='EXECUTIVE_CONTINUITY_PARTIAL',error=type(exc).__name__+': '+str(exc));save()
        finally:
            if r:r.close()
    print(dumps({'status':report['status'],'checks':report['checks'],'error':report.get('error')}));return 0 if report['status']=='EXECUTIVE_CONTINUITY_PASS' else 2

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--installed-home',required=True);parser.add_argument('--out',required=True);a=parser.parse_args();sys.exit(run(a.installed_home,a.out))
