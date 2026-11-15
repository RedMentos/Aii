"""Adversarial A5 contract checks; synthetic host tests, no Android claim."""
import unittest
from v13.percept_admission import Percept, admit

class StrictTypes(unittest.TestCase):
    def base(self, **kw):
        fields = dict(source_id="s1", modality="audio", start_ms=0, end_ms=10,
                      summary="noise", consent=True, final=True, priority=0)
        fields.update(kw)
        return Percept(**fields)

    def test_truthy_consent_is_not_permission(self):
        for value in ("false", "yes", 1, [], None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                admit([self.base(consent=value)], 1000)

    def test_truthy_final_is_not_finality(self):
        for value in ("false", 1, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                admit([self.base(final=value)], 1000)

    def test_boolean_timestamp_rejected(self):
        for field in ("start_ms", "end_ms"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                admit([self.base(**{field: True})], 1000)

    def test_priority_type_rejected_before_sort(self):
        for value in ("999", 1.5, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                admit([self.base(priority=value)], 1000)

    def test_invalid_summary_type_rejected(self):
        with self.assertRaises(ValueError):
            admit([self.base(summary=42)], 1000)

    def test_invalid_source_id_type_rejected(self):
        with self.assertRaises(ValueError):
            admit([self.base(source_id=5)], 1000)

    def test_valid_false_is_omitted(self):
        result = admit([self.base(consent=False)], 1000)
        self.assertEqual(result.selected, ())
        self.assertEqual(result.omitted, ("s1",))

    def test_valid_audio_and_ui_admitted(self):
        result = admit([self.base(), self.base(source_id="ui", modality="ui")], 1000)
        self.assertEqual(len(result.selected), 2)

if __name__ == "__main__":
    unittest.main()
