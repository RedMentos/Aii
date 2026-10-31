"""Run117AI authoritative event-to-SourceRef counterexample and wrapper tests."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.run52_b1b2_cross_turn_native import OVERRIDES
from tests import test_run117ah_body_source_id_candidate as ah
from v13.b1b2_source_id_quote_candidate import (
    KIND, select as frozen_select,
)
from v13.b1b2_source_id_event_binding_candidate import select_bound


class EventBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = ah.rows()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.row = self.rows[0]
        self.r = ah.QuoteRuntime(Path(self.tmp.name) / 'home', self.row)
        self.r.cfg.update(OVERRIDES)
        self.prior = self.r.store.event(self.r.session, self.row['prior'])

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def bound(self, event, role, callback=None, **flags):
        kwargs = {'operator_opt_in': True, 'callback_opt_in': True}
        kwargs.update(flags)
        return select_bound(self.r, event, role,
                            callback if callback is not None else ah.choose(role),
                            **kwargs)

    def count(self):
        return self.r.store.one(
            'SELECT COUNT(*) AS n FROM packets WHERE kind=?',
            (KIND,))['n']

    def assert_no_authority(self, result):
        self.assertFalse(result['native_model_proven'])
        self.assertFalse(result['output_committed'])
        self.assertFalse(result['source_semantic_truth_authority'])
        self.assertTrue(result['model_hypothesis_not_fact'])
        self.assertEqual(result['tool_dispatches'], 0)
        self.assertEqual(result['delivery_authority'], 0)
        self.assertEqual(result['learning_authority'], 0)
        self.assertEqual(result['jepa_weight'], 0)
        self.assertFalse(result['redmi_measured'])
        self.assertFalse(result['whole_system_complete'])

    def test_six_frozen_rows_prior_b2_and_current_b1(self):
        for row in self.rows:
            with self.subTest(project=row['id']):
                with tempfile.TemporaryDirectory() as d:
                    r = ah.QuoteRuntime(Path(d) / 'home', row)
                    r.cfg.update(OVERRIDES)
                    try:
                        prior = r.store.event(r.session, row['prior'])
                        b2 = select_bound(
                            r, prior, 'B2_GIST', ah.choose('B2_GIST'),
                            operator_opt_in=True, callback_opt_in=True)
                        current = r.store.event(r.session, row['current'])
                        b1 = select_bound(
                            r, current, 'B1_DETAIL', ah.choose('B1_DETAIL'),
                            operator_opt_in=True, callback_opt_in=True)
                        for result, event in ((b2, prior), (b1, current)):
                            self.assertEqual(result['status'],
                                             'SHADOW_EVENT_SOURCE_BOUND_CORRECT', result)
                            self.assertTrue(result['authoritative_event_source_verified'])
                            self.assertTrue(result['model_selection_correct_shadow'])
                            self.assertEqual(result['source_ref'], event['source_ref'])
                            self.assert_no_authority(result)
                        self.assertEqual(r.store.one(
                            'SELECT COUNT(*) AS n FROM actions')['n'], 0)
                    finally:
                        r.close()

    def test_frozen_selector_accepts_forged_latest_event_old_source_ref(self):
        # Explicitly preserve and demonstrate the frozen source-lineage bug;
        # do not edit its pinned source while the seed1069 native cohort is open.
        current = self.r.store.event(self.r.session, self.row['current'])
        forged = dict(current, source_ref=self.prior['source_ref'])
        result = frozen_select(
            self.r, forged, 'B2_GIST', ah.choose('B2_GIST'),
            operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(result['status'], 'SHADOW_SOURCE_ID_SELECTED', result)
        stored = json.loads(self.r.store.one(
            'SELECT payload FROM packets WHERE id=?',
            (result['packet_id'],))['payload'])
        self.assertEqual(stored['event_id'], current['event_id'])
        self.assertEqual(stored['source_ref'], self.prior['source_ref'])
        self.assertNotEqual(stored['source_ref'], current['source_ref'])

    def test_wrapper_refuses_same_forged_event_before_callback_and_write(self):
        current = self.r.store.event(self.r.session, self.row['current'])
        forged = dict(current, source_ref=self.prior['source_ref'])
        called = []
        before = self.count()
        result = self.bound(forged, 'B2_GIST',
                            lambda _: called.append(True))
        self.assertEqual(result['status'], 'EVENT_SOURCE_PREFLIGHT_RED')
        self.assertEqual(called, [])
        self.assertEqual(self.count(), before)
        self.assert_no_authority(result)

    def test_wrong_source_offset_or_generation_refused(self):
        current = self.r.store.event(self.r.session, self.row['current'])
        cases = [
            dict(current, source_ref=dict(
                current['source_ref'], char_end=10)),
            dict(current, brain_generation_id='FORGED_GENERATION'),
        ]
        for event in cases:
            with self.subTest(event=event):
                called = []
                result = self.bound(event, 'B1_DETAIL',
                                    lambda _: called.append(True))
                self.assertEqual(result['status'], 'EVENT_SOURCE_PREFLIGHT_RED')
                self.assertEqual(called, [])
                self.assert_no_authority(result)

    def test_stale_event_and_deleted_source_refused(self):
        self.r.store.event(self.r.session, self.row['current'])
        self.assertEqual(self.bound(self.prior, 'B2_GIST')['status'],
                         'EVENT_SOURCE_PREFLIGHT_RED')
        with self.r.store.tx() as db:
            db.execute('UPDATE sources SET deleted=1 WHERE id=?',
                       (self.prior['source_ref']['source_id'],))
        self.assertEqual(self.bound(self.prior, 'B2_GIST')['status'],
                         'EVENT_SOURCE_PREFLIGHT_RED')

    def test_off_and_real_approval_refused_without_callback(self):
        called = []
        for flags, status in (
            ({'operator_opt_in': False}, 'OFF'),
            ({'callback_opt_in': False}, 'OFF'),
            ({'approval_receipt': {'approved': True}},
             'REAL_TTY_APPROVAL_UNSUPPORTED_RED'),
        ):
            result = self.bound(self.prior, 'B2_GIST',
                                lambda _: called.append(True), **flags)
            self.assertEqual(result['status'], status)
            self.assert_no_authority(result)
        self.assertEqual(called, [])
        self.assertEqual(self.count(), 0)

    def test_wrong_and_abstain_remain_fallible(self):
        def wrong(messages):
            data = json.loads(messages[1]['content'])
            return json.dumps({'span_id': next(
                x['span_id'] for x in data['candidates']
                if 'Binding policy:' not in x['text'])})
        wrong_result = self.bound(self.prior, 'B2_GIST', wrong)
        self.assertEqual(wrong_result['status'],
                         'SHADOW_EVENT_SOURCE_BOUND_WRONG', wrong_result)
        self.assertFalse(wrong_result['model_selection_correct_shadow'])
        self.assert_no_authority(wrong_result)
        abstain = self.bound(
            self.prior, 'B2_GIST', lambda _: '{"span_id":"NONE"}')
        self.assertEqual(abstain['status'],
                         'SHADOW_EVENT_SOURCE_BOUND_ABSTAIN', abstain)
        self.assertFalse(abstain['model_selection_correct_shadow'])
        self.assert_no_authority(abstain)

    def test_callback_prompt_mutation_or_late_correction_refused(self):
        def mutate(messages):
            messages[1]['content'] = '{}'
            return '{"span_id":"NONE"}'
        result = self.bound(self.prior, 'B2_GIST', mutate)
        self.assertEqual(result['status'], 'FROZEN_SELECTOR_RED')
        self.assertEqual(result['component_status'],
                         'CALLBACK_PROMPT_MUTATED_RED')
        def correct(_):
            self.r.store.event(self.r.session,
                               'Project Auric correction: cancel request.')
            return '{"span_id":"NONE"}'
        result = self.bound(self.prior, 'B2_GIST', correct)
        self.assertEqual(result['status'], 'FROZEN_SELECTOR_RED')
        self.assertEqual(result['component_status'],
                         'CALLBACK_STORE_CHANGED_RED')

    def test_invalid_json_and_callback_exception_fail_closed(self):
        result = self.bound(self.prior, 'B2_GIST',
                            lambda _: '{"span_id":"a","span_id":"b"}')
        self.assertEqual(result['status'], 'FROZEN_SELECTOR_RED')
        self.assertEqual(result['component_status'], 'MODEL_JSON_RED')
        def raise_error(_):
            raise RuntimeError('synthetic callback failure')
        result = self.bound(self.prior, 'B2_GIST', raise_error)
        self.assertEqual(result['status'], 'FROZEN_SELECTOR_RED')
        self.assertEqual(result['component_status'], 'CALLBACK_EXCEPTION_RED')


if __name__ == '__main__':
    unittest.main()
