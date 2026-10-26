"""Run560: original Run491 oracle/history binding, model-free negative tests."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import run491_step2_heldout10 as frozen
import run500_step2_stage_map as stages
import run559_offline_review as review


class FrozenFixtureOrigin(unittest.TestCase):
    def setUp(self):
        self.stage = stages.choose(stages.registration(), 'A_s31_p03')
        source = frozen.registration()['fixtures']
        self.fixtures = [copy.deepcopy(f) for f in source
                         if f['id'] in self.stage['fixture_ids']]
        self.assertEqual([f['id'] for f in self.fixtures],
                         ['Boreal', 'Cascade'])

    def test_original_source_pair_passes_and_returns_original_oracles(self):
        result = review.frozen_oracles(self.stage, copy.deepcopy(self.fixtures))
        self.assertEqual(result, {f['id']: f['oracle'] for f in self.fixtures})
        self.assertEqual(stages.digest(self.fixtures),
                         self.stage['fixture_sha256'])

    def test_self_consistent_forged_oracle_fails_before_scoring(self):
        # A modified oracle plus a modified model score could otherwise agree.
        forged = copy.deepcopy(self.fixtures)
        forged[0]['oracle']['action'] = 'B'
        with self.assertRaisesRegex(ValueError, 'NATIVE_FIXTURE_ORACLE_OR_HISTORY_DRIFT'):
            review.frozen_oracles(self.stage, forged)

    def test_history_and_rules_source_mutation_refused(self):
        for field in ('history', 'rules', 'current'):
            with self.subTest(field=field):
                forged = copy.deepcopy(self.fixtures)
                if field == 'history':
                    forged[0]['history'][0] += ' invented extra sentence'
                elif field == 'rules':
                    forged[0]['rules']['budget'] += 1
                else:
                    forged[0]['current'] += ' changed'
                with self.assertRaisesRegex(ValueError, 'NATIVE_FIXTURE_ORACLE_OR_HISTORY_DRIFT'):
                    review.frozen_oracles(self.stage, forged)

    def test_order_missing_duplicate_and_extra_fixture_refused(self):
        for forged in (
            list(reversed(copy.deepcopy(self.fixtures))),
            copy.deepcopy(self.fixtures[:1]),
            copy.deepcopy(self.fixtures[:1]) * 2,
            copy.deepcopy(self.fixtures) + [copy.deepcopy(self.fixtures[0])],
        ):
            with self.subTest(ids=[x['id'] for x in forged]):
                with self.assertRaisesRegex(ValueError, 'NATIVE_FIXTURE_ORACLE_OR_HISTORY_DRIFT'):
                    review.frozen_oracles(self.stage, forged)

    def test_type_change_refused_even_if_python_numeric_equality_holds(self):
        forged = copy.deepcopy(self.fixtures)
        old = forged[0]['oracle']['options'][0]['cost']
        self.assertIs(type(old), int)
        forged[0]['oracle']['options'][0]['cost'] = float(old)
        self.assertTrue(forged == self.fixtures)  # Python's 8 == 8.0
        with self.assertRaisesRegex(ValueError, 'NATIVE_FIXTURE_ORACLE_OR_HISTORY_DRIFT'):
            review.frozen_oracles(self.stage, forged)


if __name__ == '__main__':
    unittest.main()
