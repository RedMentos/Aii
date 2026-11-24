#!/usr/bin/env python3
"""Independent Run68 raw synthetic native output reparse; no model execution."""
import argparse
import json
from pathlib import Path
from scripts import jef_c3_schema_fixture_727 as f

SCHEMA='v13.jef_c3_schema_disjoint727_native.v1'


def need(ok,why):
    if not ok:raise ValueError(why)


def verify(r):
    need(type(r) is dict and r.get('schema')==SCHEMA and r.get('preregistered') is True,'SCHEMA_RED')
    need(r.get('evidence_kind')=='LINUX_NATIVE_C3_JSON_SCHEMA_FORMATTER_SHADOW','EVIDENCE_KIND_RED')
    need(r.get('seed')==727 and r.get('max_tokens')==32 and r.get('table_sha256')==f.TABLE_SHA256,'COHORT_RED')
    need(r.get('model_sha256_required')==f.MODEL_SHA256 and r.get('model_sha256_observed')==f.MODEL_SHA256
         and r.get('runner_sha256_required')==f.RUNNER_SHA256 and r.get('runner_sha256_observed')==f.RUNNER_SHA256,'PINS_RED')
    need(r.get('age0')=='RECORD_ONLY' and r.get('step2')=='UTILITY_FAIL'
         and r.get('b3')=='NO_PROMOTION' and r.get('body_jepa')=='UNAVAILABLE'
         and r.get('jepa_weight')==0 and r.get('world_jepa_authority')=='SHADOW'
         and r.get('redmi_measured') is False and r.get('whole_system_complete') is False
         and r.get('delivery_authority')==0 and r.get('tool_dispatches')==0
         and r.get('learning_authority')==0 and r.get('native_outputs_redacted') is False
         and r.get('synthetic_only_model_outputs') is True
         and r.get('oracle_in_formatter_prompt') is True,'NEGATIVE_GATES_RED')
    need(r.get('closed_store_ok') is True and r.get('no_live_output') is True,'STORE_OR_OUTPUT_RED')
    cases=r.get('cases');rows=f.fixtures()
    need(type(cases) is list and len(cases)==6,'CASES_RED')
    counts={arm:0 for arm in f.ARMS}
    for row,case in zip(rows,cases):
        need(type(case) is dict and case.get('index')==row['index']
             and case.get('project_sha256')==f.sha(row['project'].encode())
             and case.get('expected')==row['expected'],'CASE_BINDING_RED')
        need(case.get('source_sha256')=={k:f.sha(row[k].encode('utf-8'))
             for k in ('current','policy_source','sheet_source')},'SOURCE_HASH_RED')
        arms=case.get('arms');order=f.ARMS if row['index']%2==0 else f.ARMS[::-1]
        need(type(arms) is list and len(arms)==2
             and all(type(a) is dict for a in arms)
             and [a['arm'] for a in arms]==list(order),'ORDER_RED')
        need(arms[0].get('input_sha256')==arms[1].get('input_sha256'),'PROMPT_CHANGED_RED')
        for a in arms:
            need(a.get('status')=='RECORDED' and a.get('native_final') is True
                 and a.get('process_reaped') is True
                 and a.get('actual_model')=='LFM2.5-350M-QAD-Q4_0.gguf','NATIVE_STRUCTURAL_RED')
            inp=a.get('input_sha256');out=a.get('output')
            need(type(inp) is str and len(inp)==64 and all(c in '0123456789abcdef' for c in inp),'INPUT_SHA_RED')
            need(type(out) is str and 0<len(out.encode('utf-8'))<=1024,'OUTPUT_SHAPE_RED')
            need(a.get('output_sha256')==f.sha(out.encode('utf-8'))
                 and a.get('output_bytes')==len(out.encode('utf-8')),'OUTPUT_HASH_RED')
            need(a.get('parsed_action')==(f.decode_schema(out) if a['arm']=='SCHEMA'
                 else out if out in ('A','B','NONE') else None),'PARSE_STATUS_RED')
            correct=f.score(out,row['expected'],a['arm'])
            need(type(a.get('strict')) is int and a['strict']==correct,'STRICT_SCORE_RED')
            need('input_messages' not in a,'SOURCE_TEXT_LEAK_RED')
            counts[a['arm']]+=correct
    need(r.get('native_call_count')==12 and r.get('strict')==counts,'COUNTS_RED')
    status=('SCHEMA_FIDELITY_DIAGNOSTIC_PASS' if counts['SCHEMA']>=4
            and counts['SCHEMA']-counts['BASELINE']>=2 else 'SCHEMA_FIDELITY_RED')
    need(r.get('status')==status,'STATUS_RED')
    return {'status':'INDEPENDENT_RUN68_NATIVE_OUTPUT_REPARSE_PASS',
            'native_calls':12,'strict':counts,'diagnostic':status,
            'claim_limit':'Synthetic formatter-copy only; no C3 reasoning/STEP2/JEPA/Redmi promotion'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('report',type=Path)
    a=p.parse_args()
    print(json.dumps(verify(json.loads(a.report.read_text())),sort_keys=True))

if __name__=='__main__':main()
