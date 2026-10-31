"""Run117AD: postgeneration guard for real persisted B1/B2/JEF/ContextOS."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tests import test_b1b2_jef_span_c3_bridge_candidate as source_tests
from v13.b1b2_jef_span_c3_postgen_candidate import evaluate, PASS
from v13.common import dumps
from v13.context_os import controller

FIXTURE = Path(__file__).resolve().parents[1] / 'docs/fixtures/RUN117Z_REAL_JEF_NATIVE_SEED1065.json'
SHA = 'cb008f27a4d1ef7f0f288419ac276ebb67c8d7958da3c62104994822dd90634d'


class PostgenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == SHA
        cls.rows = json.loads(FIXTURE.read_text())['rows']

    def setUp(self):
        self.tmp, self.r, self.prior, self.current, self.ids = (
            source_tests.BridgeTests().setup(self.rows[0]))

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def run_guard(self, callback=None, **kwargs):
        if callback is None:
            callback = lambda _: json.dumps(self.rows[0]['oracle'])
        flags = {'operator_opt_in': True, 'callback_opt_in': True}
        flags.update(kwargs)
        return evaluate(self.r, self.prior, self.current, self.ids,
                        callback, **flags)

    def assert_shadow(self, result):
        self.assertFalse(result['output_committed'])
        self.assertFalse(result['native_proof'])
        self.assertFalse(result['body_model_quote_verified'])
        self.assertFalse(result['body_hypotheses_are_facts'])
        self.assertFalse(result['source_semantic_truth_authority'])
        self.assertEqual(result['delivery_authority'], 0)
        self.assertEqual(result['learning_authority'], 0)
        self.assertEqual(result['tool_dispatches'], 0)
        self.assertEqual(result['jepa_weight'], 0)
        self.assertFalse(result['redmi_measured'])
        self.assertFalse(result['whole_system_complete'])

    def test_six_real_store_rows_exact_typed_shadow(self):
        for row in self.rows:
            with self.subTest(row=row['id']):
                tmp, r, prior, current, ids = (
                    source_tests.BridgeTests().setup(row))
                try:
                    calls_before = dict(r.calls)
                    raw = json.dumps(row['oracle'], separators=(',', ':'))
                    result = evaluate(
                        r, prior, current, ids, lambda _: raw,
                        operator_opt_in=True, callback_opt_in=True)
                    self.assertEqual(result['status'], PASS, result)
                    self.assertTrue(result['callback_invoked'])
                    self.assertTrue(result['source_rechecked'])
                    self.assertTrue(result['formatter_match_shadow'])
                    self.assertEqual(result['output_sha256'],
                                     hashlib.sha256(raw.encode()).hexdigest())
                    self.assertEqual(result['source_refs'],
                                     [prior['source_ref'], current['source_ref']])
                    self.assertEqual(result['offer_packet_ids'], ids)
                    self.assertNotIn('output', result)
                    self.assertEqual(r.calls, calls_before)
                    self.assertEqual(r.store.one(
                        'SELECT COUNT(*) AS n FROM actions')['n'], 0)
                    self.assert_shadow(result)
                finally:
                    r.close()
                    tmp.cleanup()

    def test_off_requires_both_opt_ins_no_callback_no_plan(self):
        called = []
        for flags in ({'operator_opt_in': False},
                      {'callback_opt_in': False}):
            before = self.r.store.one(
                "SELECT COUNT(*) AS n FROM packets WHERE kind='ContextPlan'")['n']
            result = self.run_guard(lambda _: called.append(True), **flags)
            self.assertEqual(result['status'], 'OFF')
            self.assertEqual(self.r.store.one(
                "SELECT COUNT(*) AS n FROM packets WHERE kind='ContextPlan'")['n'],
                before)
            self.assert_shadow(result)
        self.assertEqual(called, [])

    def test_real_approval_claim_and_noncallable_refused(self):
        called = []
        result = self.run_guard(lambda _: called.append(True),
                                approval_receipt={'approved': True})
        self.assertEqual(result['status'], 'REAL_TTY_APPROVAL_UNSUPPORTED_RED')
        self.assertEqual(called, [])
        self.assertEqual(self.run_guard(123)['status'],
                         'INVALID_GENERATOR_RED')

    def test_wrong_or_malformed_output_rejected(self):
        for raw, status in (
            ('{"choice":"B","remaining":50}', 'FORMATTER_CANDIDATE_MISMATCH_RED'),
            ('{"choice":"A","remaining":49}', 'FORMATTER_CANDIDATE_MISMATCH_RED'),
            ('{"choice":"A","choice":"B","remaining":50}', 'FORMATTER_JSON_RED'),
            ('{"choice":"A","remaining":50,"approved":true}', 'FORMATTER_JSON_RED'),
            ('{"choice":"A","remaining":true}', 'FORMATTER_JSON_RED'),
            ('{"choice":"A","remaining":NaN}', 'FORMATTER_JSON_RED'),
            ('{"choice":"A","remaining":50} trailing', 'FORMATTER_JSON_RED'),
            ('{"choice":"A","remaining":50}' + ' ' * 300, 'FORMATTER_JSON_RED'),
        ):
            with self.subTest(raw=raw[:50]):
                result = self.run_guard(lambda _: raw)
                self.assertEqual(result['status'], status, result)
                self.assertNotIn('output_sha256', result)
                self.assert_shadow(result)

    def test_callback_prompt_mutation_refused(self):
        def callback(messages):
            messages[1]['content'] = '{}'
            return json.dumps(self.rows[0]['oracle'])
        result = self.run_guard(callback)
        self.assertEqual(result['status'], 'CALLBACK_PROMPT_MUTATED_RED')
        self.assert_shadow(result)

    def test_callback_input_ids_mutation_refused(self):
        def callback(_):
            self.ids['B1_DETAIL'] = 'forged'
            return json.dumps(self.rows[0]['oracle'])
        result = self.run_guard(callback)
        self.assertEqual(result['status'], 'CALLBACK_INPUT_MUTATED_RED')
        self.assert_shadow(result)

    def test_late_authoritative_correction_refused(self):
        def callback(_):
            self.r.store.event(self.r.session,
                               'Project Helix correction: cancel options.')
            return json.dumps(self.rows[0]['oracle'])
        result = self.run_guard(callback)
        self.assertEqual(result['status'], 'CALLBACK_STORE_CHANGED_RED')
        self.assert_shadow(result)

    def test_offer_mutation_during_callback_refused(self):
        def callback(_):
            row = self.r.store.one('SELECT payload FROM packets WHERE id=?',
                                   (self.ids['B1_DETAIL'],))
            payload = json.loads(row['payload'])
            payload['offer']['summary'] = 'LATE FORGED HYPOTHESIS'
            with self.r.store.tx() as db:
                db.execute('UPDATE packets SET payload=? WHERE id=?',
                           (dumps(payload), self.ids['B1_DETAIL']))
            return json.dumps(self.rows[0]['oracle'])
        result = self.run_guard(callback)
        self.assertEqual(result['status'], 'CALLBACK_STORE_CHANGED_RED')
        self.assert_shadow(result)

    def test_context_plan_mutation_during_callback_refused(self):
        def callback(messages):
            plan_id = json.loads(messages[1]['content'])['context_plan_packet_id']
            row = self.r.store.one('SELECT payload FROM packets WHERE id=?',
                                   (plan_id,))
            payload = json.loads(row['payload'])
            payload['provenance'] = []
            with self.r.store.tx() as db:
                db.execute('UPDATE packets SET payload=? WHERE id=?',
                           (dumps(payload), plan_id))
            return json.dumps(self.rows[0]['oracle'])
        result = self.run_guard(callback)
        self.assertEqual(result['status'], 'CALLBACK_STORE_CHANGED_RED')
        self.assert_shadow(result)

    def test_rolled_back_sql_write_still_refused(self):
        def callback(_):
            row = self.r.store.one('SELECT payload FROM packets WHERE id=?',
                                   (self.ids['B2_GIST'],))
            with self.r.store.tx() as db:
                db.execute('UPDATE packets SET payload=? WHERE id=?',
                           (row['payload'], self.ids['B2_GIST']))
            return json.dumps(self.rows[0]['oracle'])
        result = self.run_guard(callback)
        self.assertEqual(result['status'], 'CALLBACK_STORE_CHANGED_RED')

    def test_revision_change_without_store_write_refused(self):
        original = self.r.models.revision
        p = patch.object(self.r.models, 'revision',
                         side_effect=lambda role: ('FORGED_REVISION' if
                             role == 'B1_DETAIL' else original(role)))
        def callback(_):
            p.start()
            return json.dumps(self.rows[0]['oracle'])
        try:
            result = self.run_guard(callback)
        finally:
            p.stop()
        self.assertEqual(result['status'],
                         'POSTGEN_SOURCE_OFFER_PLAN_CHANGED_RED', result)
        self.assert_shadow(result)

    def test_plan_read_change_without_store_write_refused(self):
        p = patch('v13.b1b2_jef_span_c3_postgen_candidate._read_bound_shadow_plan',
                  return_value=None)
        def callback(_):
            p.start()
            return json.dumps(self.rows[0]['oracle'])
        try:
            result = self.run_guard(callback)
        finally:
            p.stop()
        self.assertEqual(result['status'],
                         'POSTGEN_SOURCE_OFFER_PLAN_CHANGED_RED', result)
        self.assert_shadow(result)

    def test_contextos_active_preflight_refused(self):
        controller(self.r).set_mode('ACTIVE', authority='EXPLICIT_HUMAN')
        called = []
        result = self.run_guard(lambda _: called.append(True))
        self.assertEqual(result['status'], 'SOURCE_PREFLIGHT_RED')
        self.assertEqual(called, [])
        self.assert_shadow(result)

    def test_deleted_prior_source_preflight_refused(self):
        with self.r.store.tx() as db:
            db.execute('UPDATE sources SET deleted=1 WHERE id=?',
                       (self.prior['source_ref']['source_id'],))
        called = []
        result = self.run_guard(lambda _: called.append(True))
        self.assertEqual(result['status'], 'SOURCE_PREFLIGHT_RED')
        self.assertEqual(called, [])
        self.assert_shadow(result)

    def test_callback_exception_refused(self):
        def callback(_):
            raise RuntimeError('synthetic callback exception')
        result = self.run_guard(callback)
        self.assertEqual(result['status'], 'CALLBACK_EXCEPTION_RED')
        self.assertEqual(result['error_type'], 'RuntimeError')
        self.assert_shadow(result)


if __name__ == '__main__':
    unittest.main()
