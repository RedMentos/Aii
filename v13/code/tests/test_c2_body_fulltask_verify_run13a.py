"""Run13A independent verifier guard tests, no native or semantic claim."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from scripts import c2_body_fulltask_verify_run13a as v
from scripts import c2_body_fulltask_run13a as m

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/c2_body_fulltask_run13a_seed211_20261030.json"


class Run13AVerifierTests(unittest.TestCase):
    def test_verifier_has_distinct_nonpromotion_schema(self):
        self.assertNotEqual(v.SCHEMA, m.SCHEMA)
        self.assertIn("comparative_utility_proven", v.NEGATIVE)
        self.assertIn("step2_gate_promoted", v.NEGATIVE)

    def test_read_json_missing_rejected(self):
        with TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "RAW_MISSING"):
                v.read_json(Path(td) / "missing.json")

    def test_read_json_symlink_rejected(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "source.json"
            p.write_text('{"ok": true}')
            q = Path(td) / "link.json"
            q.symlink_to(p)
            with self.assertRaisesRegex(ValueError, "RAW_MISSING"):
                v.read_json(q)

    def test_read_json_oversize_rejected(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "huge.json"
            p.write_bytes(b" " * (v.MAX_JSON_BYTES + 1))
            with self.assertRaisesRegex(ValueError, "RAW_MISSING"):
                v.read_json(p)

    def test_verify_empty_directory_rejected(self):
        with TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "RAW_MISSING"):
                v.verify(td, FIXTURE)

    def test_wire_tuple_round_trip_matches_json(self):
        self.assertEqual(v.wire({"spans": [(1, 2)]}),
                         {"spans": [[1, 2]]})

    def test_frozen_fixture_in_verifier(self):
        self.assertEqual(m.load_fixture(FIXTURE)["seed"], 211)
        self.assertEqual(len(m.ARM_ORDER), 8)


if __name__ == "__main__":
    unittest.main()
