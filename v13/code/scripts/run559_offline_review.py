#!/usr/bin/env python3
"""Run559: independent offline SHA/source/oracle review of frozen STEP2 native batches.

No model, runner, network or Runtime calls. Requires exact raw and safe ZIP SHA
and Actions head. Supports FUTURE_001/002 and source-registered FUTURE_003..024.
"""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import zipfile

import run500_step2_stage_map as stages
import run504_remaining980_schedule as schedule

VARIANTS = ('b1_only','b2_only','both_none','both_exact','both_control',
            'same_policy_dual','prompt_only_dual')
ALLOWED = tuple(f'FUTURE_{i:03d}' for i in range(1,25))


def require(ok, why):
    if not ok:raise ValueError(why)


def sha(data):return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,
                      separators=(',',':'),allow_nan=False).encode()


def parsed(z,name):
    return json.loads(z.read(name),parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def manifest(z,name):
    names=z.namelist()
    require(len(names)==len(set(names)), 'DUPLICATE_ZIP_MEMBER')
    require(all(n and not n.startswith('/') and '..' not in n.split('/') and '\\' not in n
                for n in names), 'UNSAFE_ZIP_MEMBER')
    lines=z.read(name).decode().splitlines()
    checked=[]
    for line in lines:
        expected,path=line.split('  ',1)
        path=path.removeprefix('./')
        require(path in names and path!=name and sha(z.read(path))==expected,
                'RAW_SHA_MISMATCH:'+path)
        checked.append(path)
    require(len(checked)==len(set(checked)) and
            set(checked)==set(names)-{name}, 'RAW_MANIFEST_INCOMPLETE')
    return len(checked)


def independent_score(answer,oracle):
    require(type(answer) is dict and set(answer)=={'project','action','options'},
            'MALFORMED_NATIVE_ANSWER')
    options=answer['options']
    require(type(options) is list and len(options)==2 and
            all(type(x) is dict and set(x)=={'entity','cost','remaining','days','local','eligible'}
                for x in options) and
            {x['entity'] for x in options}=={'A','B'},'MALFORMED_NATIVE_OPTIONS')
    by={x['entity']:x for x in options}
    oracle_by={x['entity']:x for x in oracle['options']}
    def equal(a,b):return type(a)==type(b) and a==b
    checks={'project':equal(answer['project'],oracle['project']),
            'action':equal(answer['action'],oracle['action'])}
    for entity in ('A','B'):
        for field in ('cost','remaining','days','local','eligible'):
            checks[f'{entity}.{field}']=equal(by[entity][field],oracle_by[entity][field])
    return checks


def audit(raw,safe,raw_sha,safe_sha,head,prefix,batch_id):
    require(batch_id in ALLOWED,'UNKNOWN_FUTURE_BATCH')
    require(prefix.startswith('RUN') and prefix[3:].isdigit() and len(prefix)<=12,
            'INVALID_RUN_PREFIX')
    for path,expected in ((raw,raw_sha),(safe,safe_sha)):
        path=Path(path)
        require(path.is_file() and not path.is_symlink() and len(expected)==64 and
                sha(path.read_bytes())==expected,'PINNED_ZIP_SHA_MISMATCH')
    original=stages.registration()
    frozen=schedule.registration()
    batch=frozen['batches'][int(batch_id[-3:])-1]
    selected=[stages.choose(original,sid) for sid in batch['stage_ids']]
    require(batch['id']==batch_id and batch['expected_rows'] in (14,42),
            'FROZEN_BATCH_MISMATCH')
    expected_keys={(stage['arm'],stage['seed'],fixture,variant)
                   for stage in selected for fixture in stage['fixture_ids']
                   for variant in VARIANTS}
    require(len(expected_keys)==batch['expected_rows'] and
            schedule.digest([list(k) for stage in selected for k in stage['row_keys']])==batch['row_keys_sha256'],
            'FROZEN_BATCH_ROW_SHA_DRIFT')
    rootplan={'FUTURE_001':'RUN505','FUTURE_002':'RUN556'}.get(batch_id,'RUN558')
    with zipfile.ZipFile(raw) as zr,zipfile.ZipFile(safe) as zs:
        nraw=manifest(zr,prefix+'_SHA256SUMS.txt')
        names=zs.namelist()
        require(len(names)==len(set(names)),'DUPLICATE_SAFE_MEMBER')
        safe_manifest=parsed(zs,prefix+'_SAFE_MANIFEST.json')
        copied=safe_manifest['copied']
        require(safe_manifest['canonical_gate_pass'] is False and
                safe_manifest['step2_exit']=='UTILITY_FAIL' and
                set(copied)==set(names)-{prefix+'_SAFE_MANIFEST.json'},
                'SAFE_MEMBER_SET_DRIFT')
        for name,meta in copied.items():
            data=zs.read(name)
            require(len(data)==meta['bytes'] and sha(data)==meta['sha256'],
                    'SAFE_MEMBER_SHA_MISMATCH:'+name)
        require(parsed(zr,prefix+'_SAFE_AUDIT.json')==safe_manifest,
                'RAW_SAFE_MANIFEST_MISMATCH')
        require(zr.read(prefix+'_HEAD.txt').decode().strip()==head,
                'ACTIONS_HEAD_DRIFT')
        for name in ('DEPS','FIXTURE','BOOTSTRAP','NATIVE','AUDIT','SAFE','PRIVACY'):
            require(zr.read(prefix+'_'+name+'_EXIT.txt').decode().strip()=='0',
                    'NATIVE_OR_PRIVACY_EXIT_RED:'+name)
        full=parsed(zs,'RUN500_STAGE_MAP.json')
        future=parsed(zs,'RUN504_SCHEDULE.json')
        require(full==original and future==frozen,'ORIGINAL_MAP_SCHEDULE_DRIFT')
        plan=parsed(zs,rootplan+'_BATCH_PLAN.json')
        require(plan['batch_id']==batch_id and plan['stage_ids']==batch['stage_ids'] and
                plan['fixture_pairs']==batch['fixture_pairs'] and
                plan['row_keys_sha256']==batch['row_keys_sha256'] and
                plan['expected_rows']==batch['expected_rows'] and
                plan['native_executed'] is False and plan['canonical_gate_pass'] is False and
                plan['step2_exit']=='UTILITY_FAIL' and plan['jepa_weight']==0,
                'FROZEN_PLAN_DRIFT')
        preflight=parsed(zs,rootplan+'_INSTALLED_PREFLIGHT.json')
        require(preflight['model_sha256']==original['model_sha256_expected_not_retrieved'] and
                preflight['runner_sha256']==original['runner_sha256_expected_not_retrieved'] and
                bool(preflight['runtime_library_sha256']), 'PINNED_NATIVE_MODEL_RUNNER_DRIFT')
        batch_result=parsed(zs,rootplan+'_BATCH_RESULT.json')
        require(batch_result['stage_ids']==batch['stage_ids'] and
                batch_result['rows_verified']==batch['expected_rows'] and
                batch_result['native_execution_performed'] is True and
                batch_result['canonical_gate_pass'] is False and
                batch_result['step2_exit']=='UTILITY_FAIL' and
                batch_result['jepa_weight']==0 and batch_result['redmi_measured'] is False,
                'NATIVE_BATCH_RECEIPT_DRIFT')
        independent=parsed(zr,prefix+'_INDEPENDENT_REPORT.json')
        require(independent['stage_ids']==batch['stage_ids'] and
                independent['rows']==batch['expected_rows'] and
                independent['wrong_committed']==0 and
                independent['canonical_gate_pass'] is False and
                independent['step2_exit']=='UTILITY_FAIL',
                'ORIGINAL_INDEPENDENT_RECEIPT_DRIFT')
        progress=[json.loads(x) for x in zs.read(rootplan+'_BATCH_PROGRESS.jsonl').decode().splitlines()]
        require([(p['stage_id'],p['state']) for p in progress]==
                [(stage['id'],state) for stage in selected for state in ('STARTED','FINISHED')] and
                all(p['rc']==0 for p in progress if p['state']=='FINISHED'),
                'NATIVE_STAGE_PROGRESS_DRIFT')
        seen=set();scores=collections.defaultdict(list);wrong=0
        for stage in selected:
            sid=stage['id'];name=f"{stage['arm']}_s{stage['seed']}";folder='stage_'+sid+'/'
            step=parsed(zs,folder+'step2_'+name+'.json')
            tool=parsed(zs,folder+'tool_'+name+'.json')
            summary=parsed(zs,folder+'summary_'+name+'.json')
            receipt=parsed(zs,folder+'RUN500_STAGE_RESULT.json')
            stage_prereg=parsed(zs,folder+'RUN500_STAGE_PREREG.json')
            require(stage_prereg==stage and step['fixture_sha256']==stage['fixture_sha256'] and
                    summary['run']==name and summary['arm']==stage['arm'] and
                    summary['seed']==stage['seed'], 'NATIVE_STAGE_SOURCE_DRIFT:'+sid)
            require(receipt['stage_id']==sid and receipt['rows_verified']==14 and
                    receipt['native_execution_performed'] is True and
                    receipt['canonical_gate_pass'] is False and receipt['jepa_weight']==0 and
                    receipt['step2_exit']=='UTILITY_FAIL', 'NATIVE_STAGE_RECEIPT_DRIFT:'+sid)
            for kind in ('tool','summary'):
                expected=sha(zs.read(folder+kind+'_'+name+'.json'))
                require(receipt[kind+'_sha256']==expected and
                        independent['stage_hashes'][sid][kind]==expected,
                        'STAGE_HASH_DRIFT:'+sid+':'+kind)
            require(step['uses_real_weights'] is True and step['phone_measured'] is False and
                    step['source_unchanged'] is True and step['installed_artifacts_unchanged'] is True and
                    tool['installed_artifacts_unchanged'] is True,
                    'NATIVE_STAGE_NOT_REAL_OR_SOURCE_DRIFT:'+sid)
            oracles={f['id']:f['oracle'] for f in step['fixtures']}
            require(set(oracles)==set(stage['fixture_ids']) and
                    len(step['rows'])==len(tool['rows'])==14,'NATIVE_STAGE_ROWS_DRIFT:'+sid)
            source={(r['fixture'],r['variant']):r for r in step['rows']}
            for row in step['rows']:
                key=row['fixture']+':'+row['variant']
                require(step['row_sha256'][key]==sha(canonical(row)),
                        'NATIVE_SOURCE_ROW_SHA_DRIFT:'+sid+':'+key)
            stage_scores=collections.defaultdict(list)
            for row in tool['rows']:
                fid,var=row['fixture'],row['variant'];key=(stage['arm'],stage['seed'],fid,var)
                require(key in expected_keys and key not in seen and
                        row['status']=='RECORDED' and row['oracle_visible_to_native'] is False and
                        row['consumer_metrics']['status']=='FINAL',
                        'NATIVE_ROW_STATUS_OR_COVERAGE:'+str(key))
                seen.add(key)
                require(tool['row_sha256'][fid+':'+var]==sha(canonical(row)) and
                        row['consumer_messages_sha256']==sha(canonical(source[(fid,var)]['consumer_messages'])),
                        'NATIVE_ROW_OR_CONSUMER_SOURCE_SHA_DRIFT:'+str(key))
                answer=json.loads(row['answer'])
                checks=independent_score(answer,oracles[fid])
                score=row['score'];false_fields=[k for k,v in checks.items() if not v]
                require(score['field_checks']==checks and score['contradictions']==false_fields and
                        score['contradiction_count']==len(false_fields) and
                        score['scored_fields']==12 and score['exact']==all(checks.values()) and
                        math.isfinite(score['utility']) and
                        abs(score['utility']-sum(checks.values())/12)<1e-12,
                        'INDEPENDENT_ORACLE_SCORE_DRIFT:'+str(key))
                if answer['action'] in ('A','B','NONE') and answer['action']!=oracles[fid]['action']:
                    wrong+=1
                scores[var].append(score['utility']);stage_scores[var].append(score['utility'])
            for variant in VARIANTS:
                require(len(stage_scores[variant])==2 and
                        abs(summary['tool_summary'][variant]['mean_utility']-
                            sum(stage_scores[variant])/2)<1e-12,
                        'NATIVE_STAGE_MEAN_DRIFT:'+sid+':'+variant)
        require(seen==expected_keys and wrong==0,'NATIVE_UTILITY_COVERAGE_OR_WRONG_COMMIT')
        report={
            'schema':'V13_RUN559_INDEPENDENT_FUTURE_BATCH_AUDIT_V1',
            'status':'OFFLINE_VERIFIED_NO_MODEL_EXECUTION',
            'batch_id':batch_id,'actions_head':head,'raw_zip_sha256':raw_sha,
            'safe_zip_sha256':safe_sha,'raw_manifest_entries':nraw,
            'safe_manifest_entries':len(copied),'rows_verified':len(seen),
            'stage_ids':batch['stage_ids'],'wrong_committed':wrong,
            'mean_utility':{v:sum(scores[v])/len(scores[v]) for v in VARIANTS},
            'native_execution_performed_by_this_audit':False,
            'linux_native_origin_as_recorded':True,
            'canonical_gate_pass':False,'step2_exit':'UTILITY_FAIL',
            'b3_l1':'FAIL','body_jepa':'UNAVAILABLE','jepa_weight':0,
            'redmi_measured':False,
        }
        return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ('raw','safe','raw-sha','safe-sha','head','prefix','batch','output'):
        parser.add_argument('--'+arg,required=True)
    args=parser.parse_args()
    report=audit(args.raw,args.safe,args.raw_sha,args.safe_sha,args.head,args.prefix,args.batch)
    Path(args.output).write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'rows':report['rows_verified'],
                      'wrong_committed':report['wrong_committed'],
                      'mean_utility':report['mean_utility']},sort_keys=True))
    print('report_sha256',sha(Path(args.output).read_bytes()))


if __name__=='__main__':main()
