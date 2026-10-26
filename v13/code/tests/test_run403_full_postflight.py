"""Run403 independent 378-row postflight controls; reports are entirely synthetic."""
import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run394_step2_fresh as r394
import run397_step2_resume as resume
import run403_full_postflight as audit
from tests.test_run397_step2_resume import synthetic_source, write
from tests.test_run402_stage_restore import make_archive


def make_full(folder):
    folder = Path(folder)
    root = make_archive(folder / "stage1")
    work = root / "run401-full"
    with patch.object(r394, "PILOT_IDS", tuple(f["id"] for f in r394.FIXTURES)):
        native = synthetic_source(folder / "native")
    runner_sha = resume.catalog()["runner"]["linux_binaries"]["linux-x86_64"]["sha256"]
    manifest = r394.manifest(r394.FIXTURES, False, list(r394.ARMS), list(r394.SEEDS))
    completed = {}
    for seed in r394.SEEDS:
        for arm in r394.ARMS:
            rid = f"{arm}_s{seed}"
            attempt = work / "attempts" / rid / "attempt-0001"
            attempt.mkdir(parents=True, exist_ok=True)
            original = work / "attempts" / "O_s20" / "attempt-0001"
            if arm == "O" and seed == 20:
                pass
            else:
                source_root = original if arm == "O" else native
                source_rid = f"{arm}_s20"
                for prefix in ("step2_", "tool_", "summary_"):
                    src = source_root / f"{prefix}{source_rid}.json"
                    shutil.copyfile(src, attempt / f"{prefix}{rid}.json")
                shutil.copyfile(source_root / f"tool_{source_rid}.preregistration.json",
                                attempt / f"tool_{rid}.preregistration.json")
                source_path = attempt / f"step2_{rid}.json"
                source = resume.audit.load(source_path)
                source["installed_artifacts"]["runner_sha256"] = runner_sha
                write(source_path, source)
                prereg_path = attempt / f"tool_{rid}.preregistration.json"
                prereg = resume.audit.load(prereg_path)
                prereg["source_report"]["sha256"] = resume.audit.sha(source_path)
                write(prereg_path, prereg)
                tool_path = attempt / f"tool_{rid}.json"
                tool = resume.audit.load(tool_path)
                tool["preregistration_sha256"] = resume.audit.sha(prereg_path)
                write(tool_path, tool)
                summary_path = attempt / f"summary_{rid}.json"
                summary = resume.audit.load(summary_path)
                summary["run"], summary["seed"], summary["arm"] = rid, seed, arm
                write(summary_path, summary)
            verified = resume.validate_completed(attempt, arm, seed, r394.FIXTURES,
                                                  manifest, current_runner_sha=runner_sha)
            write(attempt / "RUN397_ATTEMPT.json", {
                "schema": resume.SCHEMA, "status": "COMPLETE", "arm": arm,
                "seed": seed, "validated": verified, "owner": resume.OWNER})
            completed[rid] = {"attempt": f"attempts/{rid}/attempt-0001", "validated": verified}
    write(work / "RUN397_PROGRESS.json", {
        "schema": resume.SCHEMA, "status": "ALL_ARMS_STRUCTURALLY_RECORDED",
        "manifest_sha256": resume.audit.sha(work / "RUN394_PREREGISTERED_FIXTURES.json"),
        "completed": completed, "failures_preserved": {},
        "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
        "native_success_does_not_promote_step2": True})
    return work


class Run403FullPostflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = make_full(Path(self.tmp.name))

    def test_full_378_synthetic_rows_and_paired_means_nonpromoting(self):
        r = audit.audit(self.work)
        self.assertEqual(r["status"], "FULL_POSTFLIGHT_VERIFIED_NO_GATE_PROMOTION", r.get("errors"))
        self.assertEqual(r["rows_verified"], 378)
        self.assertEqual(r["completed_attempts"], 9)
        self.assertEqual(r["paired_differences"]["pointer_minus_off"]["both_exact"]["paired_count"], 18)
        self.assertAlmostEqual(r["paired_differences"]["pointer_minus_off"]["both_exact"]["mean"], .5)
        self.assertAlmostEqual(r["paired_differences"]["pointer_minus_shared_body"]["both_exact"]["mean"], .25)
        self.assertEqual(set(r["paired_differences"]["pointer_minus_off"]["both_exact"]["by_seed"]),
                         {"20", "21", "22"})
        self.assertFalse(r["canonical_gate_pass"])
        self.assertEqual(r["step2_exit"], "UTILITY_FAIL")
        self.assertEqual(r["evidence_level"],
                         "REPORT_STRUCTURE_ONLY_ORIGIN_REQUIRES_EXTERNAL_NATIVE_ARTIFACT")

    def test_missing_arm_fails_closed(self):
        p = self.work / "RUN397_PROGRESS.json"
        j = json.loads(p.read_text())
        j["completed"].pop("P_s22")
        write(p, j)
        self.assertEqual(audit.audit(self.work)["status"], "FULL_INCOMPLETE_OR_RED")

    def test_partial_status_never_silently_averages(self):
        p = self.work / "RUN397_PROGRESS.json"
        j = json.loads(p.read_text())
        j["status"] = "INCOMPLETE"
        write(p, j)
        self.assertEqual(audit.audit(self.work)["status"], "FULL_INCOMPLETE_OR_RED")

    def test_forged_model_hash_even_with_valid_receipt_fails(self):
        source_path = self.work / "attempts/P_s21/attempt-0001/step2_P_s21.json"
        j = json.loads(source_path.read_text())
        j["installed_artifacts"]["model_sha256"]["B2_GIST"] = "0" * 64
        write(source_path, j)
        self.assertEqual(audit.audit(self.work)["status"], "FULL_INCOMPLETE_OR_RED")

    def test_wrong_native_tool_row_fails_closed(self):
        tool_path = self.work / "attempts/S_s22/attempt-0001/tool_S_s22.json"
        j = json.loads(tool_path.read_text())
        j["rows"][0]["score"]["utility"] = 0.123
        write(tool_path, j)
        self.assertEqual(audit.audit(self.work)["status"], "FULL_INCOMPLETE_OR_RED")

    def test_wrong_seed_summary_fails_closed(self):
        p = self.work / "attempts/O_s21/attempt-0001/summary_O_s21.json"
        j = json.loads(p.read_text())
        j["seed"] = 20
        write(p, j)
        self.assertEqual(audit.audit(self.work)["status"], "FULL_INCOMPLETE_OR_RED")

    def test_forged_gate_flag_fails_closed(self):
        p = self.work / "RUN397_PROGRESS.json"
        j = json.loads(p.read_text())
        j["canonical_gate_pass"] = True
        write(p, j)
        self.assertEqual(audit.audit(self.work)["status"], "FULL_INCOMPLETE_OR_RED")

    def test_attempt_path_escape_rejected(self):
        p = self.work / "RUN397_PROGRESS.json"
        j = json.loads(p.read_text())
        j["completed"]["O_s20"]["attempt"] = "../outside"
        write(p, j)
        self.assertEqual(audit.audit(self.work)["status"], "FULL_INCOMPLETE_OR_RED")


if __name__ == "__main__":
    unittest.main()
