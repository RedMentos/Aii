import unittest
from v13.timed_percept import TimedPercept
from v13.timed_a5_bridge import admit_timed

class TimedA5BridgeTests(unittest.TestCase):
    def event(self, **kwargs):
        d = dict(modality="audio", source="fixture", start_ms=10, end_ms=20,
                 consent_id="local", stage="final", rms=.3, non_speech="laugh")
        d.update(kwargs)
        return TimedPercept(**d)

    def test_acoustics_not_raw_nonverbal(self):
        r = admit_timed([self.event()], allowed_consent_ids=frozenset({"local"}), token_budget=400)
        self.assertEqual(len(r.admission.selected), 1)
        self.assertIn("rms=", r.admission.selected[0].summary)
        self.assertNotIn("laugh", r.admission.selected[0].summary)

    def test_teacher_transcript_not_promoted(self):
        r = admit_timed([self.event(provenance="teacher", transcript="private words")],
                        allowed_consent_ids=frozenset({"local"}), token_budget=400)
        self.assertNotIn("private words", r.admission.selected[0].summary)

    def test_denied_consent(self):
        r = admit_timed([self.event()], allowed_consent_ids=frozenset(), token_budget=400)
        self.assertFalse(r.admission.selected)

    def test_provisional_refused(self):
        r = admit_timed([self.event(stage="provisional")],
                        allowed_consent_ids=frozenset({"local"}), token_budget=400)
        self.assertFalse(r.admission.selected)

    def test_zero_budget(self):
        r = admit_timed([self.event()], allowed_consent_ids=frozenset({"local"}), token_budget=0)
        self.assertFalse(r.admission.selected)

    def test_duplicate_lineage(self):
        with self.assertRaises(ValueError):
            admit_timed([self.event(), self.event()], allowed_consent_ids=frozenset({"local"}), token_budget=400)

    def test_ui_content_free(self):
        r = admit_timed([self.event(modality="android_ui", rms=None, non_speech=None)],
                        allowed_consent_ids=frozenset({"local"}), token_budget=400)
        self.assertEqual(r.admission.selected[0].modality, "ui")

    def test_invalid_allowlist(self):
        with self.assertRaises(ValueError):
            admit_timed([], allowed_consent_ids={"local"}, token_budget=400)
