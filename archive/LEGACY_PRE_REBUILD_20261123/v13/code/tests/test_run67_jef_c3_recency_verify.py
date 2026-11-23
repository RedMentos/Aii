"""Synthetic independent Run67 report tamper controls; no native inference."""
import copy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import jef_c3_recency_fixture_619 as f
from scripts import run67_jef_c3_recency_verify as v


def synthetic():
    report={'schema':v.SCHEMA,'preregistered':True,
            'evidence_kind':'LINUX_NATIVE_C3_FORMATTER_COPY_SHADOW',
            'seed':619,'max_tokens':32,'table_sha256':f.TABLE_SHA256,
            'model_sha256_required':f.MODEL_SHA256,'model_sha256_observed':f.MODEL_SHA256,
            'runner_sha256_required':f.RUNNER_SHA256,'runner_sha256_observed':f.RUNNER_SHA256,
            'age0':'RECORD_ONLY','step2':'UTILITY_FAIL','b3':'NO_PROMOTION',
            'body_jepa':'UNAVAILABLE','jepa_weight':0,'world_jepa_authority':'SHADOW',
            'redmi_measured':False,'whole_system_complete':False,
            'delivery_authority':0,'tool_dispatches':0,'learning_authority':0,
            'native_outputs_redacted':True,'oracle_in_formatter_prompt':True,
            'closed_store_ok':True,'no_live_output':True,'native_call_count':12,
            'strict':{'BASELINE':0,'RECENCY':0},'status':'RECENCY_FIDELITY_RED','cases':[]}
    for row in f.fixtures():
        case={'index':row['index'],'project_sha256':f.sha(row['project'].encode()),
              'expected':row['expected'],
              'source_sha256':{k:f.sha(row[k].encode('utf-8'))
              for k in ('current','policy_source','sheet_source')},'arms':[]}
        order=f.ARMS if row['index']%2==0 else f.ARMS[::-1]
        for arm in order:
            case['arms'].append({'arm':arm,'input_sha256':f.sha(f"{row['index']}-{arm}".encode()),
              'output_sha256':f.sha(b'WRONG'),'output_bytes':5,
              'strict':0,'native_final':True,'process_reaped':True,
              'actual_model':'LFM2.5-350M-QAD-Q4_0.gguf','status':'RECORDED'})
        report['cases'].append(case)
    return report

class Verify(unittest.TestCase):
    def test_all_wrong_is_red_but_structurally_valid(self):
        r=v.verify(synthetic())
        self.assertEqual(r['diagnostic'],'RECENCY_FIDELITY_RED')

    def test_score_tamper_rejected(self):
        r=synthetic();r['cases'][0]['arms'][0]['strict']=1
        with self.assertRaisesRegex(ValueError,'STRICT_SCORE_RED'):v.verify(r)

    def test_source_hash_tamper_rejected(self):
        r=synthetic();r['cases'][0]['source_sha256']['current']='0'*64
        with self.assertRaisesRegex(ValueError,'SOURCE_HASH_RED'):v.verify(r)

    def test_native_release_missing_rejected(self):
        r=synthetic();r['cases'][0]['arms'][0]['process_reaped']=False
        with self.assertRaisesRegex(ValueError,'NATIVE_STRUCTURAL_RED'):v.verify(r)

    def test_raw_text_leak_rejected(self):
        r=synthetic();r['cases'][0]['arms'][0]['output']='secret'
        with self.assertRaisesRegex(ValueError,'RAW_TEXT_LEAK_RED'):v.verify(r)

    def test_negative_gate_tamper_rejected(self):
        r=synthetic();r['delivery_authority']=1
        with self.assertRaisesRegex(ValueError,'NEGATIVE_GATES_RED'):v.verify(r)

    def test_pin_tamper_rejected(self):
        r=synthetic();r['model_sha256_observed']='0'*64
        with self.assertRaisesRegex(ValueError,'PINS_RED'):v.verify(r)

    def test_positive_recency_requires_threshold(self):
        r=synthetic()
        for case in r['cases'][:4]:
            item=next(a for a in case['arms'] if a['arm']=='RECENCY')
            item['output_sha256']=f.sha(case['expected'].encode())
            item['output_bytes']=len(case['expected'])
            item['strict']=1
        r['strict']['RECENCY']=4
        r['status']='RECENCY_FIDELITY_DIAGNOSTIC_PASS'
        self.assertEqual(v.verify(r)['diagnostic'],'RECENCY_FIDELITY_DIAGNOSTIC_PASS')

    def test_false_green_rejected(self):
        r=synthetic();r['status']='RECENCY_FIDELITY_DIAGNOSTIC_PASS'
        with self.assertRaisesRegex(ValueError,'DIAGNOSTIC_STATUS_RED'):v.verify(r)

if __name__=='__main__':unittest.main()
