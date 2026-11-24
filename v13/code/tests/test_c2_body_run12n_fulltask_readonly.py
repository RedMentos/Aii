"""Read-only full-task diagnostic tests; no native or gate promotion."""
import importlib.util
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/c2_body_run12n_fulltask_readonly.py"
if not SCRIPT.exists():
    SCRIPT = Path(__file__).with_name("c2_body_run12n_fulltask_readonly.py")
spec = importlib.util.spec_from_file_location("fulltask", SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class FullTaskPosthocTests(unittest.TestCase):
    def test_explicit_correct_and_wrong_claims(self):
        self.assertEqual(m.explicit_faster_claim("Vale finishes sooner.", "Elm", "Vale"), "Vale")
        self.assertEqual(m.explicit_faster_claim("**Elm** finishes first.", "Elm", "Vale"), "Elm")
        self.assertEqual(m.explicit_faster_claim("Ridge will finish sooner.", "Pollen", "Ridge"), "Ridge")
        self.assertEqual(m.explicit_faster_claim("Lotus is faster.", "Kite", "Lotus"), "Lotus")

    def test_abstain_on_no_explicit_winner(self):
        self.assertEqual(m.explicit_faster_claim("The budget is insufficient.", "Elm", "Vale"), "ABSTAIN")
        self.assertEqual(m.explicit_faster_claim("Elmtree finishes sooner.", "Elm", "Vale"), "ABSTAIN")
        self.assertEqual(m.explicit_faster_claim("Elm does not finish sooner.", "Elm", "Vale"), "ABSTAIN")

    def test_contradictory_claims_fail_closed(self):
        self.assertEqual(m.explicit_faster_claim("Elm finishes first. Vale finishes sooner.", "Elm", "Vale"), "CONTRADICTORY")

    def test_missing_and_wrong_original_zip_rejected(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaisesRegex(ValueError, "ZIP_MISSING"):
                m.inspect_zip(root / "absent.zip")
            fake = root / "wrong.zip"
            fake.write_bytes(b"not original ZIP")
            with self.assertRaisesRegex(ValueError, "ORIGINAL_ZIP_HASH_MISMATCH"):
                m.inspect_zip(fake)
            link = root / "link.zip"
            link.symlink_to(fake)
            with self.assertRaisesRegex(ValueError, "ZIP_MISSING"):
                m.inspect_zip(link)

    def test_real_original_zip_if_provided(self):
        path = os.environ.get("V13_RUN12N_ORIGINAL_ZIP")
        if not path:
            self.skipTest("original ZIP not supplied to source-only test")
        result = m.inspect_zip(Path(path))
        self.assertEqual(result["manifest_verified"], 60)
        self.assertEqual(result["native_rows"], 16)
        self.assertEqual(result["stats"]["F_NATIVE_AUTO"]["numeric_points"], 1)
        self.assertEqual(result["stats"]["F_NATIVE_AUTO"]["faster_wrong"], 4)
        self.assertEqual(result["stats"]["A_C3_ONLY"]["faster_correct"], 3)
        self.assertTrue(all(x["strict_full_task"] == 0 for x in result["stats"].values()))
        self.assertFalse(result["step2_gate_promoted"])
        self.assertFalse(result["comparative_utility_proven"])


if __name__ == "__main__":
    unittest.main()