import unittest
from v13.a5_admission import admit_a5, A5AdmissionError


def packet():
    return {"schema": "v13.a5.raw-ear/1",
            "source": {"id": "synthetic-a", "authorized": True, "modality": "audio"},
            "status": "PROVISIONAL", "teacher": {"text": "private example"},
            "action_authority": False, "learning_authority": False}


class A5AdmissionTests(unittest.TestCase):
    def test_reference_without_raw_text(self):
        result = admit_a5(packet(), consent=True, max_bytes=400)
        self.assertNotIn("private example", str(result))
        self.assertTrue(result["requires_source_lookup"])
        self.assertFalse(result["learning_authority"])

    def test_consent_and_source_fail_closed(self):
        with self.assertRaises(PermissionError):
            admit_a5(packet())
        p = packet()
        p["source"]["authorized"] = False
        with self.assertRaises(A5AdmissionError):
            admit_a5(p, consent=True)

    def test_mutation_changes_digest(self):
        a = admit_a5(packet(), consent=True, max_bytes=400)
        p = packet()
        p["teacher"]["text"] = "changed"
        b = admit_a5(p, consent=True, max_bytes=400)
        self.assertNotEqual(a["source_sha256"], b["source_sha256"])

    def test_reject_authority_and_oversize(self):
        p = packet()
        p["action_authority"] = True
        with self.assertRaises(A5AdmissionError):
            admit_a5(p, consent=True)
        p = packet()
        p["teacher"]["text"] = "x" * 65536
        with self.assertRaises(A5AdmissionError):
            admit_a5(p, consent=True)

    def test_budget_never_silently_truncates(self):
        with self.assertRaises(A5AdmissionError):
            admit_a5(packet(), consent=True, max_bytes=160)


if __name__ == "__main__":
    unittest.main()
