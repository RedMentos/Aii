"""Run134 software-only composed source-bound option/project correction tests."""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import unittest

from scripts import step2_composed_source_repairs_candidate as composed
from scripts import step2_exact_rule_native_replay_preflight as frozen
from scripts import step2_option_quote_consistency_candidate as quotes
from scripts import step2_project_identity_binding_candidate as projects
from scripts import step2_tool_replay as tool
from tests.test_step2_option_quote_consistency_candidate import case
from v13.common import dumps, file_hash


class Run134ComposedSourceRepair(unittest.TestCase):
    def test_exact_quote_then_tool_then_literal_project_binding(self):
        row, fixture, raw = case()
        fixed, status, fields = quotes.repair(raw, row, fixture)
        self.assertEqual((status, fields), ("SOURCE_EXACT_OPTIONS_REPAIRED", 1))
        decision, _ = tool.tool_answer(fixed, row["consumer_messages"])
        self.assertIsNotNone(decision)
        bound, tag = projects.bind(decision, fixture["id"])
        self.assertEqual(tag, "SOURCE_ID_LITERAL_PREFIX_BOUND")
        self.assertEqual(json.loads(bound)["project"], "Atlas")
        self.assertEqual(json.loads(bound)["action"], json.loads(decision)["action"])
        self.assertEqual(json.loads(bound)["options"], json.loads(decision)["options"])
        self.assertEqual(json.loads(raw)["options"][0]["local"], False)

    def test_forged_source_fails_before_tool_and_project_binding(self):
        row, fixture, raw = case()
        row["source_evidence"][0]["source_ref"]["sha256"] = "forged"
        with self.assertRaisesRegex(ValueError, "SOURCE_REF_BYTES_DRIFT"):
            quotes.repair(raw, row, fixture)

    def test_foreign_project_not_rewritten_as_trusted_project(self):
        row, fixture, raw = case()
        changed = json.loads(raw)
        changed["project"] = "Project Borealis"
        decision, _ = tool.tool_answer(dumps(changed), row["consumer_messages"])
        self.assertIsNotNone(decision)
        with self.assertRaisesRegex(ValueError, "IDENTITY_CONFLICT"):
            projects.bind(decision, fixture["id"])

    def test_same_policy_control_requires_identical_quotes(self):
        row, fixture, raw = case()
        row["variant"] = "same_policy_dual"
        u = json.loads(row["consumer_messages"][1]["content"])
        u["analysts"].append(deepcopy(u["analysts"][0]))
        row["consumer_messages"][1]["content"] = dumps(u)
        fixed, _, fields = quotes.repair(raw, row, fixture)
        self.assertEqual(fields, 1)
        decision, _ = tool.tool_answer(fixed, row["consumer_messages"])
        self.assertIsNotNone(decision)
        bound, _ = projects.bind(decision, fixture["id"])
        self.assertEqual(json.loads(bound)["project"], fixture["id"])
        u["analysts"][1]["verified_quotes"] = ["not a verified source quote"]
        row["consumer_messages"][1]["content"] = dumps(u)
        with self.assertRaisesRegex(ValueError, "SAME_POLICY_B1_QUOTES_CONFLICT"):
            quotes.repair(raw, row, fixture)

    def test_original_frozen_42_row_composition_when_supplied(self):
        source_path = os.environ.get("V13_RUN116_SOURCE_REPORT")
        tool_path = os.environ.get("V13_RUN116_TOOL_REPORT")
        if not source_path or not tool_path:
            self.skipTest("original native source/tool raw not supplied")
        self.assertEqual(file_hash(tool_path), quotes.TOOL_SHA256)
        source = frozen.load_original(Path(source_path))
        tool_raw = json.loads(Path(tool_path).read_text(encoding="utf-8"))
        source_before, tool_before = dumps(source), dumps(tool_raw)
        report = composed.replay(source, tool_raw)
        self.assertEqual((dumps(source), dumps(tool_raw)), (source_before, tool_before))
        self.assertEqual(report["rows"], 42)
        self.assertEqual(report["native_calls"], 0)
        self.assertEqual(report["quote_repaired_rows"], 7)
        self.assertEqual(report["quote_repaired_fields"], 25)
        self.assertEqual(report["project_aliases_bound"], 40)
        self.assertEqual(report["treatment_wrong_committed"], 0)
        self.assertFalse(report["canonical_gate_pass"])
        self.assertEqual(report["step2_status"], "UTILITY_FAIL")
        self.assertEqual(report["jepa_weight"], 0)
        self.assertFalse(report["redmi_measured"])
        self.assertFalse(report["whole_system_complete"])
        self.assertEqual(len(report["rows_detail"]), 42)
        self.assertTrue(all(r["original_raw_unchanged"] for r in report["rows_detail"]))
        self.assertEqual(sum(v["rows"] for v in report["per_variant"].values()), 42)


if __name__ == "__main__":
    unittest.main()
