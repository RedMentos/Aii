"""No-native tests for serial STEP2 exact-rule transport executor."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scripts import step2_exact_rule_transport_native as native
from scripts import step2_exact_rule_native_replay_preflight as preflight


class Run126MatchedC3NativeExecutorSoftware(unittest.TestCase):
    def test_order_alternates_without_changing_seed(self):
        self.assertEqual(native.C3_SEED, 13)
        self.assertEqual(native.BODY_SOURCE_SEED, 20)
        self.assertEqual(native.execution_order(0), ("control", "treatment"))
        self.assertEqual(native.execution_order(1), ("treatment", "control"))
        self.assertEqual(native.execution_order(42), ("control", "treatment"))
        self.assertEqual(native.EXPECTED_ROWS, 84)
        self.assertEqual(native.MODEL_HASHES["C3_LANGUAGE"],
                         "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d")

    def test_action_parser_fails_closed(self):
        for value in ('', 'not json', '[]', '{"action":"DELETE"}',
                      '{"action":7}', '{"action":null}'):
            self.assertEqual(native.action_from_answer(value), "INVALID")
        for action in ("A", "B", "NONE", "UNKNOWN"):
            self.assertEqual(native.action_from_answer(
                json.dumps({"action": action})), action)

    def test_summary_counts_from_rows_not_claim(self):
        fixtures = [{"id": project, "oracle": {"action": "A"}}
                    for project in preflight.PROJECTS]
        rows = []
        for mode in ("control", "treatment"):
            for variant in preflight.VARIANTS:
                for i, project in enumerate(preflight.PROJECTS):
                    action = "A" if mode == "treatment" else "UNKNOWN"
                    rows.append({"fixture": project, "variant": variant,
                                 "mode": mode, "action": action,
                                 "score": {"utility": 1.0 if action == "A" else 0.0,
                                           "exact": action == "A"}})
        report = native.summarize(rows, fixtures)
        for variant in preflight.VARIANTS:
            self.assertEqual(report["control"][variant]["unknown"], 6)
            self.assertEqual(report["control"][variant]["decision_exact"], 0)
            self.assertEqual(report["treatment"][variant]["decision_exact"], 6)
            self.assertEqual(report["treatment"][variant]["wrong_committed"], 0)
            self.assertEqual(report["treatment"][variant]["full_json_exact"], 6)

    def test_summary_detects_wrong_committed(self):
        fixtures = [{"id": project, "oracle": {"action": "A"}}
                    for project in preflight.PROJECTS]
        rows = []
        for mode in ("control", "treatment"):
            for variant in preflight.VARIANTS:
                for project in preflight.PROJECTS:
                    rows.append({"fixture": project, "variant": variant,
                                 "mode": mode,
                                 "action": "B" if mode == "treatment" else "UNKNOWN",
                                 "score": {"utility": 0.0, "exact": False}})
        report = native.summarize(rows, fixtures)
        self.assertEqual(sum(v["wrong_committed"]
                             for v in report["treatment"].values()), 42)

    def test_missing_preflight_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "ORIGINAL_SOURCE_BYTES_DRIFT"):
                native.verify_input(Path(tmp) / "absent.json",
                                    Path(tmp) / "absent-pairs.json")

    def test_incomplete_variant_refused(self):
        fixtures = [{"id": project, "oracle": {"action": "A"}}
                    for project in preflight.PROJECTS]
        with self.assertRaisesRegex(ValueError, "INCOMPLETE_VARIANT_PAIR"):
            native.summarize([], fixtures)


if __name__ == "__main__":
    unittest.main()
