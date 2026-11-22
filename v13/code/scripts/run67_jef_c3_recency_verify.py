#!/usr/bin/env python3
"""Independent stdlib read-only Run67 native report verifier; never scores text."""
import argparse
import json
from pathlib import Path
from scripts import jef_c3_recency_fixture_619 as f

SCHEMA='v13.jef_c3_recency_disjoint619_native.v1'


def verify(r):
    need=lambda ok,msg: None if ok else (_ for _ in ()).throw(ValueError(msg))
    need(type(r) is dict,'REPORT_TYPE_RED')
    need(r.get('schema')==SCHEMA and r.get('preregistered') is True,'SCHEMA_RED')
    need(r.get('evidence_kind')=='LINUX_NATIVE_C3_FORMATTER_COPY_SHADOW','EVIDENCE_KIND_RED')
    need(r.get('seed')==619 and r.get('max_tokens')==32 and r.get('table_sha256')==f.TABLE_SHA256,'COHORT_RED')
    need(r.get('model_sha256_required')==f.MODEL_SHA256
         and r.get('model_sha256_observed')==f.MODEL_SHA256
         and r.get('runner_sha256_required')==f.RUNNER_SHA256
         and r.get('runner_sha256_observed')==f.RUNNER_SHA256,'PINS_RED')
    need(r.get('age0')=='RECORD_ONLY' and r.get('step2')=='UTILITY_FAIL'
         and r.get('b3')=='NO_PROMOTION' and r.get('body_jepa')=='UNAVAILABLE'
         and r.get('jepa_weight')==0 and r.get('world_jepa_authority')=='SHADOW'
         and r.get('redmi_measured') is False and r.get('whole_system_complete') is False
         and r.get('delivery_authority')==0 and r.get('tool_dispatches')==0
         and r.get('learning_authority')==0 and r.get('native_outputs_redacted') is True
         and r.get('oracle_in_formatter_prompt') is True,'NEGATIVE_GATES_RED')
    need(r.get('closed_store_ok') is True and r.get('no_live_output') is True,'STORE_OR_OUTPUT_RED')
    rows=f.fixtures()
    cases=r.get('cases')
    need(type(cases) is list and len(cases)==6,'CASES_RED')
    counts={arm:0 for arm in f.ARMS}
    all_input=set()
    for expected,case in zip(rows,cases):
        need(type(case) is dict and case.get('index')==expected['index']
             and case.get('project_sha256')==f.sha(expected['project'].encode())
             and case.get('expected')==expected['expected'],'CASE_BINDING_RED')
        need(case.get('source_sha256')=={k:f.sha(expected[k].encode('utf-8'))
             for k in ('current','policy_source','sheet_source')},'SOURCE_HASH_RED')
        arms=case.get('arms')
        order=f.ARMS if expected['index']%2==0 else f.ARMS[::-1]
        need(type(arms) is list and len(arms)==2
             and [a.get('arm') for a in arms if type(a) is dict]==list(order),'ORDER_RED')
        for a in arms:
            need(a.get('status')=='RECORDED' and a.get('native_final') is True
                 and a.get('process_reaped') is True
                 and a.get('actual_model')=='LFM2.5-350M-QAD-Q4_0.gguf','NATIVE_STRUCTURAL_RED')
            input_sha=a.get('input_sha256')
            output_sha=a.get('output_sha256')
            need(type(input_sha) is str and len(input_sha)==64
                 and all(c in '0123456789abcdef' for c in input_sha)
                 and type(output_sha) is str and len(output_sha)==64
                 and all(c in '0123456789abcdef' for c in output_sha),'DIGEST_SHAPE_RED')
            need(input_sha not in all_input,'DUPLICATE_INPUT_RED')
            all_input.add(input_sha)
            correct=int(output_sha==f.sha(expected['expected'].encode('utf-8')))
            need(type(a.get('strict')) is int and a['strict']==correct,'STRICT_SCORE_RED')
            need(type(a.get('output_bytes')) is int and a['output_bytes']>0,'OUTPUT_BYTES_RED')
            if correct:
                need(a['output_bytes']==len(expected['expected']),'STRICT_LENGTH_RED')
            need('output' not in a and 'input_messages' not in a,'RAW_TEXT_LEAK_RED')
            counts[a['arm']]+=correct
    need(r.get('native_call_count')==12 and r.get('strict')==counts,'COUNTS_RED')
    status=('RECENCY_FIDELITY_DIAGNOSTIC_PASS' if counts['RECENCY']>=4
            and counts['RECENCY']-counts['BASELINE']>=2 else 'RECENCY_FIDELITY_RED')
    need(r.get('status')==status,'DIAGNOSTIC_STATUS_RED')
    return {'status':'INDEPENDENT_RUN67_STRUCTURAL_AUDIT_PASS',
            'native_calls':12,'strict':counts,'diagnostic':status,
            'claim_limit':'C3 formatter-copy only; no output, learning, STEP2, B3, JEPA or Redmi promotion'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('report',type=Path)
    a=p.parse_args()
    data=json.loads(a.report.read_text())
    print(json.dumps(verify(data),sort_keys=True))

if __name__=='__main__':main()
