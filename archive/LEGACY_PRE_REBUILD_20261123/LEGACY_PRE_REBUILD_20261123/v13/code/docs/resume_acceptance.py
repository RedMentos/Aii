#!/usr/bin/env python3
"""Resume the existing native collector. Guards/test fixtures do not infer models."""
import argparse
import ast
import contextlib
import datetime
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
from v13.common import atomic_write,file_hash
from v13.resources import device

spec=importlib.util.spec_from_file_location('v13_resume_verifier',APP/'scripts/verify_acceptance.py')
verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
class GuardError(RuntimeError):pass

def literal(node,quick):
    if isinstance(node,ast.IfExp) and ast.unparse(node.test)=='a.quick':return literal(node.body if quick else node.orelse,quick)
    if isinstance(node,(ast.List,ast.Tuple)):return [literal(x,quick) for x in node.elts]
    return ast.literal_eval(node)

def registry(app,quick=False,compare_c3=False):
    """Read the actual collector's literal registry and its existing CLI modifiers."""
    tree=ast.parse((Path(app)/'scripts/acceptance.py').read_text())
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    stages=[]
    def stage_statement(n):
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='stages' for t in n.targets):stages.extend(ast.literal_eval(n.value));return True
        if isinstance(n,ast.AugAssign) and isinstance(n.target,ast.Name) and n.target.id=='stages' and isinstance(n.op,ast.Add):stages.extend(ast.literal_eval(n.value));return True
        return False
    for n in main.body:
        if stage_statement(n):continue
        if isinstance(n,ast.If):
            condition=ast.unparse(n.test)
            if condition=='not a.quick' and not quick or condition=='a.compare_c3' and compare_c3:
                for child in n.body:stage_statement(child)
    loop=next(n for n in main.body if isinstance(n,ast.For) and ast.unparse(n.iter)=='stages')
    modifiers={}
    for n in loop.body:
        if isinstance(n,ast.If):
            additions=[c for c in n.body if isinstance(c,ast.AugAssign) and isinstance(c.target,ast.Name) and c.target.id=='cmd']
            if additions:
                if not isinstance(n.test,ast.Compare) or ast.unparse(n.test.left)!='name' or len(n.test.comparators)!=1:raise GuardError('Unrecognized collector CLI conditional')
                name=ast.literal_eval(n.test.comparators[0]);modifiers[name]=[]
                for addition in additions:modifiers[name].extend(literal(addition.value,quick))
    if not stages or len({n for n,_,_ in stages})!=len(stages):raise GuardError('Collector stage registry invalid')
    for name,script,status in stages:
        if verifier.STATUSES.get(name)!=status:raise GuardError('Collector/verifier expected status mismatch: '+name)
        if script and not (Path(app)/script).is_file():raise GuardError('Missing actual stage script: '+name)
    return [{'name':n,'script':s,'expected':e,'extra_args':modifiers.get(n,[])} for n,s,e in stages]

def command(stage,app,home,result):
    base=[sys.executable,str(Path(app)/stage['script']),'--installed-home',str(home),'--out',str(result)] if stage['script'] else [sys.executable,'-m','v13','--home',str(home),'probe',stage['name']]
    return base+stage['extra_args']

def observed(name,data):return data.get('proof_status') if name=='learning' else data.get('all_passed') if name=='cancel-restart' else data.get('status')

def stable_identity():
    # Original collector recorded no physical ID. Never pretend this value was
    # available before the first companion segment. Raw OS identifier is not saved.
    for path in ('/etc/machine-id','/var/lib/dbus/machine-id'):
        try:
            value=Path(path).read_text().strip()
            if value:return {'kind':'OS_MACHINE_ID_SHA256','sha256':hashlib.sha256(value.encode()).hexdigest()}
        except OSError:pass
    return None

def validate_report(path,app,quick,compare_c3,current_device,current_identity=None):
    path=Path(path);app=Path(app);report=json.loads(path.read_text());plan=registry(app,quick,compare_c3)
    source={str(p.relative_to(app)):file_hash(p) for p in (app/'v13').glob('*.py')}
    if not source or report.get('source_hashes')!=source:raise GuardError('Production source hashes changed; new collector run required')
    if report.get('harness_hashes')!=verifier.harness_hashes(app):raise GuardError('Harness/setup/specification hashes changed; new collector run required')
    if report.get('device')!=current_device:raise GuardError('Recorded device descriptor differs; do not merge device runs')
    if report.get('canonical_architecture_complete') is not False:raise GuardError('Architecture completeness claim missing/unsupported')
    if report.get('status') not in {'RUNNING','INTERRUPTED','IMPLEMENTED_PATHS_PARTIAL','IMPLEMENTED_PATHS_PASS'}:raise GuardError('Collector status invalid')
    names=[s['name'] for s in plan];rows=report.get('stages')
    if not isinstance(rows,list):raise GuardError('Stage list missing')
    used=[r.get('name') for r in rows]
    if len(set(used))!=len(used) or any(n not in names for n in used) or used!=sorted(used,key=names.index):raise GuardError('Duplicate, unexpected or unordered stages')
    provenance=report.get('resume_provenance',{})
    if provenance:
        if provenance.get('options')!={'quick':quick,'compare_c3':compare_c3}:raise GuardError('Resume mode differs from recorded plan')
        if provenance.get('stable_identity') is not None and provenance['stable_identity']!=current_identity:raise GuardError('Resume machine identity changed')
        for record in provenance.get('preserved_pass_logs',[]):
            log=path.parent/record['file']
            if not log.is_file() or file_hash(log)!=record['sha256']:raise GuardError('Preserved original log changed: '+record['file'])
    passed=[]
    for row in rows:
        name=row['name']
        if row.get('status') not in {'PASS','FAIL','RUNNING','INTERRUPTED'}:raise GuardError('Stage state invalid: '+name)
        if row['status']!='PASS':continue
        artifact=path.parent/(name+'.json');log=path.parent/(name+'.log')
        if not artifact.is_file() or row.get('artifact_sha256')!=file_hash(artifact):raise GuardError('Completed artifact missing or changed: '+name)
        if not log.is_file():raise GuardError('Completed log missing: '+name)
        if row.get('log_sha256') and file_hash(log)!=row['log_sha256']:raise GuardError('Completed log changed: '+name)
        data=json.loads(artifact.read_text())
        if row.get('exit_code')!=0 or row.get('observed_status')!=verifier.STATUSES[name] or observed(name,data)!=verifier.STATUSES[name]:raise GuardError('Completed status/exit code invalid: '+name)
        if 'source_hashes' in data and data['source_hashes']!=source:raise GuardError('Completed stage source hashes changed: '+name)
        if data.get('canonical_architecture_complete') is True:raise GuardError('Completed stage falsely promotes architecture: '+name)
        if data.get('device') is not None and data['device']!=current_device:raise GuardError('Completed stage device differs: '+name)
        if name in {'memory-retrieval','output-adapter'}:
            reference=data.get('native_feature_artifact' if name=='memory-retrieval' else 'feature_artifact',{})
            feature=path.parent/(name+'.features.json.gz')
            if not feature.is_file() or reference.get('sha256')!=file_hash(feature):raise GuardError('Actual native features missing or changed: '+name)
        passed.append(name)
    if report['status']=='IMPLEMENTED_PATHS_PASS' and set(passed)!=set(names):raise GuardError('Complete collector lacks full requested stage coverage')
    return report,plan,passed

def archive_attempt(folder,name,segment,row):
    """Move only this stage's unsuccessful files; never touch prior PASS stages."""
    target=folder/'resume-attempts'/segment/name;target.mkdir(parents=True,exist_ok=False)
    atomic_write(target/'row.json',json.dumps(row,ensure_ascii=False,indent=2)+'\n')
    for item in list(folder.iterdir()):
        if item.is_file() and item.name.startswith(name+'.'):shutil.move(str(item),str(target/item.name))
    manifest={str(p.relative_to(target)):file_hash(p) for p in target.iterdir() if p.is_file()}
    atomic_write(target/'attempt-manifest.json',json.dumps(manifest,indent=2)+'\n');return target

def mirror(folder,archive):
    if not archive or folder.resolve()==archive.resolve():return
    archive.mkdir(parents=True,exist_ok=True)
    for item in folder.rglob('*'):
        relative=item.relative_to(folder)
        if not item.is_file() or item.name=='acceptance.json' or any(p.startswith('.') for p in relative.parts):continue
        target=archive/relative;target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and file_hash(target)==file_hash(item):continue
        # Completed files are already guards-verified. Writes expose no index
        # before the corresponding JSON/log/features are present.
        atomic_write(target,item.read_bytes())
    atomic_write(archive/'acceptance.json',(folder/'acceptance.json').read_bytes())

def active_collectors(home,app,plan):
    matches=[];wanted={'acceptance.py','resume_acceptance.py'}|{Path(s['script']).name for s in plan if s['script']}
    for entry in list(Path('/proc').glob('[0-9]*'))[:16384]:
        if int(entry.name)==os.getpid():continue
        try:args=entry.joinpath('cmdline').read_bytes().split(b'\0');args=[x.decode(errors='replace') for x in args if x]
        except OSError:continue
        if str(home) not in args:continue
        if any(Path(a).name in wanted for a in args) or ('v13' in args and 'probe' in args):matches.append(int(entry.name))
    return matches

def save_report(folder,report,archive):
    atomic_write(folder/'acceptance.json',json.dumps(report,ensure_ascii=False,indent=2)+'\n');mirror(folder,archive)

def run_stage(stage,folder,home,app,row):
    name=stage['name'];result=folder/(name+'.json');log=folder/(name+'.log');cmd=command(stage,app,home,result)
    row['command']=cmd;proc=None;started=time.monotonic()
    # A probe exports a fixed filename. Archive an older file before invocation
    # so an old PASS can never masquerade as this new process's output.
    probe_output=home/'exports'/(name+'-proof.json') if not stage['script'] else None
    if probe_output and probe_output.exists():
        target=folder/'resume-attempts'/row['segment_id']/name/'prior-home-export.json';target.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(probe_output),str(target))
        row['prior_home_export_sha256']=file_hash(target)
    try:
        with log.open('wb') as stream:
            proc=subprocess.Popen(cmd,cwd=app,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True);row['pid']=proc.pid;code=proc.wait()
        if probe_output and probe_output.is_file():shutil.copyfile(probe_output,result)
        data=json.loads(result.read_text()) if result.exists() else {};actual=observed(name,data)
        row.update(exit_code=code,observed_status=actual,status='PASS' if code==0 and actual==stage['expected'] else 'FAIL')
    except KeyboardInterrupt:
        if proc and proc.poll() is None:
            os.killpg(proc.pid,signal.SIGINT)
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        row['status']='INTERRUPTED';raise
    except Exception as exc:row.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
    finally:
        row.update(duration_s=time.monotonic()-started,artifact_sha256=file_hash(result) if result.exists() else None,log_sha256=file_hash(log) if log.exists() else None)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--installed-home',required=True);parser.add_argument('--resume',required=True,help='Existing result folder or acceptance.json');parser.add_argument('--archive-dir');parser.add_argument('--quick',action='store_true');parser.add_argument('--compare-c3',action='store_true');parser.add_argument('--check-only',action='store_true');args=parser.parse_args()
    home=Path(args.installed_home).expanduser().resolve();path=Path(args.resume).expanduser().resolve();path=path/'acceptance.json' if path.is_dir() else path;folder=path.parent
    if path.name!='acceptance.json':raise GuardError('Resume index must be acceptance.json')
    current_device=device();identity=stable_identity();report,plan,passed=validate_report(path,APP,args.quick,args.compare_c3,current_device,identity)
    if args.check_only:
        print(json.dumps({'status':'RESUME_GUARDS_PASS','passed_stages':passed,'remaining_stages':[s['name'] for s in plan if s['name'] not in passed],'new_native_calls':0,'physical_identity_scope':'Original collector descriptor only; no original physical ID available','canonical_architecture_complete':False},indent=2));return 0
    archive=Path(args.archive_dir).expanduser().resolve() if args.archive_dir else None
    if archive:
        if folder.is_relative_to(archive) or archive.is_relative_to(folder):raise GuardError('Archive and result folder must be distinct non-nested folders')
        if (archive/'acceptance.json').exists():
            prior=json.loads((archive/'acceptance.json').read_text())
            if prior.get('source_hashes')!=report['source_hashes'] or prior.get('harness_hashes')!=report['harness_hashes'] or prior.get('device')!=report['device']:raise GuardError('Archive belongs to another collector')
            _,_,archive_passed=validate_report(archive/'acceptance.json',APP,args.quick,args.compare_c3,current_device,identity)
            for name in archive_passed:
                if name not in passed or file_hash(archive/(name+'.json'))!=file_hash(folder/(name+'.json')) or file_hash(archive/(name+'.log'))!=file_hash(folder/(name+'.log')):raise GuardError('Archive contains another completed attempt: '+name)
    with (folder/'.resume.lock').open('a+') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:raise GuardError('Another resume controller owns this folder')
        active=active_collectors(home,APP,plan)
        if active:raise GuardError('Actual collector/probe still running: '+str(active))
        # Recheck hashes/statuses while holding the controller ownership lock.
        report,plan,passed=validate_report(path,APP,args.quick,args.compare_c3,current_device,identity)
        segment=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        controller_hash=file_hash(Path(__file__));original_sha=file_hash(path)
        segment_dir=folder/'resume-segments'/segment;segment_dir.mkdir(parents=True,exist_ok=False);shutil.copyfile(path,segment_dir/'before-acceptance.json');shutil.copyfile(__file__,segment_dir/'controller.py')
        provenance=report.setdefault('resume_provenance',{'options':{'quick':args.quick,'compare_c3':args.compare_c3},'stable_identity':identity,'original_device_identity_limit':'Original collector recorded descriptor only, not a physical host ID','preserved_pass_logs':[{'file':n+'.log','sha256':file_hash(folder/(n+'.log'))} for n in passed],'segments':[]})
        segment_record={'segment_id':segment,'controller_sha256':controller_hash,'collector_sha256':file_hash(APP/'scripts/acceptance.py'),'before_index_sha256':original_sha,'device':current_device,'stable_identity':identity,'started_wall_time':time.time(),'status':'RUNNING','passed_before':list(passed),'actual_stages_invoked':[]}
        provenance['segments'].append(segment_record);report['status']='RUNNING';save_report(folder,report,archive)
        for stage in plan:
            name=stage['name']
            if name in passed:continue
            # Refuse source drift, including a changed docs-only controller, between stages.
            if file_hash(Path(__file__))!=controller_hash:raise GuardError('Resume controller changed during execution')
            validate_report(path,APP,args.quick,args.compare_c3,current_device,identity)
            active=active_collectors(home,APP,plan)
            if active:raise GuardError('Concurrent native collector/probe: '+str(active))
            old=next((r for r in report['stages'] if r['name']==name),None)
            if old:archive_attempt(folder,name,segment,old)
            elif any(p.is_file() and p.name.startswith(name+'.') for p in folder.iterdir()):archive_attempt(folder,name,segment,{'name':name,'status':'UNINDEXED_PRIOR_ARTIFACT'})
            row={'name':name,'status':'RUNNING','artifact':str(folder/(name+'.json')),'log':str(folder/(name+'.log')),'segment_id':segment,'controller_sha256':controller_hash}
            if old:report['stages'][report['stages'].index(old)]=row
            else:report['stages'].append(row);report['stages'].sort(key=lambda r:[s['name'] for s in plan].index(r['name']))
            segment_record['actual_stages_invoked'].append(name);save_report(folder,report,archive)
            print(name+' — actual remaining native stage',flush=True)
            try:run_stage(stage,folder,home,APP,row)
            except KeyboardInterrupt:
                report['status']='INTERRUPTED';segment_record.update(status='INTERRUPTED',finished_wall_time=time.time());save_report(folder,report,archive);return 130
            if row['status']=='PASS':
                # This validates actual feature artifacts as well, before promotion
                # of this stage in the persisted overall report.
                candidate=folder/('.resume-validation-'+segment+'.json')
                try:
                    atomic_write(candidate,json.dumps(report,ensure_ascii=False,indent=2)+'\n')
                    validate_report(candidate,APP,args.quick,args.compare_c3,current_device,identity)
                except (GuardError,ValueError,OSError) as exc:row.update(status='FAIL',guard_error=str(exc))
                finally:candidate.unlink(missing_ok=True)
            save_report(folder,report,archive)
        report['status']='IMPLEMENTED_PATHS_PASS' if len(report['stages'])==len(plan) and all(r['status']=='PASS' for r in report['stages']) else 'IMPLEMENTED_PATHS_PARTIAL'
        segment_record.update(status=report['status'],finished_wall_time=time.time());save_report(folder,report,archive)
        verification=verifier.verify(path,APP,args.quick,args.compare_c3);atomic_write(segment_dir/'strict-verification.json',json.dumps(verification,indent=2)+'\n');mirror(folder,archive)
        print(report['status']);return 0 if verification['status']=='PASS' else 2

if __name__=='__main__':
    try:raise SystemExit(main())
    except (GuardError,ValueError,OSError,KeyError,TypeError) as exc:
        print('RESUME_REFUSED: '+str(exc),file=sys.stderr);raise SystemExit(2)
