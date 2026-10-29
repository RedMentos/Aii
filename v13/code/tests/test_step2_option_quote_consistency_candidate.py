"""Run130 source-ref-bound option consistency candidate synthetic counterexamples."""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import unittest

from scripts import step2_option_quote_consistency_candidate as candidate
from scripts import step2_exact_rule_native_replay_preflight as frozen
from v13.common import dumps, file_hash


def case():
    source = ("Project Atlas supplier data sheet. Option A: cost 60 euros, duration 3 days, "
              "local true. Option B: cost 85 euros, duration 4 days, local false.")
    fixture = {"id": "Atlas", "current": "Project Atlas. Decide.", "history": [source]}
    ref = {"sha256": hashlib.sha256(source.encode()).hexdigest(),
           "char_start": 0, "char_end": len(source), "source_id": "Atlas-h0"}
    messages = [{"role": "system", "content": "extract"},
                {"role": "user", "content": dumps({
                    "current_source": fixture["current"],
                    "analysts": [{"role": "B1_DETAIL", "verified_quotes": [source]}]})}]
    row = {"checks": {"every_source_read_validated": True},
           "source_evidence": [{"source_ref": ref, "text": source}],
           "consumer_messages": messages}
    raw = dumps({"project": "Project Atlas", "options": [
        {"entity": "A", "cost": 60, "days": 3, "local": False},
        {"entity": "B", "cost": 85, "days": 4, "local": False}],
        "budget": None, "deadline": None, "local_only": None})
    return row, fixture, raw


class Run130QuoteConsistency(unittest.TestCase):
    def test_exact_source_repairs_only_wrong_typed_field(self):
        row, fixture, raw = case()
        fixed, status, changed = candidate.repair(raw, row, fixture)
        self.assertEqual((status, changed), ("SOURCE_EXACT_OPTIONS_REPAIRED", 1))
        before, after = json.loads(raw), json.loads(fixed)
        self.assertEqual(before["project"], after["project"])
        self.assertEqual(before["budget"], after["budget"])
        self.assertEqual(before["deadline"], after["deadline"])
        self.assertEqual(before["local_only"], after["local_only"])
        self.assertTrue(after["options"][0]["local"])

    def test_matching_options_preserve_original_raw_bytes(self):
        row, fixture, raw = case()
        x = json.loads(raw)
        x["options"][0]["local"] = True
        raw = json.dumps(x, indent=2)
        fixed, status, changed = candidate.repair(raw, row, fixture)
        self.assertEqual(fixed, raw)
        self.assertEqual((status, changed), ("EXACT_OPTIONS_ALREADY_MATCH", 0))

    def test_source_hash_forgery_rejected(self):
        row, fixture, raw = case()
        row["source_evidence"][0]["source_ref"]["sha256"] = "forged"
        with self.assertRaisesRegex(ValueError, "SOURCE_REF_BYTES_DRIFT"):
            candidate.repair(raw, row, fixture)

    def test_quote_not_in_source_ref_rejected(self):
        row, fixture, raw = case()
        u = json.loads(row["consumer_messages"][1]["content"])
        u["analysts"][0]["verified_quotes"] = ["Option A: cost 1 euros, duration 1 days, local true."]
        row["consumer_messages"][1]["content"] = dumps(u)
        with self.assertRaisesRegex(ValueError, "UNVERIFIED_B1_QUOTE"):
            candidate.repair(raw, row, fixture)

    def test_no_b1_is_no_repair(self):
        row, fixture, raw = case()
        u = json.loads(row["consumer_messages"][1]["content"])
        u["analysts"] = []
        row["consumer_messages"][1]["content"] = dumps(u)
        fixed, status, changed = candidate.repair(raw, row, fixture)
        self.assertEqual((fixed, changed), (raw, 0))
        self.assertEqual(status, "NO_UNAMBIGUOUS_SOURCE_OPTIONS")

    def test_conflicting_verified_options_fail_closed(self):
        row, fixture, raw = case()
        conflict = "Option A: cost 61 euros, duration 3 days, local true."
        fixture["history"].append(conflict)
        row["source_evidence"].append({"source_ref": {
            "sha256": hashlib.sha256(conflict.encode()).hexdigest(),
            "char_start": 0, "char_end": len(conflict), "source_id": "Atlas-h1"},
            "text": conflict})
        u = json.loads(row["consumer_messages"][1]["content"])
        u["analysts"][0]["verified_quotes"].append(conflict)
        row["consumer_messages"][1]["content"] = dumps(u)
        fixed, status, changed = candidate.repair(raw, row, fixture)
        self.assertEqual((fixed, changed), (raw, 0))
        self.assertEqual(status, "NO_UNAMBIGUOUS_SOURCE_OPTIONS")

    def test_duplicate_json_keys_rejected(self):
        row, fixture, raw = case()
        raw = raw.replace('"budget":null', '"budget":null,"budget":0')
        with self.assertRaisesRegex(ValueError, "INVALID_C3_EXTRACTION_JSON"):
            candidate.repair(raw, row, fixture)

    def test_duplicate_entity_rejected(self):
        row, fixture, raw = case()
        x = json.loads(raw)
        x["options"][1]["entity"] = "A"
        with self.assertRaisesRegex(ValueError, "DUPLICATE_OPTION_ENTITY"):
            candidate.repair(dumps(x), row, fixture)

    def test_same_policy_dual_two_identical_b1_quotes_repair(self):
        row, fixture, raw = case()
        row["variant"] = "same_policy_dual"
        u = json.loads(row["consumer_messages"][1]["content"])
        u["analysts"].append(deepcopy(u["analysts"][0]))
        row["consumer_messages"][1]["content"] = dumps(u)
        fixed, status, changed = candidate.repair(raw, row, fixture)
        self.assertEqual((status, changed), ("SOURCE_EXACT_OPTIONS_REPAIRED", 1))
        self.assertTrue(json.loads(fixed)["options"][0]["local"])

    def test_duplicate_b1_rejected_outside_same_policy_control(self):
        row, fixture, raw = case()
        row["variant"] = "b1_only"
        u = json.loads(row["consumer_messages"][1]["content"])
        u["analysts"].append(deepcopy(u["analysts"][0]))
        row["consumer_messages"][1]["content"] = dumps(u)
        with self.assertRaisesRegex(ValueError, "DUPLICATE_B1_ANALYST"):
            candidate.repair(raw, row, fixture)

    def test_same_policy_conflicting_verified_quote_lists_rejected(self):
        row, fixture, raw = case()
        row["variant"] = "same_policy_dual"
        alt = "Option A: cost 61 euros, duration 3 days, local true."
        fixture["history"].append(alt)
        row["source_evidence"].append({"source_ref": {
            "sha256": hashlib.sha256(alt.encode()).hexdigest(),
            "char_start": 0, "char_end": len(alt), "source_id": "Atlas-h1"},
            "text": alt})
        u = json.loads(row["consumer_messages"][1]["content"])
        u["analysts"].append({"role": "B1_DETAIL", "verified_quotes": [alt]})
        row["consumer_messages"][1]["content"] = dumps(u)
        with self.assertRaisesRegex(ValueError, "SAME_POLICY_B1_QUOTES_CONFLICT"):
            candidate.repair(raw, row, fixture)

    def test_same_policy_missing_or_extra_b1_rejected(self):
        for quote_mode in ("one", "empty", "three"):
            row, fixture, raw = case()
            row["variant"] = "same_policy_dual"
            u = json.loads(row["consumer_messages"][1]["content"])
            if quote_mode != "one":
                u["analysts"].append(deepcopy(u["analysts"][0]))
            if quote_mode == "empty":
                u["analysts"][1]["verified_quotes"] = []
            if quote_mode == "three":
                u["analysts"].append(deepcopy(u["analysts"][0]))
            row["consumer_messages"][1]["content"] = dumps(u)
            with self.subTest(quote_mode=quote_mode), self.assertRaisesRegex(
                    ValueError, "SAME_POLICY_B1_(COUNT|QUOTES_MISSING)"):
                candidate.repair(raw, row, fixture)

    def test_original_native_42_rows_when_supplied(self):
        src = os.environ.get("V13_RUN116_SOURCE_REPORT")
        tool = os.environ.get("V13_RUN116_TOOL_REPORT")
        if not src or not tool:
            self.skipTest("original frozen native raw not supplied")
        self.assertEqual(file_hash(tool), candidate.TOOL_SHA256)
        report = candidate.replay(frozen.load_original(Path(src)),
                                  json.loads(Path(tool).read_text()))
        self.assertEqual(report["rows"], 42)
        self.assertEqual(report["native_calls"], 0)
        self.assertEqual(report["repaired_rows"], 7)
        self.assertEqual(report["repaired_fields"], 25)
        self.assertFalse(report["canonical_gate_pass"])
        self.assertEqual(report["step2_status"], "UTILITY_FAIL")


if __name__ == "__main__":
    unittest.main()
