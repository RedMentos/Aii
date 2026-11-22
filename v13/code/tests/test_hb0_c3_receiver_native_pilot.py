"""HB0c native pilot plan and scorer software tests; no model execution."""
from __future__ import annotations

from copy import deepcopy
import math
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from scripts import hb0_split_information_cohort as hb0
from scripts import hb0_c3_receiver_native_pilot as pilot


class HB0CNativePilotPreflight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = hb0.fixtures()
        cls.pin = hb0._sha(cls.rows)
        cls.plan = pilot.plan(cls.rows, cls.pin)

    def synthetic_rows(self):
        # Deliberately synthetic scorer input, NOT a native test or gate.
        return [
            {"id": p["id"], "arm": p["arm"], "status": "FINAL",
             "input_sha256": pilot.sha(pilot.canonical(p["messages"])),
             "output": "UNKNOWN", "duration_s": 1.0,
             "metrics": {"status": "FINAL"}, "model_sha256": pilot.MODEL_SHA,
             "model_called": True, "native_calls": 1, "seed": pilot.SEED}
            for p in self.plan
        ]

    def test_exact_six_by_four_plan_and_no_oracle(self):
        self.assertEqual(len(self.plan), 24)
        self.assertEqual(len({p["id"] for p in self.plan}), 6)
        for index in range(0, 24, 4):
            group = self.plan[index:index + 4]
            self.assertEqual([p["arm"] for p in group], list(pilot.ARM_ORDER))
            self.assertEqual(len({p["id"] for p in group}), 1)
            for p in group:
                self.assertNotIn("oracle_action", str(p))
                self.assertNotIn("sheet_index", str(p))
                self.assertNotIn("rule_index", str(p))
        self.assertEqual(pilot.FAMILY, 5)
        self.assertEqual(pilot.SEED, 13)
        self.assertEqual(pilot.TOKENS, 64)

    def test_missing_external_pin_refused(self):
        with self.assertRaisesRegex(ValueError, "HB0_EXTERNAL_SHA_REQUIRED"):
            pilot.plan(self.rows, "")
        with self.assertRaisesRegex(ValueError, "HB0_COHORT_DRIFT_RED"):
            pilot.plan(self.rows, "0" * 64)

    def test_strict_first_commitment_parser(self):
        self.assertEqual(pilot.action("Choose Option A. Remaining budget: 5 euros."), "A")
        self.assertEqual(pilot.action("I select Option B."), "B")
        self.assertEqual(pilot.action("Neither option is eligible."), "NONE")
        self.assertEqual(pilot.action("UNKNOWN: rules missing"), "UNKNOWN")
        self.assertEqual(pilot.action("Option A costs 5, Option B costs 7"), "UNPARSEABLE")
        self.assertEqual(pilot.action("The answer might be A"), "UNPARSEABLE")
        self.assertEqual(pilot.action(None), "UNPARSEABLE")

    def test_posthoc_scorer_does_not_promote(self):
        score = pilot.score(self.synthetic_rows(), self.rows, self.pin)
        self.assertEqual(score["status"], "POSTHOC_EXPLORATORY_NO_GATE")
        self.assertEqual(score["rows"], 24)
        self.assertEqual(set(score["per_arm"]), set(pilot.ARM_ORDER))
        self.assertFalse(score["canonical_gate_pass"])
        self.assertEqual(score["step2_status"], "UTILITY_FAIL")
        self.assertEqual(score["b3_status"], "FAIL")
        self.assertEqual(score["jepa_weight"], 0)
        self.assertFalse(score["whole_system_complete"])

    def test_duplicate_or_missing_native_row_refused(self):
        records = self.synthetic_rows()
        with self.assertRaisesRegex(ValueError, "HB0C_RAW_COUNT_RED"):
            pilot.score(records[:-1], self.rows, self.pin)
        duplicate = deepcopy(records)
        duplicate[1] = deepcopy(duplicate[0])
        with self.assertRaisesRegex(ValueError, "HB0C_RAW_IDENTITY_RED"):
            pilot.score(duplicate, self.rows, self.pin)

    def test_prompt_and_model_identity_tamper_refused(self):
        for field, value in (("input_sha256", "0" * 64),
                             ("model_sha256", "f" * 64),
                             ("seed", 17)):
            with self.subTest(field=field):
                records = self.synthetic_rows()
                records[0][field] = value
                with self.assertRaisesRegex(ValueError, "HB0C_NATIVE_ROW_INVALID"):
                    pilot.score(records, self.rows, self.pin)

    def test_nonfinite_and_negative_latency_refused(self):
        for value in (float("nan"), float("inf"), -1, True):
            with self.subTest(value=value):
                records = self.synthetic_rows()
                records[0]["duration_s"] = value
                with self.assertRaisesRegex(ValueError, "HB0C_NONFINITE_LATENCY_RED"):
                    pilot.score(records, self.rows, self.pin)

    def test_native_platform_and_missing_home_fail_closed(self):
        with TemporaryDirectory() as d:
            with patch.object(pilot.platform, "system", return_value="Windows"):
                with self.assertRaisesRegex(ValueError, "HB0C_LINUX_X86_64_ONLY"):
                    pilot._admit(Path(d))
            with self.assertRaisesRegex(ValueError, "HB0C_PINNED_HOME_REQUIRED"):
                pilot.run_native(Path(d), Path(d) / "output", self.pin)


if __name__ == "__main__":
    unittest.main()
