"""§102: every ledger row carries the ten neuro fields; brain labels without a §99 ablation never PASS."""
import json
from pathlib import Path
import tempfile
import unittest
from v13.common import APP
from v13.contracts import packet
from v13.runtime import Runtime
from v13.verification import completion_ledger
from v13 import neuro_ledger

class NeuroLedger(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name))
    def tearDown(self):self.r.close();self.tmp.cleanup()

    def test_every_row_has_the_ten_fields(self):
        led=completion_ledger(self.r);self.assertEqual(led['ledger_version'],4)
        for row in led['rows']:
            for f in neuro_ledger.FIELD_NAMES:self.assertIn(f,row,row['feature_id'])
            self.assertIn(row['neuro_claim_status'],{'NO_CLAIM','UNTESTED_LABEL','TESTED_SUPPORTED','TESTED_SUPPORTED_SYNTHETIC','TESTED_PARTIAL','TESTED_NOT_SUPPORTED','TESTED_FAIL'})
        s=led['neuro_ledger'];self.assertEqual(s['unknown_curated_ids'],[]);self.assertEqual(s['curated_rows'],len(neuro_ledger.spec()['rows']))
        self.assertEqual(sum(s['by_class'].values()),len(led['rows']))

    def test_claims_map_to_section99_verdicts(self):
        rows={x['feature_id']:x for x in completion_ledger(self.r)['rows']}
        n=rows['MODULE_NEUROMOD'];self.assertEqual(n['neuro_inspiration_class'],'MECHANISM_INSPIRED');self.assertEqual(n['neuro_claim_status'],'TESTED_PARTIAL')
        self.assertEqual(n['modulator_schema'],'ModulatorPacket');self.assertEqual(n['eligibility_owner'],'v13/neuromod.py');self.assertEqual(n['age_window_policy'],'AGE_CONTROL:'+self.r.cfg['age_plasticity_policy'])
        self.assertEqual(rows['MODULE_AGE']['neuro_claim_status'],'TESTED_NOT_SUPPORTED')
        self.assertEqual(rows['B3_LATENT']['neuro_claim_status'],'TESTED_FAIL')
        self.assertEqual(rows['F9_EPISODIC_REPLAY']['replay_authority'],'HYPOTHESIS_NO_LEARNING')
        self.assertTrue(rows['MODULE_SELFMODEL']['corollary_required']);self.assertEqual(rows['MODULE_SELFMODEL']['neuro_claim_status'],'TESTED_PARTIAL')
        self.assertEqual(rows['MODULE_HOMEOSTASIS']['neuro_claim_status'],'TESTED_SUPPORTED_SYNTHETIC');self.assertEqual(rows['MODULE_ATTENTION']['neuro_claim_status'],'TESTED_SUPPORTED_SYNTHETIC');self.assertEqual(rows['MODULE_REFLEX']['neuro_claim_status'],'TESTED_SUPPORTED_SYNTHETIC');self.assertEqual(rows['MODULE_VISION']['neuro_claim_status'],'UNTESTED_LABEL')
        self.assertEqual(rows['STEP0_STORAGE_PROVENANCE']['neuro_claim_status'],'NO_CLAIM');self.assertEqual(rows['STEP0_STORAGE_PROVENANCE']['gate_status'],'PASS')
        self.assertEqual(rows['STEP0_STORAGE_PROVENANCE']['redmi_longrun_proof']['status'],'ABSENT')

    def test_live_policy_and_train_runner_binding(self):
        self.r.cfg['age_plasticity_policy']='noise_aware'
        e=self.r.store.event(self.r.session,'x')
        p=self.r.store.add_packet('TrainRunnerProof',packet('TrainRunnerProof','F7_RUNTIME','TRAIN',e['brain_generation_id'],trainable_parameter_count=5,runner_revision='numpy-route-head-v1',device={},checks={}))
        rows={x['feature_id']:x for x in completion_ledger(self.r)['rows']}
        self.assertEqual(rows['MODULE_NEUROMOD']['age_window_policy'],'AGE_CONTROL:noise_aware')
        self.assertIsNotNone(rows['STEP5_EXTERNAL_ROUTE_LEARNING']['train_runner_proof_id'])
        self.assertIsNone(rows['C3_NATIVE_OUTPUT_DELTA']['train_runner_proof_id'])

    def test_untested_label_cannot_pass(self):
        rows=[{'feature_id':'MODULE_VISION','gate_status':'PASS','known_limitations':[]}]
        s=neuro_ledger.annotate(rows,self.r)
        self.assertEqual(rows[0]['gate_status'],'PARTIAL');self.assertEqual(s['lowered_pass'],['MODULE_VISION'])
        self.assertTrue(any('§102' in x for x in rows[0]['known_limitations']))

    def test_bad_spec_entries_are_rejected(self):
        sp=neuro_ledger.spec();d=sp['default']
        for bad in ({'neuro_inspiration_class':'FUNCTIONAL_ANALOGY','neuro_claim_limit':' '},
                    {'neuro_inspiration_class':'BRAINY'},
                    {'modulator_schema':'NoSuchSchema'},
                    {'eligibility_owner':'v13/missing.py'},
                    {'replay_authority':'FULL'},
                    {'ablation_baseline':{'hypothesis':'h','controls':['c'],'evidence':['x'],'verdict':'GREAT'}}):
            with self.assertRaises(ValueError):neuro_ledger.validate_entry(sp,'X',dict(d,**bad))

    def test_evidence_files_exist_in_repository(self):
        # The phone package ships without bench-results; in the repository every cited proof must exist.
        if not (APP.parent/'bench-results').is_dir():self.skipTest('bench-results not shipped')
        for fid,row in neuro_ledger.spec()['rows'].items():
            for p in (row.get('ablation_baseline') or {}).get('evidence',[]):self.assertTrue((APP/p).exists(),f'{fid}: {p}')

if __name__=='__main__':unittest.main()
