"""Run140 source-only B1/B2 fusion controls; no C3/native execution."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import unittest

from scripts import step2_source_only_fusion_control as candidate
from scripts import step2_exact_rule_native_replay_preflight as frozen
from scripts import step2_option_quote_consistency_candidate as quotes
from tests.test_step2_option_quote_consistency_candidate import case
from v13.common import dumps, file_hash


RULE = "Budget 100 euros. Deadline 5 days. Local-only requirement: false."


def add_b2(row, fixture, text=RULE):
    fixture["history"].append(text)
    row["source_evidence"].append({
        "source_ref": {"sha256": hashlib.sha256(text.encode()).hexdigest(),
                       "char_start": 0, "char_end": len(text),
                       "source_id": "Atlas-b2"},
        "text": text,
    })
    user = json.loads(row["consumer_messages"][1]["content"])
    b2 = next((a for a in user["analysts"] if a["role"] == "B2_GIST"), None)
    if b2 is None:
        user["analysts"].append({"role": "B2_GIST", "verified_quotes": [text]})
    else:
        b2["verified_quotes"].append(text)
    row["consumer_messages"][1]["content"] = dumps(user)


class Run140SourceOnlyFusion(unittest.TestCase):
    def test_verified_b1_and_b2_fuse_to_decision_without_c3(self):
        row, fixture, _ = case()
        row["variant"] = "both_exact"
        add_b2(row, fixture)
        out = candidate.decide_source_only(row, fixture)
        self.assertEqual(out["status"], "SOURCE_ONLY_DECISION")
        self.assertEqual(out["action"], "A")
        self.assertEqual((out["b1_quotes"], out["b2_quotes"]), (1, 1))
        self.assertEqual(out["options"][0]["remaining"], 40)
        self.assertEqual(out["options"][1]["eligible"], True)

    def test_no_b2_rules_abstains_instead_of_inventing(self):
        row, fixture, _ = case()
        row["variant"] = "b1_only"
        out = candidate.decide_source_only(row, fixture)
        self.assertEqual(out["action"], "UNKNOWN")
        self.assertEqual(out["status"], "ABSTAIN_RULES_UNAVAILABLE")
        self.assertTrue(all(o["eligible"] is None for o in out["options"]))

    def test_b2_without_b1_options_abstains(self):
        row, fixture, _ = case()
        row["variant"] = "b2_only"
        user = json.loads(row["consumer_messages"][1]["content"])
        user["analysts"] = []
        row["consumer_messages"][1]["content"] = dumps(user)
        add_b2(row, fixture)
        out = candidate.decide_source_only(row, fixture)
        self.assertEqual(out["status"], "ABSTAIN_NO_UNAMBIGUOUS_B1_OPTIONS")
        self.assertIsNone(out["options"])

    def test_forged_b2_quote_rejected(self):
        row, fixture, _ = case()
        row["variant"] = "both_exact"
        add_b2(row, fixture)
        user = json.loads(row["consumer_messages"][1]["content"])
        user["analysts"][1]["verified_quotes"] = ["Budget 900 euros."]
        row["consumer_messages"][1]["content"] = dumps(user)
        with self.assertRaisesRegex(ValueError, "UNVERIFIED_B2_QUOTE"):
            candidate.decide_source_only(row, fixture)

    def test_b2_source_ref_hash_forgery_rejected(self):
        row, fixture, _ = case()
        row["variant"] = "both_exact"
        add_b2(row, fixture)
        row["source_evidence"][-1]["source_ref"]["sha256"] = "forged"
        with self.assertRaisesRegex(ValueError, "SOURCE_REF_BYTES_DRIFT"):
            candidate.decide_source_only(row, fixture)

    def test_conflicting_b2_rules_refuse_without_revision_order(self):
        row, fixture, _ = case()
        row["variant"] = "both_exact"
        add_b2(row, fixture)
        add_b2(row, fixture, "Budget 50 euros. Deadline 1 day. Local-only requirement: true.")
        out = candidate.decide_source_only(row, fixture)
        self.assertEqual(out["action"], "UNKNOWN")
        self.assertEqual(out["status"], "ABSTAIN_RULES_UNAVAILABLE")

    def test_current_rules_override_older_verified_b2(self):
        row, fixture, _ = case()
        row["variant"] = "both_exact"
        add_b2(row, fixture, "Budget 50 euros. Deadline 1 day. Local-only requirement: true.")
        fixture["current"] = "Project Atlas. Budget 100 euros. Deadline 5 days. Local-only requirement: false. Decide."
        user = json.loads(row["consumer_messages"][1]["content"])
        user["current_source"] = fixture["current"]
        row["consumer_messages"][1]["content"] = dumps(user)
        out = candidate.decide_source_only(row, fixture)
        self.assertEqual(out["action"], "A")

    def test_duplicate_b2_analyst_rejected(self):
        row, fixture, _ = case()
        row["variant"] = "both_exact"
        add_b2(row, fixture)
        user = json.loads(row["consumer_messages"][1]["content"])
        user["analysts"].append(deepcopy(user["analysts"][1]))
        row["consumer_messages"][1]["content"] = dumps(user)
        with self.assertRaisesRegex(ValueError, "DUPLICATE_B2_ANALYST"):
            candidate.decide_source_only(row, fixture)

    def test_original_native_42_rows_source_only_control_when_supplied(self):
        source_path = os.environ.get("V13_RUN116_SOURCE_REPORT")
        tool_path = os.environ.get("V13_RUN116_TOOL_REPORT")
        if not source_path or not tool_path:
            self.skipTest("original frozen native raw not supplied")
        self.assertEqual(file_hash(tool_path), quotes.TOOL_SHA256)
        source = frozen.load_original(Path(source_path))
        tool = json.loads(Path(tool_path).read_text())
        source_before, tool_before = dumps(source), dumps(tool)
        report = candidate.replay(source, tool)
        self.assertEqual((dumps(source), dumps(tool)), (source_before, tool_before))
        self.assertEqual(report["rows"], 42)
        self.assertEqual(report["native_calls"], 0)
        self.assertFalse(report["canonical_gate_pass"])
        self.assertEqual(report["step2_status"], "UTILITY_FAIL")
        self.assertEqual(report["jepa_weight"], 0)
        self.assertFalse(report["whole_system_complete"])
        self.assertEqual(report["treatment_wrong_committed"], 0)
        self.assertEqual(report["per_variant"]["b1_only"]["committed"], 0)
        self.assertEqual(report["per_variant"]["both_exact"]["committed"], 3)
        self.assertEqual(report["per_variant"]["both_control"]["committed"], 3)


if __name__ == "__main__":
    unittest.main()
