"""Strict A5 admission regressions; synthetic only, no Android proof."""
import unittest
from v13.a5_admission import admit_a5, A5AdmissionError


def packet(source_id="mic-1"):
    return {"schema": "v13.a5.audio/1", "source": {"authorized": True, "id": source_id, "modality": "audio"},
            "status": "FINAL", "action_authority": False, "learning_authority": False}


class A5StrictAdmissionTest(unittest.TestCase):
    def test_valid(self):
        result = admit_a5(packet(), consent=True)
        self.assertEqual(result["modality"], "audio")
        self.assertTrue(result["requires_source_lookup"])
        self.assertFalse(result["action_authority"])

    def test_truthy_consent_is_not_authorization(self):
        for value in (1, "yes", [True], None, False):
            with self.subTest(value=value), self.assertRaises(PermissionError):
                admit_a5(packet(), consent=value)

    def test_boolean_and_noninteger_budget_rejected(self):
        for value in (True, False, 256.0, "256", None, 159, 4097):
            with self.subTest(value=value), self.assertRaises(A5AdmissionError):
                admit_a5(packet(), consent=True, max_bytes=value)

    def test_control_characters_in_source_rejected(self):
        for value in ("mic\\nspoof", "mic\\rspoof", "mic\\x00spoof", "mic\\tspoof", " "):
            with self.subTest(value=value), self.assertRaises(A5AdmissionError):
                admit_a5(packet(value), consent=True)

    def test_untrusted_authority_fails(self):
        for key in ("action_authority", "learning_authority"):
            p = packet()
            p[key] = True
            with self.assertRaises(A5AdmissionError):
                admit_a5(p, consent=True)


if __name__ == "__main__":
    unittest.main()
