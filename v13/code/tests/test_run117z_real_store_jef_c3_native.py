"""Run117Z new disjoint seed1065 real SQLite JEF -> C3 model-free contracts."""
from pathlib import Path
import json
import tempfile
import unittest

from scripts import run117z_real_store_jef_c3_native as pilot
from tests.test_run117s_b2_salient_source_shadow import QuoteRuntime

FIXTURE = Path(__file__).resolve().parents[1] / 'docs/fixtures/RUN117Z_REAL_JEF_NATIVE_SEED1065.json'


def fake_report():
    rows = []
    for r in pilot.fixture(FIXTURE):
        rows.append({'id': r['id'], 'status': 'RECORDED',
                     'closed_store_ok': True, 'no_live_output': True,
                     'arms': [{'arm': a, 'status': 'RECORDED',
                               'native_final': True, 'process_reaped': True,
                               'native_metrics': {'actual_model': pilot.C3_FILE},
                               'score': {'correct': 1}} for a in pilot.ARMS]})
    return {'rows': rows, 'native_c3_calls': 12,
            'deterministic_jef_calls': 6,
            'exploratory_formatter_signal': False}


class Run117ZContracts(unittest.TestCase):
    def test_frozen_fixture_and_independent_oracles(self):
        rows = pilot.fixture(FIXTURE)
        self.assertEqual(len(rows), 6)
        self.assertEqual([r['id'] for r in rows], list(pilot.IDS))
        self.assertEqual([r['oracle'] for r in rows], [
            {'choice': 'A', 'remaining': 50}, {'choice': 'A', 'remaining': 20},
            {'choice': 'B', 'remaining': 20}, {'choice': 'NONE', 'remaining': None},
            {'choice': 'B', 'remaining': 60}, {'choice': 'A', 'remaining': 0}])

    def test_fixture_byte_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'changed.json'
            p.write_bytes(FIXTURE.read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'FROZEN_FIXTURE_SHA_RED'):
                pilot.fixture(p)

    def test_six_real_store_jef_prompts_without_oracle_leak(self):
        for row in pilot.fixture(FIXTURE):
            with self.subTest(row=row['id']):
                with tempfile.TemporaryDirectory() as d:
                    runtime = QuoteRuntime(Path(d) / 'home', row)
                    try:
                        prior = runtime.store.event(runtime.session, row['prior'])
                        current = runtime.store.event(runtime.session, row['current'])
                        prompts, jef = pilot._prompts(runtime, prior, current, row)
                        self.assertEqual(jef['typed_jef_candidate'], row['oracle'])
                        self.assertEqual(jef['candidate_authority'], 0)
                        self.assertEqual(set(prompts), set(pilot.ARMS))
                        for arm, messages in prompts.items():
                            self.assertEqual([m['role'] for m in messages], ['system','user'])
                            self.assertNotIn('"oracle"', messages[1]['content'])
                            payload = json.loads(messages[1]['content'])
                            self.assertEqual(payload['policy']['text'], row['policy_span'])
                            self.assertEqual(payload['options']['text'], row['option_span'])
                            if arm == pilot.ARMS[0]:
                                self.assertNotIn('typed_jef_candidate', payload)
                            else:
                                self.assertEqual(payload['typed_jef_candidate'], row['oracle'])
                                self.assertEqual(payload['candidate_authority'], 0)
                        self.assertEqual(runtime.calls, {'B1_DETAIL':0, 'B2_GIST':0})
                    finally:
                        runtime.close()

    def test_predeclared_signal_only_if_strong_typed_gain(self):
        r = fake_report()
        for i,row in enumerate(r['rows']):
            row['arms'][0]['score']['correct'] = int(i == 0)
            row['arms'][1]['score']['correct'] = int(i < 5)
        self.assertEqual(pilot._summarize(r), pilot.GOOD[0])
        self.assertTrue(r['exploratory_formatter_signal'])

    def test_equal_scores_is_no_gain(self):
        r = fake_report()
        self.assertEqual(pilot._summarize(r), pilot.GOOD[1])
        self.assertFalse(r['exploratory_formatter_signal'])

    def test_missing_native_reap_is_red(self):
        r = fake_report();r['rows'][0]['arms'][0]['process_reaped'] = False
        self.assertEqual(pilot._summarize(r), pilot.RED)

    def test_duplicate_arm_is_red(self):
        r = fake_report();r['rows'][0]['arms'][1]['arm'] = pilot.ARMS[0]
        self.assertEqual(pilot._summarize(r), pilot.RED)

    def test_missing_jef_call_is_red(self):
        r = fake_report();r['deterministic_jef_calls'] = 5
        self.assertEqual(pilot._summarize(r), pilot.RED)


if __name__ == '__main__':
    unittest.main()
