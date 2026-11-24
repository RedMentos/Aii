"""Run115D: extracted phone archive must retain public frozen source cohorts.

Software distribution integrity only; no native evidence or gate promotion.
"""
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts import package_source as pack

FIXTURES = (
    "docs/fixtures/RUN114B_JEF_B1B2_C3_SEED947.json",
    "docs/fixtures/RUN115B_JEF_B1B2_C3_SEED971.json",
)


class PhoneFixtureParityRun115D(unittest.TestCase):
    def test_required_frozen_cohorts_and_scope(self):
        self.assertTrue(set(FIXTURES) <= pack.PHONE_REQUIRED_FIXTURES)
        for rel in FIXTURES:
            self.assertTrue(pack.phone_needed(Path(rel)))
        self.assertTrue(pack.phone_needed(Path("docs/fixtures/other-public.json")))
        self.assertFalse(pack.phone_needed(Path("docs/private/private.json")))
        self.assertFalse(pack.phone_needed(Path("docs/fixtures/not-json.txt")))

    def test_phone_roundtrip_exact_json_and_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "source"
            (root / "v13").mkdir(parents=True)
            (root / "v13/__init__.py").write_text("# source\n")
            for i, rel in enumerate(FIXTURES):
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes((json.dumps({"synthetic": True, "i": i}) + "\n").encode())
            extra = root / "docs/fixtures/other-public.json"
            extra.write_bytes(b'{"extra":true}\n')
            private = root / "docs/private/private.json"
            private.parent.mkdir(parents=True)
            private.write_bytes(b'{"private":true}\n')
            out = Path(temp) / "phone.zip"
            with patch.object(pack, "PHONE_REQUIRED_FIXTURES", set(FIXTURES)):
                receipt = pack.package(root, out, phone_install=True)
            self.assertFalse(receipt["native_models_launched"])
            self.assertFalse(receipt["canonical_gate_pass"])
            with zipfile.ZipFile(out) as z:
                self.assertIsNone(z.testzip())
                manifest = json.loads(z.read("V13-Phone/WORKSPACE_FILES.json"))
                for rel in (*FIXTURES, "docs/fixtures/other-public.json"):
                    raw = (root / rel).read_bytes()
                    self.assertEqual(z.read("V13-Phone/" + rel), raw)
                    self.assertEqual(manifest["files"][rel], sha256(raw).hexdigest())
                self.assertNotIn("docs/private/private.json", manifest["files"])

    def test_missing_frozen_cohort_fails_before_zip(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "source"
            root.mkdir()
            first = root / FIXTURES[0]
            first.parent.mkdir(parents=True)
            first.write_text("{}\n")
            out = Path(temp) / "phone.zip"
            with patch.object(pack, "PHONE_REQUIRED_FIXTURES", set(FIXTURES)):
                with self.assertRaisesRegex(ValueError, "required fixture missing"):
                    pack.package(root, out, phone_install=True)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
