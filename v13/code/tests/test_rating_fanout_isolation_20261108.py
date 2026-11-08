"""One feedback consumer must not prevent other organs from seeing a rating."""
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch
import time
import unittest

from v13 import actionlearn, callosum, deliberation, inputs, jefbridge
from v13.agi import live
from v13.runtime import Runtime


class RatingFanoutIsolation(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.runtime = Runtime(self.home)
        self.runtime.sleep.cycle.set_policy('enabled', 'off')

        def generate(messages, *args, **kwargs):
            yield 'An answer.'

        self.runtime._route = Mock(return_value=('simple', {'source': 'TEST_ROUTE_SEAM'}))
        self.runtime.pool.get = Mock(return_value=SimpleNamespace(
            role='C3_LANGUAGE', last_metrics={}, generate=generate))
        self.runtime.learner.output_delta = Mock(return_value=None)
        self.runtime.submit('A question')
        until = time.monotonic() + 10
        while not self.runtime.idle() and time.monotonic() < until:
            time.sleep(.005)
        answer = self.runtime.last_answer()
        self.assertEqual(answer['status'], 'FINAL')
        self.event_id = answer['event_id']

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def test_failure_of_each_consumer_does_not_skip_the_others(self):
        modules = (live, jefbridge, actionlearn, deliberation, callosum)
        error_kind = {
            live: 'agi_live_unavailable', jefbridge: 'jef_bridge_unavailable',
            actionlearn: 'c5_learning_unavailable', deliberation: 'deliberation_unavailable',
            callosum: 'callosum_unavailable',
        }
        for failed in modules:
            with self.subTest(failed=failed.__name__), ExitStack() as stack:
                hooks = {module.__name__: stack.enter_context(patch.object(module, 'on_rating'))
                         for module in modules}
                hooks[failed.__name__].side_effect = RuntimeError('synthetic failure')
                row = inputs.record_rating(self.runtime.store, self.event_id, 2, 'EXPLICIT_NOTE')
                self.assertEqual(row['score'], 2)
                for hook in hooks.values():
                    hook.assert_called_once_with(self.runtime.store, self.event_id, 2)
                self.assertIsNotNone(self.runtime.store.one(
                    'SELECT id FROM telemetry WHERE kind=? AND event_id=?',
                    (error_kind[failed], self.event_id)))

    def test_real_c5_receives_feedback_when_jef_hook_fails_and_survives_restart(self):
        learner = actionlearn.C5Learning(self.runtime.store)
        before = learner.report()['actions']
        key = next(k for k in before if k.endswith('|C3_LANGUAGE'))
        with patch.object(jefbridge, 'on_rating', side_effect=RuntimeError('synthetic failure')):
            inputs.record_rating(self.runtime.store, self.event_id, 2, 'EXPLICIT_NOTE')
        after = learner.report()['actions'][key]
        self.assertEqual(after['n'], before[key]['n'] + 1)
        self.assertGreater(after['modulators']['human_correction'], 0)

        self.runtime.close()
        self.runtime = Runtime(self.home)
        restored = actionlearn.C5Learning(self.runtime.store).report()['actions'][key]
        self.assertEqual(restored, after)
        self.assertEqual(inputs.ratings(self.runtime.store)[-1]['score'], 2)

    def test_failed_error_log_does_not_skip_remaining_consumers(self):
        original_log = self.runtime.store.log

        def failing_error_log(kind, event_id, metrics):
            if kind == 'jef_bridge_unavailable':
                raise OSError('synthetic telemetry failure')
            return original_log(kind, event_id, metrics)

        with patch.object(jefbridge, 'on_rating', side_effect=RuntimeError('synthetic hook failure')), \
                patch.object(self.runtime.store, 'log', side_effect=failing_error_log), \
                patch.object(actionlearn, 'on_rating') as c5, \
                patch.object(deliberation, 'on_rating') as deliberation_hook, \
                patch.object(callosum, 'on_rating') as callosum_hook:
            row = inputs.record_rating(self.runtime.store, self.event_id, 2, 'EXPLICIT_NOTE')
        self.assertEqual(row['score'], 2)
        for hook in (c5, deliberation_hook, callosum_hook):
            hook.assert_called_once_with(self.runtime.store, self.event_id, 2)


if __name__ == '__main__':
    unittest.main()
