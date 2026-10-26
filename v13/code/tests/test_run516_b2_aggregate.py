"""Run516: synthetic five-stage aggregate and fail-closed controls, no native."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run509_b2_rule_quote_prereg as frozen
import run511_b2_offer_collector as collector
import run516_b2_aggregate as agg


def write(path, obj):
    Path(path).write_text(json.dumps(obj, sort_keys=True, allow_nan=False) + "\n")


def fake_stage(index):
    plan = collector.plan(index)
    fixtures = {f["id"]: f for f in frozen.fixtures()}
    rows = []
    for name, arm, seed in plan["row_keys"]:
        fixture = fixtures[name]
        text = fixture["history"][0]
        quotes = []
        if arm == "RULE_FOCUS" and fixture["type"] != "DETAIL":
            quotes = [{"source_slot": "history0",
                       "source_sha256": hashlib.sha256(text.encode()).hexdigest(),
                       "text": text}]
        rows.append({
            "fixture": name, "arm": arm, "seed": seed,
            "status": "RECORDED",
            "source_history0_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "quotes": quotes,
        })
    report = {
        "stage_id": f"p{index:02d}",
        "source_bound_rows": 12,
        "native_execution_independently_confirmed": False,
        "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
        "b3_l1": "FAIL", "jepa_weight": 0,
        "redmi_measured": False,
        "row_keys_sha256": plan["row_keys_sha256"],
        "raw_observations_sha256": str(index) * 64,
    }
    return plan, report, rows


class Run516AggregateSource(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.dirs = []
        self.fakes = []
        for i in range(5):
            path = self.root / f"p{i:02d}"
            path.mkdir()
            plan, report, rows = fake_stage(i)
            write(path / "RUN511_STAGE_PLAN.json", plan)
            write(path / "RUN513_POSTFLIGHT.json", report)
            write(path / "RUN513_VERIFIED_METRIC_ROWS.json", rows)
            self.dirs.append(path)
            self.fakes.append((report, rows))

    def run_mocked(self, paths=None):
        def replay(work, index):
            self.assertEqual(Path(work), self.dirs[index])
            return copy.deepcopy(self.fakes[index])
        with patch.object(agg.postflight, "audit", side_effect=replay):
            return agg.aggregate(list(paths or self.dirs))

    def test_exact_sixty_paired_rows_and_negative_gates(self):
        report, rows, score = self.run_mocked()
        self.assertEqual(len(rows), 60)
        self.assertEqual(report["stage_count"], 5)
        self.assertEqual(report["paired_primary_count"], 24)
        self.assertEqual(score["primary_all_three_rule_quotes"]["RULE_FOCUS"], 24)
        self.assertEqual(score["primary_all_three_rule_quotes"]["BASE"], 0)
        self.assertEqual(report["primary_focus_minus_base_rows"], 24)
        self.assertTrue(report["preregistered_descriptive_gain_reached"])
        self.assertFalse(report["native_execution_independently_confirmed"])
        self.assertFalse(report["canonical_gate_pass"])
        self.assertEqual(report["step2_exit"], "UTILITY_FAIL")
        self.assertEqual(report["b3_l1"], "FAIL")
        self.assertEqual(report["jepa_weight"], 0)
        self.assertFalse(report["redmi_measured"])
        self.assertFalse(score["native_evidence_verified"])

    def test_missing_or_duplicate_stage_dirs_fail(self):
        with self.assertRaisesRegex(ValueError, "EXACT_FIVE_STAGE_DIRS_REQUIRED"):
            agg.aggregate(self.dirs[:4])
        with self.assertRaisesRegex(ValueError, "STAGE_DIR_MISSING_DUPLICATE_OR_SYMLINK"):
            agg.aggregate(self.dirs[:4] + [self.dirs[0]])

    def test_wrong_stage_order_fails_before_audit(self):
        paths = list(self.dirs)
        paths[0], paths[1] = paths[1], paths[0]
        with self.assertRaisesRegex(ValueError, "STAGE_ORDER_OR_FROZEN_PLAN_DRIFT"):
            agg.aggregate(paths)

    def test_modified_stored_postflight_refused(self):
        path = self.dirs[0] / "RUN513_POSTFLIGHT.json"
        value = json.loads(path.read_text())
        value["raw_observations_sha256"] = "f" * 64
        write(path, value)
        with self.assertRaisesRegex(ValueError, "STORED_POSTFLIGHT_OR_METRIC_ROWS_DRIFT"):
            self.run_mocked()

    def test_modified_stored_metric_row_refused(self):
        path = self.dirs[0] / "RUN513_VERIFIED_METRIC_ROWS.json"
        value = json.loads(path.read_text())
        value[0]["quotes"].append({"source_slot": "history0",
                                    "source_sha256": "0" * 64,
                                    "text": "fabricated"})
        write(path, value)
        with self.assertRaisesRegex(ValueError, "STORED_POSTFLIGHT_OR_METRIC_ROWS_DRIFT"):
            self.run_mocked()

    def test_nonfinite_stored_metric_row_refused(self):
        path = self.dirs[0] / "RUN513_VERIFIED_METRIC_ROWS.json"
        path.write_text('[NaN]\n')
        with self.assertRaisesRegex(ValueError, "NONFINITE_JSON"):
            self.run_mocked()

    def test_symlink_stage_refused(self):
        link = self.root / "linked"
        link.symlink_to(self.dirs[0], target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "STAGE_DIR_MISSING_DUPLICATE_OR_SYMLINK"):
            agg.aggregate([link] + self.dirs[1:])

    def test_original_run510_scorer_failure_not_masked(self):
        with patch.object(agg.metric, "score", side_effect=ValueError("SCORE_RED")):
            with self.assertRaisesRegex(ValueError, "SCORE_RED"):
                self.run_mocked()

    def test_existing_output_preflight_refused(self):
        import sys
        out = self.root / "out"
        out.mkdir()
        (out / "RUN516_AGGREGATE_REPORT.json").write_text("existing")
        argv = ["run516", "--output-dir", str(out)]
        for path in self.dirs:
            argv += ["--stage-dir", str(path)]
        with patch.object(sys, "argv", argv):
            with self.assertRaisesRegex(ValueError, "REFUSE_OVERWRITE_OR_PARTIAL_OUTPUT"):
                agg.main()


if __name__ == "__main__":
    unittest.main()
