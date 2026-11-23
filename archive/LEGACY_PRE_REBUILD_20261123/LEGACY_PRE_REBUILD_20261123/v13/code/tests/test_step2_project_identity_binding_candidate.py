"""Run129 source-bound project identity alias candidate: no native tests."""
from __future__ import annotations
import json
import os
from pathlib import Path
import unittest

from scripts import step2_project_identity_binding_candidate as candidate
from v13.utility import score_decision


class Run129ProjectIdentityCandidate(unittest.TestCase):
    def setUp(self):
        self.oracle = {"project": "Atlas", "action": "A", "options": []}
        self.base = {"project": "Project Atlas", "action": "A", "options": []}

    def test_literal_alias_bound_only_to_trusted_source_id(self):
        changed, tag = candidate.bind(json.dumps(self.base), "Atlas")
        self.assertEqual(tag, "SOURCE_ID_LITERAL_PREFIX_BOUND")
        self.assertEqual(json.loads(changed), self.oracle)
        self.assertTrue(score_decision(changed, self.oracle)["exact"])

    def test_exact_project_preserves_original_bytes(self):
        original = '{ "project": "Atlas", "action": "A", "options": [] }'
        changed, tag = candidate.bind(original, "Atlas")
        self.assertEqual(changed, original)
        self.assertEqual(tag, "SOURCE_ID_EXACT_UNCHANGED")

    def test_no_action_or_option_changes(self):
        answer = {"project": "Project Atlas", "action": "UNKNOWN",
                  "options": [{"entity": "A", "cost": 2, "days": 1,
                               "remaining": None, "local": True, "eligible": None}]}
        result, _ = candidate.bind(json.dumps(answer), "Atlas")
        self.assertEqual(json.loads(result)["action"], answer["action"])
        self.assertEqual(json.loads(result)["options"], answer["options"])

    def test_foreign_project_refused(self):
        for value in ("Project Borealis", "Borealis", "Project Atlas extra",
                      "project Atlas", "PROJECT Atlas", "Project  Atlas",
                      "Atlas/Borealis", "", " Project Atlas"):
            answer = dict(self.base, project=value)
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "IDENTITY_CONFLICT"):
                candidate.bind(json.dumps(answer), "Atlas")

    def test_untrusted_fixture_refused(self):
        for trusted in ("Unknown", "Project Atlas", "", None, 7):
            with self.subTest(trusted=trusted), self.assertRaisesRegex(ValueError, "UNTRUSTED_SOURCE_PROJECT"):
                candidate.bind(json.dumps(self.base), trusted)

    def test_duplicate_json_keys_refused(self):
        raw = '{"project":"Project Atlas","project":"Atlas","action":"A","options":[]}'
        with self.assertRaisesRegex(ValueError, "INVALID_ANSWER_JSON"):
            candidate.bind(raw, "Atlas")

    def test_missing_fields_or_invalid_types_refused(self):
        for answer in ("[]", "null", "not json", '{"project":"Project Atlas"}',
                       '{"project":null,"action":"A","options":[]}',
                       '{"project":"Project Atlas","action":7,"options":[]}'):
            with self.subTest(answer=answer), self.assertRaises(ValueError):
                candidate.bind(answer, "Atlas")

    def test_frozen_original_native_when_supplied(self):
        source_path = os.environ.get("V13_RUN116_SOURCE_REPORT")
        tool_path = os.environ.get("V13_RUN116_TOOL_REPORT")
        if not source_path or not tool_path:
            self.skipTest("original frozen native reports not supplied")
        from scripts import step2_exact_rule_native_replay_preflight as frozen
        from v13.common import file_hash
        self.assertEqual(file_hash(tool_path), candidate.TOOL_SHA256)
        source = frozen.load_original(Path(source_path))
        report = candidate.replay(source, json.loads(Path(tool_path).read_text()))
        self.assertEqual(report["rows"], 42)
        self.assertEqual(report["native_calls"], 0)
        self.assertEqual(report["literal_aliases_bound"], 40)
        self.assertEqual(report["full_exact_gained"], 6)
        self.assertFalse(report["canonical_gate_pass"])
        self.assertEqual(report["step2_status"], "UTILITY_FAIL")
        self.assertEqual(report["per_variant"]["both_exact"]["after_full_exact"], 2)


if __name__ == "__main__":
    unittest.main()
