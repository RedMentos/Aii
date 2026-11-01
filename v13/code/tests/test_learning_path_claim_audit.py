"""No-weight claim-boundary tests, including real historical LoRA manifests."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from scripts import learning_path_claim_audit as audit

CODE = Path(__file__).resolve().parents[1]
TRAINER = CODE / 'v13/lora_trainer.py'
HISTORICAL = CODE.parent / 'bench-results/ag6-live-20261010/ag6-live-lora.json'


class LearningPathAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.trainer = self.home / 'trainer.py'
        self.trainer.write_bytes(TRAINER.read_bytes())
        self.manifest = self.home / 'manifest.json'
        self.binding = self.home / 'binding.json'
        self.doc = {'metrics': {'revision': audit.SOURCE_REVISION,
            'dataset_hash': 'a' * 24, 'jepa_weight': 0., 'steps': 10,
            'trainable_parameter_count': 200, 'anchor_weight': 1.,
            'body_jepa_cos_before': .1, 'body_jepa_cos_after': .5}}
        self.save()

    def save(self):
        self.manifest.write_text(json.dumps(self.doc))

    def run_audit(self, bound=False):
        return audit.audit(self.trainer, self.manifest, self.binding if bound else None)

    def bind(self):
        self.binding.write_text(json.dumps({'schema': 'V13_LEARNING_PATH_AUDIT_INPUTS_V1',
            'trainer_sha256': hashlib.sha256(self.trainer.read_bytes()).hexdigest(),
            'manifest_sha256': hashlib.sha256(self.manifest.read_bytes()).hexdigest(),
            'dataset_hash': self.doc['metrics']['dataset_hash']}))

    def test_cosine_gain_with_disabled_objective_is_not_jepa_learning(self):
        report = self.run_audit()
        self.assertEqual(report['status'], 'AUDIT_REVIEW_ONLY')
        self.assertEqual(report['reported_run']['cosine_delta'], .4)
        self.assertEqual(report['reported_run']['jepa_configuration'], 'DISABLED')
        self.assertFalse(report['body_world_jepa_established'])
        self.assertEqual(report['jepa_component_gradient_contribution'], 'UNMEASURED')

    def test_positive_weight_and_loss_do_not_prove_gradient_or_utility(self):
        self.doc['metrics'].update(jepa_weight=1., loss_history=[{'step': 10, 'ce': .2, 'anchor_kl': 0., 'jepa': .5}])
        self.save()
        report = self.run_audit()
        self.assertFalse(report['errors'])
        self.assertEqual(report['reported_run']['jepa_configuration'], 'CONFIGURED_POSITIVE_WEIGHT')
        self.assertEqual(report['deployed_utility_attributable_to_jepa'], 'UNMEASURED')
        self.assertFalse(report['source_mechanism']['target_ema_update'])

    def test_bound_inputs_are_not_historical_attestation(self):
        self.bind()
        report = self.run_audit(True)
        self.assertEqual(report['binding_status'], 'MATCHED_AUDIT_INPUTS')
        self.assertFalse(report['historical_run_source_verified'])
        self.assertFalse(report['dataset_bytes_verified'])

    def test_manifest_source_and_dataset_binding_drift_rejected(self):
        self.bind()
        for field in ('trainer_sha256', 'manifest_sha256', 'dataset_hash'):
            with self.subTest(field=field):
                bound = json.loads(self.binding.read_text())
                old = bound[field]
                bound[field] = '0' * len(old)
                self.binding.write_text(json.dumps(bound))
                self.assertEqual(self.run_audit(True)['status'], 'INPUT_REJECTED')
                self.bind()

    def test_unknown_source_does_not_inherit_known_semantics(self):
        self.trainer.write_bytes(self.trainer.read_bytes() + b'\n# different trainer\n')
        report = self.run_audit()
        self.assertIn('UNSUPPORTED_SOURCE', report['errors'])
        self.assertIsNone(report['source_mechanism'])

    def test_nonfinite_missing_negative_and_boolean_weights_rejected(self):
        for value in (None, float('nan'), float('inf'), -1., True, '1'):
            with self.subTest(value=value):
                self.doc['metrics']['jepa_weight'] = value
                self.save()
                self.assertIn('INVALID_OR_MISSING_JEPA_WEIGHT', self.run_audit()['errors'])

    def test_history_inconsistent_with_disabled_objective_rejected(self):
        self.doc['metrics']['loss_history'] = [{'step': 1, 'ce': .1, 'anchor_kl': 0., 'jepa': .4}]
        self.save()
        self.assertIn('JEPA_LOSS_RECORDED_WHILE_DISABLED', self.run_audit()['errors'])

    def test_zero_step_or_empty_reported_history_rejected(self):
        for history in ([], [{'step': 0, 'ce': .1, 'anchor_kl': 0., 'jepa': None}]):
            with self.subTest(history=history):
                self.doc['metrics']['loss_history'] = history
                self.save()
                self.assertEqual(self.run_audit()['status'], 'INPUT_REJECTED')

    def test_matching_hashes_do_not_hide_invalid_run_configuration(self):
        self.doc['metrics']['jepa_weight'] = -1
        self.save()
        self.bind()
        report = self.run_audit(True)
        self.assertTrue(report['input_binding_matches'])
        self.assertEqual(report['status'], 'INPUT_REJECTED')

    def test_external_ema_or_gradient_claim_never_migrates_to_this_path(self):
        self.doc.update(ema_evidence={'pass': True, 'path': 'predictor_worker'}, gradient_evidence={'pass': True})
        self.save()
        report = self.run_audit()
        self.assertFalse(report['source_mechanism']['target_ema_update'])
        self.assertEqual(report['jepa_component_gradient_contribution'], 'UNMEASURED')

    def test_cli_rejects_malformed_json_without_disclosing_contents(self):
        self.manifest.write_text('{"private": "secret", "metrics": NaN}')
        run = subprocess.run([sys.executable, audit.__file__, '--trainer', str(self.trainer), '--manifest', str(self.manifest)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertNotIn('secret', run.stdout + run.stderr)
        self.assertEqual(json.loads(run.stdout)['status'], 'INPUT_REJECTED')

    def test_duplicate_keys_rejected(self):
        self.manifest.write_text('{"metrics": {}, "metrics": {}}')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.run_audit()

    def test_cli_rejects_nan_cosine_with_valid_json_output(self):
        self.doc['metrics']['body_jepa_cos_after'] = float('nan')
        self.save()
        run = subprocess.run([sys.executable, audit.__file__, '--trainer', str(self.trainer), '--manifest', str(self.manifest)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertIn('INVALID_OR_MISSING_COSINE', json.loads(run.stdout)['errors'])

    def test_real_historical_run_shows_gain_without_jepa_weight(self):
        report = audit.audit(TRAINER, HISTORICAL)
        self.assertEqual(report['status'], 'AUDIT_REVIEW_ONLY')
        self.assertEqual(report['reported_run']['jepa_configuration'], 'DISABLED')
        self.assertGreater(report['reported_run']['cosine_delta'], 0.)
        self.assertFalse(report['historical_run_source_verified'])

    def test_read_only_repeated_audit_preserves_inputs_and_directory(self):
        before = {p.name: p.read_bytes() for p in self.home.iterdir()}
        self.assertEqual(self.run_audit(), self.run_audit())
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.home.iterdir()})


if __name__ == '__main__':
    unittest.main()
