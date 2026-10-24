"""Run 13 adversarial evidence-schema review; synthetic fixtures only."""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


class TestRun13Review(unittest.TestCase):
    def setUp(self):
        from test_lp3_closed_evidence_audit import TestLP3EvidenceAudit
        self.fixture = TestLP3EvidenceAudit
        self.fixture.setUp(self)

    @property
    def auditor(self):
        from test_lp3_closed_evidence_audit import audit
        return audit

    def save(self):
        self.fixture.save(self)

    def test_manifest_cannot_add_unsupported_gate_claim(self):
        self.manifest['canonical_architecture_complete'] = True
        self.save()
        with self.assertRaisesRegex(self.auditor.EvidenceError, 'manifest fields'):
            self.auditor.audit(self.run)

    def test_seed_cannot_add_unregistered_native_claim(self):
        self.rows[0]['redmi_measured'] = True
        self.save()
        with self.assertRaisesRegex(self.auditor.EvidenceError, 'row fields'):
            self.auditor.audit(self.run)

    def test_loss_cannot_add_unregistered_training_metric(self):
        self.rows[0]['good_loss']['gradient_attribution'] = 1.0
        self.save()
        with self.assertRaisesRegex(self.auditor.EvidenceError, 'loss fields'):
            self.auditor.audit(self.run)

    def test_unknown_attempt_file_is_not_closed(self):
        (self.run / 'report-unsigned-copy.json').write_text('{"verdict":"PASS"}')
        with self.assertRaisesRegex(self.auditor.EvidenceError, 'unregistered attempt entries'):
            self.auditor.audit(self.run)

    def test_snapshot_binding_cannot_add_unverified_asset_claim(self):
        self.manifest['snapshot_binding']['upstream_assets_verified'] = True
        self.save()
        with self.assertRaisesRegex(self.auditor.EvidenceError, 'snapshot binding fields'):
            self.auditor.audit(self.run)

    def test_report_cannot_add_unregistered_gate_claim(self):
        report = self.run / 'report.json'
        obj = json.loads(report.read_text())
        obj['b3_l1_gate_pass'] = True
        report.write_text(json.dumps(obj))
        with self.assertRaisesRegex(self.auditor.EvidenceError, 'report fields'):
            self.auditor.audit(self.run)

    def test_nonfinite_exponent_is_rejected_even_when_json_parser_accepts(self):
        # json.loads('1e999') returns float('inf'), bypassing parse_constant.
        self.assertEqual(json.loads('1e999'), float('inf'))
        self.rows[0]['good_loss']['initial_nce'] = float('inf')
        self.save()
        for path in (self.run / 'seed-31.json', self.run / 'report.json'):
            path.write_text(path.read_text().replace('Infinity', '1e999'))
        with self.assertRaisesRegex(self.auditor.EvidenceError, 'nonfinite JSON float'):
            self.auditor.audit(self.run)

    def test_valid_runner_schema_still_passes(self):
        result = self.auditor.audit(self.run)
        self.assertEqual(result['audit'], 'STRUCTURAL_PASS')
        self.assertFalse(result['candidate_claim_structurally_eligible'])


if __name__ == '__main__':
    unittest.main()
