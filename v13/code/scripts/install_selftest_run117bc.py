#!/usr/bin/env python3
"""Run117BC: verified phone ZIP, three JEF native-schema DRAFT-only turns.

Default is software-only. --native-schema requires a pinned, preinstalled C3
model and runner; no downloads, no output/TTY approval, no learning authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import zipfile

FIXTURE_SHA256='6d66cd879fd8939d21ba44e9522d58fc3e1d2391cd4706df80d61eee36fbaeb0'
IDS=('P2X3FE895B9A87BF847','P2X267871443CCAE3D7','P2X27346BF0DF29B3FD')
ACTIONS=('A','B','NONE')
SCHEMA='v13.run117bc.phone_native_schema_smoke.v1'
REQUIRED=('scripts/install_selftest_run117bc.py',
          'scripts/jef_c3_c5_c6_operator_cli.py',
          'scripts/run117az_jef_route_native_phone.py',
          'v13/jef_c3_schema_draft_candidate.py',
          'tests/integration_step2_utility.py')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def rows():
    from scripts import p2x_disjoint_receiver_trainset as p2x
    original=p2x.fixtures();p2x.validate(original)
    validation=[r for r in original if r['partition']=='validation']
    selected=[]
    for action in ACTIONS:
        selected+=sorted((r for r in validation if r['oracle_action']==action),
                         key=lambda r:r['id'])[4:5]
    if tuple(r['id'] for r in selected)!=IDS:
        raise ValueError('BC_FROZEN_IDS_RED')
    frozen=[{'id':r['id'],'domain':r['domain'],'policy_source':r['b2_source'],
             'sheet_source':r['b1_source'],'current':r['current'],
             'oracle_action':r['oracle_action']} for r in selected]
    if sha(json.dumps(frozen,sort_keys=True,separators=(',',':')).encode())!=FIXTURE_SHA256:
        raise ValueError('BC_FROZEN_SHA_RED')
    return frozen


def verify_zip(path,dest):
    if not path.is_file() or path.is_symlink() or path.stat().st_size>50_000_000:
        raise ValueError('ZIP_REGULAR_SIZE_RED')
    with zipfile.ZipFile(path) as z:
        members=z.infolist()
        if len(members)>5000 or sum(x.file_size for x in members)>100_000_000:
            raise ValueError('ZIP_BUDGET_RED')
        if z.testzip() is not None:raise ValueError('ZIP_CRC_RED')
        manifest=json.loads(z.read('V13-Phone/WORKSPACE_FILES.json'))
        files=manifest['files']
        if manifest['schema_version']!=1 or set(z.namelist())!=({f'V13-Phone/{x}' for x in files}|{'V13-Phone/WORKSPACE_FILES.json'}):
            raise ValueError('ZIP_MANIFEST_SET_RED')
        if not set(REQUIRED)<=set(files):raise ValueError('ZIP_REQUIRED_SOURCE_RED')
        for name,expected in files.items():
            if (name.startswith('/') or '..' in Path(name).parts or '\\' in name
                    or not name or name.endswith('/')):
                raise ValueError('ZIP_PATH_RED')
            if sha(z.read('V13-Phone/'+name))!=expected:
                raise ValueError('ZIP_MANIFEST_SHA_RED')
        z.extractall(dest)
        return {'phone_sha256':sha(path.read_bytes()),'source_files':len(files),
                'manifest_sha256':sha(z.read('V13-Phone/WORKSPACE_FILES.json'))}


def worker(work,out,installed,*,native=False):
    from v13.common import atomic_write,dumps
    from v13.config import initialize
    from tests.integration_step2_utility import installed_links
    from scripts import jef_c3_c5_c6_operator_cli as cli
    from scripts import run117az_jef_route_native_phone as az
    if out.exists() or (work.exists() and any(work.iterdir())):
        raise FileExistsError('FRESH_WORKER_EVIDENCE_REQUIRED')
    out.mkdir(parents=True);work.mkdir(parents=True,exist_ok=True)
    report={'schema':SCHEMA,'status':'INCOMPLETE','fixture_sha256':FIXTURE_SHA256,
            'native_requested':native,'native_c3_calls':0,'native_body_calls':0,
            'native_c2_calls':0,'native_jef_calls':0,'rows':[],
            'age0':'RECORD_ONLY','step2':'UTILITY_FAIL','b3':'NO_PROMOTION',
            'body_jepa':'UNAVAILABLE','world_jepa_authority':'SHADOW',
            'jepa_weight':0,'redmi_measured':False,'whole_system_complete':False,
            'output_committed':False,'tool_dispatches':0,'learning_authority':0,
            'delivery_authority':0,'real_tty_approved':False}
    try:
        fixed=rows()
        if native:report['binding']=az.installed_binding(installed)
        for i,row in enumerate(fixed):
            home=work/f'home_{i:02}'
            initialize(home)
            if native:installed_links(home,installed)
            inp=work/f'input_{i:02}.json'
            payload={k:row[k] for k in ('domain','policy_source','sheet_source','current')}
            payload['project']=row['id']
            raw=json.dumps(payload,sort_keys=True).encode()
            inp.write_bytes(raw)
            c=cli.run(home,inp,'native_schema' if native else 'synthetic_schema_exact',
                      operator_opt_in=True,callback_opt_in=True,route_shadow=True,
                      seed_override=13 if native else None)
            audit=az._audit_home(home,row['oracle_action'])
            exact=(c.get('schema_formatter_status')=='SCHEMA_EXACT_SHADOW'
                   and c.get('status')=='SHADOW_DRAFT_PREFLIGHT_READY')
            item={'id':row['id'],'oracle_action':row['oracle_action'],
                  'input_sha256':sha(raw),'cli':c,'store_audit':audit,
                  'strict_formatter_exact':bool(exact)}
            report['rows'].append(item)
            report['native_c3_calls']+=int(c.get('native_model_called') is True)
            atomic_write(out/f'row_{i:02}.json',dumps(item)+'\n')
        report['strict_formatter_exact_count']=sum(int(x['strict_formatter_exact']) for x in report['rows'])
        valid=len(report['rows'])==3 and report['native_c3_calls']==(3 if native else 0)
        for x in report['rows']:
            c=x['cli'];a=x['store_audit']
            ok=(x['strict_formatter_exact'] and c.get('status')=='SHADOW_DRAFT_PREFLIGHT_READY'
                and c.get('route_shadow_status')==cli.JEF_C2_ROUTE_READY
                and c.get('c6_status')=='NEEDS_REAL_TTY_APPROVAL'
                and c.get('delivery_authority')==0 and c.get('learning_authority')==0
                and c.get('tool_dispatches')==0 and c.get('output_committed') is False
                and c.get('real_tty_approved') is False
                and a['assistant_messages']==1 and a['all_messages_source_action']
                and a['live_output_count']==0 and a['action_kinds']==['TEXT_REPORT'])
            if native:
                ok=ok and c.get('native_model_called') is True and c.get('native_final') is True \
                    and c.get('native_process_reaped') is True and c.get('native_seed')==13 \
                    and c.get('actual_model')==az.MODEL \
                    and c.get('native_model_sha256')==az.MODEL_SHA256 \
                    and c.get('runner_sha256')==az.RUNNER_SHA256
            else:ok=ok and c.get('native_model_called') is False
            valid=valid and ok
        report['status']='STRUCTURAL_GREEN_NO_PROMOTION' if valid else 'STRUCTURAL_RED_NO_PROMOTION'
    except BaseException as exc:
        report['status']='STRUCTURAL_RED_NO_PROMOTION'
        report['error_type']=type(exc).__name__
        report['error_message']=str(exc)[:320]
    finally:
        atomic_write(out/'report.json',dumps(report)+'\n')
        print(dumps({'status':report['status'],'rows':len(report['rows']),
                     'native_c3_calls':report['native_c3_calls'],
                     'strict_formatter_exact_count':report.get('strict_formatter_exact_count')}))
    return report['status']=='STRUCTURAL_GREEN_NO_PROMOTION'


def outer(zip_path,work,out,installed,*,native=False):
    if out.exists() or (work.exists() and any(work.iterdir())):
        raise FileExistsError('FRESH_PHONE_EVIDENCE_REQUIRED')
    out.mkdir(parents=True);work.mkdir(parents=True,exist_ok=True)
    report={'schema':SCHEMA+'.outer','status':'INCOMPLETE','native_requested':native,
            'redmi_measured':False,'output_committed':False,'tool_dispatches':0,
            'learning_authority':0,'delivery_authority':0,'jepa_weight':0,
            'step2_promoted':False,'whole_system_complete':False}
    try:
        receipt=verify_zip(zip_path,work/'extracted')
        report.update(receipt)
        extracted=work/'extracted'/'V13-Phone'
        cmd=[sys.executable,str(extracted/'scripts/install_selftest_run117bc.py'),
             '--worker','--work',str(work/'worker'),
             '--out',str(out/'WORKER'),
             '--installed',str(installed) if installed else '']
        if native:cmd.append('--native-schema')
        env=dict(os.environ,PYTHONPATH=os.pathsep.join((str(extracted),str(extracted/'tests'),str(extracted/'scripts'))),
                 V13_NO_AUTOSTART='1',NO_MODEL_DOWNLOADS='1')
        proc=subprocess.Popen(cmd,cwd=extracted,env=env,text=True,
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              start_new_session=True)
        try:
            stdout,stderr=proc.communicate(timeout=600)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL)
            stdout,stderr=proc.communicate(timeout=10)
            report['worker_timeout_reaped']=True
        (out/'WORKER_STDOUT.log').write_text(stdout[-16000:])
        (out/'WORKER_STDERR.log').write_text(stderr[-16000:])
        report['worker_exit']=proc.returncode
        if (out/'WORKER/report.json').is_file():
            child=json.loads((out/'WORKER/report.json').read_text())
            report['worker_status']=child['status']
            report['native_c3_calls']=child['native_c3_calls']
            report['strict_formatter_exact_count']=child.get('strict_formatter_exact_count')
        report['status']='STRUCTURAL_GREEN_NO_PROMOTION' if (
            proc.returncode==0 and report.get('worker_status')=='STRUCTURAL_GREEN_NO_PROMOTION'
            and not report.get('worker_timeout_reaped')) else 'STRUCTURAL_RED_NO_PROMOTION'
    except BaseException as exc:
        report['status']='STRUCTURAL_RED_NO_PROMOTION'
        report['error_type']=type(exc).__name__
        report['error_message']=str(exc)[:320]
    finally:
        (out/'report.json').write_text(json.dumps(report,sort_keys=True)+'\n')
        print(json.dumps({'status':report['status'],'native_requested':native,
                          'native_c3_calls':report.get('native_c3_calls')},sort_keys=True))
    return report['status']=='STRUCTURAL_GREEN_NO_PROMOTION'


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--zip',type=Path)
    p.add_argument('--work',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    p.add_argument('--installed',type=Path)
    p.add_argument('--native-schema',action='store_true')
    p.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    a=p.parse_args(argv)
    if a.native_schema and a.installed is None:p.error('--installed required for --native-schema')
    if a.worker:return 0 if worker(a.work,a.out,a.installed,native=a.native_schema) else 2
    if a.zip is None:p.error('--zip required')
    return 0 if outer(a.zip,a.work,a.out,a.installed,native=a.native_schema) else 2

if __name__=='__main__':raise SystemExit(main())
