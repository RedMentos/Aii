"""P0X native600 independent raw auditor software and original-artifact tests."""
import json
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from scripts import p0x_native600_raw_independent_audit as audit


class P0X600IndependentRaw(unittest.TestCase):
    def test_strict_action_json(self):
        self.assertEqual(audit.strict_action('{"action":"A"}'), "A")
        self.assertEqual(audit.strict_action('{"action":"NONE"}'), "NONE")
        self.assertEqual(audit.strict_action('{"action":"A","reason":"x"}'), "UNPARSEABLE")
        self.assertEqual(audit.strict_action('Option B'), "UNPARSEABLE")
        self.assertEqual(audit.strict_action('{"action":"C"}'), "UNPARSEABLE")

    def test_unsafe_paths(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "UNSAFE_PATH"):
                audit.safe_file(Path(tmp), "../outside")
            with self.assertRaisesRegex(ValueError, "UNSAFE_PATH"):
                audit.safe_file(Path(tmp), "/etc/passwd")

    def test_missing_pin_and_root_rejected(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex((ValueError, FileNotFoundError), ""):
                audit.verify(Path(tmp), {"schema": "v13.p0x.native600_external_pins.v1"})

    def test_original_artifact_and_stage_tamper(self):
        original = os.environ.get("P0X_ORIGINAL_600_EVIDENCE")
        pin_path = os.environ.get("P0X_ORIGINAL_600_PINS")
        if not original or not pin_path:
            self.skipTest("original 600-call artifact available only in review CI")
        root = Path(original)
        pins = json.loads(Path(pin_path).read_bytes())
        result = audit.verify(root, pins)
        self.assertEqual(result["native_rows"], 600)
        self.assertEqual(sum(x["exact"] + x["wrong_committed"] +
                             x["unknown"] + x["unparseable"]
                             for x in result["per_arm"].values()), 600)
        self.assertFalse(result["canonical_gate_pass"])
        with TemporaryDirectory() as tmp:
            clone = Path(tmp) / "evidence"
            shutil.copytree(root, clone)
            (clone / "NATIVE_EXIT.txt").write_text("1\n")
            with self.assertRaisesRegex(ValueError, "CHECKSUM_MISMATCH|STAGE_NATIVE"):
                audit.verify(clone, pins)


if __name__ == "__main__":
    unittest.main()
