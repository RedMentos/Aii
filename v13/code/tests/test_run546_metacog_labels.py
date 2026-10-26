"""Run546: malformed JEF metacognition labels cannot poison live calibration.

Source-only, no model inference, no age/tool authority change.
"""
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime
from v13.agi import hub
from v13.agi import live


class Run546MetacognitionLabels(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.runtime = Runtime(self.home)
        self.meta = hub(self.runtime).metacog

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def test_malformed_confidence_and_correctness_never_write_state(self):
        for i in range(40):
            self.meta.record('answer', 0.8, i % 2 == 0)
        before = self.meta.box.load()
        decision = self.meta.decide('answer', 0.8)
        invalid = [
            (float('nan'), True), (float('inf'), False),
            (-float('inf'), False), (-0.01, True), (1.01, False),
            ('0.8', True), (None, False), (True, True), (False, False),
            (object(), True), (0.8, 'false'), (0.8, 'true'),
            (0.8, []), (0.8, {}), (0.8, None),
            (0.8, 2), (0.8, -1), (0.8, 0.0), (0.8, 1.0),
        ]
        for confidence, correct in invalid:
            with self.subTest(confidence=repr(confidence), correct=repr(correct)):
                with self.assertRaises(ValueError):
                    self.meta.record('answer', confidence, correct)
                self.assertEqual(self.meta.box.load(), before)
                self.assertEqual(self.meta.decide('answer', 0.8), decision)

    def test_explicit_binary_labels_and_probability_boundaries_persist(self):
        for confidence, correct in [(0, False), (1, True), (0.8, 0), (0.8, 1)]:
            self.meta.record('answer', confidence, correct)
        self.assertEqual(self.meta.box.load()[0]['components']['answer']['pairs'],
                         [[0.0, 0], [1.0, 1], [0.8, 0], [0.8, 1]])
        self.runtime.close()
        self.runtime = Runtime(self.home)
        self.meta = hub(self.runtime).metacog
        self.assertEqual(self.meta.box.load()[0]['components']['answer']['pairs'],
                         [[0.0, 0], [1.0, 1], [0.8, 0], [0.8, 1]])

    def test_valid_calibration_still_drives_existing_live_effort_path(self):
        event = self.runtime.store.event(self.runtime.session, 'Budget Aurora?')
        signal = {'uncertainty': 0.2, 'route_hint': 'simple'}
        for _ in range(40):
            self.meta.record(live.ANSWER_GROUNDED, 0.8, False)
        info = {}
        adjusted = live.before_effort(self.runtime, event, info, signal)
        self.assertEqual(adjusted['uncertainty'], 0.8)
        self.assertTrue(info['metacog_abstain'])
        self.assertEqual(self.meta.report(live.ANSWER_GROUNDED)['components'][live.ANSWER_GROUNDED]['n'], 40)


if __name__ == '__main__':
    unittest.main()
