"""HB0b model-input firewall, arm matching and closed export integrity."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts import hb0_arm_export as arms
from scripts import hb0_split_information_cohort as hb0


class HB0ArmExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = hb0.fixtures()
        cls.pin = hb0._sha(cls.rows)
        cls.prompts, cls.answers = arms.build(cls.rows, cls.pin)

    def test_all_six_arms_matched_and_no_oracle_in_payload(self):
        self.assertEqual(len(self.prompts), 900)
        self.assertEqual(len(self.answers), 150)
        self.assertEqual(len({(p["id"], p["arm"]) for p in self.prompts}), 900)
        for p in self.prompts:
            self.assertEqual([m["role"] for m in p["messages"]], ["system", "user"])
            payload = json.dumps(p)
            for forbidden in ("oracle_action", "sheet_index", "rule_index", "family"):
                self.assertNotIn(forbidden, payload)
        for a in self.answers:
            self.assertIn(a["oracle_action"], ("A", "B", "NONE"))

    def test_each_arm_has_only_authorized_source_text(self):
        row = self.rows[0]
        rendered = {p["arm"]: p for p in self.prompts if p["id"] == row["id"]}
        self.assertEqual(set(rendered), set(arms.ARMS))
        user = {arm: p["messages"][1]["content"] for arm, p in rendered.items()}
        for arm in arms.ARMS:
            self.assertIn(row["current"], user[arm])
        self.assertNotIn(row["b1_source"], user["c3_only"])
        self.assertNotIn(row["b2_source"], user["c3_only"])
        self.assertNotIn("Budget ", user["c3_only"])
        self.assertNotIn("cost ", user["c3_only"])
        self.assertIn(row["b1_source"], user["b1_only"])
        self.assertNotIn(row["b2_source"], user["b1_only"])
        self.assertIn(row["b2_source"], user["b2_only"])
        self.assertNotIn(row["b1_source"], user["b2_only"])
        for arm in ("both_exact", "single_body_dual"):
            self.assertIn(row["b1_source"], user[arm])
            self.assertIn(row["b2_source"], user[arm])
        self.assertIn(row["b2_source"], user["shuffled_b1"])
        self.assertNotIn(row["b1_source"], user["shuffled_b1"])
        self.assertIn("Project HB0", user["shuffled_b1"])

    def test_external_sha_pin_and_source_tamper_refused(self):
        with self.assertRaisesRegex(ValueError, "HB0_EXTERNAL_SHA_REQUIRED"):
            arms.build(self.rows, "not-a-pin")
        with self.assertRaisesRegex(ValueError, "HB0_COHORT_DRIFT_RED"):
            arms.build(self.rows, "0" * 64)
        tampered = deepcopy(self.rows)
        tampered[0]["current"] += " Choose A."
        with self.assertRaisesRegex(ValueError, "HB0_COHORT_DRIFT_RED"):
            arms.build(tampered, self.pin)

    def test_export_verify_fresh_and_nonpromoting(self):
        with TemporaryDirectory() as d:
            path = Path(d) / "bundle"
            manifest = arms.export(path, self.pin)
            self.assertEqual(arms.verify(path, self.pin), manifest)
            self.assertEqual(manifest["status"], "MODEL_INPUT_PREPARED_SOFTWARE_ONLY_NO_GATE")
            self.assertEqual(manifest["prompts"], 900)
            self.assertEqual(manifest["answers"], 150)
            self.assertFalse(manifest["model_called"])
            self.assertFalse(manifest["canonical_gate_pass"])
            self.assertEqual(manifest["step2_status"], "UTILITY_FAIL")
            self.assertEqual(manifest["jepa_weight"], 0)
            self.assertFalse(manifest["whole_system_complete"])
            with self.assertRaisesRegex(FileExistsError, "FRESH_HB0_ARM_DIRECTORY_REQUIRED"):
                arms.export(path, self.pin)

    def test_corrupt_hash_rejected(self):
        with TemporaryDirectory() as d:
            path = Path(d) / "bundle"
            arms.export(path, self.pin)
            with (path / "prompts.jsonl").open("ab") as handle:
                handle.write(b"\n")
            with self.assertRaisesRegex(ValueError, "HB0_EXPORT_HASH_RED"):
                arms.verify(path, self.pin)

    def test_oracle_contamination_with_rehashed_manifest_rejected(self):
        with TemporaryDirectory() as d:
            path = Path(d) / "bundle"
            arms.export(path, self.pin)
            prompts = [json.loads(line) for line in (path / "prompts.jsonl").read_bytes().splitlines()]
            prompts[0]["oracle_action"] = "A"
            self._rewrite_with_hash(path, prompts)
            with self.assertRaisesRegex(ValueError, "HB0_EXPORT_CONTENT_DRIFT_RED"):
                arms.verify(path, self.pin)

    def test_wrong_project_source_and_duplicate_arm_rejected(self):
        for mode in ("foreign", "duplicate"):
            with self.subTest(mode=mode), TemporaryDirectory() as d:
                path = Path(d) / "bundle"
                arms.export(path, self.pin)
                prompts = [json.loads(line) for line in (path / "prompts.jsonl").read_bytes().splitlines()]
                if mode == "foreign":
                    prompts[0]["messages"][1]["content"] += "\nProject Foreign supplier sheet."
                else:
                    prompts[0]["arm"] = prompts[1]["arm"]
                self._rewrite_with_hash(path, prompts)
                with self.assertRaisesRegex(ValueError, "HB0_EXPORT_CONTENT_DRIFT_RED"):
                    arms.verify(path, self.pin)

    @staticmethod
    def _rewrite_with_hash(path, prompts):
        raw = arms._jsonl(prompts)
        (path / "prompts.jsonl").write_bytes(raw)
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        manifest["sha256"]["prompts.jsonl"] = arms._sha(raw)
        (path / "manifest.json").write_bytes(arms._bytes(manifest))


if __name__ == "__main__":
    unittest.main()
