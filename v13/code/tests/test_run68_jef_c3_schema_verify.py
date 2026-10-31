"""Run68 independent native report reparse tamper tests (synthetic only)."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import jef_c3_schema_fixture_727 as f
from scripts import run68_jef_c3_schema_verify as v


def synthetic():
    r={'schema':v.SCHEMA,'preregistered':True,
       'evidence_kind':'LINUX_NATIVE_C3_JSON_SCHEMA_FORMATTER_SHADOW',
       'seed':727,'max_tokens':32,'table_sha256':f.TABLE_SHA256,
       'model_sha256_required':f.MODEL_SHA256,'model_sha256_observed':f.MODEL_SHA256,
       'runner_sha256_required':f.RUNNER_SHA256,'runner_sha256_observed':f.RUNNER_SHA256,
       'age0':'RECORD_ONLY','step2':'UTILITY_FAIL','b3':'NO_PROMOTION',
       'body_jepa':'UNAVAILABLE','jepa_weight':0,'world_jepa_authority':'SHADOW',
       'redmi_measured':False,'whole_system_complete':False,
       'delivery_authority':0,'tool_dispatches':0,'learning_authority':0,
       'native_outputs_redacted':False,'synthetic_only_model_outputs':True,
       'oracle_in_formatter_prompt':True,'closed_store_ok':True,'no_live_output':True,
       'native_call_count':12,'strict':{'BASELINE':0,'SCHEMA':0},
       'status':'SCHEMA_FIDELITY_RED','cases':[]}
    for row in f.fixtures():
        case={'index':row['index'],'project_sha256':f.sha(row['project'].encode()),
              'expected':row['expected'],
              'source_sha256':{k:f.sha(row[k].encode('utf-8'))
              for k in ('current','policy_source','sheet_source')},'arms':[]}
        for arm in (f.ARMS if row['index']%2==0 else f.ARMS[::-1]):
            out='WRONG' if arm=='BASELINE' else '{"action":"INVALID"}'
            case['arms'].append({'arm':arm,'input_sha256':f.sha(f'{row["index"]}'.encode()),
              'output':out,'output_sha256':f.sha(out.encode()),'output_bytes':len(out),
              'parsed_action':None,'strict':0,'native_final':True,'process_reaped':True,
              'actual_model':'LFM2.5-350M-QAD-Q4_0.gguf','status':'RECORDED'})
        r['cases'].append(case)
    return r

class Verify(unittest.TestCase):
    def test_structural_red_science_is_valid(self):
        self.assertEqual(v.verify(synthetic())['diagnostic'],'SCHEMA_FIDELITY_RED')

    def test_hash_tamper_rejected(self):
        r=synthetic();r['cases'][0]['arms'][0]['output_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'OUTPUT_HASH_RED'):v.verify(r)

    def test_score_tamper_rejected(self):
        r=synthetic();r['cases'][0]['arms'][0]['strict']=1
        with self.assertRaisesRegex(ValueError,'STRICT_SCORE_RED'):v.verify(r)

    def test_parse_tamper_rejected(self):
        r=synthetic();a=next(x for x in r['cases'][0]['arms'] if x['arm']=='SCHEMA')
        a['parsed_action']='A'
        with self.assertRaisesRegex(ValueError,'PARSE_STATUS_RED'):v.verify(r)

    def test_prompt_change_rejected(self):
        r=synthetic();r['cases'][0]['arms'][1]['input_sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'PROMPT_CHANGED_RED'):v.verify(r)

    def test_negative_gate_rejected(self):
        r=synthetic();r['learning_authority']=1
        with self.assertRaisesRegex(ValueError,'NEGATIVE_GATES_RED'):v.verify(r)

    def test_source_tamper_rejected(self):
        r=synthetic();r['cases'][0]['source_sha256']['policy_source']='0'*64
        with self.assertRaisesRegex(ValueError,'SOURCE_HASH_RED'):v.verify(r)

    def test_false_green_rejected(self):
        r=synthetic();r['status']='SCHEMA_FIDELITY_DIAGNOSTIC_PASS'
        with self.assertRaisesRegex(ValueError,'STATUS_RED'):v.verify(r)

    def test_positive_synthetic_threshold(self):
        r=synthetic()
        for case in r['cases'][:4]:
            a=next(x for x in case['arms'] if x['arm']=='SCHEMA')
            a['output']='{"action":"'+case['expected']+'"}'
            a['output_sha256']=f.sha(a['output'].encode())
            a['output_bytes']=len(a['output'])
            a['parsed_action']=case['expected'];a['strict']=1
        r['strict']['SCHEMA']=4;r['status']='SCHEMA_FIDELITY_DIAGNOSTIC_PASS'
        self.assertEqual(v.verify(r)['diagnostic'],'SCHEMA_FIDELITY_DIAGNOSTIC_PASS')

if __name__=='__main__':unittest.main()
