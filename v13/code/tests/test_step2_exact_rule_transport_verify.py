"""Run127 synthetic-only counterexamples for independent native raw verifier."""
from __future__ import annotations
from copy import deepcopy
import json
import unittest

from scripts import step2_exact_rule_transport_verify as v
from v13.utility import score_decision


def replay(raw, messages):
    return raw, {"synthetic": True}


def sample():
    source = {
        "fixture_sha256": v.FIXTURE_SHA,
        "fixtures": [{"id": p, "oracle": {"project": p, "action": "A", "options": []}}
                     for p in v.PROJECTS],
        "row_sha256": {p + ":" + variant: "source-" + p + "-" + variant
                       for p in v.PROJECTS for variant in v.VARIANTS},
        "installed_artifacts": {"synthetic": True},
    }
    pairs = []
    for p in v.PROJECTS:
        for variant in v.VARIANTS:
            a = [{"role": "system", "content": "synthetic"},
                 {"role": "user", "content": p + variant}]
            b = deepcopy(a)
            injected = variant == "both_exact"
            if injected:
                b[1]["content"] += " prior rule"
            pairs.append({
                "fixture": p, "variant": variant,
                "source_row_sha256": source["row_sha256"][p + ":" + variant],
                "control_messages": a, "treatment_messages": b,
                "control_sha256": v.digest(v.canon(a)),
                "treatment_sha256": v.digest(v.canon(b)),
                "oracle_visible_to_native": False, "native_calls": 0,
                "injected": injected,
            })
    prepared = {"status": "SOFTWARE_PREPARED_NATIVE_NOT_LAUNCHED",
                "original_source_sha256": v.SOURCE_SHA,
                "fixture_sha256": v.FIXTURE_SHA,
                "native_calls": 0, "pair_count": 42,
                "canonical_gate_pass": False, "rows": pairs}
    raw = {"schema": "v13.step2.exact_rule_transport_native_rows.v1",
           "status": v.PASS, "canonical_gate_pass": False,
           "phone_measured": False, "rows": [], "row_sha256": {}}
    for i, pair in enumerate(pairs):
        for mode in (("control", "treatment") if i % 2 == 0 else ("treatment", "control")):
            p = pair["fixture"]
            answer = json.dumps({"project": p, "action": "A", "options": []})
            row = {"fixture": p, "variant": pair["variant"], "mode": mode,
                   "injected": pair["injected"] if mode == "treatment" else False,
                   "source_row_sha256": pair["source_row_sha256"],
                   "consumer_messages_sha256": pair[mode + "_sha256"],
                   "oracle_visible_to_native": False, "status": "RECORDED",
                   "consumer_metrics": {"status": "FINAL"},
                   "raw_answer": answer, "answer": answer, "action": "A",
                   "tool": {"synthetic": True},
                   "score": v.independent_score(answer, source["fixtures"][v.PROJECTS.index(p)]["oracle"]),
                   "elapsed_s": 0.01}
            raw["rows"].append(row)
            raw["row_sha256"][p + ":" + pair["variant"] + ":" + mode] = v.digest(v.canon(row))
    summary = {}
    for mode in ("control", "treatment"):
        summary[mode] = {variant: {
            "rows": 6, "decision_exact": 6, "unknown": 0,
            "wrong_committed": 0, "full_json_exact": 6, "mean_utility": 1.0,
        } for variant in v.VARIANTS}
    receipt = {
        "schema": "v13.step2.exact_rule_transport_matched_native.v1",
        "status": v.PASS, "source_report_sha256": v.SOURCE_SHA,
        "preflight_report_sha256": "synthetic-pairs",
        "fixture_sha256": v.FIXTURE_SHA, "native_rows_sha256": v.digest(v.canon(raw)),
        "rows": 84, "body_source_seed": 20, "c3_seed": 13,
        "native_scope": "LINUX_C3_42_MATCHED_PAIRS_84_CALLS",
        "model_hashes_before": v.MODELS, "model_hashes_after": v.MODELS,
        "installed_artifacts_before": source["installed_artifacts"],
        "installed_artifacts_after": source["installed_artifacts"],
        "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
        "age_authority": 0, "jepa_weight": 0, "weight_updates": False,
        "redmi_measured": False, "whole_system_complete": False,
        "treatment_wrong_committed": 0, "summary": summary,
    }
    return source, prepared, raw, receipt


def check(parts, reseal=True):
    source, prepared, raw, receipt = parts
    if reseal:
        receipt["native_rows_sha256"] = v.digest(v.canon(raw))
    return v.audit(source, prepared, raw, receipt,
                   source_sha=v.SOURCE_SHA, prepared_sha="synthetic-pairs",
                   raw_sha=v.digest(v.canon(raw)), replay=replay)


def rehash(parts, row):
    key = row["fixture"] + ":" + row["variant"] + ":" + row["mode"]
    parts[2]["row_sha256"][key] = v.digest(v.canon(row))


class Run127IndependentAudit(unittest.TestCase):
    def test_complete_synthetic_84_passes_without_promoting(self):
        result = check(sample())
        self.assertEqual((result["rows"], result["pairs"]), (84, 42))
        self.assertFalse(result["canonical_gate_pass"])
        self.assertEqual(result["step2_status"], "UTILITY_FAIL")
        self.assertEqual(len(result["per_fixture"]), 42)

    def test_truncation_refused(self):
        parts = sample()
        parts[2]["rows"].pop()
        with self.assertRaisesRegex(ValueError, "RAW_INCOMPLETE"):
            check(parts)

    def test_swapped_order_refused(self):
        parts = sample()
        rows = parts[2]["rows"]
        rows[0], rows[1] = rows[1], rows[0]
        with self.assertRaisesRegex(ValueError, "ROW_BINDING"):
            check(parts)

    def test_score_forgery_refused_even_if_hashes_resealed(self):
        parts = sample()
        row = parts[2]["rows"][0]
        row["score"]["utility"] = 0.75
        rehash(parts, row)
        with self.assertRaisesRegex(ValueError, "SCORE_REPLAY"):
            check(parts)

    def test_action_forgery_refused_even_if_hashes_resealed(self):
        parts = sample()
        row = parts[2]["rows"][0]
        row["action"] = "B"
        rehash(parts, row)
        with self.assertRaisesRegex(ValueError, "ACTION_REPLAY"):
            check(parts)

    def test_answer_forgery_refused_even_if_hashes_resealed(self):
        parts = sample()
        row = parts[2]["rows"][0]
        row["answer"] = "forged"
        rehash(parts, row)
        with self.assertRaisesRegex(ValueError, "TOOL_REPLAY"):
            check(parts)

    def test_nonfinal_refused(self):
        parts = sample()
        row = parts[2]["rows"][0]
        row["consumer_metrics"]["status"] = "TIMEOUT"
        rehash(parts, row)
        with self.assertRaisesRegex(ValueError, "NATIVE_NOT_FINAL"):
            check(parts)

    def test_gate_promotion_refused(self):
        parts = sample()
        parts[3]["canonical_gate_pass"] = True
        with self.assertRaisesRegex(ValueError, "RECEIPT_DRIFT"):
            check(parts)

    def test_receipt_raw_sha_mismatch_refused(self):
        parts = sample()
        parts[3]["native_rows_sha256"] = "forged"
        with self.assertRaisesRegex(ValueError, "RECEIPT_DRIFT"):
            check(parts, reseal=False)

    def test_model_hash_drift_refused(self):
        parts = sample()
        parts[3]["model_hashes_after"] = {"C3_LANGUAGE": "forged"}
        with self.assertRaisesRegex(ValueError, "RECEIPT_DRIFT"):
            check(parts)

    def test_wrong_committed_cannot_be_reported_green(self):
        parts = sample()
        row = next(r for r in parts[2]["rows"] if r["mode"] == "treatment")
        row["raw_answer"] = json.dumps({"project": row["fixture"], "action": "B", "options": []})
        row["answer"] = row["raw_answer"]
        row["action"] = "B"
        row["score"] = v.independent_score(row["answer"],
                      parts[0]["fixtures"][v.PROJECTS.index(row["fixture"])]["oracle"])
        rehash(parts, row)
        with self.assertRaisesRegex(ValueError, "SUMMARY_OR_STATUS"):
            check(parts)

    def test_duplicate_json_action_refused_by_scorer(self):
        oracle = {"project": "Atlas", "action": "A", "options": []}
        answer = '{"project":"Atlas","action":"A","action":"B","options":[]}'
        self.assertEqual(v.independent_score(answer, oracle), score_decision(answer, oracle))
        self.assertFalse(v.independent_score(answer, oracle)["exact"])

    def test_score_matches_frozen_scorer_for_typed_fields(self):
        oracle = {"project": "Atlas", "action": "A", "options": [
            {"entity": "X", "cost": 3, "remaining": 2, "days": 1,
             "local": True, "eligible": False}]}
        good = json.dumps(oracle)
        bad = json.dumps({"project": "Atlas", "action": "A", "options": [
            {"entity": "X", "cost": 3, "remaining": 2, "days": 1,
             "local": 1, "eligible": False}]})
        for answer in (good, bad, "bad json", "[]"):
            self.assertEqual(v.independent_score(answer, oracle),
                             score_decision(answer, oracle))


if __name__ == "__main__":
    unittest.main()
