"""Real local copy and native C3 actions; isolated World learning/consumer proof."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.common import APP,atomic_write,dumps,digest,file_hash
from v13.config import initialize,save_config
from v13.runtime import Runtime
from v13.operator import Operator
from v13.resources import device

def execute(r,text,role):
    e=r.store.event(r.session,text);forecast=r.world.forecast(e,role,time.monotonic()+60);aid=r.store.start_action(e['event_id'],e['brain_generation_id'],forecast=forecast);start=time.monotonic()
    output=text if role=='SOURCE_COPY' else ''.join(r.pool.get('C3_LANGUAGE').generate([{'role':'system','content':'Antworte nur mit der Hälfte des genannten Budgets, kurz auf Deutsch.'},{'role':'user','content':text}],r.cancel_event,time.monotonic()+60,24))
    if not output.strip():raise RuntimeError('Native fixture action produced no output')
    mid=r.store.message(r.session,e['event_id'],'assistant');r.store.append_message(mid,output);r.store.finish_message(mid,'FINAL',{'model_generated':role!='SOURCE_COPY'})
    r.store.finish_action(aid,'FINAL',{'role':role,'self_candidate_hash':digest(output),'action_duration_s':time.monotonic()-start,'model_generated':role!='SOURCE_COPY'})
    observation=r.world.observe(aid);r.pool.unload();return e,{'role':role,'input':text,'actual_output':output,'forecast':forecast,'observation':observation}

def main():
    p=argparse.ArgumentParser();p.add_argument('--installed-home',required=True);p.add_argument('--out',required=True);a=p.parse_args();installed=Path(a.installed_home).resolve();out=Path(a.out)
    report={'status':'RUNNING','device':device(),'scope':'digital raw-state/action-role -> actual committed own output latent; source-copy/native-C3 counterfactual fixture, not external-world truth',
            'source_hashes':{str(f.relative_to(APP)):file_hash(f) for f in (APP/'v13').glob('*.py')},'checks':{},'actions':[]}
    def save():atomic_write(out,json.dumps(report,ensure_ascii=False,indent=2))
    save()
    with tempfile.TemporaryDirectory(prefix='v13-world-') as folder:
        h=Path(folder);initialize(h)
        for name in ('models','bin'):shutil.rmtree(h/name);(h/name).symlink_to(installed/name,target_is_directory=True)
        shutil.copyfile(installed/'config/models.json',h/'config/models.json');r=Runtime(h)
        try:
            r.cfg.update(history_turns=0,answer_tokens=24,observer_mode='off');save_config(h,r.cfg)
            hashes={role:file_hash(r.models.path_for(role)) for role in ('C2_CONTROL','C3_LANGUAGE')}
            for i in range(24):
                text=f'Projekt {("Atlas","Aurora","Birke","Cedar","Delta","Eiche")[i%6]} hat ein Budget von {100+i*20} Euro. Wie hoch ist die Hälfte?'
                for role in ('SOURCE_COPY','C3_LANGUAGE'):
                    e,row=execute(r,text,role);r.memory.feedback(e['event_id'],'world','observe','learn');report['actions'].append(row);save()
            base=r.store.generation_id;r.cfg['learning_mode']='SHADOW_UPDATE';r.learner.shadow_world();u=r.store.one('SELECT * FROM updates ORDER BY created DESC LIMIT 1');manifest=json.loads(u['manifest']);metrics=manifest.get('metrics',{})
            report['update']={'status':u['status'],'manifest':manifest};report['checks'].update(actual_transitions=len(manifest['transition_packet_ids'])==48,shadow_no_commit=r.store.generation_id==base,
                gradient=metrics.get('gradient_check',False),noncollapse=metrics.get('noncollapse_pass',False),prediction_ablation=metrics.get('predictive_ablation_pass',False),action_ablation=metrics.get('action_ablation_pass',False),target_ema=metrics.get('target_changed',False),retention=metrics.get('retention_pass',False));save()
            if u['status']!='PENDING_APPROVAL':raise RuntimeError('World candidate failed held-out/action gate; measured failure retained')
            r.cfg['learning_mode']='APPROVED_COMMIT';Operator(r).run(':approve '+u['id']);session=r.session;r.close();r=Runtime(h);r.cfg['learning_mode']='APPROVED_COMMIT'
            report['checks']['restart']=r.session==session and r.learner.active('world_predictor') is not None
            report['checks']['held_out_measured_support']=metrics['held_out_support_pass'] and all(v['in_support'] for v in metrics['held_out_support'])
            e=r.store.event(r.session,'Projekt Atlas hat ein Budget von 660 Euro. Wie hoch ist die Hälfte?')
            report['checks']['untrained_action_refused']=r.learner.world_predict(e,'B1_DETAIL',time.monotonic()+20) is None
            report['novel_state_support']=[]
            for text in ('The mitochondrion synthesizes ATP through oxidative phosphorylation in the inner membrane.','昨日、庭の桜の花が咲き、鳥が静かに歌っていました。','Une sonate pour violoncelle accompagne la danse des nuages au-dessus de la mer.'):
                e=r.store.event(r.session,text);forecast=r.learner.world_predict(e,'C3_LANGUAGE',time.monotonic()+20)
                measured=r.store.one("SELECT metrics FROM telemetry WHERE kind='world_coverage' AND event_id=? ORDER BY id DESC LIMIT 1",(e['event_id'],))
                report['novel_state_support'].append({'actual_input':text,'forecast_admitted':forecast is not None,'measured_support':json.loads(measured['metrics']) if measured else None});save()
            report['checks']['measured_novelty_refusal']=any(not v['forecast_admitted'] and v['measured_support'] and v['measured_support']['in_support'] is False for v in report['novel_state_support'])
            consumers=[]
            for role in ('SOURCE_COPY','C3_LANGUAGE'):
                e,row=execute(r,'Projekt Atlas hat ein Budget von 660 Euro. Wie hoch ist die Hälfte?',role);consumers.append(row)
            report['consumers']=consumers
            report['checks']['actual_forecast_consumer']=all(len(row['forecast'].get('learned_latent_prediction',{}).get('future_latent_prediction',[]))==16 for row in consumers)
            report['checks']['spread_is_measured_not_confidence']=all(len(row['forecast']['learned_latent_prediction']['residual_spread_latent'])==16 and row['forecast']['learned_latent_prediction']['coverage']['confidence_calibrated'] is False for row in consumers)
            report['checks']['observed_prediction_error']=all(isinstance(row['observation'].get('digital_latent_error'),float) for row in consumers)
            report['checks']['no_semantic_truth_promotion']=all(row['observation']['semantic_success'] is None and row['observation']['external_world_observation'] is False for row in consumers)
            # Exercise the existing complete vertical path, rather than relying
            # only on the explicit fixture executor above.
            r.cfg['route_override']='simple';e=r.store.event(r.session,'Projekt Atlas hat ein Budget von 680 Euro. Wie hoch ist die Hälfte?');r._turn(e);answer=r.last_answer()
            action=r.store.one('SELECT * FROM actions WHERE event_id=?',(e['event_id'],));observed=r.store.one("SELECT payload FROM packets WHERE kind='PredictionOutcome' AND event_id=?",(e['event_id'],))
            report['native_vertical_consumer']={'status':answer['status'],'actual_output':answer['text'],'action':action,'observation':json.loads(observed['payload']) if observed else None}
            report['checks']['native_vertical_consumer']=answer['status']=='FINAL' and bool(json.loads(action['expected'])['forecast'].get('learned_latent_prediction')) and isinstance(report['native_vertical_consumer']['observation']['observation'].get('digital_latent_error'),float)
            active_hash=file_hash(r.learner.active('world_predictor'));before=r.store.generation_id;r.learner.shadow_world();ret=r.store.one('SELECT * FROM updates ORDER BY created DESC LIMIT 1');ret_m=json.loads(ret['manifest'])
            report['active_retention_update']={'status':ret['status'],'manifest':ret_m}
            report['checks']['active_retention_gate']=ret['status'] in ('PENDING_APPROVAL','EVALUATED_FAIL') and isinstance(ret_m['metrics']['fixed_target_retention_mse'],float) and (ret_m['metrics']['retention_pass'] or ret['status']=='EVALUATED_FAIL')
            report['checks']['active_candidate_does_not_replace_parent']=r.store.generation_id==before and file_hash(r.learner.active('world_predictor'))==active_hash
            r.store.rollback(u['id']);e=r.store.event(r.session,'Projekt Atlas Budget 660 Euro.');report['checks']['rollback_removes_consumer']=r.learner.world_predict(e,'C3_LANGUAGE') is None
            report['checks']['native_weights_unchanged']=all(file_hash(r.models.path_for(role))==value for role,value in hashes.items());report['checks']['integrity']=not r.store.integrity(True)
            report['status']='WORLD_LIFECYCLE_PASS' if all(report['checks'].values()) else 'WORLD_LIFECYCLE_PARTIAL'
        except Exception as exc:
            report.update(status='WORLD_LIFECYCLE_PARTIAL',error=type(exc).__name__+': '+str(exc));report['worker_logs']=[f.read_text()[-4000:] for f in (h/'shadow').glob('*/worker.log')]
        finally:r.close();save()
    print(dumps({'status':report['status'],'checks':report['checks'],'error':report.get('error')}));return 0 if report['status']=='WORLD_LIFECYCLE_PASS' else 2

if __name__=='__main__':sys.exit(main())
