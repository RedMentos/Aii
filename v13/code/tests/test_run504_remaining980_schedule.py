"""Run504 frozen 980-row source-only schedule: coverage, tamper, no native."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run500_step2_stage_map as stage_map
import run504_remaining980_schedule as schedule


class Remaining980Schedule(unittest.TestCase):
    def test_exact_full_coverage_and_reserved_separation(self):
        full = stage_map.registration()
        result = schedule.registration()
        self.assertEqual(result["status"], "SOURCE_ONLY_NO_NATIVE")
        self.assertEqual(result["reserved_stage_ids"],
                         [f"C_s31_p{i:02d}" for i in range(5)])
        self.assertTrue(result["reserved_p02_p04_native_verification_pending"])
        self.assertEqual(result["remaining_stage_count"], 70)
        self.assertEqual(result["remaining_planned_rows"], 980)
        self.assertEqual(result["batch_count"], 24)
        self.assertEqual([b["expected_rows"] for b in result["batches"]],
                         [42] * 23 + [14])
        reserved = set(result["reserved_stage_ids"])
        future = [sid for b in result["batches"] for sid in b["stage_ids"]]
        self.assertEqual(len(future), len(set(future)) == 70)
        self.assertFalse(set(future) & reserved)
        self.assertEqual(set(future) | reserved, {s["id"] for s in full["stages"]})
        self.assertEqual(result["full_stage_map_sha256"], schedule.digest(full))

    def test_all_980_original_keys_disjoint_and_batch_hashes(self):
        full = stage_map.registration()
        byid = {s["id"]: s for s in full["stages"]}
        plan = schedule.registration()
        future = []
        for batch in plan["batches"]:
            stages = [byid[sid] for sid in batch["stage_ids"]]
            keys = [key for stage in stages for key in stage["row_keys"]]
            self.assertEqual(batch["fixture_pairs"],
                             [stage["fixture_ids"] for stage in stages])
            self.assertEqual(batch["expected_rows"], len(keys))
            self.assertEqual(batch["row_keys_sha256"], schedule.digest(keys))
            self.assertFalse(batch["native_executed"])
            future.extend(tuple(k) for k in keys)
        self.assertEqual(len(future), len(set(future)) == 980)
        self.assertEqual(plan["remaining_row_keys_sha256"],
                         schedule.digest([list(k) for k in future]))
        reserved = {tuple(k) for stage in full["stages"]
                    if stage["id"] in plan["reserved_stage_ids"]
                    for k in stage["row_keys"]}
        self.assertFalse(set(future) & reserved)

    def test_determinism_and_all_negative_gates(self):
        a = schedule.registration()
        b = schedule.registration()
        self.assertEqual(schedule.canonical(a), schedule.canonical(b))
        for key, value in (("native_executed", False),
                           ("canonical_gate_pass", False),
                           ("step2_exit", "UTILITY_FAIL"),
                           ("b3_l1", "FAIL"),
                           ("body_jepa", "UNAVAILABLE"),
                           ("jepa_weight", 0),
                           ("redmi_measured", False)):
            self.assertEqual(a[key], value)

    def test_tampered_stage_content_rejected(self):
        original = stage_map.registration()
        for change, reason in (
            (lambda x: x["stages"][0]["row_keys"][0].__setitem__(2, "TAMPER"),
             "FROZEN_STAGE_CONTENT_DRIFT"),
            (lambda x: x["stages"][0].__setitem__("fixture_ids", ["TAMPER", "Willow"]),
             "FROZEN_STAGE_CONTENT_DRIFT"),
            (lambda x: x["stages"][0].__setitem__("id", "C_s31_p00"),
             "FROZEN_STAGE_ORDER_DRIFT"),
            (lambda x: x.__setitem__("original_fixture_sha256", "0" * 64),
             "ORIGINAL_FIXTURE_DRIFT"),
            (lambda x: x.__setitem__("runner_sha256_expected_not_retrieved", "0" * 64),
             "FROZEN_MODEL_RUNNER_DRIFT"),
        ):
            bad = copy.deepcopy(original)
            change(bad)
            with self.subTest(reason=reason), patch.object(stage_map, "registration", return_value=bad):
                with self.assertRaisesRegex(ValueError, reason):
                    schedule.registration()

    def test_exclusive_persistence_and_no_native_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "nested" / "schedule.json"
            schedule.write_exclusive(output, schedule.registration())
            self.assertEqual(json.loads(output.read_text()), schedule.registration())
            with self.assertRaises(FileExistsError):
                schedule.write_exclusive(output, schedule.registration())
            cmd = [sys.executable, str(ROOT / "scripts" / "run504_remaining980_schedule.py"),
                   "--output", str(Path(tmp) / "fresh.json"), "--execute"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("unrecognized arguments", proc.stderr)
            self.assertFalse((Path(tmp) / "fresh.json").exists())


if __name__ == "__main__":
    unittest.main()
