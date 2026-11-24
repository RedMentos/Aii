"""No-model adversarial checks for P2X calibration native executor."""
from __future__ import annotations
import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts import p2x_calibration_native_executor as native
from tests.test_p2x_calibration_instruction import synthetic_records


class P2XCalibrationNativeTests(unittest.TestCase):
    def test_record_exact_hash_and_native_metadata(self):
        prompt = native.cal.plan()[0]
        rec = native.record_call(prompt, '{"action":"UNKNOWN"}', .2,
                                 {"status": "FINAL"})
        self.assertEqual(rec["input_sha256"],
                         native.cal.sha(native.cal.canonical(prompt["messages"])))
        self.assertIsNone(rec["adapter_sha256"])
        self.assertEqual(rec["runner_binary_sha256"], native.cal.BINARY_SHA)
        self.assertEqual(rec["native_calls"], 1)

    def test_record_rejects_nonfinal_and_extra_oracle_field(self):
        prompt = native.cal.plan()[0]
        for metrics, duration in (({"status": "PARTIAL"}, .2),
                                  ({"status": "FINAL"}, -1),
                                  ({"status": "FINAL"}, 91)):
            with self.subTest(metrics=metrics, duration=duration):
                with self.assertRaisesRegex(ValueError, "NONFINAL"):
                    native.record_call(prompt, "{}", duration, metrics)
        prompt = dict(prompt, oracle_action="A")
        with self.assertRaisesRegex(ValueError, "PROMPT_SHAPE"):
            native.record_call(prompt, "{}", .1, {"status": "FINAL"})

    def test_verify_exact_raw_replay(self):
        records = synthetic_records()
        snapshot = native.cal.score(records)
        inputs = native.cal.plan()
        receipt = {
            "schema": native.SCHEMA,
            "status": "P2X_CALIBRATION_NATIVE_DIAGNOSTIC_NO_GATE",
            "recorded_calls": 360, "expected_calls": 360,
            "process_reaped": True, "adapter_sha256": None,
            "ag6_approved": False, "weight_updates": False,
            "redmi_measured": False, "whole_system_complete": False,
            "prereg_commit": "9352843a7ef6fb0eb7cc3307b98f12501e9685c2",
        }
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            for name, value in (("INPUTS.json", inputs),
                                ("RAW.json", records),
                                ("SCORE.json", snapshot)):
                (folder / name).write_bytes(native.cal.canonical(value))
                receipt[name.split(".")[0].lower() + "_sha256"] = (
                    native.native.file_sha(folder / name))
            (folder / "RECEIPT.json").write_bytes(native.cal.canonical(receipt))
            self.assertEqual(native.verify(folder)["native_calls"], 360)
            altered = copy.deepcopy(receipt)
            altered["ag6_approved"] = True
            (folder / "RECEIPT.json").write_bytes(native.cal.canonical(altered))
            with self.assertRaisesRegex(ValueError, "RECEIPT_GATE"):
                native.verify(folder)
            (folder / "RECEIPT.json").write_bytes(native.cal.canonical(receipt))
            records[0]["output"] = '{"action":"A"}'
            (folder / "RAW.json").write_bytes(native.cal.canonical(records))
            with self.assertRaisesRegex(ValueError, "SCORE_REPLAY"):
                native.verify(folder)

    def test_no_model_calls_without_pinned_home(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "PINNED_HOME"):
                native.run_native(Path(temp) / "missing", Path(temp) / "out")

    def test_cli_requires_explicit_home_or_verify(self):
        with self.assertRaises(SystemExit) as caught:
            native.main([])
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
