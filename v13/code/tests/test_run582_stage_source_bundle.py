"""Run582 complete source bundle positive/negative software-only controls."""
import json
from pathlib import Path
import tempfile
import unittest
from scripts import run582_stage_source_bundle as R

STAGES = ("A_s33_p02", "A_s33_p03", "A_s33_p04")


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


def fixture(root):
    root = Path(root)
    stages = [{"id": sid, "seed": 33, "fixture_ids": [sid + "-1", sid + "-2"]}
              for sid in STAGES]
    write(root / "RUN500_STAGE_MAP.json", {"stages": stages})
    write(root / "RUN504_SCHEDULE.json", {})
    write(root / "RUN558_BATCH_PLAN.json", {"stage_ids": list(STAGES)})
    write(root / "RUN558_INSTALLED_PREFLIGHT.json", {})
    (root / "RUN558_BATCH_PROGRESS.jsonl").write_text(
        "".join(json.dumps({"stage_id": sid}) + "\n" for sid in STAGES))
    receipts = []
    for stage in stages:
        sid = stage["id"]
        folder = root / ("stage_" + sid)
        write(folder / "RUN500_STAGE_PREREG.json", stage)
        write(folder / "RUN500_INSTALLED_PREFLIGHT.json", {})
        tool = folder / "tool_A_s33.json"
        summary = folder / "summary_A_s33.json"
        report = folder / "step2_A_s33.json"
        write(tool, {"rows": [{}] * 14})
        write(summary, {"seed": 33})
        write(report, {"rows": [{}] * 14})
        result = {"stage_id": sid, "rows_verified": 14,
                  "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
                  "tool_sha256": R.sha(tool.read_bytes()),
                  "summary_sha256": R.sha(summary.read_bytes())}
        result_path = folder / "RUN500_STAGE_RESULT.json"
        write(result_path, result)
        receipts.append({"stage_id": sid, "receipt_sha256": R.sha(result_path.read_bytes())})
    write(root / "RUN558_BATCH_RESULT.json",
          {"stage_ids": list(STAGES), "rows_verified": 42,
           "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
           "stage_receipts": receipts})
    return root


class Run582Bundle(unittest.TestCase):
    def test_complete_three_stage_bundle_includes_all_raw(self):
        with tempfile.TemporaryDirectory() as temp:
            root = fixture(Path(temp) / "work")
            dest = Path(temp) / "safe"
            receipt = R.bundle(root, dest)
            self.assertEqual(receipt["stage_count"], 3)
            self.assertEqual(receipt["expected_raw_files"], 24)
            self.assertEqual(len(receipt["copied"]), 24)
            self.assertEqual(receipt["status"], "COMPLETE_STAGE_SOURCE_BUNDLE_ONLY")
            for sid in STAGES:
                for name in ("tool_A_s33.json", "summary_A_s33.json", "step2_A_s33.json"):
                    relative = "stage_" + sid + "/" + name
                    self.assertIn(relative, receipt["copied"])
                    self.assertEqual(R.sha((dest / relative).read_bytes()),
                                     receipt["copied"][relative]["sha256"])
            self.assertFalse(receipt["native_execution_independently_verified"])
            self.assertFalse(receipt["canonical_gate_pass"])

    def test_seed32_typo_is_rejected_not_silently_skipped(self):
        with tempfile.TemporaryDirectory() as temp:
            root = fixture(Path(temp) / "work")
            stage_map = root / "RUN500_STAGE_MAP.json"
            data = json.loads(stage_map.read_text())
            data["stages"][0]["seed"] = 32
            write(stage_map, data)
            with self.assertRaisesRegex(ValueError, "STAGE_ID_SEED_MISMATCH"):
                R.collect(root)

    def test_missing_p02_tool_is_fatal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = fixture(Path(temp) / "work")
            (root / "stage_A_s33_p02/tool_A_s33.json").unlink()
            with self.assertRaisesRegex(ValueError, "MISSING_STAGE_SOURCE"):
                R.bundle(root, Path(temp) / "safe")
            self.assertFalse((Path(temp) / "safe").exists())

    def test_changed_stage_summary_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = fixture(Path(temp) / "work")
            write(root / "stage_A_s33_p02/summary_A_s33.json", {"seed": 33, "tampered": True})
            with self.assertRaisesRegex(ValueError, "STAGE_SOURCE_BINDING_CHANGED"):
                R.collect(root)

    def test_existing_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root = fixture(Path(temp) / "work")
            dest = Path(temp) / "safe"
            dest.mkdir()
            with self.assertRaisesRegex(ValueError, "REFUSE_EXISTING_BUNDLE"):
                R.bundle(root, dest)

    def test_stage_name_must_match_seed(self):
        with self.assertRaisesRegex(ValueError, "STAGE_ID_SEED_MISMATCH"):
            R.required_stage_names("A_s33_p02", 32)
        with self.assertRaisesRegex(ValueError, "STAGE_ID_SEED_MISMATCH"):
            R.required_stage_names("../A_s33_p02", 33)


if __name__ == "__main__":
    unittest.main()
