"""Adversarial, software-only cross-review of the PR47 LP3 closed-evidence auditor."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


class TestRun12Review(unittest.TestCase):
    def setUp(self):
        from test_lp3_closed_evidence_audit import TestLP3EvidenceAudit
        self._fixture = TestLP3EvidenceAudit
        self._fixture.setUp(self)

    def save(self):
        self._fixture.save(self)

    def test_partial_source_fixture_inputs_fail_closed(self):
        source = self.root / 'candidate.py'
        source.write_text('fake')
        self.manifest['script_sha256'] = self.audit_module.digest(source)
        self.save()
        with self.assertRaisesRegex(self.audit_module.EvidenceError, 'all three'):
            self.audit_module.audit(self.run, source=source)

    def test_negative_training_loss_is_invalid(self):
        self.rows[0]['good_loss']['final_nce'] = -0.1
        self.save()
        with self.assertRaisesRegex(self.audit_module.EvidenceError, 'loss'):
            self.audit_module.audit(self.run)

    def test_boolean_training_loss_is_invalid(self):
        self.rows[0]['wrong_loss']['initial_nce'] = True
        self.save()
        with self.assertRaisesRegex(self.audit_module.EvidenceError, 'loss'):
            self.audit_module.audit(self.run)

    def test_boolean_aggregate_is_invalid(self):
        self.rows[0]['near_raw_nonabstain'] = False  # bool == 0 in Python
        self.save()
        with self.assertRaisesRegex(self.audit_module.EvidenceError, 'near-miss aggregate'):
            self.audit_module.audit(self.run)

    def test_reported_positive_unanchored_is_not_auditor_supported(self):
        for row in self.rows:
            row['outputs']['raw'] = [None] * 48
            row['outputs']['wrong_trained'] = [None] * 48
            row['outputs']['value_shift'] = [None] * 48
            for name in ('raw', 'wrong_trained', 'value_shift'):
                row[name] = {'correct': 0, 'abstain': 48, 'total': 48}
        self.save()
        self.assertEqual(self.audit_module.verdict(self.rows), 'LP3_MEMORY_KEY_CANDIDATE_SUPPORTED_ONLY')
        result = self.audit_module.audit(self.run)
        self.assertEqual(result['reported_verdict'], 'LP3_MEMORY_KEY_CANDIDATE_SUPPORTED_ONLY')
        self.assertFalse(result['candidate_claim_structurally_eligible'])
        self.assertEqual(result['evidence_grade'], 'STRUCTURAL_ONLY')

    def test_positive_requires_source_fixtures_and_supplied_receipt(self):
        from test_lp3_closed_evidence_audit import write
        for row in self.rows:
            for name in ('raw', 'wrong_trained', 'value_shift'):
                row['outputs'][name] = [None] * 48
                row[name] = {'correct': 0, 'abstain': 48, 'total': 48}
        source, lp2, lora = (self.root / n for n in ('lp3.py', 'lp2.py', 'lora.py'))
        source.write_text('HARDER = '+repr(tuple((i, 'prompt') for i in range(16)))+'\n')
        lp2.write_text('FACTS_V2 = '+repr([(f'Q{i}', f'Fictional answer {i}', []) for i in range(8,16)])+'\nHELDOUT = '+repr([(i,'prompt') for i in range(16) for _ in range(2)])+'\n')
        lora.write_text('FACTS = '+repr([(f'Q{i}', f'Fictional answer {i}', []) for i in range(8)])+'\n')
        self.manifest['script_sha256'] = self.audit_module.digest(source)
        self.manifest['lp2_fixture_sha256'] = self.audit_module.digest(lp2)
        self.manifest['snapshot_binding']['fixture_dependencies_sha256']['lp2_assignment_objective.py'] = self.audit_module.digest(lp2)
        self.manifest['snapshot_binding']['fixture_dependencies_sha256']['lora_bench.py'] = self.audit_module.digest(lora)
        self.save()
        kw = dict(source=source, lp2=lp2, lora=lora)
        result = self.audit_module.audit(self.run, **kw)
        self.assertFalse(result['candidate_claim_structurally_eligible'])
        self.assertEqual(result['evidence_grade'], 'SOURCE_FIXTURES_VERIFIED_UNANCHORED')
        receipt = self.root / 'external_receipt.json'
        write(receipt, self.audit_module.receipt_for(self.run))
        result = self.audit_module.audit(self.run, receipt=receipt,
                                         receipt_sha256=self.audit_module.digest(receipt), **kw)
        self.assertTrue(result['candidate_claim_structurally_eligible'])
        self.assertEqual(result['evidence'], 'LINUX_FILES_ONLY_NOT_NATIVE_REPRODUCTION')
        self.assertEqual(result['original_gates']['step2'], 'UTILITY_FAIL')

    @property
    def audit_module(self):
        import test_lp3_closed_evidence_audit
        return test_lp3_closed_evidence_audit.audit


if __name__ == '__main__':
    unittest.main()
