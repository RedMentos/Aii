"""Synthetic stdlib-only W7S replay tests; no model or filesystem world."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts import verify_w7s_world_jepa_report as audit


class W7SIndependentReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.work = self.root / "work"
        self.work.mkdir()
        self.result = self.root / "RESULT.json"
        self.data = self.fixture()
        self.write()

    def tearDown(self):
        self.tmp.cleanup()

    def fixture(self):
        support = {k: 20 for k in audit.CLASSES}
        score = {"own_only_self": .8, "world_only_world": .7,
                 "both_world": .7, "none_self": .8, "balanced": .75}
        row = {
            "capacity": {"local_latent_dim": 16, "world_concat_dim": 96},
            "attribution": {"jepa": dict(score, n=dict(support)),
                            "no_action": dict(score, n=dict(support))},
            "cf_retrieval": {"jepa_covered": .5},
        }
        data = {
            "schema": "v13.w7s.world_jepa_disjoint_support_exact_row.v1",
            "evidence_kind": "LINUX_REALFILE_WORLD_JEPA_SHADOW_EXACT_ROWS",
            "registered": True, "seeds": list(audit.SEEDS),
            "args": dict(audit.ARGS), **audit.PINS,
            "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
            "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
            "jepa_weight": 0, "world_jepa_authority": "SHADOW",
            "redmi_measured": False, "whole_system_complete": False,
            "same_collected_rows": True, "same_core_parameter_count": True,
            "same_optimizer_steps": True, "same_training_example_count": False,
            "global_96d_capacity_control_complete": False,
            "affected_slot_copies": 5,
            "attribution_support_preflight": [
                {"seed": seed, "counts": dict(support)}
                for seed in audit.SEEDS],
            "status": "SHADOW_CANDIDATE_FAIL",
        }
        for arm in audit.ARMS:
            data[arm] = [dict(copy.deepcopy(row), seed=seed)
                         for seed in audit.SEEDS]
            gates, summary = audit.replay_w7(data[arm])
            data[arm + "_w7"] = gates
            data[arm + "_w7_summary"] = summary
            data[arm + "_gates"] = {
                k: False for k in (
                    "W1_cf_retrieval_covered", "W2_controls_fail",
                    "W3_no_collapse", "W4_confidence_tracks_error",
                    "W5_attribution_jepa", "W6_no_action_attribution_worse")}
        data["exploratory"] = {
            "per_seed_balanced_gap_delta": [0., 0., 0.],
            "mean_balanced_gap_delta": 0.,
            "H1_balanced_gap_improvement": False,
            "H2_covered_cf_and_controls": False,
            "per_seed_w7c_delta": [0., 0., 0.],
            "mean_w7c_delta": 0.,
            "H3_w7c_improvement": False,
        }
        return data

    def write(self):
        self.result.write_text(json.dumps(self.data), encoding="utf-8")
        for arm in audit.ARMS:
            for row in self.data[arm]:
                path = self.work / f"{arm}-{row['seed']}-RESULT.json"
                path.write_text(json.dumps(dict(row, _conf_err=[[.1, .2]])),
                                encoding="utf-8")

    def test_positive_nine_row_replay_is_not_native_proof(self):
        result = audit.verify(self.result, self.work)
        self.assertEqual(result["status"],
                         "W7S_W7_SUPPORT_REPLAY_VERIFIED_SHADOW")
        self.assertEqual(result["rows"], 9)
        self.assertFalse(result["native_proof"])
        self.assertFalse(result["promotion"])

    def test_tampered_support_refused(self):
        self.data["attribution_support_preflight"][0]["counts"]["world_only"] = 14
        self.write()
        with self.assertRaisesRegex(ValueError, "PREFIT_FLOOR"):
            audit.verify(self.result, self.work)

    def test_tampered_w7_verdict_refused(self):
        self.data["balanced_slot_w7"]["W7a_both_world_action_gain"] = True
        self.write()
        with self.assertRaisesRegex(ValueError, "W7_GATES"):
            audit.verify(self.result, self.work)

    def test_tampered_row_file_refused(self):
        path = self.work / "balanced_slot-601-RESULT.json"
        raw = json.loads(path.read_text())
        raw["attribution"]["jepa"]["both_world"] = .99
        path.write_text(json.dumps(raw), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "ROW_FILE_MISMATCH"):
            audit.verify(self.result, self.work)

    def test_tampered_source_pin_refused(self):
        self.data["world_jepa_blob"] = "0" * 40
        self.write()
        with self.assertRaisesRegex(ValueError, "FROZEN_PINS"):
            audit.verify(self.result, self.work)

    def test_nonfinite_and_duplicate_json_refused(self):
        self.result.write_text('{"x":NaN}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "NONFINITE_JSON"):
            audit.verify(self.result, self.work)
        self.result.write_text('{"x":1,"x":2}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "DUPLICATE_JSON_KEY"):
            audit.verify(self.result, self.work)

    def test_original_red_stays_red_without_fabricating_rows(self):
        self.data["status"] = "RED"
        for arm in audit.ARMS:
            self.data[arm] = []
        self.write()
        result = audit.verify(self.result, self.work)
        self.assertEqual(result["status"], "ORIGINAL_RED_OR_INCOMPLETE")
        self.assertFalse(result["w7_verified"])
        self.assertFalse(result["native_proof"])


if __name__ == "__main__":
    unittest.main()
