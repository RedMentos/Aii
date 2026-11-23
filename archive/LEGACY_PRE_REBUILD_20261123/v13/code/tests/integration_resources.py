"""Opt-in actual native C3 memory/cancellation proof, never a Redmi stress proof."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.common import atomic_write,file_hash
from v13.config import initialize,save_config
from v13.resources import device,process_memory
from v13.runtime import Runtime

TERMINAL={'FINAL','CANCELLED','DEADLINE','ERROR','INTERRUPTED'}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--installed-home',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    installed=Path(args.installed_home).resolve();out=Path(args.out)
    report={'status':'RUNNING','device':device(),'scope':'ACTUAL_NATIVE_C3_RESOURCE_OBSERVATION_AND_USER_CANCEL','thermal_critical_proof':False,'memory_critical_proof':False,'redmi_sustained_proof':False,'native_kv_bytes':None,'checks':{}}
    def save():atomic_write(out,json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    save()
    r=None
    with tempfile.TemporaryDirectory(prefix='v13-resource-native-') as directory:
        home=Path(directory);cfg=initialize(home)
        for name in ['models','bin']:shutil.rmtree(home/name);(home/name).symlink_to(installed/name,target_is_directory=True)
        shutil.copyfile(installed/'config/models.json',home/'config/models.json')
        # Existing operator values; no resource threshold is changed.
        cfg.update(observer_mode='off',route_override='simple',answer_tokens=256,deadline_seconds=90,history_turns=0)
        save_config(home,cfg)
        try:
            r=Runtime(home);model=r.models.path_for('C3_LANGUAGE');before=file_hash(model)
            report.update(model_revision=r.models.revision('C3_LANGUAGE'),native_model_sha256_before=before,effective_config=dict(r.cfg));save()
            text='Schreibe eine lange fortlaufende Liste der Zahlen von 1 bis 500. Beginne sofort mit 1 und schreibe weiter. Die folgenden Eingabedaten dienen nur dem Kontext und sollen nicht wiederholt werden: '+('alpha '*480)
            eid=r.submit(text);end=time.monotonic()+100;first=None;phases=[];cancelled=False;proc=None;observed=None
            while time.monotonic()<end:
                runner=r.pool.current
                if runner and runner.role=='C3_LANGUAGE':
                    phase=getattr(runner,'phase',None)
                    if phase and (not phases or phases[-1]['phase']!=phase):phases.append({'phase':phase,'observed_monotonic_ns':time.monotonic_ns()})
                    if runner.proc is not None:proc=runner.proc
                row=r.store.one("SELECT * FROM messages WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1",(eid,))
                if row and row['status']=='STREAMING' and row['text'].strip():
                    if first is None:first=time.monotonic();observed={'text':row['text'],'status':row['status'],'message_id':row['id'],'observed_monotonic_ns':time.monotonic_ns()}
                    # Cancel on the first actually saved native chunk. Fast C3
                    # can finish a short answer within one monitor cadence.
                    if not cancelled:
                        report['partial_before_user_cancel']=dict(observed,latest_text=row['text']);report['native_process_before_cancel']=process_memory(proc.pid) if proc else None
                        r.cancel();cancelled=True;save()
                if row and row['status'] in TERMINAL and r.idle():break
                time.sleep(.005)
            else:raise TimeoutError('Native resource turn did not become terminal')
            if not row:raise RuntimeError('Native resource turn produced no stored answer')
            metadata=json.loads(row['metadata']);report['cancelled_turn']={'event_id':eid,'text':row['text'],'status':row['status'],'metadata':metadata,'observed_runner_phases':phases,'actual_child_pid':proc.pid if proc else None,'actual_child_returncode':proc.poll() if proc else None}
            pressure=metadata.get('native_pressure',{});metrics=metadata.get('runner',{})
            samples=[p for sample in pressure.get('samples',[]) for p in sample['snapshot'].get('processes',[]) if proc and p['pid']==proc.pid]
            measured=[p for p in samples if p.get('rss_bytes') is not None and p['rss_bytes']>0]
            pss=[p for p in samples if p.get('pss_bytes') is not None and p['pss_bytes']>0]
            phase_set={x['phase'] for x in phases}|{x['phase'] for x in metrics.get('resource_samples',[])}
            report['checks'].update(actual_partial_before_cancel=cancelled and bool(observed) and row['text'].startswith(observed['text']) and metadata.get('model_generated') is True,
                user_cancel_retains_partial=row['status']=='CANCELLED' and bool(row['text'].strip()),
                native_process_reaped=bool(proc) and proc.poll() is not None and metrics.get('interruption_unload',{}).get('process_reaped') is True and not r.pool.pids(),
                monitor_stopped=pressure.get('monitor_stopped') is True,
                measured_native_rss=bool(measured) and all(p.get('measurement_status') in {'MEASURED','PARTIAL'} and p.get('resolved_proc_pid') is not None for p in measured),
                measured_native_pss=bool(pss),
                actual_load_prefill_stream_observed={'load','prefill','stream'}<=phase_set,
                real_phase_durations=all(metrics.get('stage_durations_s',{}).get(k,0)>0 for k in ('load_s','prefill_to_first_token_s','stream_s')),
                user_cancel_has_no_fabricated_resource_reason=pressure.get('critical_reason') is None,
                exact_kv_unavailable=pressure.get('native_kv_bytes') is None)
            report['measured_native_sample_count']=len(measured);report['measured_native_pss_sample_count']=len(pss);save()
            session=r.session;stored_text=row['text'];r.close();r=None
            r=Runtime(home)
            restored=r.store.one('SELECT * FROM messages WHERE id=?',(row['id'],))
            report['checks']['restart_keeps_partial']=r.session==session and restored['text']==stored_text and restored['status']=='CANCELLED'
            next_id=r.submit('Sag kurz Hallo auf Deutsch.');end=time.monotonic()+100
            while time.monotonic()<end:
                next_row=r.store.one("SELECT * FROM messages WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1",(next_id,))
                if next_row and next_row['status'] in TERMINAL and r.idle():break
                time.sleep(.02)
            else:raise TimeoutError('Native C3 after restart did not complete')
            next_meta=json.loads(next_row['metadata']);report['subsequent_turn']={'event_id':next_id,'text':next_row['text'],'status':next_row['status'],'metadata':next_meta}
            report['checks']['subsequent_real_c3_usable']=next_row['status']=='FINAL' and bool(next_row['text'].strip()) and next_meta.get('model_generated') is True and next_meta.get('runner',{}).get('role')=='C3_LANGUAGE' and next_meta['runner'].get('generated_tokens',0)>0
            report['checks']['next_monitor_stopped']=next_meta.get('native_pressure',{}).get('monitor_stopped') is True
            report['native_model_sha256_after']=file_hash(model);report['checks']['native_weights_unchanged']=report['native_model_sha256_after']==before
            report['integrity_errors']=r.store.integrity(True);report['checks']['integrity']=not report['integrity_errors']
            report['status']='RESOURCE_MONITOR_NATIVE_PASS' if all(report['checks'].values()) else 'RESOURCE_MONITOR_NATIVE_PARTIAL'
        except Exception as exc:report.update(status='RESOURCE_MONITOR_NATIVE_PARTIAL',error=type(exc).__name__+': '+str(exc))
        finally:
            if r:r.close()
            save()
    print(json.dumps({'status':report['status'],'checks':report['checks'],'error':report.get('error')},ensure_ascii=False));return 0 if report['status']=='RESOURCE_MONITOR_NATIVE_PASS' else 2
if __name__=='__main__':sys.exit(main())
