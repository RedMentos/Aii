"""Run 14: preregistered LP3 JSON protocol types, software/synthetic only.

These are adversarial mutations of a locally fabricated attempt, NOT native
model results. Each mutation is consistent across manifest/report/seed files.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


class TestRun14ProtocolTypes(unittest.TestCase):
    def setUp(self):
        from test_lp3_closed_evidence_audit import TestLP3EvidenceAudit
        self.fixture = TestLP3EvidenceAudit
        self.fixture.setUp(self)
        from test_lp3_closed_evidence_audit import audit
        self.auditor = audit

    def save(self):
        self.fixture.save(self)

    def assert_invalid(self, pattern):
        self.save()
        with self.assertRaisesRegex(self.auditor.EvidenceError, pattern):
            self.auditor.audit(self.run)

    def test_steps_float_is_not_registered_integer(self):
        self.manifest['params']['steps'] = 30.0
        self.assert_invalid('protocol')

    def test_items_float_is_not_registered_integer(self):
        self.manifest['params']['items'] = 16.0
        self.assert_invalid('protocol')

    def test_holdout_float_is_not_registered_integer(self):
        self.manifest['params']['holdout'] = 48.0
        self.assert_invalid('protocol')

    def test_seed_list_float_is_not_registered_integer(self):
        self.manifest['params']['seeds'][0] = 31.0
        self.assert_invalid('protocol')

    def test_row_seed_float_is_not_registered_integer(self):
        from test_lp3_closed_evidence_audit import write
        self.rows[0]['seed'] = 31.0
        write(self.run / 'seed-31.json', self.rows[0])
        write(self.run / 'report.json', {**self.manifest, 'rows': self.rows,
                                        'verdict': self.auditor.verdict(self.rows)})
        with self.assertRaisesRegex(self.auditor.EvidenceError, 'seed'):
            self.auditor.audit(self.run)

    def test_float_encoded_temperature_int_is_not_registered_float(self):
        # 0.1 cannot be an integer, but the same typed invariant is checked
        # for all real-valued knobs; 0.0/0 integer substitutions would pass
        # equality for some other protocols and must not be allowed here.
        self.manifest['params']['temperature'] = 0
        self.assert_invalid('protocol')

    def test_seed_row_boolean_is_not_integer(self):
        self.rows[0]['seed'] = True
        self.assert_invalid('seed')

    def test_unmodified_registered_attempt_passes(self):
        self.save()
        result = self.auditor.audit(self.run)
        self.assertEqual(result['audit'], 'STRUCTURAL_PASS')
        self.assertFalse(result['candidate_claim_structurally_eligible'])


if __name__ == '__main__':
    unittest.main()
