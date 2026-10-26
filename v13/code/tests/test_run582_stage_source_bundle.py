"""Run582 complete source bundle positive/negative software-only controls."""
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from scripts import run582_stage_source_bundle as R

STAGES = ("A_s33_p02", "A_s33_p03", "A_s33_p04")


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


VARIANTS = ("b1_only", "b2_only", "both_none", "both_exact", "both_control",
            "same_policy_dual", "prompt_only_dual")


def fixture(root):
    root = Path(root)
    stages = []
    for i, sid in enumerate(STAGES):
        ids = [f"fixture{i}a", f"fixture{i}b"]
        keys = [["A", 33, fid, variant] for fid in ids for variant in VARIANTS]
        stages.append({"id": sid, "arm": "A", "seed": 33,
                       "fixture_ids": ids, "row_keys": keys})
    full = {"stages": stages}
    write(root / "RUN500_STAGE_MAP.json", full)
    all_keys = [key for stage in stages for key in stage["row_keys"]]
    pairs = [stage["fixture_ids"] for stage in stages]
    scheduled = {"id": "FUTURE_005", "stage_ids": list(STAGES),
                 "fixture_pairs": pairs, "expected_rows": 42,
                 "row_keys_sha256": R.canonical_digest(all_keys)}
    schedule = {"full_stage_map_sha256": R.canonical_digest(full),
                "batches": [scheduled]}
    write(root / "RUN504_SCHEDULE.json", schedule)
    write(root / "RUN558_BATCH_PLAN.json",
          {"batch_id": "FUTURE_005", "stage_ids": list(STAGES),
           "fixture_pairs": pairs, "expected_rows": 42,
           "row_keys_sha256": R.canonical_digest(all_keys),
           "full_stage_map_sha256": R.canonical_digest(full),
           "source_schedule_sha256": R.canonical_digest(schedule)})
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
        rows = [{"fixture": key[2], "variant": key[3]} for key in stage["row_keys"]]
        write(tool, {"rows": rows})
        write(summary, {"seed": 33})
        write(report, {"rows": rows})
        result = {"stage_id": sid, "rows_verified": 14,
                  "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
                  "tool_sha256": R.sha(tool.read_bytes()),
                  "summary_sha256": R.sha(summary.read_bytes())}
        result_path = folder / "RUN500_STAGE_RESULT.json"
        write(result_path, result)
        receipts.append({"stage_id": sid, "receipt_sha256": R.sha(result_path.read_bytes())})
    write(root / "RUN558_BATCH_RESULT.json",
          {"batch_id": "FUTURE_005", "stage_ids": list(STAGES), "rows_verified": 42,
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
            with self.assertRaisesRegex(ValueError, "FROZEN_BATCH_SOURCE_BINDING_CHANGED"):
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

    def test_intermediate_stage_directory_symlink_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = fixture(Path(temp) / "work")
            stage = root / "stage_A_s33_p02"
            moved = Path(temp) / "external_stage"
            stage.rename(moved)
            stage.symlink_to(moved, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "UNSAFE_STAGE_PARENT"):
                R.collect(root)

    def test_inspector_refuses_zip_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "unsafe.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("../RUN558_BATCH_PLAN.json", "{}")
            with self.assertRaisesRegex(ValueError, "SAFE_ZIP_INVALID"):
                R.inspect_safe_zip(archive)

    def test_stage_name_must_match_seed(self):
        with self.assertRaisesRegex(ValueError, "STAGE_ID_SEED_MISMATCH"):
            R.required_stage_names("A_s33_p02", 32)
        with self.assertRaisesRegex(ValueError, "STAGE_ID_SEED_MISMATCH"):
            R.required_stage_names("../A_s33_p02", 33)


    def test_duplicate_tool_row_cannot_be_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = fixture(Path(temp) / "work")
            path = root / "stage_A_s33_p02/tool_A_s33.json"
            value = json.loads(path.read_text())
            value["rows"][1] = dict(value["rows"][0])
            write(path, value)
            # Even if an attacker updates the per-stage receipt and hashes,
            # the registered 2 x 7 row-key set must still be enforced.
            with self.assertRaisesRegex(ValueError, "STAGE_ROW_COVERAGE_INVALID"):
                R.collect(root)

    def test_wrong_fixture_in_step2_report_cannot_be_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = fixture(Path(temp) / "work")
            path = root / "stage_A_s33_p03/step2_A_s33.json"
            value = json.loads(path.read_text())
            value["rows"][0]["fixture"] = "other_project"
            write(path, value)
            with self.assertRaisesRegex(ValueError, "STAGE_ROW_COVERAGE_INVALID"):
                R.collect(root)

    def test_non_dict_row_cannot_be_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = fixture(Path(temp) / "work")
            path = root / "stage_A_s33_p04/step2_A_s33.json"
            value = json.loads(path.read_text())
            value["rows"][0] = ["fixture", "variant"]
            write(path, value)
            with self.assertRaisesRegex(ValueError, "STAGE_ROW_COVERAGE_INVALID"):
                R.collect(root)

    def test_plan_fixture_pair_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = fixture(Path(temp) / "work")
            path = root / "RUN558_BATCH_PLAN.json"
            value = json.loads(path.read_text())
            value["fixture_pairs"][0] = ["wrong", "pair"]
            write(path, value)
            with self.assertRaisesRegex(ValueError, "FROZEN_BATCH_ROW_KEYS_CHANGED"):
                R.collect(root)

    def test_schedule_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = fixture(Path(temp) / "work")
            path = root / "RUN504_SCHEDULE.json"
            value = json.loads(path.read_text())
            value["batches"][0]["stage_ids"].reverse()
            write(path, value)
            with self.assertRaisesRegex(ValueError, "FROZEN_BATCH_SOURCE_BINDING_CHANGED"):
                R.collect(root)

    def test_duplicate_receipt_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = fixture(Path(temp) / "work")
            path = root / "RUN558_BATCH_RESULT.json"
            value = json.loads(path.read_text())
            value["stage_receipts"].append(dict(value["stage_receipts"][0]))
            write(path, value)
            with self.assertRaisesRegex(ValueError, "STAGE_RECEIPT_SET_CHANGED"):
                R.collect(root)



if __name__ == "__main__":
    unittest.main()
