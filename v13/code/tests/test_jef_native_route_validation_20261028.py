"""No-model JEF native C2 route admissibility and _route integration checks."""
import threading
import time
from types import SimpleNamespace
import unittest

from v13.runtime import Runtime, _validated_native_route


def native(*calls, success=True, confidence=.8, validation=None, **extra):
    return {'success': success, 'confidence': confidence,
            'validation': validation if validation is not None else {},
            'function_calls': list(calls), **extra}


def call(name, route):
    return {'name': name, 'arguments': {'route': route}}


def fake_runtime(control):
    r = Runtime.__new__(Runtime)
    r._session_local = threading.local()
    r._selected_session = 'session'
    r.cfg = {'route_override': 'auto', 'control_seconds': 2}
    r.consolidation = SimpleNamespace(route=lambda *a, **k: None)
    r.store = SimpleNamespace(log=lambda *a, **k: None, components=lambda: {})
    r.executive = SimpleNamespace(control_context=lambda *a: {'packet_id': 'p'},
                                  control_admissible=lambda *a: (True, 'OK'))
    r.guard = SimpleNamespace(state={})
    r.needle = SimpleNamespace(last_metrics={}, control=lambda *a: control)
    r.learner = SimpleNamespace(propose=lambda *a: None,
                                control_calibrate=lambda *a: None)
    r.cancel_event = threading.Event()
    return r


class JefNativeValidatedRouteTests(unittest.TestCase):
    def test_valid_select_processing_first_wins(self):
        c = native(call('other_tool', 'gist'),
                   call('select_processing', 'detail'),
                   call('select_processing', 'both'))
        self.assertEqual(_validated_native_route(c), 'detail')

    def test_unrelated_metadata_and_wrong_name_are_not_proposals(self):
        for c in (native(call('other_tool', 'detail')),
                  native(metadata={'route': 'detail'}),
                  native(call('other_tool', 'detail'), debug='{"route":"detail"}')):
            with self.subTest(c=c):
                self.assertIsNone(_validated_native_route(c))

    def test_invalid_native_negation_nonfinite_and_failure_rejected(self):
        cases = (native(call('select_processing','detail'), success=False),
                 native(call('select_processing','detail'), confidence=float('nan')),
                 native(call('select_processing','detail'), validation={'negation': True}),
                 native(call('select_processing','detail'), validation={'ungrounded': True}),
                 native(call('select_processing','nope')))
        for c in cases:
            with self.subTest(c=c):
                self.assertIsNone(_validated_native_route(c))

    def test_runtime_scaffold_simple_never_uses_unrelated_route(self):
        r = fake_runtime(native(call('other_tool', 'detail'),
                                metadata={'route': 'gist'}))
        e = {'event_id': 'e', 'source_ref': {'source_id': 's'}}
        route, info = r._route('hello', e, time.monotonic() + 10)
        self.assertEqual(route, 'simple')
        self.assertEqual(info['source'], 'BOOT_SCAFFOLD')
        self.assertTrue(info['native_control_rejected'])

    def test_runtime_uses_validated_native_advisory_only(self):
        r = fake_runtime(native(call('other_tool', 'gist'),
                                call('select_processing', 'detail')))
        e = {'event_id': 'e', 'source_ref': {'source_id': 's'}}
        route, info = r._route('hello', e, time.monotonic() + 10)
        self.assertEqual(route, 'detail')
        self.assertEqual(info['source'], 'NATIVE_C2_ADVISORY')
        self.assertFalse(info.get('native_control_rejected', False))

    def test_scaffold_detail_is_not_overridden_by_native_simple(self):
        r = fake_runtime(native(call('select_processing', 'simple')))
        e = {'event_id': 'e', 'source_ref': {'source_id': 's'}}
        route, info = r._route('Calculate 10+20', e, time.monotonic() + 10)
        self.assertEqual(route, 'detail')
        self.assertEqual(info['source'], 'BOOT_SCAFFOLD')


if __name__ == '__main__':
    unittest.main()
