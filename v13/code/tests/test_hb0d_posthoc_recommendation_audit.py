"""HB0d synthetic-only parser and closed-evidence verification tests."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import hb0d_posthoc_recommendation_audit as audit
from scripts import hb0_c3_receiver_native_pilot as pilot
from scripts import hb0_split_information_cohort as hb0


class PosthocExtractor(unittest.TestCase):
    def test_explicit_decisions(self):
        examples = {
            'I recommend Option A.': 'A',
            'I would choose B.': 'B',
            'Therefore, select Option A.': 'A',
            'Option B is the best choice.': 'B',
            'My recommendation is Option B.': 'B',
            'Final answer: A.': 'A',
            'Neither option is eligible.': 'NONE',
            'Both options are ineligible.': 'NONE',
            'UNKNOWN: rules missing.': 'UNKNOWN',
            "I can't decide.": 'UNKNOWN',
            'I recommend A. I recommend A.': 'A',
            'I recommend A. I recommend B.': 'AMBIGUOUS',
        }
        for text, expected in examples.items():
            with self.subTest(text=text):
                got = audit.extract(text)
                self.assertEqual(got['action'], expected)
                for start, end in got['spans']:
                    self.assertGreaterEqual(start, 0)
                    self.assertLessEqual(end, len(text))

    def test_no_false_commit_on_description_negation_or_hypothesis(self):
        cases = [
            'Option A costs 5, Option B costs 7.',
            'Do not choose Option A.',
            'I would choose A if the price were lower.',
            'I recommend A or B.',
            'I recommend A, but actually B is preferable.',
            '"I recommend A" is a quote.',
            '> I recommend B',
            'Would you choose A?',
            'Option A is eligible. Option B is not.',
            'Maybe choose Option B.',
            'The user asked me to recommend A.',
            'Option A is the best choice?',
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertEqual(audit.extract(text)['action'], 'UNPARSEABLE')
        for value in (None, 7, [], 'A' * 50001):
            self.assertEqual(audit.extract(value)['action'], 'UNPARSEABLE')


class PosthocEvidence(unittest.TestCase):
    def make_evidence(self, root):
        rows = hb0.fixtures()
        fixture = hb0._sha(rows)
        inputs = pilot.plan(rows, fixture)
        records = [{
            'id': p['id'], 'arm': p['arm'], 'status': 'FINAL',
            'input_sha256': pilot.sha(pilot.canonical(p['messages'])),
            'output': 'The best option is A.', 'duration_s': 1.0,
            'metrics': {'status': 'FINAL'}, 'model_sha256': pilot.MODEL_SHA,
            'model_called': True, 'native_calls': 1, 'seed': pilot.SEED,
        } for p in inputs]
        score = pilot.score(records, rows, fixture)
        raw = {'status': 'RECORDED_LINUX_NATIVE_C3_DIAGNOSTIC_NO_GATE',
               'rows': records, 'model_sha256': pilot.MODEL_SHA,
               'fixture_sha256': fixture}
        raw_bytes = audit.canonical(raw)
        score_bytes = audit.canonical(score)
        inputs_bytes = audit.canonical(inputs)
        hashes = [audit.sha(raw_bytes), audit.sha(score_bytes)]
        receipt = {'status': raw['status'], 'raw_sha256': hashes[0],
                   'score_sha256': hashes[1], 'input_sha256': audit.sha(inputs_bytes),
                   'model_sha256': pilot.MODEL_SHA,
                   'model_sha256_after': pilot.MODEL_SHA,
                   'runner_sha256_before': 'x', 'runner_sha256_after': 'x',
                   'process_reaped': True, 'age_authority': 0,
                   'jepa_weight': 0, 'weight_updates': False,
                   'canonical_gate_pass': False, 'redmi_measured': False,
                   'recorded_calls': 24}
        for name, data in [('RAW.json', raw_bytes), ('SCORE.json', score_bytes),
                           ('INPUTS.json', inputs_bytes),
                           ('RECEIPT.json', audit.canonical(receipt))]:
            (root / name).write_bytes(data)
        return hashes, fixture

    def test_synthetic_audit_keeps_original_scoring_and_negative_gates(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            hashes, fixture = self.make_evidence(root)
            with patch.object(audit, 'PARENT_RAW', hashes[0]), \
                 patch.object(audit, 'PARENT_SCORE', hashes[1]):
                report = audit.audit(root, hashes[0], hashes[1], fixture)
            self.assertEqual(report['rows'], 24)
            self.assertEqual(sum(v['explicit'] for v in report['per_arm'].values()), 24)
            self.assertEqual(sum(v['exact'] + v['wrong_committed'] for v in report['per_arm'].values()), 24)
            self.assertEqual(sum(v['unparseable'] for v in report['original_per_arm'].values()), 24)
            self.assertFalse(report['canonical_gate_pass'])
            self.assertEqual(report['step2_status'], 'UTILITY_FAIL')
            self.assertEqual(report['b3_status'], 'FAIL')
            self.assertEqual(report['jepa_weight'], 0)
            self.assertFalse(report['redmi_measured'])
            self.assertNotIn('The best option', json.dumps(report))
            self.assertEqual(len({(r['id_sha256'], r['arm']) for r in report['details']}), 24)

    def test_tampered_raw_or_score_fails_closed(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            hashes, fixture = self.make_evidence(root)
            with patch.object(audit, 'PARENT_RAW', hashes[0]), \
                 patch.object(audit, 'PARENT_SCORE', hashes[1]):
                (root / 'RAW.json').write_bytes(b'{}')
                with self.assertRaisesRegex(ValueError, 'HB0D_ORIGINAL_HASH_RED'):
                    audit.audit(root, hashes[0], hashes[1], fixture)
            hashes, fixture = self.make_evidence(root)
            score = json.loads((root / 'SCORE.json').read_bytes())
            score['rows'] = 23
            score_bytes = audit.canonical(score)
            (root / 'SCORE.json').write_bytes(score_bytes)
            receipt = json.loads((root / 'RECEIPT.json').read_bytes())
            receipt['score_sha256'] = audit.sha(score_bytes)
            (root / 'RECEIPT.json').write_bytes(audit.canonical(receipt))
            with patch.object(audit, 'PARENT_RAW', hashes[0]), \
                 patch.object(audit, 'PARENT_SCORE', receipt['score_sha256']):
                with self.assertRaisesRegex(ValueError, 'HB0D_ORIGINAL_SCORE_DRIFT_RED'):
                    audit.audit(root, hashes[0], receipt['score_sha256'], fixture)

    def test_unapproved_external_pin_refused(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'HB0D_EXTERNAL_PIN_RED'):
                audit.audit(Path(tmp), '0' * 64, '1' * 64, audit.FIXTURE)


if __name__ == '__main__':
    unittest.main()
