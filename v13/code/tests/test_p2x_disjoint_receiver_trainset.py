"""P2X disjoint source-composition corpus source-only adversarial tests."""
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p2x_disjoint_receiver_trainset.py"
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("p2x_disjoint", SCRIPT)
p2x = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p2x)


class P2XTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = p2x.fixtures()

    def test_exact_360_and_partitions(self):
        x = p2x.validate(self.rows)
        self.assertEqual((x["train"], x["validation"], x["calibration"]), (252, 72, 36))
        self.assertTrue(x["no_p0x_source_overlap"])
        self.assertFalse(x["whole_system_complete"])

    def test_deterministic_fixture_hash(self):
        self.assertEqual(p2x.sha(p2x.canonical(self.rows)),
                         p2x.sha(p2x.canonical(p2x.fixtures())))

    def test_per_family_counterfactual_balance(self):
        for family in range(60):
            group = [r for r in self.rows if r["family"] == family]
            self.assertEqual({a: sum(r["oracle_action"] == a for r in group)
                              for a in ("A", "B", "NONE")},
                             {"A": 2, "B": 2, "NONE": 2})

    def test_both_sources_and_single_source_ablation(self):
        for row in self.rows[:24]:
            self.assertEqual(p2x.decide_sources(row["current"], [row["b1_source"], row["b2_source"]]),
                             row["oracle_action"])
            self.assertEqual(p2x.decide_sources(row["current"], [row["b1_source"]]), "UNKNOWN")
            self.assertEqual(p2x.decide_sources(row["current"], [row["b2_source"]]), "UNKNOWN")

    def test_foreign_b1_fails_closed(self):
        for row in self.rows[:24]:
            foreign = p2x.foreign_sheet(row, self.rows)
            self.assertNotEqual(p2x._source_project(foreign), row["id"])
            self.assertEqual(p2x.decide_sources(row["current"], [row["b2_source"], foreign]), "UNKNOWN")

    def test_train_and_validation_balances(self):
        train, val, answers = p2x.training_and_validation(self.rows)
        self.assertEqual((len(train), len(val), len(answers)), (504, 360, 72))
        self.assertEqual(sum(r["target_action"] == "UNKNOWN" for r in train), 252)
        for a in ("A", "B", "NONE"):
            self.assertEqual(sum(r["target_action"] == a for r in train), 84)
        for arm in p2x.NEGATIVES:
            self.assertEqual(sum(r["arm"] == arm for r in train), 63)
        self.assertFalse(any("oracle_action" in r["messages"][0]["content"] for r in train + val))

    def test_tampered_source_rejected(self):
        rows = [dict(r) for r in self.rows]
        rows[0]["b1_source"] = "wrong"
        with self.assertRaisesRegex(ValueError, "TAMPER"):
            p2x.validate(rows)

    def test_missing_row_rejected(self):
        with self.assertRaisesRegex(ValueError, "COUNT"):
            p2x.validate(self.rows[:-1])

    def test_duplicate_project_id_rejected(self):
        rows = [dict(r) for r in self.rows]
        rows[0]["id"] = rows[1]["id"]
        with self.assertRaisesRegex(ValueError, "ID"):
            p2x.validate(rows)

    def test_export_external_hash_required(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "PIN"):
                p2x.export(Path(d) / "out", "0" * 64)

    def test_export_manifest_and_exclusive_creation(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "export"
            pin = p2x.sha(p2x.canonical(self.rows))
            m = p2x.export(out, pin)
            self.assertEqual(m["train_examples"], 504)
            self.assertEqual(m["validation_inputs"], 360)
            for name, digest in m["sha256"].items():
                self.assertEqual(hashlib.sha256((out / name).read_bytes()).hexdigest(), digest)
            self.assertEqual(json.loads((out / "manifest.json").read_text())["fixture_sha256"], pin)
            with self.assertRaisesRegex(ValueError, "FRESH_OUTPUT"):
                p2x.export(out, pin)


if __name__ == "__main__":
    unittest.main()
