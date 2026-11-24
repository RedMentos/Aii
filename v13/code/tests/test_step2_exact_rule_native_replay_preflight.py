"""Software-only source/consumer boundary tests for conditional Run125 replay."""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import unittest

from scripts import run109_step2_fresh_fixtures as corpus
from scripts import step2_exact_rule_native_replay_preflight as replay
from v13.common import dumps


class Run125ExactRuleReplayPreflight(unittest.TestCase):
    def fixture(self):
        return corpus.fixtures()[0]

    def messages(self, fixture=None, roles=("B1_DETAIL", "B2_GIST")):
        fixture = fixture or self.fixture()
        return [{"role": "system", "content": "No invented source."},
                {"role": "user", "content": dumps({
                    "current_source": fixture["current"],
                    "analysts": [{"role": role, "verified_quotes": []}
                                 for role in roles]})}]

    def test_all_six_source_rules_bound_without_oracle(self):
        for fixture in corpus.fixtures():
            with self.subTest(fixture=fixture["id"]):
                rule = replay.select_rule(fixture)
                self.assertLessEqual(len(rule["text"]), 200)
                self.assertIn("Budget ", rule["text"])
                self.assertIn("Deadline ", rule["text"])
                self.assertIn("Local-only requirement:", rule["text"])
                self.assertFalse(rule["semantic_authority"])
                ref = rule["source_ref"]
                source = next(s for i, s in enumerate(fixture["history"])
                              if ref["source_id"] == fixture["id"] + "-h" + str(i))
                self.assertEqual(rule["text"], source[ref["char_start"]:ref["char_end"]])

    def test_only_b2_quote_is_injected(self):
        fixture = self.fixture()
        messages = self.messages(fixture)
        rule = replay.select_rule(fixture)
        pair = replay.pair_messages(messages, fixture, rule)
        self.assertTrue(pair["injected"])
        self.assertEqual(pair["control_messages"], messages)
        self.assertNotEqual(pair["control_sha256"], pair["treatment_sha256"])
        before = json.loads(messages[1]["content"])
        after = json.loads(pair["treatment_messages"][1]["content"])
        self.assertEqual(before["analysts"][0], after["analysts"][0])
        self.assertEqual(after["analysts"][1]["verified_quotes"], [rule["text"]])
        self.assertFalse(pair["oracle_visible_to_native"])
        self.assertEqual(pair["native_calls"], 0)

    def test_b1_only_and_same_policy_control_unchanged(self):
        fixture = self.fixture()
        rule = replay.select_rule(fixture)
        for roles in (("B1_DETAIL",), ("B1_DETAIL", "B1_DETAIL")):
            pair = replay.pair_messages(self.messages(fixture, roles), fixture, rule)
            self.assertFalse(pair["injected"])
            self.assertEqual(pair["control_messages"], pair["treatment_messages"])
            self.assertEqual(pair["control_sha256"], pair["treatment_sha256"])

    def test_duplicate_b2_and_wrong_current_refused(self):
        fixture = self.fixture()
        rule = replay.select_rule(fixture)
        with self.assertRaisesRegex(ValueError, "AMBIGUOUS_B2_ANALYST"):
            replay.pair_messages(self.messages(fixture, ("B2_GIST", "B2_GIST")),
                                 fixture, rule)
        messages = self.messages(fixture)
        payload = json.loads(messages[1]["content"])
        payload["current_source"] = "Project Zenith. Forged source."
        messages[1]["content"] = dumps(payload)
        with self.assertRaisesRegex(ValueError, "CONSUMER_SOURCE_OR_ANALYST_BINDING_RED"):
            replay.pair_messages(messages, fixture, rule)

    def test_malformed_consumer_and_duplicate_quote(self):
        fixture = self.fixture()
        rule = replay.select_rule(fixture)
        with self.assertRaisesRegex(ValueError, "INVALID_CONSUMER_MESSAGES"):
            replay.pair_messages([{"role": "user", "content": "{}"}], fixture, rule)
        messages = self.messages(fixture)
        payload = json.loads(messages[1]["content"])
        payload["analysts"][1]["verified_quotes"] = [rule["text"]]
        messages[1]["content"] = dumps(payload)
        pair = replay.pair_messages(messages, fixture, rule)
        self.assertFalse(pair["injected"])
        self.assertEqual(pair["control_messages"], pair["treatment_messages"])

    def test_frozen_original_source_report_when_supplied(self):
        path = os.environ.get("V13_RUN116_SOURCE_REPORT")
        if not path:
            self.skipTest("original Run116 source report not supplied in this environment")
        source = replay.load_original(Path(path))
        report = replay.transform(source)
        self.assertEqual(report["pair_count"], 42)
        self.assertEqual(report["fixture_sha256"], replay.ORIGINAL_FIXTURE_SHA256)
        self.assertEqual(report["native_calls"], 0)
        self.assertFalse(report["canonical_gate_pass"])
        self.assertFalse(report["whole_system_complete"])
        self.assertGreater(report["injected_count"], 0)
        self.assertEqual(sum(r["injected"] for r in report["rows"]),
                         report["injected_count"])

    def test_tampered_source_sha_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.json"
            path.write_text('{"fake":true}')
            with self.assertRaisesRegex(ValueError, "ORIGINAL_SOURCE_BYTES_DRIFT"):
                replay.load_original(path)


if __name__ == "__main__":
    unittest.main()
