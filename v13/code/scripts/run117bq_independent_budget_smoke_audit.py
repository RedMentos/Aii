#!/usr/bin/env python3
"""Independent read-only Run117BP known-seed401 C3 receipt audit.

Structural consistency is not native attestation or independent generalization.
No writes, model execution, output authority, or promotion.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re

IDS = ('Helios', 'Lyra', 'Orion', 'Cedar', 'Mistral', 'Nexus')
FIXTURE_SHA = '8aa69cc86d2e2067e809d4f703ddbff3fc575ea111d7afd97a73012e0bda0e21'
MODEL_SHA = '3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d'
RUNNER_SHA = '79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39'
MODEL_REV = '657e078c94084481950a2d555a941481f715536b'
NEGATIVE = {'age0':'RECORD_ONLY','step2':'UTILITY_FAIL','b3':'NO_PROMOTION',
            'body_jepa':'UNAVAILABLE','world_jepa':'SHADOW','jepa_weight':0,
            'redmi_measured':False,'whole_system_complete':False,
            'delivery_authority':0,'learning_authority':0,'tool_dispatches':0,
            'output_committed':False}
EXPORT_SUFFIXES = {'.gguf','.safetensors','.pt','.pth','.ckpt','.onnx','.tflite'}


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    out = {}
    for key,value in pairs:
        if key in out: raise ValueError('duplicate JSON key')
        out[key] = value
    return out


def strict(raw):
    def reject(_): raise ValueError('nonfinite JSON')
    return json.loads(raw,object_pairs_hook=unique,parse_constant=reject)


def typed(v):
    return (type(v) is dict and set(v)=={'choice','remaining'}
            and type(v['choice']) is str and v['choice'] in ('A','B','NONE','UNKNOWN')
            and ((v['choice'] in ('NONE','UNKNOWN') and v['remaining'] is None)
                 or (v['choice'] in ('A','B') and type(v['remaining']) is int and v['remaining']>=0)))


def audit(report, fixture, root=None):
    errors=[]
    def check(ok,label):
        if not ok: errors.append(label)
    check(type(report) is dict,'REPORT_SHAPE')
    if type(report) is not dict:return {'status':'AUDIT_RED','errors':errors}
    check(report.get('schema')=='v13.run117bp.jef_c3_budget_native_smoke.v1','SCHEMA')
    check(report.get('evidence_class')=='LINUX_NATIVE_C3_KNOWN_SEED401_REGRESSION_ONLY','EVIDENCE_CLASS')
    check(report.get('fixture_sha256')==FIXTURE_SHA and report.get('seed')==401,'COHORT_PIN')
    check(report.get('registered_cohort_reused') is True and report.get('independent_generalization') is False,'GENERALIZATION_CLAIM')
    check(report.get('native_body_calls')==0 and report.get('native_c2_calls')==0 and report.get('native_jef_calls')==0,'NATIVE_ROLE_CLAIM')
    check(all(type(report.get(k)) is type(v) and report.get(k)==v for k,v in NEGATIVE.items()),'NEGATIVE_GATES')
    check(report.get('installed_binding')=={'c3_model_sha256':MODEL_SHA,'c3_revision':MODEL_REV,'runner_sha256':RUNNER_SHA},'MODEL_PIN')
    check(report.get('installed_binding_unchanged') is True,'MODEL_PIN_POST')
    check(type(fixture) is dict and fixture.get('seed')==401 and
          tuple(r.get('id') for r in fixture.get('fixtures',[]) if type(r) is dict)==IDS,'FIXTURE_IDS')
    frows=fixture.get('fixtures',[]) if type(fixture) is dict else []
    rows=report.get('rows')
    check(type(rows) is list and len(rows)==6,'ROW_COUNT')
    if type(rows) is not list:rows=[]
    check(tuple(r.get('id') for r in rows if type(r) is dict)==IDS,'ROW_ORDER')
    hashes=report.get('row_sha256')
    check(type(hashes) is dict and set(hashes)==set(IDS),'ROW_HASH_KEYS')
    for i,row in enumerate(rows):
        label='ROW_'+str(i)
        if type(row) is not dict or i>=len(frows):
            errors.append(label+'_SHAPE');continue
        expected=frows[i].get('oracle')
        check(typed(expected),label+'_FIXTURE_ORACLE')
        check(type(hashes) is dict and hashes.get(row.get('id'))==sha(canonical(row).encode()),label+'_HASH')
        check(row.get('expected_oracle')==expected,label+'_ORACLE')
        check(row.get('status')=='RECORDED',label+'_STATUS')
        check(row.get('native_final') is True,label+'_FINAL')
        check(row.get('process_reaped') is True,label+'_REAPED')
        metrics=row.get('native_c3_metrics')
        check(type(metrics) is dict and metrics.get('status')=='FINAL',label+'_NATIVE_METRICS')
        releases=row.get('process_releases')
        check(type(releases) is list and len(releases)>0 and
              any(type(x) is dict and x.get('before') is not None for x in releases) and
              all(type(x) is dict and x.get('process_reaped') is True for x in releases),label+'_RELEASE_RECEIPT')
        guard=row.get('guard')
        check(type(guard) is dict and guard.get('status')=='FORMATTER_MATCH_SHADOW' and
              guard.get('source_rechecked') is True and guard.get('callback_invoked') is True and
              guard.get('native_proof') is False and guard.get('delivery_authority')==0 and
              guard.get('learning_authority')==0 and guard.get('jepa_weight')==0 and
              guard.get('output_committed') is False,label+'_GUARD')
        refs=row.get('source_ref_sha256')
        check(type(refs) is list and len(refs)==2 and all(type(x) is str and re.fullmatch('[0-9a-f]{64}',x) for x in refs),label+'_REFS')
        if type(guard) is dict:check(guard.get('source_ref_sha256')==refs,label+'_GUARD_REFS')
        messages=row.get('native_prompt')
        if type(messages) is list and len(messages)==2 and all(type(m) is dict for m in messages):
            check(messages[0].get('role')=='system' and messages[1].get('role')=='user',label+'_PROMPT_ROLES')
            check(set(messages[1])=={'role','content'},label+'_PROMPT_USER_SHAPE')
            try:packet=strict(messages[1]['content'])
            except (ValueError,TypeError,KeyError):packet=None
            if type(packet) is dict:
                check(set(packet)=={'typed_jef_candidate','candidate_authority','source_ref_sha256'},label+'_PROMPT_FIELDS')
                check(packet.get('candidate_authority')==0 and type(packet.get('candidate_authority')) is int,label+'_PROMPT_AUTHORITY')
                check(packet.get('source_ref_sha256')==refs,label+'_PROMPT_REFS')
                check(packet.get('typed_jef_candidate')==expected and typed(packet.get('typed_jef_candidate')),label+'_TYPED_CANDIDATE')
                if type(guard) is dict:
                    check(guard.get('candidate_sha256')==sha(canonical(packet.get('typed_jef_candidate')).encode()),label+'_CANDIDATE_HASH')
            else:errors.append(label+'_PROMPT_PACKET')
            psha=sha(canonical(messages).encode())
            check(row.get('native_prompt_sha256')==psha,label+'_PROMPT_HASH')
            if type(guard) is dict:check(guard.get('prompt_sha256')==psha,label+'_GUARD_PROMPT_HASH')
        else:errors.append(label+'_PROMPT_SHAPE')
        raw=row.get('native_output')
        if type(raw) is str:
            try:parsed=strict(raw)
            except (ValueError,TypeError):parsed=None
            check(typed(parsed) and parsed==expected,label+'_OUTPUT_EXACT')
            if type(guard) is dict:
                check(guard.get('output_sha256')==sha(raw.encode()),label+'_OUTPUT_HASH')
                check(guard.get('output_bytes')==len(raw.encode()),label+'_OUTPUT_BYTES')
        else:errors.append(label+'_OUTPUT_SHAPE')
        check(row.get('oracle_visible_to_native') is False,label+'_ORACLE_VISIBILITY_CLAIM')
        check('error_type' not in row and 'close_error_type' not in row,label+'_ROW_ERRORS')
    check(report.get('summary')=={'rows':6,'native_final':6,'process_reaped':6,'source_rechecked':6,'formatter_match':6},'SUMMARY')
    check(report.get('native_c3_calls')==6 and type(report.get('native_c3_calls')) is int,'NATIVE_CALL_COUNT')
    check(report.get('status')=='NATIVE_FORMATTER_SMOKE_MATCH_6_OF_6','SELF_REPORTED_STATUS')
    if root is not None:
        for p in Path(root).rglob('*'):
            if p.is_file() and p.suffix.lower() in EXPORT_SUFFIXES:
                errors.append('MODEL_EXPORT_PRESENT:'+str(p.relative_to(root)))
    return {'status':'AUDIT_STRUCTURAL_PASS_NO_NATIVE_ATTESTATION' if not errors else 'AUDIT_RED',
            'errors':errors,'rows_checked':len(rows),'native_attested':False,
            'independent_generalization':False,'step2':'UTILITY_FAIL',
            'body_jepa':'UNAVAILABLE','jepa_weight':0,'whole_system_complete':False}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--report',type=Path,required=True)
    p.add_argument('--fixture',type=Path,required=True)
    p.add_argument('--root',type=Path)
    a=p.parse_args()
    raw=a.fixture.read_bytes()
    if sha(raw)!=FIXTURE_SHA:raise SystemExit('FROZEN_FIXTURE_SHA_RED')
    result=audit(strict(a.report.read_text()),strict(raw.decode()),a.root)
    print(canonical(result))
    if result['status']!='AUDIT_STRUCTURAL_PASS_NO_NATIVE_ATTESTATION':raise SystemExit(1)

if __name__=='__main__':main()
