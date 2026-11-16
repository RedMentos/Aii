import unittest
from v13.perception_budget_candidate import PerceptSummary, admit_percepts

class AdmissionTests(unittest.TestCase):
    def packet(self, **kw):
        d = dict(source="mic", modality="audio", text="loud non-speech event",
                 priority=1, consent=True, provenance="provisional", timestamp_ms=100)
        d.update(kw)
        return PerceptSummary(**d)

    def test_consent(self):
        self.assertEqual(admit_percepts([self.packet(consent=False)], now_ms=100), ())
    def test_stale_future(self):
        self.assertEqual(admit_percepts([self.packet(timestamp_ms=0),
                         self.packet(timestamp_ms=201)], now_ms=200, max_age_ms=10), ())
    def test_priority_budget(self):
        a = self.packet(source="a", text="x"*50, priority=0)
        b = self.packet(source="b", text="important", priority=5)
        out = admit_percepts([a,b], max_chars=55, now_ms=100)
        self.assertEqual(len(out), 1)
        self.assertIn("important", out[0])
    def test_provenance(self):
        self.assertEqual(admit_percepts([self.packet(provenance="unknown")], now_ms=100), ())
    def test_no_partial(self):
        self.assertEqual(admit_percepts([self.packet()], max_chars=4, now_ms=100), ())
        with self.assertRaises(ValueError):
            admit_percepts([], max_chars=-1)
    def test_non_speech(self):
        self.assertIn("non-speech", admit_percepts([self.packet()], now_ms=100)[0])

if __name__ == "__main__":
    unittest.main()
