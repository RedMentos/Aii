"""P0X preregistered five-domain 150 held-out source cohort tests (software only)."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts import p0x_independent_source_holdout as p0x


class P0XSoftware(unittest.TestCase):
    def test_counts_balance_disjoint_domains_and_counterfactual(self):
        rows = p0x.fixtures()
        result = p0x.validate(rows)
        self.assertEqual(result["rows"], 180)
        self.assertEqual(result["holdout"], 150)
        self.assertEqual(result["calibration"], 30)
        self.assertEqual(result["heldout_action_balance"], {"A": 50, "B": 50, "NONE": 50})
        self.assertEqual(len({r["id"] for r in rows}), 180)
        self.assertEqual({r["domain"] for r in rows}, {d[0] for d in p0x.DOMAINS})
        self.assertTrue(all(r["id"].startswith("P0X") and len(r["id"]) == 19 for r in rows))
        self.assertTrue(all(not r["id"].startswith("HB0") for r in rows))
        self.assertFalse(result["canonical_gate_pass"])
        self.assertEqual(result["step2_status"], "UTILITY_FAIL")
        self.assertFalse(result["redmi_measured"])

    def test_both_sources_required_and_foreign_identity_firewall(self):
        rows = p0x.fixtures()
        for row in rows:
            current, b1, b2 = row["current"], row["b1_source"], row["b2_source"]
            foreign = p0x.foreign_sheet(row, rows)
            self.assertEqual(p0x.decide_sources(current, []), "UNKNOWN")
            self.assertEqual(p0x.decide_sources(current, [b1]), "UNKNOWN")
            self.assertEqual(p0x.decide_sources(current, [b2]), "UNKNOWN")
            self.assertEqual(p0x.decide_sources(current, [foreign]), "UNKNOWN")
            self.assertEqual(p0x.decide_sources(current, [b2, foreign]), "UNKNOWN")
            self.assertEqual(p0x.decide_sources(current, [b2, foreign, b1]),
                             row["oracle_action"])
            self.assertNotEqual(p0x._source_project(foreign), row["id"])

    def test_model_payload_oracle_separated_and_750_controls(self):
        prompts, answers = p0x.model_inputs(p0x.fixtures())
        self.assertEqual(len(prompts), 750)
        self.assertEqual(len(answers), 150)
        self.assertEqual({p["arm"] for p in prompts}, set(p0x.ARMS))
        self.assertEqual(len({(p["id"], p["arm"]) for p in prompts}), 750)
        self.assertEqual(len({a["id"] for a in answers}), 150)
        for p in prompts:
            raw = p0x.canonical(p).decode()
            for key in ("oracle_action", "sheet_index", "rule_index", "max_first", "max_second"):
                self.assertNotIn(key, raw)
        self.assertTrue(all("oracle_action" in a for a in answers))

    def test_reproducibility_tamper_duplicate_and_single_source_red(self):
        rows = p0x.fixtures()
        self.assertEqual(p0x.sha(p0x.canonical(rows)),
                         p0x.sha(p0x.canonical(p0x.fixtures())))
        corrupted = deepcopy(rows)
        corrupted[0]["b1_source"] = corrupted[1]["b1_source"]
        with self.assertRaisesRegex(ValueError, "P0X_SOURCE_OR_ORACLE_TAMPER_RED"):
            p0x.validate(corrupted)
        duplicate = deepcopy(rows)
        duplicate[0] = deepcopy(duplicate[1])
        with self.assertRaisesRegex(ValueError, "P0X_ID_COVERAGE_RED"):
            p0x.validate(duplicate)
        first = rows[0]
        self.assertEqual(p0x.decide_sources(first["current"], [first["b2_source"],
                          p0x.foreign_sheet(first, rows)]), "UNKNOWN")

    def test_export_requires_external_pin_and_fresh_path(self):
        rows = p0x.fixtures()
        digest = p0x.sha(p0x.canonical(rows))
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, "P0X_EXTERNAL_FIXTURE_PIN_RED"):
                p0x.export(root / "wrong", "0" * 64)
            self.assertFalse((root / "wrong").exists())
            manifest = p0x.export(root / "fresh", digest)
            self.assertEqual(manifest["model_inputs"], 750)
            self.assertEqual(manifest["answers"], 150)
            for name in ("inputs.jsonl", "answers.jsonl"):
                data = (root / "fresh" / name).read_bytes()
                self.assertEqual(p0x.sha(data), manifest["sha256"][name])
                self.assertTrue(all(json.loads(line) for line in data.splitlines()))
            with self.assertRaisesRegex(ValueError, "P0X_FRESH_OUTPUT_REQUIRED"):
                p0x.export(root / "fresh", digest)
            self.assertFalse(manifest["canonical_gate_pass"])
            self.assertFalse(manifest["whole_system_complete"])


if __name__ == "__main__":
    unittest.main()
