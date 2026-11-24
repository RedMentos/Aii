"""Run26 synthetic closed-artifact tests. No native/model evidence is claimed."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts import run26_ag12_native_crossorgan as pilot
from v13.agi.generality import build_suite


def _negative():
    return {
        "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
        "b3_promoted": False, "step2_promoted": False,
        "body_jepa_promoted": False, "redmi_measured": False,
        "learned_german_transfer_proven": False,
        "whole_system_complete": False,
    }


def _runs(name):
    role = pilot.MODELS[name][0]
    return {lang: {"status": "DONE", "roles": [role],
                   "stats": {role: {"items": 88, "errors": 0}}}
            for lang in ("de", "en")}


def _report(kind):
    if kind == "c3":
        return _negative() | {
            "evidence_kind": "LINUX_NATIVE_C3_AG12_ONLY",
            "seed": 13, "native_role": "C3_LANGUAGE",
            "model_sha256": pilot.MODELS["c3"][1],
            "runner_tar_sha256": pilot.RUNNER_SHA,
            "actual_llama_server_sha256": pilot.RUNNER_BINARY_SHA,
            "native_calls_observed": 176, "runtime_closed": True,
            "no_holdout_prompts_in_events": True,
            "no_holdout_prompts_in_messages": True,
            "runs": _runs("c3"),
        }
    return _negative() | {
        "evidence_kind": "LINUX_NATIVE_B1_B2_AG12_ONLY",
        "seed": 13, "status": "DONE", "native_calls": 352,
        "models": {
            name: {
                "status": "DONE", "role": pilot.MODELS[name][0],
                "model_sha256": pilot.MODELS[name][1],
                "runner_tar_sha256": pilot.RUNNER_SHA,
                "runner_binary_sha256": pilot.RUNNER_BINARY_SHA,
                "native_calls": 176, "closed": True,
                "process_reaped": True, "no_events": True,
                "no_messages": True, "runs": _runs(name),
            } for name in ("b1", "b2")
        },
    }


def _rowset(name, lang):
    suite = build_suite(seed=13, lang=lang)
    step = {"c3": 4, "b1": 3, "b2": 5}[name]
    return {
        "status": "DONE", "items": 88, "suite_hash": suite["hash"],
        "results": [{"id": i["id"], "correct": int(j % step == 0),
                     "confidence": 0.5} for j, i in enumerate(suite["items"])],
    }


def _artifact(path, kind, mutate=None):
    files = {
        "HEAD.txt": (pilot.C3_HEAD if kind == "c3" else pilot.BODIES_HEAD) + "\n",
        "native/REPORT.json": json.dumps(_report(kind)),
    }
    for stage in pilot.STAGES:
        files[stage + "_EXIT.txt"] = "0\n"
    for name in (("c3",) if kind == "c3" else ("b1", "b2")):
        for lang in ("de", "en"):
            loc = "native/" + ("" if name == "c3" else name + "/")
            files[loc + "AG12_" + lang.upper() + "_ROWS.json"] = json.dumps(_rowset(name, lang))
    if mutate:
        mutate(files)
    files["SHA256SUMS"] = "".join(
        hashlib.sha256(data.encode()).hexdigest() + "  ./" + name + "\n"
        for name, data in sorted(files.items()))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ClosedNativeCrossOrganRun26(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.c3 = self.home / "c3.zip"
        self.bodies = self.home / "bodies.zip"
        self.c3_sha = _artifact(self.c3, "c3")
        self.bodies_sha = _artifact(self.bodies, "bodies")

    def tearDown(self):
        self.tmp.cleanup()

    def analyze(self, **kw):
        return pilot.analyze(
            kw.get("c3", self.c3), kw.get("bodies", self.bodies),
            kw.get("c3_sha", self.c3_sha), kw.get("bodies_sha", self.bodies_sha))

    def test_full_synthetic_rows_aggregate_only_no_fusion_claim(self):
        result = self.analyze()
        self.assertEqual(result["status"], "DIAGNOSTIC_ONLY")
        for lang in ("de", "en"):
            m = result["languages"][lang]
            self.assertEqual(m["items"], 88)
            self.assertEqual(m["correct_counts"]["c3"], 22)
            self.assertEqual(m["correct_counts"]["b1"], 30)
            self.assertEqual(m["correct_counts"]["b2"], 18)
            self.assertGreaterEqual(m["correct_counts"]["b1_or_b2_oracle"], 30)
            self.assertGreaterEqual(m["correct_counts"]["all_three_oracle"],
                                    m["correct_counts"]["b1_or_b2_oracle"])
            self.assertEqual(sum(x["items"] for x in m["by_family"].values()), 88)
        self.assertFalse(result["actual_fusion_proven"])
        self.assertFalse(result["learned_german_transfer_proven"])
        self.assertFalse(result["whole_system_complete"])
        self.assertNotIn("prompt", json.dumps(result))
        self.assertNotIn("answer", json.dumps(result))

    def test_original_sha_mismatch_fails_before_rows(self):
        with self.assertRaisesRegex(pilot.EvidenceError, "ORIGINAL_ZIP_SHA"):
            self.analyze(c3_sha="0" * 64)

    def test_failed_stage_is_red_even_with_valid_manifest_and_zip(self):
        def mutate(files):
            files["NATIVE_EXIT.txt"] = "1\n"
        sha = _artifact(self.bodies, "bodies", mutate)
        with self.assertRaisesRegex(pilot.EvidenceError, "STAGE_NATIVE"):
            self.analyze(bodies_sha=sha)

    def test_holdout_prompt_export_vetoed_even_when_zip_is_rehashed(self):
        def mutate(files):
            key = "native/b1/AG12_DE_ROWS.json"
            rows = json.loads(files[key])
            rows["results"][0]["prompt"] = "do not export prompts"
            files[key] = json.dumps(rows)
        sha = _artifact(self.bodies, "bodies", mutate)
        with self.assertRaisesRegex(pilot.EvidenceError, "ROW_INTEGRITY"):
            self.analyze(bodies_sha=sha)

    def test_wrong_suite_identity_vetoed(self):
        def mutate(files):
            key = "native/b2/AG12_EN_ROWS.json"
            rows = json.loads(files[key])
            rows["suite_hash"] = "0" * 64
            files[key] = json.dumps(rows)
        sha = _artifact(self.bodies, "bodies", mutate)
        with self.assertRaisesRegex(pilot.EvidenceError, "ROW_SUITE"):
            self.analyze(bodies_sha=sha)

    def test_negative_gate_tamper_vetoed(self):
        def mutate(files):
            report = json.loads(files["native/REPORT.json"])
            report["jepa_weight"] = 1
            files["native/REPORT.json"] = json.dumps(report)
        sha = _artifact(self.bodies, "bodies", mutate)
        with self.assertRaisesRegex(pilot.EvidenceError, "NEGATIVE_GATES"):
            self.analyze(bodies_sha=sha)

    def test_failed_cli_writes_red_without_metrics(self):
        out = self.home / "closed-red.json"
        with self.assertRaisesRegex(RuntimeError, "INVALID_NATIVE_EVIDENCE"):
            pilot.main(["--c3-zip", str(self.c3), "--bodies-zip", str(self.bodies),
                        "--c3-sha", "0" * 64, "--bodies-sha", self.bodies_sha,
                        "--out", str(out)])
        result = json.loads(out.read_text())
        self.assertEqual(result["status"], "RED")
        self.assertIsNone(result["coverage"])
        self.assertNotIn("languages", result)
        self.assertEqual(result["jepa_weight"], 0)


if __name__ == "__main__":
    unittest.main()
