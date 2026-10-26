"""Run500 source-only stage-map/runner tests; no native model or downloads."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run491_step2_heldout10 as F
import run500_step2_stage_map as S


def synthetic(stage):
    rows = [
        {"fixture": fid, "variant": v, "status": "RECORDED",
         "oracle_visible_to_native": False, "score": {"utility": 0.5}}
        for fid in stage["fixture_ids"] for v in F.VARIANTS
    ]
    tool = {"installed_artifacts_unchanged": True, "rows": rows}
    summary = {
        "run": f"{stage['arm']}_s{stage['seed']}",
        "arm": stage["arm"], "seed": stage["seed"],
        "tool_status": "UTILITY_FAIL", "step2_status": "UTILITY_FAIL",
        "tool_summary": {v: {"wrong_committed": 0} for v in F.VARIANTS},
    }
    return tool, summary


class FrozenStageMap(unittest.TestCase):
    def test_exact_disjoint_1050_rows_and_75_stages(self):
        reg = S.registration()
        self.assertEqual(reg["original_fixture_sha256"], F.FIXTURE_SHA256)
        self.assertEqual((reg["stage_count"], reg["expected_native_rows"]), (75, 1050))
        self.assertEqual(reg["model_sha256_expected_not_retrieved"], F.MODEL_SHA256)
        self.assertEqual(reg["runner_sha256_expected_not_retrieved"], F.RUNNER_SHA256)
        self.assertFalse(reg["native_executed"])
        self.assertFalse(reg["canonical_gate_pass"])
        self.assertEqual(reg["step2_exit"], "UTILITY_FAIL")
        keys = [tuple(key) for stage in reg["stages"] for key in stage["row_keys"]]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(keys), 1050)
        self.assertEqual(reg["row_keys_sha256"], S.digest([list(k) for k in keys]))
        self.assertEqual(reg, S.registration())

    def test_stage_order_and_immutable_fixture_pairing(self):
        reg = S.registration()
        self.assertEqual(reg["stages"][0]["id"], "A_s31_p00")
        self.assertEqual(reg["stages"][0]["fixture_ids"], ["Vesper", "Willow"])
        self.assertEqual(reg["stages"][4]["fixture_ids"], ["Drift", "Eon"])
        self.assertEqual(reg["stages"][-1]["id"], "E_s33_p04")
        for stage in reg["stages"]:
            self.assertEqual(len(stage["row_keys"]), 14)
            self.assertEqual(S.digest(stage["row_keys"]), stage["row_keys_sha256"])
        for bad in ("A_s31_p05", "C_s31_p00/../", "C_s30_p00", None, ""):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "UNKNOWN_STAGE_ID"):
                S.choose(reg, bad)

    def test_in_memory_harness_is_restored_even_on_error(self):
        import step2_z2_timescale as z2
        import step2_z2b_seeds as z2b
        stage = S.registration()["stages"][0]
        before_fixtures = z2.FIXTURES
        before_arms = copy.deepcopy(z2b.ARMS)
        before_seeds = z2b.SEEDS
        with self.assertRaisesRegex(RuntimeError, "forced"):
            with S.scoped_stage(stage):
                self.assertEqual([f["id"] for f in z2.FIXTURES], ["Vesper", "Willow"])
                self.assertEqual(set(z2b.ARMS), set(F.ARMS))
                self.assertEqual(z2b.SEEDS, F.SEEDS)
                raise RuntimeError("forced")
        self.assertIs(z2.FIXTURES, before_fixtures)
        self.assertEqual(z2b.ARMS, before_arms)
        self.assertEqual(z2b.SEEDS, before_seeds)

    def test_structural_receipt_refuses_missing_wrong_or_failed_rows(self):
        stage = S.registration()["stages"][0]
        tool, summary = synthetic(stage)
        result = S.verify_stage(stage, tool, summary)
        self.assertEqual(result["rows_verified"], 14)
        self.assertFalse(result["canonical_gate_pass"])
        for mutation, reason in (
            (lambda t, s: t["rows"].pop(), "STAGE_ROWS_INCOMPLETE"),
            (lambda t, s: t["rows"][0].update(status="ERROR"), "STAGE_ROW_INVALID"),
            (lambda t, s: t["rows"][0]["score"].update(utility=float("nan")), "STAGE_ROW_INVALID"),
            (lambda t, s: t.update(installed_artifacts_unchanged=False), "STAGE_INSTALLED_DRIFT"),
            (lambda t, s: s.update(seed=32), "STAGE_SUMMARY_IDENTITY"),
            (lambda t, s: s["tool_summary"]["both_exact"].update(wrong_committed=1), "STAGE_WRONG_COMMITTED"),
        ):
            t, s = synthetic(stage)
            mutation(t, s)
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                S.verify_stage(stage, t, s)

    def test_fixture_only_is_exclusive_and_does_not_infer(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "RUN500_STAGE_MAP.json"
            reg = S.registration()
            S.write_new(p, reg)
            self.assertEqual(json.loads(p.read_text()), reg)
            with self.assertRaises(FileExistsError):
                S.write_new(p, reg)

    def test_tampered_map_or_existing_stage_refused_before_native(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            manifest = work / "RUN500_STAGE_MAP.json"
            reg = S.registration()
            S.write_new(manifest, reg)
            stage = reg["stages"][0]
            stage_dir = work / ("stage_" + stage["id"])
            stage_dir.mkdir()
            with self.assertRaisesRegex(ValueError, "REFUSE_STAGE_OVERWRITE_OR_PARTIAL_RERUN"):
                S.require(not stage_dir.exists(), "REFUSE_STAGE_OVERWRITE_OR_PARTIAL_RERUN")
            reg["stages"][0]["row_keys"][0][2] = "TAMPER"
            self.assertNotEqual(json.loads(manifest.read_text()), reg)


if __name__ == "__main__":
    unittest.main()
