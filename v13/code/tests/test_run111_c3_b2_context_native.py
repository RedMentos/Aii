"""Run111 registered fixture, strict scorer and real Store/Context OS preflight."""
from pathlib import Path
import tempfile
import unittest

from scripts.run111_c3_b2_context_native import fixture, run, score, FIXTURE_SHA

FIXTURE = Path(__file__).resolve().parents[1] / 'docs/fixtures/RUN111_C3_PRIOR_RULES_SEED881.json'


class Run111C3B2Context(unittest.TestCase):
    def test_frozen_fixture_four_disjoint_source_pairs(self):
        rows = fixture(FIXTURE)
        self.assertEqual([r['id'] for r in rows], ['Tilia', 'Zephyr', 'Oriole', 'Sable'])
        self.assertEqual([r['expected'] for r in rows], ['B', 'B', 'A', 'NONE'])
        self.assertTrue(all(r['quote'] in r['prior'] for r in rows))

    def test_fixture_byte_mutation_refused(self):
        with tempfile.TemporaryDirectory() as t:
            changed = Path(t) / 'mutated.json'
            changed.write_bytes(FIXTURE.read_bytes().replace(b'173 credits', b'174 credits', 1))
            with self.assertRaises(ValueError):
                fixture(changed)

    def test_strict_json_score_refuses_duplicates_and_wrong_schema(self):
        self.assertEqual(score('{"choice":"B"}', 'B')['correct'], 1)
        for raw in ('{"choice":"A","choice":"B"}', '{"choice":true}',
                    '{"choice":"B","oracle":"B"}', '{"choice":"UNKNOWN"}',
                    '{"choice":"B"} extra', '{"choice":NaN}', 'B'):
            self.assertEqual(score(raw, 'B')['correct'], 0, raw)

    def test_model_free_real_context_os_preflight_both_widths(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            report = run(FIXTURE, root / 'work', root / 'evidence')
            self.assertEqual(report['status'], 'MODEL_FREE_PREFLIGHT_PASS',
                             report.get('error'))
            self.assertFalse(report['native_c3'])
            self.assertTrue(report['synthetic_b2'])
            self.assertEqual(len(report['rows']), 8)
            for row in report['rows']:
                self.assertEqual(row['status'], 'RECORDED', row.get('error'))
                self.assertEqual(row['plan_mode'], 'SHADOW')
                self.assertTrue(row['closed_store_ok'])
                self.assertTrue(row['no_live_output'])
                self.assertFalse(row['native_final'])
                self.assertFalse(row['process_reaped'])
                source = {f['id']: f for f in fixture(FIXTURE)}[row['id']]
                self.assertEqual(row['verified_quote'],
                                 source['prior'] if row['arm'] == 'WIDE_400' else source['quote'])
                content = '\n'.join(m['content'] for m in row['messages'])
                if row['arm'] == 'WIDE_400':
                    self.assertIn('Maximum deadline:', content)
                    self.assertIn('Required local-only:', content)
                else:
                    self.assertNotIn('Maximum deadline:', content)
                    self.assertNotIn('Required local-only:', content)
            self.assertEqual(report['step2'], 'UTILITY_FAIL')
            self.assertEqual(report['jepa_weight'], 0)
            self.assertFalse(report['whole_system_complete'])


if __name__ == '__main__':
    unittest.main()
