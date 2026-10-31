"""Synthetic-only native prompt byte transport audit tests (no model calls)."""
import copy
import json
import unittest

from scripts import jef_b1b2_context_fixture_797 as f
from scripts import run77_prompt_transport_audit as audit
from v13.common import dumps


def synthetic_report():
    rows = []
    for fixture in f.fixtures():
        for arm in f.ARMS:
            row = {"project": fixture["project"], "arm": arm,
                   "offers": [], "captures": {}}
            for role in f.ROLES:
                key = "recent_source" if role == "B1_DETAIL" else "earlier_context"
                authority = ("RECENT_SOURCE_NOT_FACT" if role == "B1_DETAIL"
                             else "PRIOR_HYPOTHESIS_NOT_FACT")
                query = {key: ([{"exact_source_excerpt": fixture["prior"],
                                "authority": authority}]
                               if arm == "WITH_PRIOR" else []),
                         "source_segments": [{"text": fixture["current"]}]}
                messages = [{"role": "system", "content": "synthetic only"},
                            {"role": "user", "content": dumps(query)}]
                row["offers"].append({"role": role, "phase": "current"})
                row["captures"][role + ":current"] = {
                    "messages": messages,
                    "messages_sha256": f.sha(dumps(messages).encode()),
                }
            rows.append(row)
    return {"rows": rows}


def resign(capture):
    capture["messages_sha256"] = f.sha(dumps(capture["messages"]).encode())


class PromptTransportTests(unittest.TestCase):
    def test_exact_native_source_transport_both_roles_synthetic(self):
        result = audit.audit_report(synthetic_report())
        self.assertEqual(result["status"],
                         "PROMPT_BYTES_SOURCE_TRANSPORT_VERIFIED_SHADOW")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["verified"], {
            role: {"WITH_PRIOR": 6, "CURRENT_ONLY": 6}
            for role in f.ROLES})
        self.assertFalse(result["native_utility_proven"])

    def test_query_packet_reference_alone_not_enough(self):
        report = synthetic_report()
        capture = report["rows"][0]["captures"]["B2_GIST:current"]
        query = json.loads(capture["messages"][1]["content"])
        query["earlier_context"] = []
        capture["messages"][1]["content"] = dumps(query)
        resign(capture)
        result = audit.audit_report(report)
        self.assertIn("PRIOR_POLICY_NOT_EXACT_IN_NATIVE_QUERY",
                      [e["code"] for e in result["findings"]])
        self.assertEqual(result["verified"]["B2_GIST"]["WITH_PRIOR"], 5)

    def test_current_only_prior_leak_fails(self):
        report = synthetic_report()
        capture = report["rows"][1]["captures"]["B1_DETAIL:current"]
        query = json.loads(capture["messages"][1]["content"])
        query["recent_source"] = [{"exact_source_excerpt": f.fixtures()[0]["prior"],
                                   "authority": "RECENT_SOURCE_NOT_FACT"}]
        capture["messages"][1]["content"] = dumps(query)
        resign(capture)
        result = audit.audit_report(report)
        self.assertIn("ABLATION_PRIOR_POLICY_LEAK_RED",
                      [e["code"] for e in result["findings"]])

    def test_capture_mutation_detected(self):
        report = synthetic_report()
        old = copy.deepcopy(report)
        report["rows"][0]["captures"]["B1_DETAIL:current"]["messages"][1]["content"] += " "
        result = audit.audit_report(report)
        self.assertIn("NATIVE_CAPTURE_HASH_RED",
                      [e["code"] for e in result["findings"]])
        self.assertNotEqual(report, old)

    def test_missing_rows_not_native_proof(self):
        result = audit.audit_report({"rows": []})
        self.assertEqual(result["status"], "PROMPT_TRANSPORT_RED")
        self.assertFalse(result["native_utility_proven"])


if __name__ == "__main__":
    unittest.main()
