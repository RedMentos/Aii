"""Independent synthetic evidence fixtures; no model/Redmi assertions."""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'lp3_closed_evidence_audit.py'
spec = importlib.util.spec_from_file_location('lp3_audit', SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def write(path, obj):
    path.write_text(json.dumps(obj, sort_keys=True, indent=2) + '\n')


class TestLP3EvidenceAudit(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.root / 'run'
        self.run.mkdir()
        values = [f'Fictional answer {i}' for i in range(16)]
        expected = [x for v in values for x in (v, v)] + values
        self.manifest = {'schema': 'V13_LP3_MEMORY_KEY_V1', 'params': copy.deepcopy(audit.PARAMS),
                         'master_sha256': audit.PINNED_WEIGHT, 'runtime_enabled': False,
                         'phone_measured': False, 'body_jepa_gate_pass': False,
                         'step2_gate_pass': False, 'script_sha256': 'f' * 64,
                         'lp2_fixture_sha256': 'e' * 64,
                         'snapshot_binding': {'revision': '55e5a53e8637c4522a0577040fe68682db3fbbb6',
                                              'assets_sha256': {'model.safetensors': audit.PINNED_WEIGHT},
                                              'fixture_dependencies_sha256': {'lora_bench.py': 'd' * 64}}}
        self.rows = []
        for seed in audit.SEEDS:
            outputs = {'raw': expected[:], 'predicted': expected[:], 'wrong_trained': expected[:],
                       'value_shift': expected[:], 'zero_intervention': [None] * 48}
            row = {'seed': seed, 'expected': expected[:], 'outputs': outputs,
                   'near_outputs': {'raw': [None] * 13, 'predicted': [None] * 13},
                   'near_raw_nonabstain': 0, 'near_pred_nonabstain': 0,
                   'good_loss': {'steps': 30, 'initial_nce': 2.5, 'final_nce': 0.2},
                   'wrong_loss': {'steps': 30, 'initial_nce': 2.5, 'final_nce': 0.2}}
            for arm, out in outputs.items():
                row[arm] = {'correct': sum(x == y for x, y in zip(expected, out)),
                            'abstain': sum(x is None for x in out), 'total': 48}
            self.rows.append(row)
        self.save()

    def save(self):
        write(self.run / 'run_manifest.json', self.manifest)
        for row in self.rows:
            write(self.run / f"seed-{row['seed']}.json", row)
        write(self.run / 'report.json', {**self.manifest, 'rows': self.rows,
                                        'verdict': audit.verdict(self.rows)})

    def test_valid_synthetic_cohort_structural_only(self):
        r = audit.audit(self.run)
        self.assertEqual(r['audit'], 'STRUCTURAL_PASS')
        self.assertEqual(r['anchor'], 'UNANCHORED_STRUCTURAL_ONLY')
        self.assertEqual(r['reported_verdict'], 'LP3_MEMORY_KEY_NOT_SUPPORTED')

    def test_seed_and_report_disagree(self):
        row = self.rows[0]
        row['outputs']['raw'][0] = None
        write(self.run / 'seed-31.json', row)
        with self.assertRaisesRegex(audit.EvidenceError, 'differs'):
            audit.audit(self.run)

    def test_duplicate_json_key_refused(self):
        (self.run / 'run_manifest.json').write_text('{"schema":1,"schema":2}')
        with self.assertRaisesRegex(audit.EvidenceError, 'duplicate'):
            audit.audit(self.run)

    def test_forged_report_verdict_refused(self):
        r = json.loads((self.run / 'report.json').read_text())
        r['verdict'] = 'LP3_MEMORY_KEY_CANDIDATE_SUPPORTED_ONLY'
        write(self.run / 'report.json', r)
        with self.assertRaisesRegex(audit.EvidenceError, 'verdict'):
            audit.audit(self.run)

    def test_coordinated_row_edit_detected_by_receipt(self):
        receipt = self.root / 'receipt.json'
        write(receipt, audit.receipt_for(self.run))
        anchor = audit.digest(receipt)
        audit.audit(self.run, receipt=receipt, receipt_sha256=anchor)
        self.rows[0]['good_loss']['final_nce'] = 0.5
        self.save()
        with self.assertRaisesRegex(audit.EvidenceError, 'receipt file hash mismatch'):
            audit.audit(self.run, receipt=receipt, receipt_sha256=anchor)

    def test_tampered_receipt_detected_by_external_sha(self):
        receipt = self.root / 'receipt.json'
        write(receipt, audit.receipt_for(self.run))
        anchor = audit.digest(receipt)
        receipt.write_text(receipt.read_text() + ' ')
        with self.assertRaisesRegex(audit.EvidenceError, 'external SHA'):
            audit.audit(self.run, receipt=receipt, receipt_sha256=anchor)

    def test_missing_seed_refused(self):
        (self.run / 'seed-37.json').unlink()
        with self.assertRaisesRegex(audit.EvidenceError, 'missing/nonregular'):
            audit.audit(self.run)

    def test_failed_marker_refused(self):
        (self.run / 'failed-seed-37.json').write_text('{}')
        with self.assertRaisesRegex(audit.EvidenceError, 'failed seed'):
            audit.audit(self.run)

    def test_wrong_expected_order_refused(self):
        self.rows[0]['expected'][32], self.rows[0]['expected'][33] = self.rows[0]['expected'][33], self.rows[0]['expected'][32]
        self.save()
        with self.assertRaisesRegex(audit.EvidenceError, 'ordering'):
            audit.audit(self.run)

    def test_zero_arm_must_abstain(self):
        self.rows[0]['outputs']['zero_intervention'][0] = self.rows[0]['expected'][0]
        self.rows[0]['zero_intervention'] = {'correct': 1, 'abstain': 47, 'total': 48}
        self.save()
        with self.assertRaisesRegex(audit.EvidenceError, 'zero intervention'):
            audit.audit(self.run)

    def test_wrong_source_hash_refused(self):
        source = self.root / 'candidate.py'
        source.write_text('not the registered script')
        with self.assertRaisesRegex(audit.EvidenceError, 'local source hash'):
            audit.audit(self.run, source=source)

    def test_symlink_seed_refused(self):
        p = self.run / 'seed-31.json'
        original = self.root / 'elsewhere.json'
        p.rename(original)
        p.symlink_to(original)
        with self.assertRaisesRegex(audit.EvidenceError, 'nonregular'):
            audit.audit(self.run)

    def test_out_of_bank_answer_refused(self):
        self.rows[0]['outputs']['predicted'][0] = 'forged answer'
        self.save()
        with self.assertRaisesRegex(audit.EvidenceError, 'out-of-bank'):
            audit.audit(self.run)

    def test_fixture_binding_catches_consistent_label_rewrite(self):
        source = self.root / 'lp3.py'
        lp2 = self.root / 'lp2.py'
        lora = self.root / 'lora.py'
        source.write_text('HARDER = '+repr(tuple((i, 'prompt') for i in range(16)))+'\n')
        lp2.write_text('FACTS_V2 = '+repr([(f'Q{i}', f'Fictional answer {i}', []) for i in range(8,16)])+'\nHELDOUT = '+repr([(i,'prompt') for i in range(16) for _ in range(2)])+'\n')
        lora.write_text('FACTS = '+repr([(f'Q{i}', f'Fictional answer {i}', []) for i in range(8)])+'\n')
        self.manifest['script_sha256'] = audit.digest(source)
        self.manifest['lp2_fixture_sha256'] = audit.digest(lp2)
        self.manifest['snapshot_binding']['fixture_dependencies_sha256']['lora_bench.py'] = audit.digest(lora)
        self.save()
        self.assertTrue(audit.audit(self.run, source=source, lp2=lp2, lora=lora)['local_source_fixture_consistent'])
        self.rows[0]['expected'][0] = 'Fictional answer 1'
        self.save()
        with self.assertRaisesRegex(audit.EvidenceError, 'source fixtures'):
            audit.audit(self.run, source=source, lp2=lp2, lora=lora)

    def test_protocol_mismatch_refused(self):
        self.manifest['params']['steps'] = 31
        self.save()
        with self.assertRaisesRegex(audit.EvidenceError, 'protocol'):
            audit.audit(self.run)

if __name__ == '__main__':
    unittest.main()