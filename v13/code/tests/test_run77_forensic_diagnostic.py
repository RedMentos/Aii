"""Synthetic-only tests for read-only Run77 forensic diagnostics; no native claim."""
import copy
import unittest

from scripts import jef_b1b2_context_fixture_797 as f
from scripts import run77_native_forensic_diagnostic as forensic
from scripts import run77_b1b2_context_verify as original
from v13.common import dumps


def synthetic_report():
    rows = []
    scores = {role: {arm: 0 for arm in f.ARMS} for role in f.ROLES}
    for fixture in f.fixtures():
        for arm in f.ARMS:
            prior = {"source_id": "prior:" + fixture["project"],
                     "sha256": fixture["source_sha256"]["prior"]}
            current = {"source_id": "current:" + fixture["project"],
                       "sha256": fixture["source_sha256"]["current"]}
            sequence = ([(role, "prior") for role in f.ROLES]
                        if arm == "WITH_PRIOR" else [])
            sequence += [(role, "current") for role in f.ROLES]
            row = {
                "project": fixture["project"], "arm": arm,
                "status": "RECORDED",
                "source_sha256": fixture["source_sha256"],
                "closed_store_ok": True, "processes_reaped": True,
                "no_live_output": True,
                "native_call_count": len(sequence),
                "prior_source_ref": prior if arm == "WITH_PRIOR" else None,
                "current_source_ref": current,
                "offers": [], "captures": {},
            }
            for role, phase in sequence:
                ref = prior if phase == "prior" else current
                event_id = "event:" + fixture["project"] + ":" + phase
                summary = ("I recommend Option " + fixture["action"]
                           + ". Remaining budget: "
                           + str(fixture["remaining"]) + " credits."
                           if fixture["action"] != "NONE"
                           else "Neither option qualifies.")
                offer = {
                    "event_id": event_id, "role": role,
                    "native_metrics": {"status": "FINAL",
                                       "actual_model": original.MODELS[role]},
                    "offer": {"summary": summary, "quotes": []},
                    "evidence_refs": [],
                }
                query = {
                    "event_id": event_id, "target_role": role,
                    "source_refs": [ref],
                    "context_source_refs": ([prior]
                        if phase == "current" and arm == "WITH_PRIOR" else []),
                }
                entry = {
                    "role": role, "phase": phase, "status": "RECORDED",
                    "guarded_status": "SHADOW_LATEST_USER_OFFER_PRODUCED",
                    "process_reaped": True, "event_id": event_id,
                    "source_ref": ref, "offer": offer, "query": query,
                }
                messages = [{"role": "user", "content": "synthetic"}]
                row["captures"][role + ":" + phase] = {
                    "messages": messages,
                    "messages_sha256": f.sha(dumps(messages).encode()),
                }
                if phase == "current":
                    entry["summary"] = summary
                    entry["strict"] = f.strict_summary(
                        summary, fixture["action"], fixture["remaining"])
                    entry["context_source_refs_verified"] = True
                    scores[role][arm] += entry["strict"]
                    if role == "B2_GIST" and arm == "WITH_PRIOR":
                        entry["prior_evidence_refs_verified"] = False
                row["offers"].append(entry)
            rows.append(row)
    return {
        "schema": original.SCHEMA, "seed": f.SEED,
        "table_sha256": f.TABLE_SHA256,
        "binding": {"model_sha256": {
            "B1_DETAIL": f.B1_SHA256,
            "B2_GIST": f.B2_SHA256},
            "runner_sha256": f.RUNNER_SHA256},
        "rows": rows, "native_call_count": 36,
        "scores": scores, "b2_prior_evidence": 0,
        "status": f.scientific_verdict(scores, 0),
        "independent_utility_proven": False,
        "delivery_authority": 0, "learning_authority": 0,
        "output_committed": False, "tool_dispatches": 0,
        "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "world_jepa": "SHADOW", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
    }


class ForensicDiagnosticTests(unittest.TestCase):
    def test_synthetic_valid_report_does_not_claim_native(self):
        r = forensic.diagnose(synthetic_report())
        self.assertEqual(r["status"], "INDEPENDENT_RUN77_NATIVE_REPARSE_PASS")
        self.assertEqual(r["native_calls_observed"], 36)
        self.assertEqual(r["findings"], [])
        self.assertFalse(r["step2_promoted"])
        self.assertTrue(r["diagnostic_only"])

    def test_driver_and_verifier_prior_evidence_predicates_diverge(self):
        report = synthetic_report()
        row = report["rows"][0]
        entry = next(e for e in row["offers"]
                     if e["role"] == "B2_GIST" and e["phase"] == "current")
        prior = row["prior_source_ref"]
        fixture = f.fixtures()[0]
        # This ref is a real source span, but not a quote in the offer:
        # original driver's loose predicate could count it as verified.
        entry["offer"]["evidence_refs"] = [{
            "source_id": prior["source_id"], "sha256": prior["sha256"],
            "char_start": 0, "char_end": 7,
        }]
        self.assertEqual(fixture["prior"][0:7], "Project")
        entry["prior_evidence_refs_verified"] = True
        report["b2_prior_evidence"] = 1
        result = forensic.diagnose(report)
        self.assertEqual(result["status"], "ORIGINAL_VERIFIER_RED")
        self.assertIn("RUN77_B2_PRIOR_EVIDENCE_RED",
                      result["original_error"])
        self.assertIn("B2_EVIDENCE_PREDICATE_DIVERGENCE",
                      [e["code"] for e in result["findings"]])

    def test_missing_native_rows_never_pass(self):
        report = synthetic_report()
        report["rows"] = report["rows"][:1]
        report["native_call_count"] = 4
        result = forensic.diagnose(report)
        self.assertEqual(result["status"], "ORIGINAL_VERIFIER_RED")
        self.assertIn("ROW_COUNT_RED",
                      [e["code"] for e in result["findings"]])
        self.assertEqual(result["native_calls_observed"], 4)

    def test_source_mutation_detected_without_repair(self):
        report = synthetic_report()
        original_copy = copy.deepcopy(report)
        report["rows"][0]["current_source_ref"]["sha256"] = "0" * 64
        result = forensic.diagnose(report)
        self.assertEqual(result["status"], "ORIGINAL_VERIFIER_RED")
        self.assertIn("CURRENT_REF_RED",
                      [e["code"] for e in result["findings"]])
        self.assertNotEqual(report, original_copy)
        self.assertEqual(report["rows"][0]["current_source_ref"]["sha256"],
                         "0" * 64)

    def test_untrusted_report_input_rejected(self):
        result = forensic.diagnose([])
        self.assertEqual(result["status"], "FORENSIC_INPUT_RED")


if __name__ == "__main__":
    unittest.main()
