#!/usr/bin/env python3
"""Run117BA paired native C3 token/schema JEF formatter diagnostic, zero authority."""
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

FIXTURE_SHA256 = '6c2a0b7cd6da01eaee94ee51b6192ddb8ef413b9f630e26613a573aff2412fc2'
IDS = ('P2X070C21C676DE2933', 'P2X0B0686437F05F4A8',
       'P2X007D0E2CB1187E5F', 'P2X0F0C6ADF683C800C',
       'P2X0396F1A5C1ABB3D3', 'P2X0FE4E750279F6E41')
ACTIONS = ('A', 'A', 'B', 'B', 'NONE', 'NONE')
SCHEMA = 'v13.run117ba.paired_native_c3_formatter.v1'


def rows():
    originals = p2x.fixtures()
    p2x.validate(originals)
    validation = [r for r in originals if r['partition'] == 'validation']
    selected = []
    for action in ('A', 'B', 'NONE'):
        selected.extend(sorted((r for r in validation if r['oracle_action'] == action),
                               key=lambda r: r['id'])[:2])
    if tuple(r['id'] for r in selected) != IDS or tuple(r['oracle_action'] for r in selected) != ACTIONS:
        raise ValueError('FROZEN_VALIDATION_IDS_RED')
    frozen = [{'id':r['id'],'domain':r['domain'],'policy_source':r['b2_source'],
               'sheet_source':r['b1_source'],'current':r['current'],
               'oracle_action':r['oracle_action']} for r in selected]
    raw = json.dumps(frozen,sort_keys=True,separators=(',',':')).encode('utf-8')
    if hashlib.sha256(raw).hexdigest() != FIXTURE_SHA256:
        raise ValueError('FROZEN_VALIDATION_SHA_RED')
    return frozen


def run(work, installed, out, *, native=False):
    if out.exists() or (work.exists() and any(work.iterdir())):
        raise FileExistsError('FRESH_EVIDENCE_REQUIRED')
    out.mkdir(parents=True);work.mkdir(parents=True,exist_ok=True)
    report = {'schema':SCHEMA,'status':'INCOMPLETE','fixture_sha256':FIXTURE_SHA256,
              'native_requested':native,'native_c3_calls':0,'native_body_calls':0,
              'native_c2_calls':0,'native_jef_calls':0,'rows':[],
              'age0':'RECORD_ONLY','step2':'UTILITY_FAIL','b3':'NO_PROMOTION',
              'body_jepa':'UNAVAILABLE','world_jepa_authority':'SHADOW',
              'jepa_weight':0,'redmi_measured':False,'whole_system_complete':False,
              'delivery_authority':0,'learning_authority':0,'tool_dispatches':0,
              'output_committed':False,'real_tty_approved':False,
              'causal_schema_effect_proven':False,'seed_confounded':True}
    try:
        fixed=rows()
        if native:
            report['binding']=az.installed_binding(installed)
        for i,row in enumerate(fixed):
            order=('TOKEN','SCHEMA') if i%2==0 else ('SCHEMA','TOKEN')
            pair={'id':row['id'],'oracle_action':row['oracle_action'],
                  'arm_order':list(order),'arms':[]}
            for arm in order:
                home=work/f'home_{i:02d}_{arm.lower()}'
                initialize(home)
                if native: installed_links(home,installed)
                inp=work/f'input_{i:02d}_{arm.lower()}.json'
                payload={k:row[k] for k in ('domain','policy_source','sheet_source','current')}
                payload['project']=row['id']
                raw=json.dumps(payload,sort_keys=True).encode('utf-8')
                inp.write_bytes(raw)
                mode=('native' if arm=='TOKEN' else 'native_schema') if native else (
                      'synthetic_exact' if arm=='TOKEN' else 'synthetic_schema_exact')
                result=cli.run(home,inp,mode,operator_opt_in=True,
                               callback_opt_in=True,route_shadow=True)
                audit=az._audit_home(home,row['oracle_action'])
                exact=(result.get('model_formatter_status')=='FORMATTER_MATCH_SHADOW'
                       and result.get('source_only_fallback') is False) if arm=='TOKEN' else (
                       result.get('schema_formatter_status')=='SCHEMA_EXACT_SHADOW'
                       and result.get('status')=='SHADOW_DRAFT_PREFLIGHT_READY')
                item={'arm':arm,'mode':mode,'input_sha256':hashlib.sha256(raw).hexdigest(),
                      'cli':result,'store_audit':audit,'strict_formatter_exact':bool(exact)}
                pair['arms'].append(item)
                report['native_c3_calls']+=int(result.get('native_model_called') is True)
                atomic_write(out/f'row_{i:02d}_{arm.lower()}.json',dumps(item)+'\n')
            report['rows'].append(pair)
        scores={arm:sum(int(next(a for a in row['arms'] if a['arm']==arm)['strict_formatter_exact'])
                        for row in report['rows']) for arm in ('TOKEN','SCHEMA')}
        report['strict_scores']=scores
        report['paired_schema_gain']=scores['SCHEMA']-scores['TOKEN']
        valid=True
        for pair in report['rows']:
            for item in pair['arms']:
                c=item['cli'];s=item['store_audit'];arm=item['arm']
                ok=(c.get('delivery_authority')==0 and c.get('learning_authority')==0
                    and c.get('tool_dispatches')==0 and c.get('output_committed') is False
                    and c.get('real_tty_approved') is False and s['live_output_count']==0
                    and c.get('route_shadow_status')==cli.JEF_C2_ROUTE_READY)
                if native:
                    ok=ok and c.get('native_model_called') is True and c.get('native_final') is True \
                        and c.get('native_process_reaped') is True \
                        and c.get('actual_model')==az.MODEL \
                        and c.get('native_model_sha256')==az.MODEL_SHA256 \
                        and c.get('runner_sha256')==az.RUNNER_SHA256
                else:
                    ok=ok and c.get('native_model_called') is False
                if c.get('status')=='SHADOW_DRAFT_PREFLIGHT_READY':
                    ok=ok and c.get('c6_status')=='NEEDS_REAL_TTY_APPROVAL' \
                        and s['assistant_messages']==1 and s['all_messages_source_action'] \
                        and s['action_kinds']==['TEXT_REPORT']
                else:
                    ok=ok and arm=='SCHEMA' and c.get('status')=='DRAFT_STAGE_RED' \
                        and s['assistant_messages']==0 and s['action_kinds']==[] \
                        and item['strict_formatter_exact'] is False
                valid=valid and ok
        valid=valid and len(report['rows'])==6 and report['native_c3_calls']==(12 if native else 0)
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

if __name__=='__main__':
    raise SystemExit(main())
