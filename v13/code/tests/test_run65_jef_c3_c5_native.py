"""Run65 independent report verifier corruption tests (synthetic, no native)."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from v13.common import dumps
from scripts.run65_jef_c3_c5_native_verify import verify, sha
from scripts.run63_jef_c3_native import C3_SHA256, RUNNER_SHA256, cohort
from scripts.run47_jef_c3_typed_receiver_native import NEGATIVE
from scripts import p2x_disjoint_receiver_trainset as p2x


class Run65VerifierTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "report.json"
        self.report = self.fake()

    def tearDown(self):
        self.tmp.cleanup()

    def fake(self):
        rows = []
        for fixture in cohort():
            action = fixture["oracle_action"]
            refs = {}
            for name, field in (("current", "current"),
                                ("policy", "b2_source"),
                                ("sheet", "b1_source")):
                refs[name] = {
                    "source_id": "src_" + name + fixture["id"],
                    "sha256": sha(fixture[field].encode("utf-8")),
                    "char_start": 0,
                    "char_end": len(fixture[field]),
                    "modality": "text",
                }
            payload = {
                "current_source": fixture["current"],
                "policy_source": fixture["b2_source"],
                "sheet_source": fixture["b1_source"],
                "typed_jef_action": action,
                "source_ref_sha256": ["2" * 64, "3" * 64],
                "candidate_authority": 0,
            }
            messages = [{"role": "system", "content": "synthetic test"},
                        {"role": "user", "content": json.dumps(payload)}]
            candidate_sha = sha(action.encode("utf-8"))
            staged = {
                "status": "JEF_C5_SOURCE_ONLY_DRAFT_STAGED_SHADOW",
                "source_action": action,
                "candidate_sha256": candidate_sha,
                "candidate_bytes": len(action),
                "model_formatter_status": "FORMATTER_MATCH_SHADOW",
                "draft_origin": "MODEL_EXACT_SHADOW",
                "source_only_fallback": False,
                "source_ref_sha256": payload["source_ref_sha256"],
                "prompt_sha256": "1" * 64,
                "draft_message_id": 1,
                "c5_action_id": "act_" + fixture["id"],
                "c3_receiver_success": False,
                "delivery_authority": 0,
                "output_committed": False,
                "tool_dispatches": 0,
                "learning_authority": 0,
                "native_proof": False,
                "real_tty_approved": False,
            }
            meta = {
                "shadow": True, "origin": "MODEL_EXACT_SHADOW",
                "source_action": action,
                "source_ref_sha256": payload["source_ref_sha256"],
                "prompt_sha256": staged["prompt_sha256"],
                "candidate_sha256": candidate_sha,
                "model_formatter_status": "FORMATTER_MATCH_SHADOW",
            }
            row = {
                "schema": "v13.run65.jef_c3_c5_native_row.v1",
                "id": fixture["id"], "oracle_action": action,
                "source_sha256": {
                    k: sha(fixture[k].encode("utf-8"))
                    for k in ("current", "b1_source", "b2_source")},
                "source_refs": refs,
                "input_messages": messages,
                "input_sha256": sha(dumps(messages).encode("utf-8")),
                "typed_jef_action": action,
                "native_output": action,
                "output_sha256": candidate_sha,
                "native_metrics": {
                    "status": "FINAL",
                    "actual_model": "LFM2.5-350M-QAD-Q4_0.gguf"},
                "native_c3_final": True,
                "native_strict_correct": 1,
                "source_only_fallback": False,
                "native_process_count": 1,
                "processes_reaped": True,
                "process_releases": [{"before": {"rss": 100},
                                      "process_reaped": True}],
                "staged": staged,
                "c6": {
                    "status": "NEEDS_REAL_TTY_APPROVAL",
                    "preflight_only": True,
                    "source_rechecked": True,
                    "c5_binding_verified": True,
                    "candidate_sha256": candidate_sha,
                    "source_only_fallback": False,
                    "delivery_authority": 0,
                    "output_committed": False,
                    "tool_dispatches": 0,
                    "learning_authority": 0,
                    "native_proof": False,
                    "real_tty_approved": False,
                },
                "draft_snapshot": {
                    "id": 1, "role": "assistant", "text": action,
                    "status": "DRAFT", "metadata": dumps(meta),
                    "text_sha256": candidate_sha,
                },
                "status": "RECORDED",
                "draft_count": 1, "no_live_output": True,
                "closed_store_audit": {"ok": True},
                "negative_gates": NEGATIVE,
                "tty_approved": False,
                "output_committed": False,
                "tool_dispatches": 0,
                "learning_authority": 0,
                "candidate_authority": 0,
                "oracle_visible_to_native": False,
            }
            rows.append(row)
        return {
            "schema": "v13.run65.jef_c3_c5_native_report.v1",
            "seed": p2x.SEED, "model_seed": 13,
            "claim": "P2X_CALIBRATION_C3_C5_C6_STRUCTURAL_NOT_DISJOINT_UTILITY",
            "binding": {
                "model_sha256": {"C3_LANGUAGE": C3_SHA256},
                "runner_sha256": RUNNER_SHA256},
            "negative_gates": NEGATIVE,
            "selected_ids": [r["id"] for r in cohort()],
            "rows": rows,
            "row_sha256": {r["id"]: sha(dumps(r).encode("utf-8")) for r in rows},
            "installed_binding_unchanged": True,
            "native_strict_count": 3,
            "source_only_fallback_count": 0,
            "status": "SOURCE_ONLY_DRAFT_STRUCTURAL_PASS",
        }

    def check(self, report=None):
        self.path.write_text(dumps(report if report is not None else self.report))
        return verify(self.path)

    def rehash(self, report):
        report["row_sha256"] = {
            r["id"]: sha(dumps(r).encode("utf-8")) for r in report["rows"]}

    def test_synthetic_structural_contract(self):
        result = self.check()
        self.assertEqual(result["status"], "SOURCE_ONLY_DRAFT_STRUCTURAL_PASS")
        self.assertEqual(result["native_calls"], 3)
        self.assertEqual(result["native_strict_count"], 3)

    def test_wrong_native_output_with_source_only_fallback_is_not_c3_success(self):
        report = copy.deepcopy(self.report)
        row = report["rows"][0]
        row["native_output"] = "Option " + row["oracle_action"]
        row["output_sha256"] = sha(row["native_output"].encode("utf-8"))
        row["native_strict_correct"] = 0
        row["source_only_fallback"] = True
        row["staged"]["model_formatter_status"] = "FORMATTER_MISMATCH_RED"
        row["staged"]["draft_origin"] = "SOURCE_ONLY_FALLBACK_C3_RED"
        row["staged"]["source_only_fallback"] = True
        row["c6"]["source_only_fallback"] = True
        meta = json.loads(row["draft_snapshot"]["metadata"])
        meta["origin"] = "SOURCE_ONLY_FALLBACK_C3_RED"
        meta["model_formatter_status"] = "FORMATTER_MISMATCH_RED"
        row["draft_snapshot"]["metadata"] = dumps(meta)
        report["native_strict_count"] = 2
        report["source_only_fallback_count"] = 1
        self.rehash(report)
        result = self.check(report)
        self.assertEqual(result["status"], "SOURCE_ONLY_DRAFT_STRUCTURAL_PASS")
        self.assertEqual(result["native_strict_count"], 2)
        self.assertEqual(result["source_only_fallback_count"], 1)

    def test_tamper_and_forged_green_refuse(self):
        mutations = {
            "row_hash": lambda r: r["row_sha256"].update(
                {r["rows"][0]["id"]: "0" * 64}),
            "source": lambda r: r["rows"][0]["source_sha256"].update(
                {"current": "0" * 64}),
            "model": lambda r: r["rows"][0]["native_metrics"].update(
                {"actual_model": "fake.gguf"}),
            "draft": lambda r: r["rows"][0]["draft_snapshot"].update(
                {"text": "FORGED"}),
            "c5": lambda r: r["rows"][0]["staged"].update(
                {"c5_action_id": None}),
            "c6": lambda r: r["rows"][0]["c6"].update(
                {"status": "APPROVED"}),
            "no_live": lambda r: r["rows"][0].update(
                {"no_live_output": False}),
            "fallback": lambda r: r["rows"][0]["staged"].update(
                {"source_only_fallback": True}),
            "negative_gates": lambda r: r.update(
                {"negative_gates": {}}),
            "binding": lambda r: r["binding"].update(
                {"runner_sha256": "0" * 64}),
            "status": lambda r: r.update({"status": "AGI_COMPLETE"}),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                report = copy.deepcopy(self.report)
                mutate(report)
                if name != "row_hash":
                    self.rehash(report)
                self.assertEqual(self.check(report)["status"], "STRUCTURAL_RED")


if __name__ == "__main__":
    unittest.main()
