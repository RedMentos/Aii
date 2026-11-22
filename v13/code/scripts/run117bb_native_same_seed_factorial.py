#!/usr/bin/env python3
"""Run117BB: four-arm paired native C3 token/schema x seed, shadow-only."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from v13.common import atomic_write, dumps
from v13.config import initialize
from tests.integration_step2_utility import installed_links
from scripts import p2x_disjoint_receiver_trainset as p2x
from scripts import jef_c3_c5_c6_operator_cli as cli
from scripts import run117az_jef_route_native_phone as az

FIXTURE_SHA256='93ba613a9427db204a89c652ed60f4ef271181b780cb159e9e40659a1a5f5fd1'
IDS=('P2X1AEB386F7D1AB7C5','P2X21F4A96EB49D1F3B',
     'P2X13843D8F3EAF1A12','P2X14163A11B8FE5595',
     'P2X1E641242DD58B2E7','P2X20DCA77F282F3C0F')
ACTIONS=('A','A','B','B','NONE','NONE')
ARMS=(('TOKEN',13),('SCHEMA',13),('TOKEN',727),('SCHEMA',727))
SCHEMA='v13.run117bb.same_seed_factorial_native.v1'


def rows():
    originals=p2x.fixtures();p2x.validate(originals)
    validation=[r for r in originals if r['partition']=='validation']
    selected=[]
    for action in ('A','B','NONE'):
        selected+=sorted((r for r in validation if r['oracle_action']==action),
                         key=lambda r:r['id'])[2:4]
    if tuple(r['id'] for r in selected)!=IDS or tuple(r['oracle_action'] for r in selected)!=ACTIONS:
        raise ValueError('BB_FROZEN_IDS_RED')
    frozen=[{'id':r['id'],'domain':r['domain'],'policy_source':r['b2_source'],
             'sheet_source':r['b1_source'],'current':r['current'],
             'oracle_action':r['oracle_action']} for r in selected]
    if hashlib.sha256(json.dumps(frozen,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=FIXTURE_SHA256:
        raise ValueError('BB_FROZEN_SHA_RED')
    return frozen


def run(work,installed,out,*,native=False):
    if out.exists() or (work.exists() and any(work.iterdir())):
        raise FileExistsError('FRESH_RAW_REQUIRED')
    out.mkdir(parents=True);work.mkdir(parents=True,exist_ok=True)
    report={'schema':SCHEMA,'status':'INCOMPLETE','fixture_sha256':FIXTURE_SHA256,
            'native_requested':native,'native_c3_calls':0,'native_c2_calls':0,
            'native_body_calls':0,'native_jef_calls':0,'rows':[],
            'age0':'RECORD_ONLY','step2':'UTILITY_FAIL','b3':'NO_PROMOTION',
            'body_jepa':'UNAVAILABLE','world_jepa_authority':'SHADOW','jepa_weight':0,
            'redmi_measured':False,'whole_system_complete':False,
            'output_committed':False,'tool_dispatches':0,'learning_authority':0,
            'delivery_authority':0,'real_tty_approved':False,
            'independent_c3_reasoning_proven':False,'step2_promoted':False}
    try:
        fixed=rows()
        if native:report['binding']=az.installed_binding(installed)
        for i,row in enumerate(fixed):
            order=ARMS[i%4:]+ARMS[:i%4]
            pair={'id':row['id'],'oracle_action':row['oracle_action'],
                  'arm_order':[f'{a}_S{s}' for a,s in order],'arms':[]}
            for kind,seed in order:
                label=f'{kind.lower()}_s{seed}'
                home=work/f'home_{i:02d}_{label}'
                initialize(home)
                if native:installed_links(home,installed)
                inp=work/f'input_{i:02d}_{label}.json'
                payload={k:row[k] for k in ('domain','policy_source','sheet_source','current')}
                payload['project']=row['id']
                raw=json.dumps(payload,sort_keys=True).encode()
                inp.write_bytes(raw)
                mode=('native' if kind=='TOKEN' else 'native_schema') if native else (
                      'synthetic_exact' if kind=='TOKEN' else 'synthetic_schema_exact')
                c=cli.run(home,inp,mode,operator_opt_in=True,callback_opt_in=True,
                          route_shadow=True,seed_override=seed if native else None)
                audit=az._audit_home(home,row['oracle_action'])
                exact=(c.get('model_formatter_status')=='FORMATTER_MATCH_SHADOW'
                       and c.get('source_only_fallback') is False) if kind=='TOKEN' else (
                       c.get('schema_formatter_status')=='SCHEMA_EXACT_SHADOW'
                       and c.get('status')=='SHADOW_DRAFT_PREFLIGHT_READY')
                item={'arm':f'{kind}_S{seed}','kind':kind,'seed':seed,'mode':mode,
                      'input_sha256':hashlib.sha256(raw).hexdigest(),
                      'cli':c,'store_audit':audit,'strict_formatter_exact':bool(exact)}
                pair['arms'].append(item)
                report['native_c3_calls']+=int(c.get('native_model_called') is True)
                atomic_write(out/f'row_{i:02d}_{label}.json',dumps(item)+'\n')
            report['rows'].append(pair)
        scores={f'{kind}_S{seed}':sum(int(next(a for a in row['arms'] if a['arm']==f'{kind}_S{seed}')['strict_formatter_exact'])
                                  for row in report['rows']) for kind,seed in ARMS}
        report['strict_scores']=scores
        report['paired_schema_gains']={str(seed):scores[f'SCHEMA_S{seed}']-scores[f'TOKEN_S{seed}'] for seed in (13,727)}
        valid=len(report['rows'])==6 and report['native_c3_calls']==(24 if native else 0)
        for pair in report['rows']:
            valid=valid and len(pair['arms'])==4
            for item in pair['arms']:
                c=item['cli'];a=item['store_audit'];kind=item['kind'];seed=item['seed']
                ok=(c.get('delivery_authority')==0 and c.get('learning_authority')==0
                    and c.get('tool_dispatches')==0 and c.get('output_committed') is False
                    and c.get('real_tty_approved') is False and a['live_output_count']==0
                    and c.get('route_shadow_status')==cli.JEF_C2_ROUTE_READY)
                if native:
                    ok=ok and c.get('native_seed')==seed and c.get('native_model_called') is True \
                        and c.get('native_final') is True and c.get('native_process_reaped') is True \
                        and c.get('actual_model')==az.MODEL \
                        and c.get('native_model_sha256')==az.MODEL_SHA256 \
                        and c.get('runner_sha256')==az.RUNNER_SHA256
                else:
                    ok=ok and c.get('native_model_called') is False
                if c.get('status')=='SHADOW_DRAFT_PREFLIGHT_READY':
                    ok=ok and c.get('c6_status')=='NEEDS_REAL_TTY_APPROVAL' \
                        and a['assistant_messages']==1 and a['all_messages_source_action'] \
                        and a['action_kinds']==['TEXT_REPORT']
                else:
                    ok=ok and kind=='SCHEMA' and c.get('status')=='DRAFT_STAGE_RED' \
                        and a['assistant_messages']==0 and a['action_kinds']==[] \
                        and item['strict_formatter_exact'] is False
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
                     'strict_scores':report.get('strict_scores')}))
    return report['status']=='STRUCTURAL_GREEN_NO_PROMOTION'


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    p.add_argument('--installed',type=Path)
    p.add_argument('--native',action='store_true')
    a=p.parse_args(argv)
    if a.native and a.installed is None:p.error('--installed required for --native')
    return 0 if run(a.work,a.installed,a.out,native=a.native) else 2

if __name__=='__main__':raise SystemExit(main())
