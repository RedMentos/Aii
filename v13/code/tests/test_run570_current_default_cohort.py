"""Run570 prospective new disjoint CURRENT/LEGACY source-only cohort tests."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import run570_current_default_cohort as cohort


class CurrentDefaultDisjointSource(unittest.TestCase):
    def test_plan_is_exact_disjoint_84_rows_and_reproducible(self):
        a = cohort.registration()
        b = cohort.registration()
        self.assertEqual(cohort.canonical(a), cohort.canonical(b))
        self.assertEqual(a['status'], 'SOURCE_ONLY_NEW_COHORT_NOT_EXECUTED')
        self.assertEqual(a['planned_native_consumer_rows'], 84)
        self.assertEqual(len(a['row_keys']), len(set(a['row_keys'])) == 84)
        self.assertEqual(a['row_keys_sha256'], cohort.digest(a['row_keys']))
        self.assertEqual(a['arms'], ['CURRENT', 'LEGACY'])
        self.assertEqual(a['seed'], 41)
        self.assertEqual(a['native_executed'], False)
        self.assertEqual(a['canonical_gate_pass'], False)
        self.assertEqual(a['step2_exit'], 'UTILITY_FAIL')
        self.assertEqual(a['b3_l1'], 'FAIL')
        self.assertEqual(a['body_jepa'], 'UNAVAILABLE')
        self.assertEqual(a['jepa_weight'], 0)
        self.assertEqual(a['redmi_measured'], False)
        self.assertEqual(a['original_frozen_fixture_sha256'], cohort.frozen.FIXTURE_SHA256)
        self.assertEqual(len(a['source_fixtures']), 6)
        self.assertEqual(set(a['scoring_oracles_not_for_native_messages']),
                         {x[0] for x in cohort.SPECS})
        for row in a['source_fixtures']:
            self.assertEqual(set(row), {'id', 'type', 'history', 'current'})
            self.assertNotIn('oracle', row)
            self.assertNotIn('rules', row)

    def test_exact_config_identity_and_age_safety(self):
        a = cohort.registration()['config_snapshots']
        self.assertEqual(a['CURRENT']['b2_quote_select'], 'pointer')
        self.assertEqual(a['CURRENT']['eligibility_reader'], 'fixed')
        self.assertIs(a['CURRENT']['tool_answer_first'], True)
        self.assertEqual(a['LEGACY']['b2_quote_select'], 'off')
        self.assertEqual(a['LEGACY']['eligibility_reader'], 'c3')
        self.assertIs(a['LEGACY']['tool_answer_first'], False)
        self.assertNotEqual(a['CURRENT'], a['LEGACY'])
        for arm in a.values():
            self.assertEqual(arm['learning_mode'], 'RECORD_ONLY')
            self.assertEqual(arm['system_stage'], 0)
            self.assertIs(arm['latents_enabled'], False)
            self.assertIs(arm['teacher_enabled'], False)
            self.assertEqual(arm['answer_language'], 'en')
            self.assertEqual(arm['b2_control'], 'two_body')

    def test_tampered_source_and_oracle_refused(self):
        rows = [cohort.z2.episode(*spec) for spec in cohort.SPECS]
        cohort.validate_fixtures(rows)
        for mutation in ('source', 'oracle', 'history', 'type'):
            bad = copy.deepcopy(rows)
            if mutation == 'source':
                bad[0]['current'] += ' Budget 1 euros.'
            elif mutation == 'oracle':
                bad[1]['oracle']['action'] = 'A'
            elif mutation == 'history':
                bad[2]['history'][2] += ' changed'
            else:
                bad[3]['type'] = 'SPLIT'
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):
                    cohort.validate_fixtures(bad)

    def test_old_registered_name_overlap_refused(self):
        with patch.object(cohort, 'SPECS',
                          (('Vesper',) + cohort.SPECS[0][1:],) + cohort.SPECS[1:]):
            rows = [cohort.z2.episode(*spec) for spec in cohort.SPECS]
            with self.assertRaisesRegex(ValueError, 'REGISTERED_COHORT_OVERLAP'):
                cohort.validate_fixtures(rows)

    def test_invalid_default_and_legacy_fail_closed(self):
        with patch.dict(cohort.config.DEFAULTS, {'b2_quote_select': 'off'}):
            with self.assertRaisesRegex(ValueError, 'CURRENT_QUOTE_PATH_CHANGED'):
                cohort.configs()
        with patch.dict(cohort.config.LEGACY_QUOTE_PATH, {'eligibility_reader': 'fixed'}):
            with self.assertRaisesRegex(ValueError, 'LEGACY_QUOTE_PATH_CHANGED'):
                cohort.configs()
        with patch.dict(cohort.config.DEFAULTS, {'learning_mode': 'ACTIVE'}):
            with self.assertRaisesRegex(ValueError, 'SAFETY_OR_LANGUAGE_CONFIG_CHANGED'):
                cohort.configs()

    def test_mutated_frozen_registration_refused(self):
        original = cohort.frozen.registration()
        original['fixture_sha256'] = '0' * 64
        with patch.object(cohort.frozen, 'registration', return_value=original):
            with self.assertRaisesRegex(ValueError, 'FROZEN_SOURCE_REGISTRATION_CHANGED'):
                cohort.registration()

    def test_exclusive_output_and_no_native_execute_flag(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'plan.json'
            with patch.object(sys, 'argv', ['run570', '--plan', '--output', str(out)]):
                cohort.main()
            data = json.loads(out.read_text())
            self.assertEqual(data['planned_native_consumer_rows'], 84)
            original = out.read_bytes()
            with patch.object(sys, 'argv', ['run570', '--plan', '--output', str(out)]):
                with self.assertRaises(FileExistsError):
                    cohort.main()
            self.assertEqual(out.read_bytes(), original)
            with patch.object(sys, 'argv', ['run570', '--execute', '--output', str(out)]):
                with self.assertRaises(SystemExit):
                    cohort.main()


if __name__ == '__main__':
    unittest.main()
