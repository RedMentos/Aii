#!/usr/bin/env python3
"""Run117BP known-seed401 real C3 native integration smoke of Run117BO SHADOW.

Regression of an existing frozen cohort, NOT independent generalization.
One native C3 formatter call per synthetic real-Store pair; no live output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

from v13.agi.jef_c3_budget_formatter_shadow_run117bo import format_shadow
from v13.common import atomic_write, dumps, file_hash
from v13.config import DEFAULTS, initialize, save_config
from v13.runtime import Runtime
from tests.integration_step2_utility import installed_links
from v13.models import ModelManager
from scripts.run115j_typed_jef_role_native import C3_SHA, C3_REV, RUNNER_SHA

FIXTURE_SHA = '8aa69cc86d2e2067e809d4f703ddbff3fc575ea111d7afd97a73012e0bda0e21'
FIXTURE_IDS = ('Helios', 'Lyra', 'Orion', 'Cedar', 'Mistral', 'Nexus')
CONFIG = DEFAULTS | {'threads': 2, 'temperature': 0., 'seed': 13,
                     'observer_mode': 'off', 'answer_tokens': 96,
                     'deadline_seconds': 120, 'observer_seconds': 30,
                     'body_residency_mb': 0, 'history_turns': 0,
                     'memory_top_k': 0, 'teacher_enabled': False,
                     'learning_mode': 'RECORD_ONLY'}
NEGATIVE = {'age0':'RECORD_ONLY','step2':'UTILITY_FAIL','b3':'NO_PROMOTION',
            'body_jepa':'UNAVAILABLE','world_jepa':'SHADOW','jepa_weight':0,
            'redmi_measured':False,'whole_system_complete':False,
            'delivery_authority':0,'learning_authority':0,'tool_dispatches':0,
            'output_committed':False}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def fixture(path):
    raw=Path(path).read_bytes()
    if sha(raw)!=FIXTURE_SHA:raise ValueError('FROZEN_FIXTURE_SHA_RED')
    data=json.loads(raw)
    if (data.get('seed')!=401 or data.get('schema')!='v13.run46b.jef_source_eligibility_seed401.v1'
            or tuple(x['id'] for x in data.get('fixtures',()))!=FIXTURE_IDS):
        raise ValueError('FROZEN_FIXTURE_COHORT_RED')
    for row in data['fixtures']:
        if (set(row)!={'id','prior','current','oracle'}
                or set(row['oracle'])!={'choice','remaining'}):
            raise ValueError('FROZEN_FIXTURE_ROW_RED')
    return data


def summary(rows):
    return {'rows':len(rows),'native_final':sum(x.get('native_final') is True for x in rows),
            'process_reaped':sum(x.get('process_reaped') is True for x in rows),
            'source_rechecked':sum(x.get('guard',{}).get('source_rechecked') is True for x in rows),
            'formatter_match':sum(x.get('status')=='RECORDED' for x in rows)}


def run_row(home,installed,row):
    initialize(home)
    save_config(home,CONFIG)
    installed_links(home,installed)
    r=Runtime(home)
    item={'id':row['id'],'status':'ERROR','oracle_visible_to_native':False,
          'native_output':'','native_final':False,'process_reaped':False,
          'process_releases':[], 'source_ref_sha256':[],
          'guard':None,'native_c3_metrics':None}
    start=time.monotonic()
    try:
        prior=r.store.event(r.session,row['prior'])['source_ref']
        current=r.store.event(r.session,row['current'])['source_ref']
        item['source_ref_sha256']=[sha(dumps(ref).encode('utf-8')) for ref in (prior,current)]
        def generate(messages,schema):
            item['native_prompt']=messages
            item['native_prompt_sha256']=sha(dumps(messages).encode('utf-8'))
            runner=r.pool.get('C3_LANGUAGE')
            item['native_output']=''.join(runner.generate(
                messages,r.cancel_event,time.monotonic()+90,96,schema,seed=13))
            item['native_c3_metrics']=dict(runner.last_metrics)
            item['native_final']=runner.last_metrics.get('status')=='FINAL'
            r.pool.unload()
            return item['native_output']
        item['guard']=format_shadow(r.store,r.session,prior,current,generate,
                                    operator_opt_in=True,callback_opt_in=True)
        item['expected_oracle']=row['oracle']
        item['status']=('RECORDED' if item['guard']['status']=='FORMATTER_MATCH_SHADOW'
                        and item['native_final'] else 'FORMATTER_OR_NATIVE_RED')
    except (Exception,KeyboardInterrupt) as exc:
        item['error_type']=type(exc).__name__
        item['status']='INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'ERROR'
    finally:
        try:r.close()
        except Exception as exc:
            item['close_error_type']=type(exc).__name__
            item['status']='STRUCTURAL_RED'
        item['process_releases']=list(r.pool.release_history)
        item['process_reaped']=bool(item['process_releases']) and all(
            x.get('process_reaped') is True for x in item['process_releases'])
        if item['status']=='RECORDED' and not item['process_reaped']:
            item['status']='STRUCTURAL_RED'
        item['elapsed_s']=round(time.monotonic()-start,3)
    return item


def pinned_c3(installed):
    models=ModelManager(installed)
    model_sha=file_hash(models.path_for('C3_LANGUAGE'))
    runner_sha=file_hash(installed/'bin/llama-server')
    revision=models.revision('C3_LANGUAGE')
    if (model_sha!=C3_SHA or runner_sha!=RUNNER_SHA or revision!=C3_REV):
        raise ValueError('PINNED_C3_MODEL_OR_RUNNER_RED')
    return {'c3_model_sha256':model_sha,'c3_revision':revision,
            'runner_sha256':runner_sha}


def run(installed,out,fixture_path):
    f=fixture(fixture_path)
    if out.exists():raise FileExistsError('OUTPUT_EXISTS_RED')
    out.mkdir(parents=True)
    binding=pinned_c3(installed)
    report={'schema':'v13.run117bp.jef_c3_budget_native_smoke.v1',
            'evidence_class':'LINUX_NATIVE_C3_KNOWN_SEED401_REGRESSION_ONLY',
            'fixture_sha256':FIXTURE_SHA,'seed':401,'registered_cohort_reused':True,
            'independent_generalization':False,'native_body_calls':0,
            'native_c2_calls':0,'native_jef_calls':0,
            'native_c3_calls':0,'installed_binding':binding,
            'rows':[],'row_sha256':{},'status':'RUNNING',**NEGATIVE}
    atomic_write(out/'report.json',dumps(report))
    for row in f['fixtures']:
        item=run_row(out/('home-'+row['id']),installed,row)
        report['rows'].append(item)
        report['native_c3_calls']+=int(item['native_c3_metrics'] is not None)
        report['row_sha256'][row['id']]=sha(dumps(item).encode('utf-8'))
        report['summary']=summary(report['rows'])
        atomic_write(out/'report.json',dumps(report))
        print(dumps({'id':row['id'],'status':item['status'],
                     'guard':(item['guard'] or {}).get('status')}),flush=True)
    report['installed_binding_unchanged']=pinned_c3(installed)==binding
    ok=(report['summary']['formatter_match']==6
        and report['summary']['native_final']==6
        and report['summary']['process_reaped']==6
        and report['summary']['source_rechecked']==6
        and report['installed_binding_unchanged'])
    report['status']=('NATIVE_FORMATTER_SMOKE_MATCH_6_OF_6' if ok else
                      'NATIVE_FORMATTER_SMOKE_NO_FULL_SIGNAL')
    atomic_write(out/'report.json',dumps(report))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--installed',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--fixture',type=Path,required=True)
    args=p.parse_args()
    r=run(args.installed,args.out,args.fixture)
    print(dumps({'status':r['status'],'summary':r['summary']}))


if __name__=='__main__':main()
