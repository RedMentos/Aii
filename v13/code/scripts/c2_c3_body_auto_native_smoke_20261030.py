"""Seed47 fresh auto-route C2→C3/Body native integration smoke; no utility gate."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time
import traceback

from v13.config import initialize, save_config
from v13.models import ModelManager
from v13.proofs import audit_event
from v13.runtime import Runtime
from scripts.c2_native_route_provenance_20261030 import valid_control_evidence

SCHEMA='v13.c2_c3_body.auto_native_smoke.v1'
SEED=47
FIXTURES=(
 {'project':'Zephyr47','budget':287,'a':'Marigold','a_cost':191,'a_days':4,'b':'Basalt','b_cost':263,'b_days':7},
 {'project':'Solstice47','budget':346,'a':'Kestrel','a_cost':214,'a_days':8,'b':'Linden','b_cost':319,'b_days':3},
 {'project':'Talon47','budget':229,'a':'Orion','a_cost':173,'a_days':6,'b':'Willow','b_cost':205,'b_days':2},
)
FIXTURE_SHA256='74818535a13819a65d4d32801d704fecd7716ea99c112b33c3bca248f3442c36'

def fixture_hash():
    return hashlib.sha256(json.dumps(FIXTURES,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def prompt(f):
    return (f"Compare options for Project {f['project']}. Budget: {f['budget']} Euro. "
            f"Option {f['a']} costs {f['a_cost']} Euro and takes {f['a_days']} days. "
            f"Option {f['b']} costs {f['b_cost']} Euro and takes {f['b_days']} days. "
            "Both options must be local, no cloud. State the remaining budget "
            "for each named option and briefly explain the time/cost tradeoff.")

def validate_fixtures():
    if fixture_hash()!=FIXTURE_SHA256 or len(FIXTURES)!=3:
        raise ValueError('FIXTURE_PIN_CHANGED')
    if len({f['project'] for f in FIXTURES})!=3:
        raise ValueError('DUPLICATE_PROJECT')
    for f in FIXTURES:
        if not (0<f['a_cost']<f['budget'] and 0<f['b_cost']<f['budget']):
            raise ValueError('INVALID_COSTS')
        if f['a']==f['b'] or f['a_days']==f['b_days']:
            raise ValueError('INVALID_PAIR')
        for expected in (f['budget']-f['a_cost'],f['budget']-f['b_cost']):
            import re
            if re.search(rf'(?<!\d){expected}(?!\d)',prompt(f)):
                raise ValueError('REMAINDER_LEAK')
    return True

def evidence_flags(audit,context,session,eid,text,needle_alive):
    """Separate native invocation, native route selection and Body path."""
    if not isinstance(audit,dict):return {'native_invocation':False,'native_selected':False,'full_body_path':False,'native_output':False}
    meta=audit.get('output_metadata') or {}
    route_info=meta.get('route') or {}
    c2=meta.get('c2_packet') or {}
    route=c2.get('route')
    source=context.get('query_ref') if isinstance(context,dict) else None
    e={'event_id':eid,'session_id':session,'source_ref':source}
    native=bool(needle_alive and isinstance(source,dict) and valid_control_evidence(e,text,route,route_info,context_packet=context))
    selected=bool(native and route_info.get('source')=='NATIVE_C2_ADVISORY')
    roles={p.get('role') for p in audit.get('offers',[]) if isinstance(p,dict)}
    # Final source-bound output is distinct from C2 route invocation.
    checks=audit.get('checks') or {}
    runner=meta.get('runner') or {}
    output=bool(checks and all(v is True for v in checks.values())
                and not audit.get('source_errors')
                and meta.get('model_generated') is True
                and runner.get('role') in ('C3_LANGUAGE','B1_DETAIL','B2_GIST')
                and isinstance(audit.get('output'),str) and audit['output'].strip())
    body=bool(output and {'B1_DETAIL','B2_GIST'}<=roles)
    return {'native_invocation':native,'native_selected':selected,
            'full_body_path':body,'native_output':output}

def fresh_turn(base_home,base_cfg,fixture,index,out):
    text=prompt(fixture)
    with tempfile.TemporaryDirectory(dir=base_home/'tmp',prefix='c2-c3-body-auto-') as td:
        home=Path(td)
        cfg=initialize(home)
        cfg.update(base_cfg)
        cfg.update(learning_mode='RECORD_ONLY',system_stage=0,user_stage_cap=0,
                   teacher_enabled=False,latents_enabled=False,jepa_weight=0,
                   seed=SEED,history_turns=0,route_override='auto',
                   observer_mode='background',control_seconds=20.0)
        save_config(home,cfg)
        for name in ('models','bin'):
            shutil.rmtree(home/name)
            (home/name).symlink_to(base_home/name,target_is_directory=True)
        shutil.copyfile(base_home/'config/models.json',home/'config/models.json')
        r=Runtime(home)
        record=None
        proc=None
        try:
            eid=r.submit(text)
            end=time.monotonic()+r.cfg['deadline_seconds']+2*r.cfg['observer_seconds']+15
            while not r.idle():
                if time.monotonic()>end:
                    r.cancel()
                    raise TimeoutError('NATIVE_AUTO_TURN_DEADLINE')
                time.sleep(.05)
            audit=audit_event(r.store,eid)
            meta=audit.get('output_metadata') or {}
            route_info=meta.get('route') or {}
            ctx_id=route_info.get('executive_control_context_id')
            row=r.store.one("SELECT payload FROM packets WHERE id=? AND kind='ExecutiveControlContext'",(ctx_id,)) if ctx_id else None
            context=json.loads(row['payload']) if row else None
            proc=r.needle.proc
            alive=proc is not None and proc.poll() is None
            source_exact=bool(context and r.store.read_source(context['query_ref'])==text)
            flags=evidence_flags(audit,context,r.session,eid,text,alive)
            flags['native_invocation']=bool(flags['native_invocation'] and source_exact)
            flags['native_selected']=bool(flags['native_selected'] and flags['native_invocation'])
            releases=list(r.pool.release_history)
            roles={x.get('role') for x in releases}
            release_valid=bool(flags['full_body_path'] and {'B1_DETAIL','B2_GIST'}<=roles
                               and all(x.get('process_reaped') is True for x in releases))
            flags['full_body_path']=release_valid
            record={'index':index,'fixture':fixture['project'],'prompt':text,
                    'event_id':eid,'session_id':r.session,'source_exact':source_exact,
                    'context_packet':context,'route_info':route_info,
                    'c2_route':(meta.get('c2_packet') or {}).get('route'),
                    'native_pid':proc.pid if proc else None,
                    'flags':flags,'body_offer_roles':sorted({x.get('role') for x in audit.get('offers',[])}),
                    'body_process_releases':releases,'output_role':(meta.get('runner') or {}).get('role'),
                    'final_output':audit.get('output'),'raw_audit':audit,
                    'learning_mode':'RECORD_ONLY','jepa_weight':0,
                    'redmi_measured':False,'step2_gate_promoted':False}
        finally:
            r.close()
            if record is not None:
                record['native_c2_process_reaped']=bool(proc is not None and proc.poll() is not None)
                record['flags']['native_invocation']=bool(record['flags']['native_invocation'] and record['native_c2_process_reaped'])
                record['flags']['native_selected']=bool(record['flags']['native_selected'] and record['flags']['native_invocation'])
                (out/'raw'/f'{index:02d}_AUTO.json').write_text(json.dumps(record,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n')
        return record

def run(base_home,out):
    base_home,out=Path(base_home).resolve(),Path(out).resolve()
    if out.exists():raise FileExistsError('FRESH_OUTPUT_REQUIRED')
    validate_fixtures()
    out.mkdir(parents=True);(out/'raw').mkdir()
    report={'schema':SCHEMA,'seed':SEED,'fixture_sha256':FIXTURE_SHA256,
            'fixtures':FIXTURES,'status':'INCOMPLETE','rows':[],
            'learning_mode':'RECORD_ONLY','jepa_weight':0,
            'step2_gate_promoted':False,'b3_promoted':False,
            'body_jepa_available':False,'redmi_measured':False,
            'whole_system_complete':False,'comparative_utility_proven':False}
    try:
        cfg=initialize(base_home)
        if cfg['learning_mode']!='RECORD_ONLY' or cfg['system_stage']!=0 or cfg['latents_enabled'] or cfg.get('jepa_weight',0)!=0:
            raise ValueError('BASE_NOT_AGE0')
        v=ModelManager(base_home).verify(deep=True)
        if not all(v.get(k,{}).get('ok') is True and v[k].get('hash_checked') is True for k in ('needle','language','body','gist')):
            raise ValueError('MODEL_PINS_UNVERIFIED')
        report['model_verification']={k:{'ok':v[k]['ok'],'hash_checked':v[k]['hash_checked']} for k in ('needle','language','body','gist')}
        for i,f in enumerate(FIXTURES):
            try:row=fresh_turn(base_home,cfg,f,i,out)
            except BaseException as exc:
                traceback.print_exc()
                row={'index':i,'fixture':f['project'],'error_type':type(exc).__name__,
                     'error':str(exc)[:320], 'flags':{'native_invocation':False,'native_selected':False,
                     'full_body_path':False,'native_output':False}}
            report['rows'].append(row)
            (out/'progress.json').write_text(json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
        report['native_c2_invocations']=sum(bool(x['flags']['native_invocation']) for x in report['rows'])
        report['native_c2_selected_route']=sum(bool(x['flags']['native_selected']) for x in report['rows'])
        report['full_body_offer_paths']=sum(bool(x['flags']['full_body_path']) for x in report['rows'])
        report['native_final_outputs']=sum(bool(x['flags']['native_output']) for x in report['rows'])
        report['status']='NATIVE_AUTO_ROUTE_3_OF_3' if report['native_c2_invocations']==3 and report['native_final_outputs']==3 else 'PARTIAL_RED'
    except BaseException as exc:
        traceback.print_exc()
        report.update(status='PILOT_ERROR',error_type=type(exc).__name__,error=str(exc)[:320])
    finally:
        (out/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    print(json.dumps({'status':report['status'],'native_c2_invocations':report.get('native_c2_invocations',0),
                      'native_c2_selected_route':report.get('native_c2_selected_route',0),
                      'full_body_offer_paths':report.get('full_body_offer_paths',0)},sort_keys=True))
    return report['status']=='NATIVE_AUTO_ROUTE_3_OF_3'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--home',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    return 0 if run(a.home,a.out) else 2

if __name__=='__main__':raise SystemExit(main())
