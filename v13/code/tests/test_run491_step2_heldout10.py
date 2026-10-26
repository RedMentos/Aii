"""Run491: source-only held-out ten-episode preregistration and tamper tests."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import run491_step2_heldout10 as m


class Heldout10Preflight(unittest.TestCase):
    def test_exact_registered_hash_and_1050_planned_rows(self):
        result = m.registration()
        self.assertEqual(result['fixture_sha256'], m.FIXTURE_SHA256)
        self.assertEqual(hashlib.sha256(m.canonical(result['fixtures'])).hexdigest(),
                         'c434a5765ed85b7c51022c5aaea0ba4c3150ef0f1490f466b4a8833e41b44c63')
        self.assertEqual(len(result['fixtures']), 10)
        self.assertEqual(result['planned_native_consumer_rows'], 5 * 3 * 10 * 7)
        self.assertIs(result['native_executed'], False)
        self.assertIs(result['canonical_gate_pass'], False)
        self.assertEqual(result['step2_exit'], 'UTILITY_FAIL')

    def test_six_split_two_rule_two_detail(self):
        rows = m.fixtures()
        self.assertEqual([r['type'] for r in rows].count('SPLIT'), 6)
        self.assertEqual([r['type'] for r in rows].count('RULE'), 2)
        self.assertEqual([r['type'] for r in rows].count('DETAIL'), 2)
        self.assertEqual([r['oracle']['action'] for r in rows].count('NONE'), 1)
        self.assertTrue(m.validate(rows))

    def test_roles_have_different_exact_source_windows(self):
        for row in m.fixtures():
            with self.subTest(project=row['id']):
                if row['type'] in ('SPLIT', 'DETAIL'):
                    self.assertNotIn('Option A:', row['history'][2][:240])
                    self.assertIn('Option A:', row['history'][2][:600])
                    self.assertIn('Option B:', row['history'][2][:600])
                if row['type'] in ('SPLIT', 'RULE'):
                    self.assertIn('Budget ', row['history'][0])
                    self.assertNotIn('Budget ', row['current'])

    def test_mutation_or_missing_episode_rejected(self):
        original = m.fixtures()
        bad = copy.deepcopy(original)
        bad[0]['rules']['budget'] += 1
        with self.assertRaisesRegex(ValueError, 'FROZEN_FIXTURE_BYTES_CHANGED'):
            m.validate(bad)
        with self.assertRaisesRegex(ValueError, 'TEN_EPISODES_REQUIRED'):
            m.validate(original[:-1])

    def test_old_fixture_names_not_reused(self):
        old = {'Kestrel', 'Lumen', 'Meridian', 'Nimbus', 'Orion', 'Perseus',
               'Quasar', 'Rigel', 'Sirius', 'Tycho',
               'Alder', 'Beacon', 'Cypress', 'Delta', 'Ember', 'Fable'}
        self.assertFalse(old & {r['id'] for r in m.fixtures()})

    def test_registered_seeds_and_model_hashes(self):
        self.assertEqual(m.SEEDS, (31, 32, 33))
        self.assertEqual(len(set(m.MODEL_SHA256.values())), 3)
        self.assertTrue(all(len(h) == 64 for h in m.MODEL_SHA256.values()))
        self.assertEqual(m.registration()['model_sha256_expected_not_retrieved'], m.MODEL_SHA256)

    def test_cli_refuses_overwrite_and_never_claims_native(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'registered.json'
            cmd = [sys.executable, str(ROOT / 'scripts' / 'run491_step2_heldout10.py'),
                   '--output', str(out)]
            first = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            content = out.read_bytes()
            report = json.loads(content)
            self.assertEqual(report['status'], 'SOURCE_ONLY_PREREG_VALIDATED_NO_NATIVE')
            self.assertIs(report['native_executed'], False)
            second = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn('REFUSE_OVERWRITE_PREVIOUS_REGISTRATION', second.stderr)
            self.assertEqual(out.read_bytes(), content)


if __name__ == '__main__':
    unittest.main()
