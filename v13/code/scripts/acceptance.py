#!/usr/bin/env python3
"""Actual-weight path tests with one durable result directory per invocation."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.common import APP,atomic_write,file_hash
from v13.resources import device
from verify_acceptance import harness_hashes
from acceptance_checkpoint import VERSION, installed_identity, acquire_lock, validate_resume, preserve_interrupted, process_identity

def main():
    p=argparse.ArgumentParser();p.add_argument('--installed-home',required=True);p.add_argument('--quick',action='store_true');p.add_argument('--compare-c3',action='store_true');p.add_argument('--archive-dir',help='Mirror completed stage reports/logs for incremental source checkpoints');p.add_argument('--resume',help='Continue one exact existing acceptance result directory');p.add_argument('--stage-limit',type=int,help='Stop after this many total stages, retaining the complete required stage plan');a=p.parse_args()
    home=Path(a.installed_home).expanduser().resolve();stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out=Path(a.resume).expanduser().resolve() if a.resume else home/'exports'/('acceptance-'+stamp)
    if not a.resume:out.mkdir(parents=True,exist_ok=False)
    if not out.is_dir():p.error('Resume directory missing')
    collector_lock=acquire_lock(out)
    report={'status':'RUNNING','device':device(),'stages':[],'canonical_architecture_complete':False,'source_hashes':{str(f.relative_to(APP)):file_hash(f) for f in (APP/'v13').glob('*.py')},'harness_hashes':harness_hashes(APP),'user_brain_training':False}
    archive=Path(a.archive_dir).expanduser().resolve() if a.archive_dir else None
    if archive:
        if archive==out or archive.is_relative_to(out) or out.is_relative_to(archive):p.error('Archive and live directory must be separate')
        if a.resume:
            if not archive.is_dir():p.error('Existing resume archive required')
        else:archive.mkdir(parents=True,exist_ok=False)
    def save():
        text=json.dumps(report,ensure_ascii=False,indent=2);atomic_write(out/'acceptance.json',text)
        if archive:
            # Preserve every completed proof and its actual feature companion
            # before exposing the matching index. Never replace an old run.
            for f in out.iterdir():
                if f.name!='acceptance.json' and f.is_file():shutil.copyfile(f,archive/f.name)
            if (out/'interrupted-attempts').exists():shutil.copytree(out/'interrupted-attempts',archive/'interrupted-attempts',dirs_exist_ok=True)
            atomic_write(archive/'acceptance.json',text)
    stages=[('jef-modes',None,'JEF_MODES_PASS'),('experience','tests/integration_experience.py','EXPERIENCE_REPLAY_PASS'),('learning','tests/integration_learning.py','LEARNING_LIFECYCLE_PASS')]
    stages += [('executive','tests/integration_executive.py','EXECUTIVE_CONTINUITY_PASS'),('resources','tests/integration_resources.py','RESOURCE_MONITOR_NATIVE_PASS')]
    stages += [('readouts','tests/integration_readouts.py','READOUT_LIFECYCLE_PASS'),('native-taps','tests/integration_taps.py','NATIVE_TAP_PASS'),('predictor-b1','tests/integration_predictor.py','PREDICTOR_LIFECYCLE_PASS'),('predictor-b2','tests/integration_predictor.py','PREDICTOR_LIFECYCLE_PASS')]
    stages += [('control-calibration','tests/integration_control_calibration.py','CONTROL_CALIBRATION_PASS')]
    stages += [('memory-retrieval','tests/integration_retrieval.py','MEMORY_RETRIEVAL_PASS')]
    stages += [('consolidation','tests/integration_consolidation.py','CONSOLIDATION_PASS')]
    stages += [('output-adapter','tests/integration_output_adapter.py','OUTPUT_ADAPTER_PASS')]
    stages += [('a3-student','tests/integration_student.py','STUDENT_LIFECYCLE_PASS')]
    stages += [('world-predictor','tests/integration_world.py','WORLD_LIFECYCLE_PASS')]
    if not a.quick:stages += [('step12',None,'VERTICAL_CHECKS_PASS'),('body-state',None,'BODY_STATE_CHECKS_PASS'),('second-attempt','tests/integration_second_attempt.py','FAMILY_CHECKS_PASS'),('cancel-restart','tests/integration_real.py',True)]
    stages += [('sustained',None,'BOUNDED_STABILITY_PASS')]
    if a.compare_c3:stages += [('c3-comparison','scripts/benchmark_c3.py','PAIRED_NATIVE_COMPLETE')]
    stage_spec=[{'name':name,'script':script,'expected':expected} for name,script,expected in stages]
    if a.stage_limit is not None and not 1<=a.stage_limit<=len(stages):p.error('stage-limit outside complete stage plan')
    binding={'source_hashes':report['source_hashes'],'harness_hashes':report['harness_hashes'],
             'device':report['device'],'installed':installed_identity(home),
             'quick':a.quick,'compare_c3':a.compare_c3}
    if a.resume:
        report=json.loads((out/'acceptance.json').read_text())
        validate_resume(report,out,binding,stage_spec)
        if archive:
            archived=archive/'acceptance.json'
            if not archived.is_file() or json.loads(archived.read_text()).get('resume_binding')!=binding:p.error('Archive does not belong to this exact cohort')
            validate_resume(report,archive,binding,stage_spec)
        preserve_interrupted(report,out)
        report.setdefault('resume_segments',[]).append({'time_utc':stamp,'completed_stages_kept':len(report['stages'])})
        report['status']='RUNNING'
    else:report.update(checkpoint_version=VERSION,resume_binding=binding,stage_spec=stage_spec,resume_segments=[])
    save()
    for name,script,expected in stages[len(report['stages']):]:
        if a.stage_limit is not None and len(report['stages'])>=a.stage_limit:break
        result=out/(name+'.json');log=out/(name+'.log');start=time.monotonic();row={'name':name,'status':'RUNNING','artifact':str(result),'log':str(log)};report['stages'].append(row);save()
        cmd=[sys.executable,str(APP/script),'--installed-home',str(home),'--out',str(result)] if script else [sys.executable,'-m','v13','--home',str(home),'probe',name]
        if name=='sustained':cmd+=['--cycles','4' if a.quick else '12']
        if name=='c3-comparison':cmd+=['--download-candidate']
        if name=='predictor-b2':cmd+=['--role','B2_GIST']
        if name=='output-adapter':cmd+=['--production']
        print(f'[{len(report["stages"])}/{len(stages)}] {name} — echte Modelle, Bericht: {result}',flush=True)
        proc=None
        try:
            with log.open('wb') as stream:
                proc=subprocess.Popen(cmd,cwd=APP,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(collector_lock.fileno(),))
                row['process_identity']=process_identity(proc.pid);save()
                code=proc.wait()
            if not script:
                source=home/'exports'/(name+'-proof.json')
                if source.exists():shutil.copyfile(source,result)
            data=json.loads(result.read_text()) if result.exists() else {}
            actual=data.get('proof_status') if name=='learning' else (data.get('all_passed') if name=='cancel-restart' else data.get('status'))
            row.update(exit_code=code,observed_status=actual,status='PASS' if code==0 and actual==expected else 'FAIL',duration_s=time.monotonic()-start,artifact_sha256=file_hash(result) if result.exists() else None)
            print('  '+row['status']+' · '+str(actual),flush=True)
        except KeyboardInterrupt:
            if proc and proc.poll() is None:
                os.killpg(proc.pid,signal.SIGINT)
                try:proc.wait(timeout=10)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            row.update(status='INTERRUPTED',duration_s=time.monotonic()-start);report['status']='INTERRUPTED';save();print('Abgebrochen. Teilberichte bleiben: '+str(out));return 130
        except Exception as exc:row.update(status='FAIL',error=type(exc).__name__+': '+str(exc),duration_s=time.monotonic()-start)
        row['checkpoint_files']={f.name:file_hash(f) for f in out.glob(name+'.*') if f.is_file()}
        save()
    if binding['source_hashes']!={str(f.relative_to(APP)):file_hash(f) for f in (APP/'v13').glob('*.py')} or binding['harness_hashes']!=harness_hashes(APP) or binding['installed']!=installed_identity(home):
        report['status']='SOURCE_OR_INSTALLATION_CHANGED';save();return 2
    if len(report['stages'])!=len(stage_spec):
        report['status']='DIAGNOSTIC_INCOMPLETE';save()
        print('Teilabschnitt gespeichert. Gesamtprüfung offen: '+str(len(report['stages']))+'/'+str(len(stage_spec))+'. Fortsetzen mit --resume '+str(out),flush=True)
        return 2
    report['status']='IMPLEMENTED_PATHS_PASS' if all(x['status']=='PASS' for x in report['stages']) else 'IMPLEMENTED_PATHS_PARTIAL';save()
    print(report['status']+'\nBerichte: '+str(out)+'\nDas Ergebnis bewertet die ausgeführten Pfade; offene Canon-Funktionen bleiben offen.')
    return 0 if report['status']=='IMPLEMENTED_PATHS_PASS' else 2

if __name__=='__main__':sys.exit(main())
