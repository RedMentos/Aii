"""Run68 RED-first: uncalibrated native C2 must never override scaffold."""
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from v13.runtime import Runtime


class C2NativeShadowGate(unittest.TestCase):
    def make_runtime(self, *, component=None, calibration=None,
                     proposal='detail', learned=None):
        r = Runtime.__new__(Runtime)
        r._session_local = threading.local()
        r._selected_session = 'test-session'
        r.cfg = {'route_override': 'auto', 'control_seconds': 4.}
        r.cancel_event = threading.Event()
        r.consolidation = SimpleNamespace(route=lambda *a, **kw: None)
        components = ({'control_calibration': component}
                      if component is not None else {})
        r.store = SimpleNamespace(components=lambda: components,
                                  log=lambda *a, **kw: None)
        r.guard = SimpleNamespace(state='NORMAL')
        r.executive = SimpleNamespace(
            control_context=lambda *a, **kw: {'packet_id': 'context'},
            control_admissible=lambda *a, **kw: (True, 'OK'))
        r.learner = SimpleNamespace(
            propose=lambda *a, **kw: learned,
            compare_student_route=lambda *a, **kw: None,
            control_calibrate=lambda *a, **kw: calibration)
        r.needle = SimpleNamespace(
            last_metrics={},
            control=lambda *a, **kw: {
                'success': True,
                'function_calls': [
                    {'name': 'select_processing',
                     'arguments': {'route': proposal}}],
                'confidence': 1.})
        return r

    def route(self, r, text='Hello there'):
        e = {'event_id': 'evt', 'source_ref': {'source_id': 'source'}}
        with patch('v13.episodic_route.for_turn', return_value=(None, None)):
            return r._route(text, e, time.monotonic()+10.)

    def test_no_calibration_component_is_shadow_only(self):
        r = self.make_runtime()
        route, info = self.route(r)
        self.assertEqual(route, 'simple')
        self.assertEqual(info['source'], 'BOOT_SCAFFOLD')
        self.assertTrue(info['native_control_shadow_only'])
        self.assertEqual(info['native_control']['function_calls'][0]
                         ['arguments']['route'], 'detail')
        self.assertFalse(info['calibrated'])

    def test_fabricated_high_map_without_approved_component_still_shadow(self):
        r = self.make_runtime(calibration={
            'in_support': True, 'calibrated_confidence': .95})
        route, info = self.route(r)
        self.assertEqual(route, 'simple')
        self.assertTrue(info['native_control_shadow_only'])

    def test_approved_in_support_calibration_allows_existing_simple_override(self):
        r = self.make_runtime(
            component={'update_id': 'approved-u1'},
            calibration={'in_support': True, 'calibrated_confidence': .8})
        route, info = self.route(r)
        self.assertEqual(route, 'detail')
        self.assertEqual(info['source'], 'NATIVE_C2_CALIBRATED')
        self.assertTrue(info['calibrated'])
        self.assertNotIn('native_control_shadow_only', info)

    def test_low_calibration_keeps_scaffold_and_rejection_telemetry(self):
        r = self.make_runtime(
            component={'update_id': 'approved-u1'},
            calibration={'in_support': True, 'calibrated_confidence': .3})
        route, info = self.route(r)
        self.assertEqual(route, 'simple')
        self.assertTrue(info['native_control_rejected'])
        self.assertNotEqual(info['source'], 'NATIVE_C2_CALIBRATED')

    def test_out_of_support_keeps_scaffold(self):
        r = self.make_runtime(
            component={'update_id': 'approved-u1'},
            calibration={'in_support': False, 'calibrated_confidence': None})
        route, info = self.route(r)
        self.assertEqual(route, 'simple')
        self.assertTrue(info['native_control_rejected'])

    def test_approved_component_without_inference_keeps_scaffold(self):
        r = self.make_runtime(component={'update_id': 'approved-u1'})
        route, info = self.route(r)
        self.assertEqual(route, 'simple')
        self.assertTrue(info['native_control_rejected'])

    def test_non_simple_scaffold_never_native_overridden(self):
        r = self.make_runtime(
            component={'update_id': 'approved-u1'},
            calibration={'in_support': True, 'calibrated_confidence': .8})
        route, info = self.route(r, 'Calculate 2+2')
        self.assertEqual(route, 'detail')
        self.assertEqual(info['source'], 'BOOT_SCAFFOLD')

    def test_approved_learned_head_still_has_separate_route(self):
        r = self.make_runtime(learned={'route': 'gist', 'margin': .2})
        route, info = self.route(r)
        self.assertEqual(route, 'gist')
        self.assertEqual(info['source'], 'APPROVED_EXTERNAL_HEAD')

    def test_explicit_operator_override_unchanged(self):
        r = self.make_runtime()
        r.cfg['route_override'] = 'both'
        route, info = self.route(r)
        self.assertEqual(route, 'both')
        self.assertEqual(info['source'], 'OPERATOR_ROUTE_OVERRIDE')


if __name__ == '__main__':
    unittest.main()
