"""Run87 independent verifier adversarial SYNTHETIC report tests, NO native run."""
import copy
import unittest

try:
    from scripts import jef_b1b2_budget_fixture_877 as f
    from scripts import run87_b1b2_budget_verify as v
    from v13.common import dumps
except ImportError:
    f = v = dumps = None


def fake_ref(text, name):
    return {"source_id": "src_" + name, "sha256": f.sha(text.encode()),
            "char_start": 0, "char_end": len(text), "modality": "text"}


def synthetic_report():
    """Fake structural verifier fixture; NEVER native evidence."""
    report = {
        "schema": v.SCHEMA, "seed": f.SEED, "table_sha256": f.TABLE_SHA256,
        "binding": {"model_sha256": {"B1_DETAIL": f.B1_SHA256,
                                       "B2_GIST": f.B2_SHA256},
                    "runner_sha256": f.RUNNER_SHA256},
        "status": "BUDGET_NONINFERIOR_SHADOW", "rows": [],
        "scores": {role: {arm: 0 for arm in f.ARMS} for role in f.ROLES},
        "b2_long_prior_evidence": 0, "native_call_count": 48,
        "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "world_jepa": "SHADOW", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
        "independent_utility_proven": False,
        "delivery_authority": 0, "learning_authority": 0,
        "output_committed": False, "tool_dispatches": 0,
    }
    for fixture in f.fixtures():
        prior = fake_ref(fixture["prior"], fixture["project"] + "_prior")
        current = fake_ref(fixture["current"], fixture["project"] + "_current")
        for arm in fixture["arm_order"]:
            tokens = f.OBSERVER_TOKENS[arm]
            cap = f.summary_cap(tokens)
            row = {
                "project": fixture["project"], "arm": arm,
                "source_sha256": fixture["source_sha256"],
                "status": "RECORDED", "closed_store_ok": True,
                "processes_reaped": True, "no_live_output": True,
                "native_call_count": 4, "observer_tokens": tokens,
                "quote_min_chars": f.QUOTE_MIN_CHARS,
                "expected_summary_max_chars": cap,
                "prior_source_ref": prior, "current_source_ref": current,
                "offers": [], "captures": [], "summary_saturation": {
                    role: False for role in f.ROLES},
                "b2_prior_evidence": False,
            }
            captures = {}
            for phase, ref in (("prior", prior), ("current", current)):
                for role in f.ROLES:
                    event_id = "evt_" + fixture["project"] + "_" + arm + "_" + phase
                    summary = "insufficient evidence"
                    schema = {"properties": {"summary": {"maxLength": cap}}}
                    messages = [{"role": "user", "content": fixture[phase]}]
                    captures[role + ":" + phase] = {
                        "messages": messages,
                        "messages_sha256": f.sha(dumps(messages).encode()),
                        "schema": schema,
                        "schema_sha256": f.sha(dumps(schema).encode()),
                        "observer_tokens": tokens, "summary_max_chars": cap,
                    }
                    entry = {
                        "role": role, "phase": phase, "status": "RECORDED",
                        "guarded_status": "SHADOW_LATEST_USER_OFFER_PRODUCED",
                        "event_id": event_id, "source_ref": ref,
                        "process_reaped": True,
                        "offer": {
                            "event_id": event_id, "role": role,
                            "native_metrics": {"status": "FINAL",
                                               "actual_model": v.MODELS[role]},
                            "offer": {"summary": summary, "quotes": []},
                            "evidence_refs": [],
                        },
                        "query": {"event_id": event_id, "target_role": role,
                                  "source_refs": [ref],
                                  "context_source_refs": [] if phase == "prior" else [prior]},
                        "summary": summary, "summary_length": len(summary),
                        "summary_saturated": False,
                    }
                    if phase == "current":
                        entry["context_source_refs_verified"] = True
                        entry["strict"] = f.strict_summary(
                            summary, fixture["action"], fixture["remaining"])
                        if role == "B2_GIST":
                            entry["prior_evidence_refs_verified"] = False
                    row["offers"].append(entry)
            row["captures"] = captures
            report["rows"].append(row)
    return report


@unittest.skipUnless(v is not None, "full V13 repository required for synthetic verifier tests")
class Run87NativeVerifierSyntheticTests(unittest.TestCase):
    def setUp(self):
        self.report = synthetic_report()

    def reject(self, code):
        with self.assertRaisesRegex(ValueError, code):
            v.verify(self.report)

    def test_01_synthetic_structure_accepted_without_native_claim(self):
        result = v.verify(self.report)
        self.assertEqual(result["status"], "INDEPENDENT_RUN87_NATIVE_REPARSE_PASS")
        self.assertEqual(result["native_calls"], 48)
        self.assertFalse(result["step2_promoted"])
        self.assertFalse(result["prior_context_causal_utility_proven"])

    def test_02_missing_row(self):
        self.report["rows"].pop()
        self.reject("ROW_COUNT_RED")

    def test_03_wrong_arm_order(self):
        self.report["rows"][0], self.report["rows"][1] = self.report["rows"][1], self.report["rows"][0]
        self.reject("ROW_BOUNDARY_RED")

    def test_04_source_ref_forgery(self):
        self.report["rows"][0]["prior_source_ref"]["sha256"] = "0" * 64
        self.reject("SOURCE_REF_RED")

    def test_05_wrong_model(self):
        self.report["rows"][0]["offers"][0]["offer"]["native_metrics"]["actual_model"] = "fake"
        self.reject("NATIVE_OFFER_BINDING_RED")

    def test_06_wrong_budget_tokens(self):
        self.report["rows"][0]["observer_tokens"] = 160
        self.reject("ROW_BOUNDARY_RED")

    def test_07_wrong_native_schema_cap(self):
        self.report["rows"][0]["captures"]["B1_DETAIL:prior"]["summary_max_chars"] = 84
        self.reject("NATIVE_SCHEMA_CAPTURE_RED")

    def test_08_wrong_summary_length(self):
        self.report["rows"][0]["offers"][0]["summary_length"] = 100
        self.reject("SUMMARY_CAP_RED")

    def test_09_current_context_leak(self):
        self.report["rows"][0]["offers"][2]["query"]["context_source_refs"] = []
        self.reject("CONTEXT_TRANSPORT_RED")

    def test_10_prior_context_leak(self):
        self.report["rows"][0]["offers"][0]["query"]["context_source_refs"] = [
            self.report["rows"][0]["prior_source_ref"]]
        self.reject("PRIOR_CONTEXT_LEAK_RED")

    def test_11_strict_score_forgery(self):
        self.report["rows"][0]["offers"][2]["strict"] = 1
        self.reject("STRICT_SCORE_RED")

    def test_12_b2_evidence_forgery(self):
        self.report["rows"][0]["offers"][3]["prior_evidence_refs_verified"] = True
        self.reject("B2_PRIOR_EVIDENCE_RED")

    def test_13_gate_promotion_refused(self):
        self.report["step2"] = "PASS"
        self.reject("AUTHORITY_RED")

    def test_14_score_forgery(self):
        self.report["scores"]["B1_DETAIL"]["LONG_160"] = 1
        self.reject("AGGREGATE_SCORE_RED")

    def test_15_status_forgery(self):
        self.report["status"] = "BUDGET_LONG_SMALL_SIGNAL_SHADOW"
        self.reject("REGISTERED_VERDICT_RED")

    def test_16_missing_capture(self):
        del self.report["rows"][0]["captures"]["B1_DETAIL:prior"]
        self.reject("OFFER_COUNT_RED")

if __name__ == "__main__":
    unittest.main()
