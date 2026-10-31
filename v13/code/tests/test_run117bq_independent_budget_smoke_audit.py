"""Adversarial self-report audit tests. Synthetic only, no native proof."""
import json
from pathlib import Path
import tempfile
import unittest
from scripts.run117bq_independent_budget_smoke_audit import (
    audit, canonical, sha, IDS, NEGATIVE, MODEL_SHA, RUNNER_SHA, MODEL_REV, FIXTURE_SHA,
)


def fake():
    fixture={'seed':401,'fixtures':[]}
    report={'schema':'v13.run117bp.jef_c3_budget_native_smoke.v1',
            'evidence_class':'LINUX_NATIVE_C3_KNOWN_SEED401_REGRESSION_ONLY',
            'fixture_sha256':FIXTURE_SHA,'seed':401,'registered_cohort_reused':True,
            'independent_generalization':False,'native_body_calls':0,'native_c2_calls':0,
            'native_jef_calls':0,'native_c3_calls':6,
            'installed_binding':{'c3_model_sha256':MODEL_SHA,'c3_revision':MODEL_REV,'runner_sha256':RUNNER_SHA},
            'installed_binding_unchanged':True,'rows':[], 'row_sha256':{},
            'summary':{'rows':6,'native_final':6,'process_reaped':6,'source_rechecked':6,'formatter_match':6},
            'status':'NATIVE_FORMATTER_SMOKE_MATCH_6_OF_6',**NEGATIVE}
    for i,ident in enumerate(IDS):
        oracle={'choice':('A' if i%2==0 else 'NONE'),'remaining':(8 if i%2==0 else None)}
        fixture['fixtures'].append({'id':ident,'oracle':oracle})
        refs=[sha((ident+'prior').encode()),sha((ident+'current').encode())]
        messages=[{'role':'system','content':'copy'},
                  {'role':'user','content':canonical({'typed_jef_candidate':oracle,'candidate_authority':0,'source_ref_sha256':refs})}]
        raw=canonical(oracle)
        guard={'status':'FORMATTER_MATCH_SHADOW','source_rechecked':True,'callback_invoked':True,
               'native_proof':False,'delivery_authority':0,'learning_authority':0,'jepa_weight':0,
               'output_committed':False,'source_ref_sha256':refs,
               'candidate_sha256':sha(canonical(oracle).encode()),
               'prompt_sha256':sha(canonical(messages).encode()),
               'output_sha256':sha(raw.encode()),'output_bytes':len(raw.encode())}
        row={'id':ident,'status':'RECORDED','expected_oracle':oracle,'native_final':True,
             'process_reaped':True,'native_c3_metrics':{'status':'FINAL'},
             'process_releases':[{'before':{'pid':123},'process_reaped':True}],
             'guard':guard,'source_ref_sha256':refs,'native_prompt':messages,
             'native_prompt_sha256':sha(canonical(messages).encode()),
             'native_output':raw,'oracle_visible_to_native':False}
        report['rows'].append(row)
        report['row_sha256'][ident]=sha(canonical(row).encode())
    return report,fixture


class Audit(unittest.TestCase):
    def test_synthetic_perfect_self_report_not_attested(self):
        r,f=fake();a=audit(r,f)
        self.assertEqual(a['status'],'AUDIT_STRUCTURAL_PASS_NO_NATIVE_ATTESTATION')
        self.assertFalse(a['native_attested'])

    def test_forged_final_and_reap_denied(self):
        r,f=fake();r['rows'][0]['native_c3_metrics']['status']='ERROR'
        self.assertIn('ROW_0_NATIVE_METRICS',audit(r,f)['errors'])
        r,f=fake();r['rows'][0]['process_releases']=[]
        self.assertIn('ROW_0_RELEASE_RECEIPT',audit(r,f)['errors'])

    def test_forged_output_and_hash_denied(self):
        r,f=fake();r['rows'][0]['native_output']='{"choice":"A","remaining":9}'
        self.assertIn('ROW_0_OUTPUT_EXACT',audit(r,f)['errors'])
        r,f=fake();r['rows'][0]['native_output']='{"choice":"A","choice":"B","remaining":8}'
        self.assertIn('ROW_0_OUTPUT_EXACT',audit(r,f)['errors'])

    def test_fake_model_and_negative_gate_denied(self):
        r,f=fake();r['installed_binding']['c3_model_sha256']='0'*64
        self.assertIn('MODEL_PIN',audit(r,f)['errors'])
        r,f=fake();r['step2']='PASS'
        self.assertIn('NEGATIVE_GATES',audit(r,f)['errors'])

    def test_prompt_leak_and_wrong_candidate_denied(self):
        r,f=fake();r['rows'][0]['native_prompt'][1]['content']=canonical({'typed_jef_candidate':{'choice':'B','remaining':3},'candidate_authority':0,'source_ref_sha256':r['rows'][0]['source_ref_sha256']})
        self.assertIn('ROW_0_TYPED_CANDIDATE',audit(r,f)['errors'])
        r,f=fake();p=json.loads(r['rows'][0]['native_prompt'][1]['content']);p['oracle']='leak';r['rows'][0]['native_prompt'][1]['content']=canonical(p)
        self.assertIn('ROW_0_PROMPT_FIELDS',audit(r,f)['errors'])

    def test_wrong_order_and_hash_denied(self):
        r,f=fake();r['rows'][0],r['rows'][1]=r['rows'][1],r['rows'][0]
        self.assertIn('ROW_ORDER',audit(r,f)['errors'])
        r,f=fake();r['row_sha256']['Helios']='0'*64
        self.assertIn('ROW_0_HASH',audit(r,f)['errors'])

    def test_export_scan(self):
        r,f=fake()
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(audit(r,f,d)['status'],'AUDIT_STRUCTURAL_PASS_NO_NATIVE_ATTESTATION')
            (Path(d)/'predictor.pt').write_bytes(b'weights')
            self.assertIn('MODEL_EXPORT_PRESENT:predictor.pt',audit(r,f,d)['errors'])


if __name__=='__main__':unittest.main()
