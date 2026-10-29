"""Run101 acceptance guards; software only, never native or model mocks as evidence."""
import unittest

from scripts.run101_two_project_c3_native import _native_ok, _preflight_ok, REVISION


REF = {"source_id": "src_test", "sha256": "a" * 64,
       "modality": "text", "char_start": 0, "char_end": 8}


class Run101GateTests(unittest.TestCase):
    def test_native_accepts_only_exact_project_amount_and_teardown(self):
        good = {"status": "FINAL", "native_calls": 1,
                "model_called": True, "process_reaped": True,
                "model_revision": REVISION, "source_ref": REF,
                "answer": "The budget for Project Dovan is 731 Euros."}
        self.assertTrue(_native_ok(good, "Dovan", "731 Euro", REF))
        for changes in (
            {"status": "UNVERIFIED_NATIVE_ANSWER"},
            {"native_calls": 0},
            {"process_reaped": False},
            {"model_revision": "other"},
            {"source_ref": {"sha256": "wrong"}},
            {"answer": "Project Mira has 731 Euros."},
            {"answer": "Project Dovan has 942 Euros."},
            {"answer": "Project Dovan has 731 Euros and 942 Euros."},
            {"answer": "Project Dovan has 731.000 Euros."},
            {"answer": "Project Dovan has 731 Euros but Project Mira has 942 Euros."},
        ):
            with self.subTest(changes=changes):
                self.assertFalse(_native_ok(dict(good, **changes), "Dovan", "731 Euro", REF))

    def test_missing_source_and_out_of_scope_never_leak_numbers(self):
        for status in ("CLARIFY", "NOT_APPLICABLE"):
            self.assertTrue(_preflight_ok({
                "status": status, "native_calls": 0,
                "model_called": False, "answer": "No verified budget."
            }, status))
            self.assertFalse(_preflight_ok({
                "status": status, "native_calls": 0,
                "model_called": False, "answer": "731 Euro"
            }, status))
            self.assertFalse(_preflight_ok({
                "status": status, "native_calls": 1,
                "model_called": True, "answer": ""
            }, status))


if __name__ == "__main__":
    unittest.main()
