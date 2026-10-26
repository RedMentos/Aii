"""Run397 source-only append-only resume tests with synthetic native-shaped rows, no models."""
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run394_step2_fresh as r394
import run397_step2_resume as resume
from tests.test_run396_step2_pilot_audit import make_synthetic, write


def synthetic_source(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    folder = make_synthetic(folder)
    for arm in resume.r394.ARMS:
        rid = arm + "_s20"
        source_path = folder / f"step2_{rid}.json"
        source = resume.audit.load(source_path)
        spec = resume.catalog()["models"]
        role_models = {"B1_DETAIL": "body", "B2_GIST": "body" if arm == "S" else "gist",
                       "C3_LANGUAGE": "language"}
        source.update(installed_artifacts_unchanged=True, phone_measured=False, canonical_gate_pass=False)
        source["installed_artifacts"] = {
            "model_sha256": {role: spec[key]["files"][0]["sha256"] for role, key in role_models.items()},
            "model_revisions": {role: spec[key]["revision"] for role, key in role_models.items()},
            "runner_sha256": hashlib.sha256(b"synthetic-runner-not-executable").hexdigest(),
            "runner_runtime_libraries_sha256": {}}
        write(source_path, source)
        prereg_path = folder / f"tool_{rid}.preregistration.json"
        prereg = resume.audit.load(prereg_path)
        prereg["source_report"]["sha256"] = resume.audit.sha(source_path)
        write(prereg_path, prereg)
        tool_path = folder / f"tool_{rid}.json"
        tool = resume.audit.load(tool_path)
        tool["preregistration_sha256"] = resume.audit.sha(prereg_path)
        write(tool_path, tool)
    return folder


class FakeModels:
    def __init__(self, *args, **kwargs):
        self.installed = {}
        for k, v in resume.catalog()["models"].items():
            if k not in ("needle", "language", "body", "gist"):
                continue
            files = list(v["files"])
            if k == "needle":
                files += v["platforms"][resume.platform_tag()]
            self.installed[k] = {
                "model_id": v["model_id"], "exact_revision": v["revision"],
                "license_id": v["license_id"],
                "files": {f["local_name"]: {"sha256": f["sha256"], "size": f["size"]}
                          for f in files}}

    def verify(self, deep=False):
        return {k: {"ok": True, "hash_checked": True}
                for k in ("needle", "language", "body", "gist")}


class FakeNative:
    def __init__(self, source):
        self.source = Path(source)
        self.calls = []

    def run(self, installed, attempt, arm, seed):
        rid = f"{arm}_s{seed}"
        self.calls.append(rid)
        for prefix in ("step2_", "tool_", "summary_"):
            src = self.source / f"{prefix}{rid}.json"
            shutil.copyfile(src, Path(attempt) / src.name)
        src = self.source / f"tool_{rid}.preregistration.json"
        shutil.copyfile(src, Path(attempt) / src.name)
        return resume.audit.load(Path(attempt) / f"summary_{rid}.json")


class Run397ResumeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.work = self.root / "work"
        self.native = synthetic_source(self.root / "native")
        self.installed = self.root / "installed"
        (self.installed / "bin").mkdir(parents=True)
        (self.installed / "config").mkdir()
        (self.installed / "bin/llama-server").write_bytes(b"synthetic-runner-not-executable")
        write(self.installed / "config/runner.json", {
            "tag": resume.catalog()["runner"]["tag"],
            "binary_sha256": resume.audit.sha(self.installed / "bin/llama-server")})

    def fake_execute(self, fake, **kwargs):
        with patch.object(resume, "ModelManager", FakeModels), \
             patch.object(r394, "configure", return_value=fake):
            return resume.run(self.work, self.installed, pilot=True, execute=True, **kwargs)

    def test_plan_only_is_not_native_and_does_not_promote(self):
        result = resume.run(self.work, None, pilot=True, execute=False)
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(result["completed"], {})
        self.assertFalse(result["canonical_gate_pass"])
        self.assertEqual(result["step2_exit"], "UTILITY_FAIL")
        self.assertEqual(list(self.work.glob("attempts/**/*")), [])

    def test_real_shaped_synthetic_rows_are_checked_before_receipt(self):
        manifest = resume.checked_manifest(self.work,
            [f for f in r394.FIXTURES if f["id"] in r394.PILOT_IDS],
            list(r394.ARMS), [20], True)
        data = resume.validate_completed(self.native, "O", 20,
            [f for f in r394.FIXTURES if f["id"] in r394.PILOT_IDS], manifest)
        self.assertEqual(data["rows"], 14)
        self.assertFalse(data["canonical_gate_pass"])

    def test_all_three_arms_completed_once_and_reused(self):
        fake = FakeNative(self.native)
        first = self.fake_execute(fake)
        self.assertEqual(first["status"], "ALL_ARMS_STRUCTURALLY_RECORDED")
        self.assertEqual(fake.calls, ["O_s20", "P_s20", "S_s20"])
        self.assertEqual(len(first["completed"]), 3)
        second = self.fake_execute(fake)
        self.assertEqual(second["status"], "ALL_ARMS_STRUCTURALLY_RECORDED")
        self.assertEqual(len(fake.calls), 3)
        self.assertEqual(len(list(self.work.glob("attempts/*/attempt-*/RUN397_ATTEMPT.json"))), 3)

    def test_bounded_three_invocations_resume_without_duplicate_native_calls(self):
        fake = FakeNative(self.native)
        first = self.fake_execute(fake, max_new_arms=1)
        self.assertEqual(first["status"], "INCOMPLETE")
        self.assertEqual(list(first["completed"]), ["O_s20"])
        second = self.fake_execute(fake, max_new_arms=1)
        self.assertEqual(second["status"], "INCOMPLETE")
        self.assertEqual(set(second["completed"]), {"O_s20", "P_s20"})
        third = self.fake_execute(fake, max_new_arms=1)
        self.assertEqual(third["status"], "ALL_ARMS_STRUCTURALLY_RECORDED")
        self.assertEqual(fake.calls, ["O_s20", "P_s20", "S_s20"])
        self.assertEqual(len(list(self.work.glob("attempts/*/attempt-*/RUN397_ATTEMPT.json"))), 3)

    def test_reject_invalid_bounded_attempt_limit(self):
        for value in (0, -1, True, 1.5):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "INVALID_MAX_NEW_ARMS"):
                    resume.run(self.work, None, max_new_arms=value)

    def test_partial_failed_attempt_preserved_and_new_attempt_numbered(self):
        p = self.work / "attempts/O_s20/attempt-0001"
        p.mkdir(parents=True)
        (p / "partial.json").write_text('{"status":"INTERRUPTED"}')
        fake = FakeNative(self.native)
        result = self.fake_execute(fake)
        self.assertEqual(result["status"], "ALL_ARMS_STRUCTURALLY_RECORDED")
        self.assertTrue((p / "partial.json").exists())
        self.assertTrue((self.work / "attempts/O_s20/attempt-0002/RUN397_ATTEMPT.json").exists())
        self.assertIn("O_s20", result["failures_preserved"])

    def test_corrupt_completed_receipt_is_never_reused(self):
        fake = FakeNative(self.native)
        self.fake_execute(fake)
        tool = self.work / "attempts/P_s20/attempt-0001/tool_P_s20.json"
        with tool.open("ab") as f:
            f.write(b" ")
        second = self.fake_execute(fake)
        self.assertEqual(fake.calls.count("P_s20"), 2)
        self.assertEqual(fake.calls.count("O_s20"), 1)
        self.assertEqual(fake.calls.count("S_s20"), 1)
        self.assertTrue((self.work / "attempts/P_s20/attempt-0002/RUN397_ATTEMPT.json").exists())
        self.assertIn("P_s20", second["failures_preserved"])

    def test_reject_forged_recorded_model_hash_even_when_rows_rehashed(self):
        rid = "O_s20"
        source_path = self.native / f"step2_{rid}.json"
        source = resume.audit.load(source_path)
        source["installed_artifacts"]["model_sha256"]["B2_GIST"] = "0" * 64
        write(source_path, source)
        prereg_path = self.native / f"tool_{rid}.preregistration.json"
        prereg = resume.audit.load(prereg_path)
        prereg["source_report"]["sha256"] = resume.audit.sha(source_path)
        write(prereg_path, prereg)
        tool_path = self.native / f"tool_{rid}.json"
        tool = resume.audit.load(tool_path)
        tool["preregistration_sha256"] = resume.audit.sha(prereg_path)
        write(tool_path, tool)
        fixtures = [f for f in r394.FIXTURES if f["id"] in r394.PILOT_IDS]
        manifest = resume.checked_manifest(self.work, fixtures, list(r394.ARMS), [20], True)
        with self.assertRaisesRegex(ValueError, "RECORDED_MODEL_IDENTITY_MISMATCH"):
            resume.validate_completed(self.native, "O", 20, fixtures, manifest)

    def test_reject_deep_valid_but_unregistered_model_swap(self):
        class SwappedModels(FakeModels):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.installed["gist"]["exact_revision"] = "unregistered-swap"
        fake = FakeNative(self.native)
        with patch.object(resume, "ModelManager", SwappedModels), \
             patch.object(r394, "configure", return_value=fake):
            with self.assertRaisesRegex(ValueError, "INSTALLED_CATALOG_IDENTITY_MISMATCH"):
                resume.run(self.work, self.installed, pilot=True, execute=True)
        self.assertEqual(fake.calls, [])

    def test_frozen_manifest_mismatch_fails_closed(self):
        resume.run(self.work, None, pilot=True, execute=False)
        p = self.work / "RUN394_PREREGISTERED_FIXTURES.json"
        j = resume.audit.load(p)
        j["seeds"] = [99]
        write(p, j)
        with self.assertRaisesRegex(ValueError, "FROZEN_MANIFEST_MISMATCH"):
            resume.run(self.work, None, pilot=True, execute=False)

    def test_reject_attempt_root_symlink_before_any_native_work(self):
        self.work.mkdir()
        outside = self.root / "outside-attempts"
        outside.mkdir()
        (self.work / "attempts").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "UNSAFE_ATTEMPT_SYMLINK"):
            resume.run(self.work, None, pilot=True, execute=False)

    def test_reject_owner_lock_symlink_before_open(self):
        self.work.mkdir()
        outside = self.root / "outside-owner"
        outside.write_text("do-not-touch")
        (self.work / "RUN397_OWNER.lock").symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "UNSAFE_WORK_OWNER_LOCK"):
            resume.run(self.work, None, pilot=True, execute=False)
        self.assertEqual(outside.read_text(), "do-not-touch")

    def test_second_owner_cannot_take_same_work(self):
        self.work.mkdir()
        with (self.work / "RUN397_OWNER.lock").open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(RuntimeError, "RUN397_WORK_OWNER_ACTIVE"):
                resume.run(self.work, None, pilot=True, execute=False)


if __name__ == "__main__":
    unittest.main()
