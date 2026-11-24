"""Opt-in native-embedding training proof; uses an isolated disposable brain."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.common import atomic_write,dumps
from v13.operator import Operator
from v13.config import initialize
from v13.runtime import Runtime
from v13.resources import device

def main():
    p=argparse.ArgumentParser();p.add_argument('--installed-home',required=True);p.add_argument('--out',required=True);a=p.parse_args();installed=Path(a.installed_home).resolve();report={'device':device(),'embeddings':'actual pinned Needle native API; no random vectors','purpose':'external route head only'}
    samples={'simple':['Guten Morgen, wie geht es dir?','Guten Abend, wie geht es dir?','Guten Tag, wie geht es dir?','Gute Nacht, wie geht es dir?'], 'detail':['Wie viel ist die Hälfte von 120 Euro?','Wie viel ist die Hälfte von 140 Euro?','Wie viel ist die Hälfte von 180 Euro?','Wie viel ist die Hälfte von 200 Euro?'], 'gist':['Was ist die Kernaussage: Pflanzen benötigen Wasser.','Was ist die Kernaussage: Bäume benötigen Licht.','Was ist die Kernaussage: Blumen benötigen Pflege.','Was ist die Kernaussage: Gras benötigt Feuchtigkeit.'], 'both':['Welche Vor- und Nachteile haben Solarenergie und Windenergie?','Welche Vor- und Nachteile haben Bus und Bahn?','Welche Vor- und Nachteile haben Python und Java?','Welche Vor- und Nachteile haben Stadt und Land?']}
    with tempfile.TemporaryDirectory(prefix='v13-learning-') as d:
        h=Path(d);initialize(h)
        for name in ['models','bin']:shutil.rmtree(h/name);(h/name).symlink_to(installed/name,target_is_directory=True)
        shutil.copyfile(installed/'config/models.json',h/'config/models.json');r=Runtime(h)
        try:
            for route,questions in samples.items():
                for text in questions:
                    e=r.store.event(r.session,text);r.memory.feedback(e['event_id'],'route',route,permission='learn')
            before=r.store.generation_id;r.cfg['learning_mode']='SHADOW_UPDATE';report['result']=r.learner.shadow();report['active_unchanged_after_shadow']=r.store.generation_id==before
            u=r.store.one('SELECT * FROM updates ORDER BY created DESC LIMIT 1');report['manifest']=json.loads(u['manifest']);report['status']=u['status'];report['actual_candidate_bytes']=(h/u['path']).stat().st_size
            if u['status']=='PENDING_APPROVAL':
                r.cfg['learning_mode']='APPROVED_COMMIT';Operator(r).run(':approve '+u['id']);report['generation_changed_after_explicit_test_approval']=r.store.generation_id!=before
                session=r.session;r.close();r=Runtime(h)
                report['restart_same_session']=r.session==session;report['active_head_after_restart']=r.learner.active() is not None
                routes=[]
                for expected,questions in samples.items():
                    e=r.store.event(r.session,questions[-1]);actual,trace=r._route(questions[-1],e,time.monotonic()+15)
                    routes.append({'expected':expected,'actual':actual,'source':trace['source'],'matches':expected==actual,'learned_head_consumed':trace['source']=='APPROVED_EXTERNAL_HEAD'})
                report['actual_routes_after_restart']=routes
                # F7 observes actual optimizer/retention outcomes. A second
                # explicit shadow job must consume the persisted reduced budget
                # without changing the active generation or the operator cfg.
                policy=json.loads(Operator(r).run(':plasticity route'))['components']['route']
                report['plasticity_after_restart']=policy;cfg_before=dict(r.cfg);parent=r.store.generation_id
                r.store.db.execute("CREATE TRIGGER f7_crash_fixture BEFORE INSERT ON packets WHEN NEW.kind='PlasticityState' BEGIN SELECT RAISE(ABORT,'simulated F7 publication crash'); END")
                r.cfg['learning_mode']='SHADOW_UPDATE';report['second_shadow_result']=r.learner.shadow()
                second=r.store.one('SELECT * FROM updates ORDER BY created DESC LIMIT 1');second_manifest=json.loads(second['manifest'])
                report['second_candidate_status_after_f7_crash']=second['status'];r.store.db.execute('DROP TRIGGER f7_crash_fixture')
                r.learner.plasticity.reconcile()
                report['second_shadow_manifest']=second_manifest;r.cfg['learning_mode']=cfg_before['learning_mode']
                report['plasticity_checks']={'measured_first_trial':policy['trials']==1 and .5<=policy['plasticity_gain']<1.,
                    'restart_keeps_budget':second_manifest['training_policy']['plasticity_gain']==policy['plasticity_gain'],
                    'worker_uses_budget':second_manifest['training_policy']['effective_learning_rate']<r.cfg['learning_rate'] and second_manifest['metrics']['effective_learning_rate']==second_manifest['training_policy']['effective_learning_rate'] and second_manifest['metrics']['effective_max_update_norm']==second_manifest['training_policy']['effective_max_update_norm'] and second_manifest['metrics']['max_applied_step_norm']<=second_manifest['training_policy']['effective_max_update_norm']+1e-12 and second_manifest['metrics']['optimizer_steps']==r.cfg['learning_steps'],
                    'second_shadow_no_commit':r.store.generation_id==parent,'operator_config_unchanged':r.cfg==cfg_before,
                    'finished_candidate_survives_f7_crash':second['status'] in {'PENDING_APPROVAL','EVALUATED_FAIL'},
                    'typed_trial_and_budget':len(r.store.rows("SELECT * FROM packets WHERE kind='PlasticityState'"))==2 and len(r.store.rows("SELECT * FROM packets WHERE kind='PlasticityBudget'"))==2}
                # Rollback uses immutable parent weights and preserves current rules.
                r.store.rollback(u['id']);report['rollback_removed_head']=not r.store.generation()['hashes']
            else:report['activation']='blocked by evaluation gate as required'
            report['integrity_errors']=r.store.integrity(True)
            report['checks']={'shadow_does_not_commit':report['active_unchanged_after_shadow'],'candidate_has_changed_weights':report['manifest']['metrics']['loss_after']<report['manifest']['metrics']['loss_before'],'train_gradient':report['manifest']['metrics']['gradient_check'],'explicit_activation':report.get('generation_changed_after_explicit_test_approval',False),'restart_uses_head':report.get('active_head_after_restart',False),'actual_learned_route_use':bool(report.get('actual_routes_after_restart')) and all(x['matches'] and x['learned_head_consumed'] for x in report['actual_routes_after_restart']),'rollback':report.get('rollback_removed_head',False),'integrity':not report['integrity_errors']}
            report['checks'].update({'f7_'+k:v for k,v in report.get('plasticity_checks',{'measured_first_trial':False}).items()})
            report['proof_status']='LEARNING_LIFECYCLE_PASS' if all(report['checks'].values()) else 'LEARNING_LIFECYCLE_PARTIAL'
        except Exception as exc:
            report.update(proof_status='LEARNING_INTERRUPTED',error=type(exc).__name__+': '+str(exc))
            report['worker_logs']=[p.read_text()[-4000:] for p in (h/'shadow').glob('*/worker.log')]
        finally:
            r.close();atomic_write(Path(a.out),json.dumps(report,ensure_ascii=False,indent=2))
    atomic_write(Path(a.out),json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({'proof_status':report['proof_status'],'checks':report.get('checks'), 'error':report.get('error')},ensure_ascii=False));return 0 if report['proof_status']=='LEARNING_LIFECYCLE_PASS' else 2
if __name__=='__main__':sys.exit(main())
