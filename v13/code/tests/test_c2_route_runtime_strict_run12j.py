"""Run12J: Runtime C2 advisory must bind to one validated select_processing call.

Pure fake-Needle seam: no model, no age/learning authority, no native evidence.
"""
import threading
import time
import unittest
from types import SimpleNamespace
from v13.runtime import Runtime


def native(route='detail', **extra):
    return {
        'success': True, 'confidence': .9,
        'validation': {'negation': False, 'ungrounded': []},
        'function_calls': [{'name': 'select_processing',
                            'arguments': {'route': route}}],
    } | extra


class FakeRuntime:
    _route = Runtime._route
    cfg = {'route_override': 'auto', 'control_seconds': 4.0}
    session = 'chat_test'
    cancel_event = threading.Event()
    guard = SimpleNamespace(state='NORMAL')

    def __init__(self, output):
        self.consolidation = SimpleNamespace(route=lambda *a, **k: None)
        self.executive = SimpleNamespace(
            control_context=lambda *a, **k: {'packet_id': 'pkt_context'},
            control_admissible=lambda *a, **k: (True, None))
        self.store = SimpleNamespace(components=lambda: {}, log=lambda *a, **k: None)
        self.learner = SimpleNamespace(propose=lambda *a, **k: None,
                                       control_calibrate=lambda *a, **k: None)
        self.needle = SimpleNamespace(last_metrics={}, control=lambda *a, **k: output)

    def _head_shadow(self, *a, **k):
        return None

    def call(self):
        return self._route('hi', {'event_id': 'evt_test',
                                  'source_ref': {'source_id': 'src_test'}},
                           time.monotonic() + 10)


class RuntimeC2StrictRun12J(unittest.TestCase):
    def test_single_valid_native_tool_keeps_existing_advisory(self):
        route, info = FakeRuntime(native('detail')).call()
        self.assertEqual(route, 'detail')
        self.assertEqual(info['source'], 'NATIVE_C2_ADVISORY')

    def test_foreign_nested_route_cannot_preempt_validated_tool(self):
        control = {'route': 'gist', 'diagnostic': {'route': 'both'}} | native('detail')
        route, info = FakeRuntime(control).call()
        self.assertEqual(route, 'detail')
        self.assertEqual(info['source'], 'NATIVE_C2_ADVISORY')

    def test_failed_native_control_must_not_route(self):
        route, info = FakeRuntime(native('detail', success=False) | {'route': 'both'}).call()
        self.assertEqual(route, 'simple')
        self.assertEqual(info['source'], 'BOOT_SCAFFOLD')

    def test_ambiguous_and_foreign_tool_calls_must_not_route(self):
        cases = (
            native('detail', function_calls=[
                {'name': 'select_processing', 'arguments': {'route': 'detail'}},
                {'name': 'select_processing', 'arguments': {'route': 'both'}}]),
            native('detail', function_calls=[
                {'name': 'foreign', 'arguments': {'route': 'gist'}}]),
            native('detail', function_calls=[
                {'name': 'foreign', 'arguments': {'route': 'gist'}},
                {'name': 'select_processing', 'arguments': {'route': 'detail'}}]),
            native('detail', confidence=float('nan')),
            native('detail', validation={'negation': True}),
        )
        for control in cases:
            with self.subTest(control=repr(control)[:120]):
                route, info = FakeRuntime(control).call()
                self.assertEqual(route, 'simple')
                self.assertEqual(info['source'], 'BOOT_SCAFFOLD')

    def test_scaffold_route_non_simple_remains_authoritative(self):
        # Non-simple scaffold remains outside this narrow change; no broad
        # native admission or new learned-route permission is granted.
        fake = FakeRuntime(native('both'))
        fake._route = Runtime._route.__get__(fake, FakeRuntime)
        route, info = fake._route('What is 2+2?',
                                 {'event_id': 'evt_test', 'source_ref': {'source_id': 'src_test'}},
                                 time.monotonic() + 10)
        self.assertEqual(route, 'detail')
        self.assertEqual(info['source'], 'BOOT_SCAFFOLD')


if __name__ == '__main__':
    unittest.main()
