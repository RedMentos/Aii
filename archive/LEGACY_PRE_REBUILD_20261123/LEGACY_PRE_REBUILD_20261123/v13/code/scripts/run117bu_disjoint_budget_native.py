#!/usr/bin/env python3
"""Run117BU paired disjoint seed1103 native C3 typed-JEF vs raw-source pilot.

Software harness only until a separate pinned native workflow is launched.
No B1/B2/C2/JEF native inference, output, tool or learning authority.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import time
import threading

from v13.agi.jef_c3_budget_formatter_shadow_run117bo import format_shadow, SCHEMA
from v13.common import atomic_write, dumps, file_hash
from v13.config import DEFAULTS, initialize, save_config
from v13.store import Store, audit_closed
from v13.runners import RunnerPool
from tests.integration_step2_utility import installed_links
from v13.models import ModelManager
from scripts.run115j_typed_jef_role_native import C3_SHA, C3_REV, RUNNER_SHA
from scripts.run113b_b1b2_c3_native import _reaped

SEED=1103
FIXTURE_SHA='f8ca7a22c47f991d630c9df1b1b2ee2943d24123246c8ffaf45db65998403f65'
IDS=('Aurora','Boreal','Cirrus','Delta','Eos','Fjord','Gaia','Helix')
ARMS=('TYPED_JEF','RAW_SOURCE')
CONFIG=DEFAULTS|{'threads':2,'temperature':0.,'seed':13,'observer_mode':'off',
                'answer_tokens':96,'deadline_seconds':120,'observer_seconds':30,
                'body_residency_mb':0,'history_turns':0,'memory_top_k':0,
                'teacher_enabled':False,'learning_mode':'RECORD_ONLY'}
NEGATIVE={'age0':'RECORD_ONLY','step2':'UTILITY_FAIL','b3':'NO_PROMOTION',
          'body_jepa':'UNAVAILABLE','world_jepa':'SHADOW','jepa_weight':0,
          'redmi_measured':False,'whole_system_complete':False,
          'delivery_authority':0,'learning_authority':0,'tool_dispatches':0,
          'output_committed':False}
RAW_SYSTEM=('Use only the two exact user messages. Apply the earlier binding project '
            'budget, deadline and local-only policy to current options. Choose '
            'the cheapest eligible option, A on a tie. If a required rule is '
            'missing return UNKNOWN with null remaining. If no option is '
            'eligible return NONE with null remaining. Return JSON with exactly '
            'choice and remaining, no commentary, tools or actions.')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def fixture(path):
    raw=Path(path).read_bytes()
    if sha(raw)!=FIXTURE_SHA:raise ValueError('FROZEN_FIXTURE_SHA_RED')
    data=json.loads(raw)
    if (data.get('schema')!='v13.run117bs.c3_disjoint_budget_seed1103.v1'
            or type(data.get('seed')) is not int or data['seed']!=SEED
            or data.get('arms')!=list(ARMS)
            or tuple(x['id'] for x in data.get('fixtures',()))!=IDS):
        raise ValueError('FROZEN_COHORT_RED')
    for row in data['fixtures']:
        if set(row)!={'id','prior','current','oracle'} or set(row['oracle'])!={'choice','remaining'}:
            raise ValueError('FROZEN_ROW_RED')
    return data


def _unique(pairs):
    result={}
    for k,v in pairs:
        if k in result:raise ValueError('DUPLICATE_JSON_RED')
        result[k]=v
    return result


def _nonfinite(_):raise ValueError('NONFINITE_JSON_RED')


def score(raw,oracle):
    if type(raw) is not str:return {'valid_json':False,'exact':False}
    try:v=json.loads(raw,object_pairs_hook=_unique,parse_constant=_nonfinite)
    except (ValueError,TypeError,OverflowError):return {'valid_json':False,'exact':False}
    valid=(type(v) is dict and set(v)=={'choice','remaining'}
           and type(v['choice']) is str and v['choice'] in ('A','B','NONE','UNKNOWN')
           and ((v['choice'] in ('NONE','UNKNOWN') and v['remaining'] is None)
                or (v['choice'] in ('A','B') and type(v['remaining']) is int and v['remaining']>=0)))
    return {'valid_json':bool(valid),'exact':bool(valid and v==oracle)}


def order(index):return ARMS if index%2==0 else ARMS[::-1]


def pinned_c3(installed):
    m=ModelManager(installed)
    d={'c3_model_sha256':file_hash(m.path_for('C3_LANGUAGE')),
       'c3_revision':m.revision('C3_LANGUAGE'),
       'runner_sha256':file_hash(installed/'bin/llama-server')}
    if d!={'c3_model_sha256':C3_SHA,'c3_revision':C3_REV,'runner_sha256':RUNNER_SHA}:
        raise ValueError('PINNED_MODEL_RUNNER_RED')
    return d


def run_row(home,installed,row,index):
    initialize(home);save_config(home,CONFIG);installed_links(home,installed)
    store=Store(home)
    session=store.new_session()
    pool=RunnerPool(home,ModelManager(home),CONFIG,approval_store=store)
    cancel_event=threading.Event()
    item={'id':row['id'],'status':'ERROR','arms':[],
          'source_ref_sha256':[],'closed_store_ok':False,'error_type':None}
    try:
        prior=store.event(session,row['prior'])['source_ref']
        current=store.event(session,row['current'])['source_ref']
        refs=[sha(dumps(x).encode()) for x in (prior,current)]
        item['source_ref_sha256']=refs
        source_text=[store.read_source(x) for x in (prior,current)]
        assert source_text==[row['prior'],row['current']]
        for arm in order(index):
            result={'arm':arm,'native_output':'','native_final':False,
                    'process_reaped':False,'process_releases':[],
                    'native_metrics':None,'guard':None,'messages':None,
                    'source_rechecked':False,'score':{'valid_json':False,'exact':False},
                    'status':'ERROR'}
            item['arms'].append(result)  # Preserve even a failed/partial native arm.
            start_release=len(pool.release_history)
            epoch=(store.db.total_changes,store.db.execute('PRAGMA data_version').fetchone()[0])
            def generate(messages,schema):
                result['messages']=messages
                result['prompt_sha256']=sha(dumps(messages).encode())
                runner=pool.get('C3_LANGUAGE')
                try:
                    for chunk in runner.generate(
                            messages,cancel_event,time.monotonic()+90,96,schema,seed=13):
                        if type(chunk) is not str:
                            raise TypeError('NATIVE_CHUNK_TYPE_RED')
                        result['native_output'] += chunk  # Retain partial tokens on failure.
                finally:
                    try:
                        result['native_metrics']=dict(runner.last_metrics)
                        result['native_final']=runner.last_metrics.get('status')=='FINAL'
                    finally:
                        pool.unload()
                return result['native_output']
            completed=False
            try:
                if arm=='TYPED_JEF':
                    result['guard']=format_shadow(store,session,prior,current,generate,
                                                  operator_opt_in=True,callback_opt_in=True)
                    result['source_rechecked']=result['guard'].get('source_rechecked') is True
                else:
                    messages=[{'role':'system','content':RAW_SYSTEM},
                              {'role':'user','content':dumps({
                                  'prior_exact':source_text[0],
                                  'current_exact':source_text[1],
                                  'source_ref_sha256':refs,
                                  'candidate_authority':0})}]
                    generate(messages,SCHEMA)
                    result['source_rechecked']=(
                        (store.db.total_changes,store.db.execute('PRAGMA data_version').fetchone()[0])==epoch
                        and [store.read_source(x) for x in (prior,current)]==source_text)
                completed=True
            except (Exception,KeyboardInterrupt) as exc:
                result['error_type']=type(exc).__name__
                raise
            finally:
                result['process_releases']=list(pool.release_history[start_release:])
                result['process_reaped']=_reaped(result['process_releases'])
                result['score']=score(result['native_output'],row['oracle'])
                guard_ok=(arm=='RAW_SOURCE' or (result['guard'] or {}).get('status')=='FORMATTER_MATCH_SHADOW')
                result['status']='RECORDED' if (completed and result['native_final']
                                               and result['process_reaped']
                                               and result['source_rechecked'] and guard_ok) else 'STRUCTURAL_RED'
        item['status']='RECORDED' if len(item['arms'])==2 and all(x['status']=='RECORDED' for x in item['arms']) else 'STRUCTURAL_RED'
    except (Exception,KeyboardInterrupt) as exc:
        item['error_type']=type(exc).__name__
        item['status']='INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'ERROR'
    finally:
        try:pool.unload();store.close()
        except Exception as exc:
            item['close_error_type']=type(exc).__name__
            item['status']='STRUCTURAL_RED'
        try:item['closed_store_ok']=audit_closed(home)['ok'] is True
        except Exception:item['closed_store_ok']=False
    if not item['closed_store_ok']:item['status']='STRUCTURAL_RED'
    return item


def summarize(rows):
    scores={arm:0 for arm in ARMS};paired=0;final=0;reaped=0;rechecked=0
    for row in rows:
        arm_map={a['arm']:a for a in row.get('arms',())}
        for arm in ARMS:
            a=arm_map.get(arm,{})
            scores[arm]+=int(a.get('score',{}).get('exact') is True)
            final+=int(a.get('native_final') is True)
            reaped+=int(a.get('process_reaped') is True)
            rechecked+=int(a.get('source_rechecked') is True)
        paired+=int(arm_map.get('TYPED_JEF',{}).get('score',{}).get('exact') is True)
        paired-=int(arm_map.get('RAW_SOURCE',{}).get('score',{}).get('exact') is True)
    return {'rows':len(rows),'native_final':final,'process_reaped':reaped,
            'source_rechecked':rechecked,'scores':scores,'paired_net':paired}


def run(installed,out,fixture_path):
    f=fixture(fixture_path)
    if out.exists():raise FileExistsError('OUTPUT_EXISTS_RED')
    out.mkdir(parents=True)
    binding=pinned_c3(installed)
    report={'schema':'v13.run117bu.disjoint_budget_native.v1',
            'evidence_class':'LINUX_NATIVE_C3_DISJOINT_GRAMMAR_PILOT',
            'seed':SEED,'fixture_sha256':FIXTURE_SHA,
            'registered_cohort_reused':False,'independent_generalization':False,
            'native_body_calls':0,'native_c2_calls':0,'native_jef_calls':0,
            'native_c3_calls':0,'installed_binding':binding,'rows':[],
            'row_sha256':{},'status':'RUNNING',**NEGATIVE}
    atomic_write(out/'report.json',dumps(report))
    for i,row in enumerate(f['fixtures']):
        item=run_row(out/('home-'+row['id']),installed,row,i)
        report['rows'].append(item)
        report['native_c3_calls']+=sum(x.get('native_metrics') is not None for x in item['arms'])
        report['row_sha256'][row['id']]=sha(dumps(item).encode())
        report['summary']=summarize(report['rows'])
        atomic_write(out/'report.json',dumps(report))
        print(dumps({'id':row['id'],'status':item['status'],
                     'scores':{x['arm']:x['score'] for x in item['arms']}}),flush=True)
    report['installed_binding_unchanged']=pinned_c3(installed)==binding
    s=report['summary']
    complete=(s['rows']==8 and s['native_final']==s['process_reaped']==s['source_rechecked']==16
              and report['native_c3_calls']==16 and report['installed_binding_unchanged']
              and all(x['status']=='RECORDED' and x['closed_store_ok'] for x in report['rows']))
    signal=(complete and s['scores']['TYPED_JEF']>=7 and s['paired_net']>=3)
    report['status']='EXPLORATORY_TYPED_ADVANTAGE' if signal else 'NO_EXPLORATORY_TYPED_ADVANTAGE'
    report['complete_native_receipts']=bool(complete)
    atomic_write(out/'report.json',dumps(report))
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--installed',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--fixture',type=Path,required=True)
    a=p.parse_args();r=run(a.installed,a.out,a.fixture)
    print(dumps({'status':r['status'],'summary':r['summary']}))

if __name__=='__main__':main()
