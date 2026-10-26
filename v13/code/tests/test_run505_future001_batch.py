"""Run505 source-only plan and mocked serialized executor tests; no native calls."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run500_step2_stage_map as stage_map
import run504_remaining980_schedule as schedule
import run505_future001_batch as batch


def workdir(tmp):
    work = Path(tmp)
    stage_map.write_new(work / "RUN500_STAGE_MAP.json", stage_map.registration())
    schedule.write_exclusive(work / "RUN504_SCHEDULE.json", schedule.registration())
    return work


def mock_child(command, log_path, timeout_s=3600):
    stage_id = command[command.index("--stage-id") + 1]
    work = Path(command[command.index("--work") + 1])
    folder = work / ("stage_" + stage_id)
    folder.mkdir()
    (folder / "RUN500_STAGE_RESULT.json").write_text(json.dumps({
        "status": "STAGE_14_ROWS_STRUCTURALLY_VERIFIED_ONLY",
        "stage_id": stage_id, "rows_verified": 14,
        "native_execution_performed": True, "canonical_gate_pass": False,
        "step2_exit": "UTILITY_FAIL", "b3_l1": "FAIL",
        "body_jepa": "UNAVAILABLE", "jepa_weight": 0,
        "redmi_measured": False,
    }))
    Path(log_path).write_text("MOCK_ONLY_NO_NATIVE\n")
    return 0


class Future001SourceOnly(unittest.TestCase):
    def test_exact_original_batch_and_no_reserved_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = workdir(tmp)
            result = batch.plan(work)
            self.assertEqual(result["batch_id"], "FUTURE_001")
            self.assertEqual(result["stage_ids"],
                             ["A_s31_p00", "A_s31_p01", "A_s31_p02"])
            self.assertEqual(result["expected_rows"], 42)
            self.assertEqual(result["fixture_pairs"],
                             [["Vesper", "Willow"], ["Xenia", "Yarrow"],
                              ["Crescent", "Asteria"]])
            self.assertEqual(result["row_keys_sha256"],
                             schedule.registration()["batches"][0]["row_keys_sha256"])
            self.assertFalse(result["native_executed"])
            self.assertFalse(result["canonical_gate_pass"])
            self.assertEqual(result["step2_exit"], "UTILITY_FAIL")
            self.assertEqual(result, batch.plan(work))

    def test_source_manifest_tamper_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = workdir(tmp)
            value = batch.plan(work)
            stage_map.write_new(work / "RUN505_BATCH_PLAN.json", value)
            with self.assertRaises(FileExistsError):
                stage_map.write_new(work / "RUN505_BATCH_PLAN.json", value)
            altered = copy.deepcopy(value)
            altered["expected_rows"] = 41
            (work / "RUN505_BATCH_PLAN.json").write_text(json.dumps(altered))
            installed = work / "installed"
            installed.mkdir()
            with patch("run496_heldout10_native_pilot.verify_installed",
                       side_effect=AssertionError("NATIVE PREFLIGHT CALLED")):
                with self.assertRaisesRegex(ValueError, "RUN505_BATCH_PLAN_NOT_FROZEN"):
                    batch.execute(work, installed)
            future = json.loads((work / "RUN504_SCHEDULE.json").read_text())
            future["batches"][0]["stage_ids"][0] = "C_s31_p00"
            (work / "RUN504_SCHEDULE.json").write_text(json.dumps(future))
            with self.assertRaisesRegex(ValueError, "FROZEN_FUTURE_SCHEDULE_REQUIRED"):
                batch.plan(work)

    def test_mocked_three_stage_success_and_no_implicit_rerun(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = workdir(tmp)
            stage_map.write_new(work / "RUN505_BATCH_PLAN.json", batch.plan(work))
            installed = work / "installed"; installed.mkdir()
            with patch("run496_heldout10_native_pilot.verify_installed",
                       return_value={"MOCK_SOURCE_ONLY": True}), \
                 patch.object(batch, "run_child", side_effect=mock_child) as native:
                result = batch.execute(work, installed)
            self.assertEqual(native.call_count, 3)
            self.assertEqual(result["rows_verified"], 42)
            self.assertFalse(result["canonical_gate_pass"])
            progress = [json.loads(x) for x in
                        (work / "RUN505_BATCH_PROGRESS.jsonl").read_text().splitlines()]
            self.assertEqual(len(progress), 6)
            self.assertEqual([x["state"] for x in progress], ["STARTED", "FINISHED"] * 3)
            with self.assertRaisesRegex(ValueError, "REFUSE_BATCH_RERUN_OR_PARTIAL"):
                batch.execute(work, installed)

    def test_second_stage_red_preserved_and_third_not_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = workdir(tmp)
            stage_map.write_new(work / "RUN505_BATCH_PLAN.json", batch.plan(work))
            installed = work / "installed"; installed.mkdir()
            calls = []
            def fail_second(command, log_path, timeout_s=3600):
                stage_id = command[command.index("--stage-id") + 1]
                calls.append(stage_id)
                if len(calls) == 2:
                    Path(log_path).write_text("MOCK_RED_NO_NATIVE\n")
                    return 17
                return mock_child(command, log_path, timeout_s)
            with patch("run496_heldout10_native_pilot.verify_installed",
                       return_value={"MOCK_SOURCE_ONLY": True}), \
                 patch.object(batch, "run_child", side_effect=fail_second):
                with self.assertRaisesRegex(RuntimeError, "RUN505_STOPPED_AT_A_s31_p01_RC_17"):
                    batch.execute(work, installed)
            self.assertEqual(calls, ["A_s31_p00", "A_s31_p01"])
            self.assertFalse((work / "stage_A_s31_p02").exists())
            progress = [json.loads(x) for x in
                        (work / "RUN505_BATCH_PROGRESS.jsonl").read_text().splitlines()]
            self.assertEqual(progress[-1]["rc"], 17)
            with self.assertRaisesRegex(ValueError, "REFUSE_BATCH_RERUN_OR_PARTIAL"):
                batch.execute(work, installed)

    def test_malformed_receipt_stops_before_next_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = workdir(tmp)
            stage_map.write_new(work / "RUN505_BATCH_PLAN.json", batch.plan(work))
            installed = work / "installed"; installed.mkdir()
            def wrong_receipt(command, log_path, timeout_s=3600):
                rc = mock_child(command, log_path, timeout_s)
                stage_id = command[command.index("--stage-id") + 1]
                receipt = work / ("stage_" + stage_id) / "RUN500_STAGE_RESULT.json"
                d = json.loads(receipt.read_text())
                d["jepa_weight"] = 1
                receipt.write_text(json.dumps(d))
                return rc
            with patch("run496_heldout10_native_pilot.verify_installed",
                       return_value={"MOCK_SOURCE_ONLY": True}), \
                 patch.object(batch, "run_child", side_effect=wrong_receipt) as native:
                with self.assertRaisesRegex(RuntimeError, "RUN505_STOPPED_AT_A_s31_p00_RC_98"):
                    batch.execute(work, installed)
            self.assertEqual(native.call_count, 1)
            self.assertFalse((work / "stage_A_s31_p01").exists())
            progress = [json.loads(x) for x in
                        (work / "RUN505_BATCH_PROGRESS.jsonl").read_text().splitlines()]
            self.assertEqual(progress[-1]["rc"], 98)

    def test_existing_stage_rejected_before_installed_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = workdir(tmp)
            stage_map.write_new(work / "RUN505_BATCH_PLAN.json", batch.plan(work))
            installed = work / "installed"; installed.mkdir()
            (work / "stage_A_s31_p02").mkdir()
            with patch("run496_heldout10_native_pilot.verify_installed",
                       side_effect=AssertionError("NATIVE PREFLIGHT CALLED")):
                with self.assertRaisesRegex(ValueError, "REFUSE_EXISTING_STAGE_DIR"):
                    batch.execute(work, installed)


if __name__ == "__main__":
    unittest.main()
