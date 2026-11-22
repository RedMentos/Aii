"""Real SQLite source/restart/adversarial tests for default-OFF JEF span budget."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tests.test_run117s_b2_salient_source_shadow import QuoteRuntime
from v13.jef_span_budget_shadow_candidate import build_jef_span_budget_shadow

FIXTURE = Path(__file__).resolve().parents[1] / 'docs/fixtures/RUN117W_C3_ARITHMETIC_SEED1063.json'
SHA = '2b62fd13c81201c23574fa42ad87176f5d25f755b534a76f4386c9ec9c608ed9'


class JEFSpanBudget(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == SHA
        cls.rows = json.loads(FIXTURE.read_text())['rows']

    def setup(self, row):
        tmp = tempfile.TemporaryDirectory()
        runtime = QuoteRuntime(Path(tmp.name) / 'home', row)
        prior = runtime.store.event(runtime.session, row['prior'])
        current = runtime.store.event(runtime.session, row['current'])
        return tmp, runtime, prior, current

    def test_all_six_real_store_decisions_no_model(self):
        for row in self.rows:
            with self.subTest(row=row['id']):
                tmp, runtime, prior, current = self.setup(row)
                try:
                    before = dict(runtime.calls)
                    result = build_jef_span_budget_shadow(runtime, prior, current,
                                                          operator_opt_in=True)
                    self.assertEqual(result['status'], 'SHADOW_SOURCE_BOUND_JEF_BUDGET_VERIFIED', result)
                    self.assertEqual(result['typed_jef_candidate'], row['oracle'])
                    self.assertEqual(result['candidate_authority'], 0)
                    self.assertFalse(result['output_committed'])
                    self.assertEqual(result['tool_dispatches'], 0)
                    self.assertEqual(result['jepa_weight'], 0)
                    self.assertEqual(runtime.calls, before)
                    payload = json.loads(result['messages'][1]['content'])
                    self.assertEqual(payload['policy']['text'], row['policy_span'])
                    self.assertEqual(payload['options']['text'], row['option_span'])
                    self.assertEqual(payload['typed_jef_candidate'], row['oracle'])
                    self.assertNotIn(row['policy_span'], result['messages'][0]['content'])
                    self.assertEqual(runtime.store.one('SELECT COUNT(*) AS n FROM actions')['n'], 0)
                finally:
                    runtime.close(); tmp.cleanup()

    def test_off_is_strict_and_no_model(self):
        tmp, runtime, prior, current = self.setup(self.rows[0])
        try:
            self.assertEqual(build_jef_span_budget_shadow(runtime, prior, current)['status'], 'OFF')
            self.assertEqual(runtime.calls, {'B1_DETAIL': 0, 'B2_GIST': 0})
        finally:
            runtime.close(); tmp.cleanup()

    def test_stale_latest_user_correction_veto(self):
        tmp, runtime, prior, current = self.setup(self.rows[0])
        try:
            runtime.store.event(runtime.session, 'Project Arbor correction. Ignore earlier option A.')
            result = build_jef_span_budget_shadow(runtime, prior, current, operator_opt_in=True)
            self.assertEqual(result['status'], 'SOURCE_POINTER_REFUSED_RED')
        finally:
            runtime.close(); tmp.cleanup()

    def test_current_rule_override_refused(self):
        row = dict(self.rows[0]);row['current'] += ' Binding policy: budget 1 euros; deadline 1 days; local-only false.'
        tmp, runtime, prior, current = self.setup(row)
        try:
            result = build_jef_span_budget_shadow(runtime, prior, current, operator_opt_in=True)
            self.assertEqual(result['status'], 'GRAMMAR_OR_OVERRIDE_RED')
        finally:
            runtime.close(); tmp.cleanup()

    def test_duplicate_prior_policy_refused(self):
        row = dict(self.rows[0])
        row['prior'] += ' ' + row['policy_span']
        tmp, runtime, prior, current = self.setup(row)
        try:
            result = build_jef_span_budget_shadow(runtime, prior, current, operator_opt_in=True)
            self.assertEqual(result['status'], 'GRAMMAR_OR_OVERRIDE_RED')
        finally:
            runtime.close(); tmp.cleanup()

    def test_unparseable_second_option_refused(self):
        row = dict(self.rows[0])
        row['current'] += ' Option A: cost unknown euros.'
        tmp, runtime, prior, current = self.setup(row)
        try:
            result = build_jef_span_budget_shadow(runtime, prior, current, operator_opt_in=True)
            self.assertEqual(result['status'], 'GRAMMAR_OR_OVERRIDE_RED')
        finally:
            runtime.close(); tmp.cleanup()

    def test_incomplete_current_policy_override_refused(self):
        row = dict(self.rows[0])
        row['current'] += ' Binding policy: budget unknown euros.'
        tmp, runtime, prior, current = self.setup(row)
        try:
            result = build_jef_span_budget_shadow(runtime, prior, current, operator_opt_in=True)
            self.assertEqual(result['status'], 'GRAMMAR_OR_OVERRIDE_RED')
        finally:
            runtime.close(); tmp.cleanup()

    def test_source_ref_tamper_refused(self):
        tmp, runtime, prior, current = self.setup(self.rows[0])
        try:
            current['source_ref'] = dict(current['source_ref'], sha256='0'*64)
            result = build_jef_span_budget_shadow(runtime, prior, current, operator_opt_in=True)
            self.assertEqual(result['status'], 'SOURCE_POINTER_REFUSED_RED')
        finally:
            runtime.close(); tmp.cleanup()

    def test_restart_same_store_same_decision(self):
        row = self.rows[1]
        tmp, runtime, prior, current = self.setup(row)
        home = runtime.home
        session = runtime.session
        try:
            first = build_jef_span_budget_shadow(runtime, prior, current, operator_opt_in=True)
            self.assertEqual(first['status'], 'SHADOW_SOURCE_BOUND_JEF_BUDGET_VERIFIED')
            runtime.close()
            from v13.runtime import Runtime
            runtime = Runtime(home)
            runtime.session = session
            second = build_jef_span_budget_shadow(runtime, prior, current, operator_opt_in=True)
            self.assertEqual(second['status'], 'SHADOW_SOURCE_BOUND_JEF_BUDGET_VERIFIED', second)
            self.assertEqual(second['typed_jef_candidate'], first['typed_jef_candidate'])
            self.assertEqual(second['messages_sha256'], first['messages_sha256'])
        finally:
            runtime.close(); tmp.cleanup()


if __name__ == '__main__':
    unittest.main()