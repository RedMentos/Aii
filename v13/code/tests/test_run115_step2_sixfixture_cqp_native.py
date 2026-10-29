"""Run115 synthetic guard regressions; no native/model execution."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts import run115_step2_sixfixture_cqp_native as pilot
from scripts import run111_step2_fresh_native_preflight as pre
from v13.common import digest, dumps


class Run115SixFixtureGuards(unittest.TestCase):
    def setUp(self):
        self.models = {"B1_DETAIL": "b1", "B2_GIST": "b2", "C3_LANGUAGE": "c3"}
        rows = []
        for fixture in pilot.FIXTURE_IDS:
            for variant in pilot.VARIANTS:
                rows.append({
                    "fixture": fixture, "variant": variant, "status": "RECORDED",
                    "processes_reaped": True, "oracle_visible_to_native": False,
                    "native_consumer_metrics": {"status": "FINAL"},
                    "consumer_messages": [{"role": "user", "content": "test"}],
                    "score": {"utility": 0.0, "exact": False},
                })
        self.source = {
            "status": "UTILITY_FAIL", "canonical_gate_pass": False,
            "phone_measured": False, "all_structural_checks_passed": True,
            "source_unchanged": True, "installed_artifacts_unchanged": True,
            "distinct_bodies": True, "same_weight_file": False,
            "fixture_sha256": pilot.FIXTURE_SHA256,
            "fixtures": pre.corpus.fixtures(), "paired": {"complete": True},
            "preparations": [
                {"fixture": f, "status": "RECORDED",
                 "model_sha256": self.models} for f in pilot.FIXTURE_IDS],
            "rows": rows, "wire_arm": {"arm": "w1"},
        }
        self.seal_source()
        tool_rows = []
        for row in rows:
            tool_rows.append({
                "fixture": row["fixture"], "variant": row["variant"],
                "status": "RECORDED", "oracle_visible_to_native": False,
                "consumer_metrics": {"status": "FINAL"},
                "consumer_messages_sha256": digest(dumps(row["consumer_messages"])),
                "score": {"utility": 0.0, "exact": False},
            })
        self.tool = {
            "status": "TOOL_UTILITY_FAIL", "canonical_gate_pass": False,
            "phone_measured": False, "installed_artifacts_unchanged": True,
            "paired_tool": {"complete": True}, "rows": tool_rows,
            "summary": {"tool": {
                v: {"rows": len(pilot.FIXTURE_IDS), "wrong_committed": 0}
                for v in pilot.VARIANTS}},
        }
        self.seal_tool()

    def seal_source(self):
        self.source["row_sha256"] = {
            r["fixture"] + ":" + r["variant"]: digest(dumps(r))
            for r in self.source["rows"]}

    def seal_tool(self):
        self.tool["row_sha256"] = {
            r["fixture"] + ":" + r["variant"]: digest(dumps(r))
            for r in self.tool["rows"]}

    def test_frozen_prereg_unchanged_and_42_rows(self):
        dry = pilot.prereg()
        self.assertFalse(dry["native_execution"])
        self.assertEqual(dry["registration"]["registered_native_rows"], 378)
        self.assertEqual(pilot.EXPECTED_ROWS, 42)
        self.assertEqual(pilot.EXPECTED_OFFERS, 72)
        self.assertEqual(len(pilot.exact_pairs()), 42)

    def test_synthetic_complete_source_and_tool_structural_only(self):
        result = pilot.verify_source(
            self.source, {"offers": 72, "with_question": 72}, self.models)
        self.assertEqual(result["rows"], 42)
        self.assertEqual(pilot.verify_tool(self.source, self.tool)["wrong_committed"], 0)
        self.assertFalse(self.source["canonical_gate_pass"])
        self.assertFalse(self.tool["canonical_gate_pass"])

    def test_reject_missing_source_row_even_with_resealed_hashes(self):
        self.source["rows"].pop()
        self.seal_source()
        with self.assertRaisesRegex(ValueError, "SOURCE_STRUCTURAL_FAIL"):
            pilot.verify_source(
                self.source, {"offers": 72, "with_question": 72}, self.models)

    def test_reject_duplicate_source_pair_even_with_resealed_hashes(self):
        self.source["rows"][-1] = deepcopy(self.source["rows"][0])
        self.seal_source()
        with self.assertRaisesRegex(ValueError, "SOURCE_STRUCTURAL_FAIL"):
            pilot.verify_source(
                self.source, {"offers": 72, "with_question": 72}, self.models)

    def test_reject_unsealed_source_row_and_nonfinal_native(self):
        self.source["rows"][0]["consumer_messages"].append(
            {"role": "user", "content": "tamper"})
        with self.assertRaisesRegex(ValueError, "SOURCE_ROW_FAIL"):
            pilot.verify_source(
                self.source, {"offers": 72, "with_question": 72}, self.models)
        self.seal_source()
        self.source["rows"][0]["native_consumer_metrics"]["status"] = "TIMEOUT"
        self.seal_source()
        with self.assertRaisesRegex(ValueError, "SOURCE_ROW_FAIL"):
            pilot.verify_source(
                self.source, {"offers": 72, "with_question": 72}, self.models)

    def test_reject_model_drift_and_wrong_offer_count(self):
        self.source["preparations"][0]["model_sha256"] = {"B1_DETAIL": "wrong"}
        with self.assertRaisesRegex(ValueError, "SOURCE_STRUCTURAL_FAIL"):
            pilot.verify_source(
                self.source, {"offers": 72, "with_question": 72}, self.models)
        self.source["preparations"][0]["model_sha256"] = self.models
        with self.assertRaisesRegex(ValueError, "SOURCE_STRUCTURAL_FAIL"):
            pilot.verify_source(
                self.source, {"offers": 71, "with_question": 72}, self.models)

    def test_reject_tool_wrong_committed_and_missing_row(self):
        self.tool["summary"]["tool"]["both_exact"]["wrong_committed"] = 1
        with self.assertRaisesRegex(ValueError, "TOOL_WRONG_COMMITTED"):
            pilot.verify_tool(self.source, self.tool)
        self.tool["summary"]["tool"]["both_exact"]["wrong_committed"] = 0
        self.tool["rows"].pop()
        self.seal_tool()
        with self.assertRaisesRegex(ValueError, "TOOL_STRUCTURAL_FAIL"):
            pilot.verify_tool(self.source, self.tool)

    def test_reject_tool_source_message_mismatch(self):
        self.tool["rows"][0]["consumer_messages_sha256"] = "0" * 64
        self.seal_tool()
        with self.assertRaisesRegex(ValueError, "TOOL_ROW_FAIL"):
            pilot.verify_tool(self.source, self.tool)

    def test_replay_requires_complete_source_and_frozen_fixture(self):
        module = pilot.private_tool_replay()
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.json"
            path.write_text(json.dumps(self.source), encoding="utf-8")
            self.assertEqual(len(module.recorded(path)["rows"]), 42)
            self.source["paired"]["complete"] = False
            path.write_text(json.dumps(self.source), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "REPLAY_INPUT_REFUSED"):
                module.recorded(path)

    def test_reject_gate_promotion_and_same_weights(self):
        self.source["canonical_gate_pass"] = True
        with self.assertRaisesRegex(ValueError, "SOURCE_STRUCTURAL_FAIL"):
            pilot.verify_source(
                self.source, {"offers": 72, "with_question": 72}, self.models)
        self.source["canonical_gate_pass"] = False
        self.source["same_weight_file"] = True
        with self.assertRaisesRegex(ValueError, "SOURCE_STRUCTURAL_FAIL"):
            pilot.verify_source(
                self.source, {"offers": 72, "with_question": 72}, self.models)


if __name__ == "__main__":
    unittest.main()
