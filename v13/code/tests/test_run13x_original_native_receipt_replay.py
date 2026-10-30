"""Run13X original ZIP replay and negative counterexamples; no native rerun."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts import run13x_original_native_receipt_replay as x
from v13.agi.jef_c3_shadow_fallback_run13v import _native_receipt_ok

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run13t_c3_verbatim_seed283_20261030.json"


class OriginalNativeReceiptReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("RUN13X_ORIGINAL_ZIP")
        if not path or not Path(path).is_file():
            raise RuntimeError("RUN13X_REQUIRES_EXACT_ORIGINAL_NATIVE_ZIP")
        cls.original = Path(path)
        cls.cases = x.load_cases(FIXTURE)

    def raw(self, index=0, arm="COPY_BASELINE"):
        with zipfile.ZipFile(self.original) as z:
            return x.strict_json(z.read(f"pilot/raw/{index:02d}_{arm}.json"))

    def test_exact_original_native_zip_readonly_counterfactual(self):
        result = x.replay(self.original, FIXTURE)
        self.assertEqual(result["original_native_rows"], 16)
        self.assertEqual(result["distinct_native_pids"], 16)
        self.assertEqual(result["counterfactual_c3_facts_candidates"], 3)
        self.assertEqual(result["counterfactual_jef_fallback_candidates"], 13)
        self.assertEqual(result["original_diagnostic"], "FIDELITY_HURT")
        self.assertFalse(result["source_store_rechecked"])
        self.assertFalse(result["native_receipt_attested"])
        self.assertFalse(result["utility_gate_promoted"])
        self.assertEqual(result["learning_mode"], "RECORD_ONLY")
        self.assertEqual(result["step2_status"], "UTILITY_FAIL")
        self.assertEqual(result["b3_status"], "NO_PROMOTION")
        self.assertEqual(result["body_jepa_status"], "UNAVAILABLE")
        self.assertEqual(result["jepa_weight"], 0)
        self.assertFalse(result["redmi_measured"])
        self.assertFalse(result["whole_system_complete"])

    def test_actual_native_output_hash_and_length_are_bound(self):
        row = self.raw()
        audit = x.audit_row(row, self.cases[0], 0, "COPY_BASELINE")
        self.assertTrue(_native_receipt_ok(audit["receipt"], audit["snapshot"],
                                            audit["output"]))
        altered = x.expected_answer(self.cases[0])
        self.assertNotEqual(altered, audit["output"])
        self.assertFalse(_native_receipt_ok(audit["receipt"], audit["snapshot"],
                                             altered))

    def test_receipt_tamper_model_prompt_source_hash_bytes_and_bool_calls(self):
        audit = x.audit_row(self.raw(), self.cases[0], 0, "COPY_BASELINE")
        receipt, snapshot, output = audit["receipt"], audit["snapshot"], audit["output"]
        for field, bad in (
            ("model_sha256", "0"*64),
            ("prompt_sha256", "0"*64),
            ("source_event_id", "evt_fake"),
            ("native_output_sha256", "0"*64),
            ("native_output_bytes", len(output.encode("utf-8"))+1),
            ("native_calls", True),
            ("native_output_bytes", True),
            ("native_pid", True),
        ):
            with self.subTest(field=field):
                changed = dict(receipt, **{field: bad})
                self.assertFalse(_native_receipt_ok(changed, snapshot, output))

    def test_row_schema_gate_and_native_lifecycle_counterexamples(self):
        row = self.raw()
        for field, bad in (
            ("native_calls", True),
            ("native_status", "NOT_RUN"),
            ("native_reaped", False),
            ("learning_mode", "ONLINE"),
            ("jepa_weight", 1),
            ("model_revision", "wrong"),
            ("final_output", None),
        ):
            with self.subTest(field=field):
                changed = dict(row, **{field: bad})
                with self.assertRaises(ValueError):
                    x.audit_row(changed, self.cases[0], 0, "COPY_BASELINE")
        with self.assertRaises(ValueError):
            x.audit_row(dict(row, unknown_field=1), self.cases[0], 0, "COPY_BASELINE")

    def test_json_duplicate_and_nonfinite_fail_closed(self):
        for raw in (b'{"a":1,"a":2}', b'{"x":NaN}',
                    b'{"x":Infinity}', b'[]'):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    x.strict_json(raw)

    def test_original_zip_byte_tamper_and_wrong_fixture_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            changed = Path(td) / "altered.zip"
            original = bytearray(self.original.read_bytes())
            original[-1] ^= 1
            changed.write_bytes(original)
            with self.assertRaises(ValueError):
                x.replay(changed, FIXTURE)
            fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
            fixture["cases"][0]["budget"] += 1
            wrong = Path(td) / "wrong.json"
            wrong.write_text(json.dumps(fixture), encoding="utf-8")
            with self.assertRaises(ValueError):
                x.replay(self.original, wrong)


if __name__ == "__main__":
    unittest.main()
