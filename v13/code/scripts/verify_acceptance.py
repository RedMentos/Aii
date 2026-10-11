#!/usr/bin/env python3
"""Verify completed native artifacts against current code, without inference claims."""
import argparse
import hashlib
import json
from pathlib import Path

STATUSES={'jef-modes':'JEF_MODES_PASS','experience':'EXPERIENCE_REPLAY_PASS',
          'executive':'EXECUTIVE_CONTINUITY_PASS','resources':'RESOURCE_MONITOR_NATIVE_PASS',
          'learning':'LEARNING_LIFECYCLE_PASS','readouts':'READOUT_LIFECYCLE_PASS',
          'native-taps':'NATIVE_TAP_PASS','predictor-b1':'PREDICTOR_LIFECYCLE_PASS',
          'predictor-b2':'PREDICTOR_LIFECYCLE_PASS','control-calibration':'CONTROL_CALIBRATION_PASS',
          'memory-retrieval':'MEMORY_RETRIEVAL_PASS',
          'consolidation':'CONSOLIDATION_PASS',
          'output-adapter':'OUTPUT_ADAPTER_PASS',
          'a3-student':'STUDENT_LIFECYCLE_PASS','world-predictor':'WORLD_LIFECYCLE_PASS',
          'step12':'VERTICAL_CHECKS_PASS','body-state':'BODY_STATE_CHECKS_PASS',
          'second-attempt':'FAMILY_CHECKS_PASS','cancel-restart':True,
          'sustained':'BOUNDED_STABILITY_PASS','c3-comparison':'PAIRED_NATIVE_COMPLETE'}
FULL_ONLY={'step12','body-state','second-attempt','cancel-restart'}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def harness_hashes(app):
    app=Path(app);files=[]
    for directory in ('scripts','tests','specs'):
        files.extend(p for p in (app/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.py','.sh','.cpp','.json'})
    files.extend(app.glob('*.sh'))
    return {str(p.relative_to(app)):sha(p) for p in sorted(files)}

def verify(report_path,app,quick=False,compare_c3=False):
    report_path=Path(report_path);app=Path(app);report=json.loads(report_path.read_text());errors=[]
    expected=set(STATUSES)-({'c3-comparison'} if not compare_c3 else set())-(FULL_ONLY if quick else set())
    rows=report.get('stages',[]);names=[r.get('name') for r in rows]
    if report.get('status')!='IMPLEMENTED_PATHS_PASS':errors.append('Collector did not complete successfully')
    if len(set(names))!=len(names) or set(names)!=expected:errors.append('Required stages missing, duplicated or unexpected')
    current={str(p.relative_to(app)):sha(p) for p in (app/'v13').glob('*.py')}
    if not current or report.get('source_hashes')!=current:errors.append('Current production source hashes differ from collector')
    current_harness=harness_hashes(app)
    if report.get('harness_hashes')!=current_harness:errors.append('Test/setup/specification hashes missing or different from collector')
    artifacts=[]
    for row in rows:
        name=row.get('name')
        if name not in STATUSES:continue
        # Sibling artifacts remain verifiable after moving a checkpoint.
        artifact=report_path.parent/(name+'.json')
        if not artifact.is_file():errors.append('Missing stage artifact: '+name);continue
        digest=sha(artifact);artifacts.append({'stage':name,'file':artifact.name,'sha256':digest})
        if digest!=row.get('artifact_sha256'):errors.append('Stage artifact hash mismatch: '+name)
        if row.get('status')!='PASS' or row.get('exit_code')!=0 or row.get('observed_status')!=STATUSES[name]:errors.append('Stage did not pass: '+name)
        data=json.loads(artifact.read_text())
        if name=='memory-retrieval':
            native=data.get('native_feature_artifact',{});native_path=report_path.parent/(name+'.features.json.gz')
            if not native_path.is_file() or native.get('sha256')!=sha(native_path):errors.append('Missing or changed actual native memory features')
        if name=='output-adapter':
            native=data.get('feature_artifact',{});native_path=report_path.parent/(name+'.features.json.gz')
            if not native_path.is_file() or native.get('sha256')!=sha(native_path):errors.append('Missing or changed actual native output features')
        actual=data.get('proof_status') if name=='learning' else data.get('all_passed') if name=='cancel-restart' else data.get('status')
        if actual!=STATUSES[name]:errors.append('Stage artifact status mismatch: '+name)
        if 'source_hashes' in data and data['source_hashes']!=current:errors.append('Stage source hashes differ: '+name)
        if data.get('canonical_architecture_complete') is True:errors.append('Unexpected architecture promotion: '+name)
    return {'status':'PASS' if not errors else 'FAIL','errors':errors,'stages':len(rows),
            'source_files':len(current),'source_hashes_match':report.get('source_hashes')==current,
            'harness_files':len(current_harness),'harness_hashes_match':report.get('harness_hashes')==current_harness,
            'artifacts':artifacts,'collector_sha256':sha(report_path),
            'scope':'Artifact integrity and current-source stage coverage only; no new phone, quality or full Canon proof',
            'canonical_architecture_complete':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('report');p.add_argument('--app',default=str(Path(__file__).resolve().parents[1]));p.add_argument('--quick',action='store_true');p.add_argument('--compare-c3',action='store_true');p.add_argument('--out');a=p.parse_args()
    try:result=verify(a.report,a.app,a.quick,a.compare_c3)
    except (ValueError,OSError,KeyError,TypeError) as exc:result={'status':'FAIL','errors':[type(exc).__name__+': '+str(exc)],'canonical_architecture_complete':False}
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if a.out:
        out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);tmp=out.with_suffix('.partial');tmp.write_text(text);tmp.replace(out)
    print(text,end='');return 0 if result['status']=='PASS' else 2

if __name__=='__main__':raise SystemExit(main())
