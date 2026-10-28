"""Run85 real model-less Age0 doctor must preserve negative acceptance gates."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.operator import Operator
from v13.runtime import Runtime


class TestRun85DoctorNegativeGates(unittest.TestCase):
    def _open(self, home):
        r = Runtime(home)
        r.sleep.cycle.set_policy("enabled", "off")
        return r, Operator(r)

    def _assert_negative_doctor(self, d):
        self.assertEqual(d["build"], "0.1.0-age0-lab")
        self.assertFalse(d["canonical_architecture_complete"])
        self.assertEqual(d["data_integrity_errors"], [])
        self.assertEqual(d["learning_mode"], "RECORD_ONLY")
        self.assertTrue({"language", "body", "gist", "needle"} <= set(d["missing_models"]))
        self.assertFalse(d["native_runner_exists"])
        self.assertFalse(d["needle_embedding_worker_exists"])
        caps = d["native_capabilities"]
        self.assertEqual(caps["latent_injection"]["status"], "OFF")
        self.assertEqual(caps["live_receiver_latent_tap"]["status"], "UNAVAILABLE")
        self.assertEqual(caps["body_training"]["status"], "UNAVAILABLE")
        self.assertEqual(caps["model_callable_tools"]["status"], "OFF")
        self.assertIn("OFF", d["gates"]["B3_latents"])
        self.assertIn("OFF", d["gates"]["higher_age"])
        self.assertIn("UNAVAILABLE", d["gates"]["vision_audio"])
        ledger = d["completion_ledger_summary"]
        self.assertEqual(ledger["B3_LATENT"], "BLOCKED_BY_PROOF")
        self.assertEqual(ledger["BODY_JEPA"], "NOT_STARTED")
        self.assertEqual(ledger["STEP1_JEF_VERTICAL"], "PARTIAL")

    def test_doctor_ledger_gates_and_restart_do_not_promote_models(self):
        with tempfile.TemporaryDirectory(prefix="v13-run85-doctor-") as td:
            home = Path(td)
            r, op = self._open(home)
            try:
                with patch.object(r.pool, "get", side_effect=AssertionError("NATIVE_MODEL_CALLED")):
                    doctor = json.loads(op.run(":doctor"))
                    full = json.loads(op.run(":doctor full"))
                    ledger = json.loads(op.run(":ledger"))
                    gates = json.loads(op.run(":gates summary"))
                self._assert_negative_doctor(doctor)
                self._assert_negative_doctor(full)
                self.assertIn("rows", ledger)
                self.assertTrue(ledger["rows"])
                self.assertIn("gates", gates)
                self.assertTrue(any(status != "GREEN" for status in gates["gates"].values()))
                self.assertIn("GREEN", gates["definition"])
                for name in ("schema_registry", "completion_ledger", "logging_policy", "open_questions"):
                    artifact = Path(full["build_artifacts"][name])
                    self.assertTrue(artifact.is_file())
                    self.assertEqual(artifact.parent, home / "exports")
                self.assertEqual(json.loads(op.run(":models")), {})
            finally:
                r.close()

            r, op = self._open(home)
            try:
                with patch.object(r.pool, "get", side_effect=AssertionError("NATIVE_MODEL_CALLED")):
                    self._assert_negative_doctor(json.loads(op.run(":doctor")))
                self.assertEqual(json.loads(op.run(":status"))["learning"], "RECORD_ONLY")
            finally:
                r.close()


if __name__ == "__main__":
    unittest.main()
