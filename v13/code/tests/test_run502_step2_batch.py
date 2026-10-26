"""Run502 source-only batch plan and mocked executor adversarial tests.

No model inference, runner download or native worker is performed.
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run500_step2_stage_map as S
import run502_step2_batch as B


def fixture_work(tmp):
    work = Path(tmp)
    S.write_new(work / "RUN500_STAGE_MAP.json", S.registration())
    return work


def fake_run_child(command, log_path, timeout_s=3600):
    stage_id = command[command.index("--stage-id") + 1]
    work = Path(command[command.index("--work") + 1])
    folder = work / ("stage_" + stage_id)
    folder.mkdir()
    (folder / "RUN500_STAGE_RESULT.json").write_text(json.dumps({
        "status": "STAGE_14_ROWS_STRUCTURALLY_VERIFIED_ONLY",
        "stage_id": stage_id, "rows_verified": 14,
        "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
        "native_execution_performed": True,
    }))
    Path(log_path).write_text("MOCKED_SOURCE_ONLY_NO_NATIVE\n")
    return 0


class BatchSourceOnly(unittest.TestCase):
    def test_exact_disjoint_42_keys_and_no_prior_stage_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = fixture_work(tmp)
            result = B.plan(work)
            self.assertEqual(result["stage_ids"], list(B.BATCH_IDS))
            self.assertEqual(result["fixture_pairs"], [list(x) for x in B.BATCH_FIXTURES])
            self.assertEqual(result["expected_rows"], 42)
            self.assertFalse(result["native_executed"])
            self.assertFalse(result["canonical_gate_pass"])
            self.assertEqual(result["step2_exit"], "UTILITY_FAIL")
            self.assertEqual(result, B.plan(work))

    def test_plan_requires_exact_map_and_is_exclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = fixture_work(tmp)
            result = B.plan(work)
            S.write_new(work / "RUN502_BATCH_PLAN.json", result)
            with self.assertRaises(FileExistsError):
                S.write_new(work / "RUN502_BATCH_PLAN.json", result)
            source = work / "RUN500_STAGE_MAP.json"
            mutated = json.loads(source.read_text())
            mutated["stages"][0]["row_keys"][0][2] = "TAMPER"
            source.write_text(json.dumps(mutated))
            with self.assertRaisesRegex(ValueError, "RUN500_STAGE_MAP_DRIFT"):
                B.plan(work)

    def test_mocked_three_stage_execution_persists_receipts_without_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = fixture_work(tmp)
            S.write_new(work / "RUN502_BATCH_PLAN.json", B.plan(work))
            installed = work / "installed"; installed.mkdir()
            with patch("run496_heldout10_native_pilot.verify_installed", return_value={"synthetic": True}), \
                 patch.object(B, "run_child", side_effect=fake_run_child) as native:
                result = B.execute(work, installed)
            self.assertEqual(native.call_count, 3)
            self.assertEqual(result["rows_verified"], 42)
            self.assertFalse(result["canonical_gate_pass"])
            self.assertEqual(len(result["stage_receipts"]), 3)
            progress = [json.loads(line) for line in (work / "RUN502_BATCH_PROGRESS.jsonl").read_text().splitlines()]
            self.assertEqual(len(progress), 6)
            self.assertEqual([p["state"] for p in progress], ["STARTED","FINISHED"]*3)
            with self.assertRaisesRegex(ValueError, "REFUSE_BATCH_RERUN_OR_PARTIAL"):
                B.execute(work, installed)

    def test_second_stage_red_preserves_first_and_refuses_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = fixture_work(tmp)
            S.write_new(work / "RUN502_BATCH_PLAN.json", B.plan(work))
            installed = work / "installed"; installed.mkdir()
            seen = []
            def second_fails(command, log_path, timeout_s=3600):
                stage_id = command[command.index("--stage-id") + 1]
                seen.append(stage_id)
                if len(seen) == 2:
                    Path(log_path).write_text("SYNTHETIC_RED_ONLY\n")
                    return 17
                return fake_run_child(command, log_path, timeout_s)
            with patch("run496_heldout10_native_pilot.verify_installed", return_value={"synthetic": True}), \
                 patch.object(B, "run_child", side_effect=second_fails):
                with self.assertRaisesRegex(RuntimeError, "BATCH_STOPPED_AT_C_s31_p03_RC_17"):
                    B.execute(work, installed)
            self.assertEqual(seen, ["C_s31_p02", "C_s31_p03"])
            self.assertTrue((work / "stage_C_s31_p02" / "RUN500_STAGE_RESULT.json").exists())
            self.assertFalse((work / "stage_C_s31_p04").exists())
            progress = [json.loads(line) for line in (work / "RUN502_BATCH_PROGRESS.jsonl").read_text().splitlines()]
            self.assertEqual(len(progress), 4)
            self.assertEqual(progress[-1]["rc"], 17)
            with self.assertRaisesRegex(ValueError, "REFUSE_BATCH_RERUN_OR_PARTIAL"):
                B.execute(work, installed)

    def test_invalid_stage_receipt_is_recorded_red_before_next_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = fixture_work(tmp)
            S.write_new(work / "RUN502_BATCH_PLAN.json", B.plan(work))
            installed = work / "installed"; installed.mkdir()
            def invalid_receipt(command, log_path, timeout_s=3600):
                rc = fake_run_child(command, log_path, timeout_s)
                stage_id = command[command.index("--stage-id") + 1]
                receipt = work / ("stage_" + stage_id) / "RUN500_STAGE_RESULT.json"
                data = json.loads(receipt.read_text())
                data["native_execution_performed"] = False
                receipt.write_text(json.dumps(data))
                return rc
            with patch("run496_heldout10_native_pilot.verify_installed", return_value={"synthetic": True}), \
                 patch.object(B, "run_child", side_effect=invalid_receipt) as native:
                with self.assertRaisesRegex(RuntimeError, "BATCH_STOPPED_AT_C_s31_p02_RC_98"):
                    B.execute(work, installed)
            self.assertEqual(native.call_count, 1)
            progress = [json.loads(line) for line in (work / "RUN502_BATCH_PROGRESS.jsonl").read_text().splitlines()]
            self.assertEqual(len(progress), 2)
            self.assertEqual(progress[-1]["rc"], 98)
            self.assertFalse((work / "stage_C_s31_p03").exists())

    def test_existing_stage_or_tampered_batch_plan_fails_before_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = fixture_work(tmp)
            result = B.plan(work)
            S.write_new(work / "RUN502_BATCH_PLAN.json", result)
            installed = work / "installed"; installed.mkdir()
            (work / "stage_C_s31_p04").mkdir()
            with patch("run496_heldout10_native_pilot.verify_installed", side_effect=AssertionError("native called")):
                with self.assertRaisesRegex(ValueError, "REFUSE_EXISTING_STAGE_DIR"):
                    B.execute(work, installed)
            (work / "stage_C_s31_p04").rmdir()
            result["expected_rows"] = 41
            (work / "RUN502_BATCH_PLAN.json").write_text(json.dumps(result))
            with patch("run496_heldout10_native_pilot.verify_installed", side_effect=AssertionError("native called")):
                with self.assertRaisesRegex(ValueError, "BATCH_PLAN_NOT_FROZEN"):
                    B.execute(work, installed)


if __name__ == "__main__":
    unittest.main()
