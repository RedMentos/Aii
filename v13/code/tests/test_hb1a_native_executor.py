"""HB1a native executor fail-closed software tests; no model execution."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from scripts import hb1a_native_executor as native
from scripts import hb1a_two_body_native_pilot as plan


class HB1ANativeAdmission(unittest.TestCase):
    def test_platform_refusal_before_any_native_calls(self):
        with TemporaryDirectory() as temp:
            with patch.object(native.platform, "system", return_value="Windows"):
                with self.assertRaisesRegex(ValueError, "HB1A_LINUX_X86_64_ONLY"):
                    native.admit(Path(temp))

    def test_missing_home_refusal_before_any_native_calls(self):
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "HB1A_PINNED_HOME_REQUIRED"):
                native.run_native(Path(temp), Path(temp) / "raw", plan.FIXTURE)
            self.assertFalse((Path(temp) / "raw").exists())

    def test_schema_and_negative_gates_remain_unpromoted(self):
        self.assertEqual(plan.SEED, 13)
        self.assertEqual(plan.BODY_TOKENS, 96)
        self.assertEqual(plan.C3_TOKENS, 48)
        self.assertEqual(plan.OVERALL_SECONDS, 3000)
        self.assertEqual(plan.C3_SCHEMA["properties"]["action"]["enum"],
                         ["A", "B", "NONE", "UNKNOWN"])
        self.assertFalse(plan.C3_SCHEMA["additionalProperties"])
        self.assertEqual(len(plan.MODEL_SHAS), 3)


if __name__ == "__main__":
    unittest.main()
