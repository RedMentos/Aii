"""Run105 validator tests: exact sourced native answer, negative controls, no authority."""
import unittest

from scripts.run105_human_tty_c3_native import (
    _age0, _native_ok, _preflight_ok, MODEL_SHA, REVISION,
)

REF = {"source_id": "synthetic", "sha256": "a" * 64, "char_start": 0,
       "char_end": 8, "modality": "text"}


class HumanSourceNativeValidation(unittest.TestCase):
    def test_accept_exact_project_euro_source_and_reaped_model(self):
        value = {"status": "FINAL", "answer": "The budget for Project Elyra is 615 Euros.",
                 "native_calls": 1, "model_called": True, "process_reaped": True,
                 "model_revision": REVISION, "source_ref": REF}
        self.assertTrue(_native_ok(value, REF))
        for key, replacement in (
            ("status", "READY"), ("native_calls", 0),
            ("model_called", False), ("process_reaped", False),
            ("model_revision", "unverified"), ("source_ref", {}),
            ("answer", "The budget for Project Dovan is 615 Euros."),
            ("answer", "The budget for Project Elyra is 616 Euros."),
            ("answer", "The budget for Project Elyra is 615 Euros and 12 extras."),
            ("answer", "Project Elyra has -615 Euros."),
            ("answer", "Project Elyra has 615 Euros, also Project Dovan."),
        ):
            with self.subTest(key=key, replacement=replacement):
                changed = dict(value, **{key: replacement})
                self.assertFalse(_native_ok(changed, REF))

    def test_negative_preflight_must_not_expose_numbers_or_call_model(self):
        clarify = {"status": "CLARIFY", "answer":
                   "I don't have a verified budget for Project dovan. Could you provide it?",
                   "model_called": False, "native_calls": 0}
        self.assertTrue(_preflight_ok(clarify, "CLARIFY"))
        self.assertFalse(_preflight_ok(dict(clarify, answer="615 Euro"), "CLARIFY"))
        self.assertFalse(_preflight_ok(dict(clarify, native_calls=1), "CLARIFY"))
        self.assertFalse(_preflight_ok(dict(clarify, model_called=True), "CLARIFY"))
        self.assertTrue(_preflight_ok(dict(clarify, status="NOT_APPLICABLE",
                                          answer=""), "NOT_APPLICABLE"))

    def test_age0_negative_gates(self):
        cfg = {"system_stage": 0, "learning_mode": "RECORD_ONLY",
               "latents_enabled": False, "jepa_weight": 0}
        self.assertTrue(_age0(cfg))
        for key, value in (("system_stage", 1), ("learning_mode", "ACTIVE"),
                           ("latents_enabled", True), ("jepa_weight", 0.01)):
            with self.subTest(key=key):
                self.assertFalse(_age0(dict(cfg, **{key: value})))
        self.assertEqual(len(MODEL_SHA), 64)


if __name__ == "__main__":
    unittest.main()
