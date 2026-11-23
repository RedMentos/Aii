"""Run112 exact disjoint fixture and actual Store/Context OS software preflight."""
from pathlib import Path
import tempfile
import unittest

from scripts.run112_real_b2_to_c3_native import fixture, run
from scripts.run111_c3_b2_context_native import score

FIXTURE = Path(__file__).resolve().parents[1] / 'docs/fixtures/RUN112_REAL_B2_C3_SEED907.json'


class Run112RealB2C3(unittest.TestCase):
    def test_exact_frozen_new_fixture(self):
        row = fixture(FIXTURE)
        self.assertEqual(row['project'], 'Nova')
        self.assertEqual(row['expected'], 'A')
        self.assertIn(row['quote'], row['prior'])
        self.assertNotIn('Tilia', row['current'])

    def test_fixture_mutation_refused(self):
        with tempfile.TemporaryDirectory() as t:
            changed = Path(t) / 'mutated.json'
            changed.write_bytes(FIXTURE.read_bytes().replace(b'162 credits', b'163 credits', 1))
            with self.assertRaises(ValueError):
                fixture(changed)

    def test_native_choice_scorer_is_strict(self):
        self.assertEqual(score('{"choice":"A"}', 'A')['correct'], 1)
        for raw in ('{"choice":"A","choice":"B"}', '{"choice":"B"}',
                    '{"choice":"A","extra":true}', '{"choice":false}',
                    '{"choice":"UNKNOWN"}', 'A'):
            self.assertEqual(score(raw, 'A')['correct'], 0)

    def test_real_store_context_plan_model_free_preflight(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            result = run(FIXTURE, root / 'work', root / 'evidence')
            self.assertEqual(result['status'], 'MODEL_FREE_PREFLIGHT_PASS',
                             result.get('error'))
            self.assertTrue(result['prior_verified_for_c3'])
            self.assertEqual(result['preflight_plan_mode'], 'SHADOW')
            self.assertEqual(result['b2_native_calls'], 0)
            self.assertEqual(result['c3_native_calls'], 0)
            self.assertTrue(result['no_live_output'])
            self.assertTrue(result['closed_store_ok'])
            self.assertFalse(result['output_committed'])
            self.assertFalse(result['whole_system_complete'])


if __name__ == '__main__':
    unittest.main()
