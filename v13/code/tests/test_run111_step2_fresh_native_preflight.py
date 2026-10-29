"""Run111 reversible fresh STEP2 preflight: model-free guards and negative gates."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run109_step2_fresh_fixtures as corpus
from scripts import run111_step2_fresh_native_preflight as pre


class Run111PreflightTests(unittest.TestCase):
    def test_frozen_source_catalog_and_378_rows_without_native(self):
        report = pre.dry_run()
        reg = report["registration"]
        self.assertEqual(report["status"], "PREPARED_NOT_NATIVE_REGISTERED")
        self.assertFalse(report["native_execution"])
        self.assertFalse(report["models_loaded"])
        self.assertEqual(report["native_calls"], 0)
        self.assertFalse(report["canonical_gate_pass"])
        self.assertEqual(report["step2_status"], "UTILITY_FAIL")
        self.assertFalse(report["whole_system_complete"])
        self.assertEqual(reg["registered_native_rows"], 378)
        self.assertEqual(reg["projects"], list(pre.EXPECTED_PROJECTS))
        self.assertEqual(reg["seeds"], [20, 21, 22])
        self.assertEqual(set(reg["arms"]), {"CQP", "DQP", "CQ"})
        self.assertEqual(reg["fixture_sha256"], corpus.inspect()["fixture_sha256"])
        self.assertEqual(reg["fixture_sha256"], pre.FIXTURE_SHA256)
        self.assertEqual(reg["source_git_blobs"], pre.FROZEN_BLOBS)
        self.assertEqual(reg["catalog_git_blob"], pre.CATALOG_BLOB)

    def test_arm_settings_and_invalid_arm_seed_refused(self):
        cqp = pre.settings("CQP", 20)
        dqp = pre.settings("DQP", 20)
        cq = pre.settings("CQ", 20)
        self.assertEqual(cqp["b2_quote_select"], "pointer")
        self.assertEqual(dqp["b2_quote_select"], "pointer")
        self.assertEqual(cq["b2_quote_select"], "off")
        self.assertEqual(cqp["b2_control"], "two_body")
        self.assertEqual(dqp["b2_control"], "shared_body_dual_state")
        self.assertEqual(cqp["seed"], 20)
        for arm, seed in (("BAD", 20), ("CQP", 19), ("CQP", 23),
                          ("CQP", True), ("CQP", 20.0)):
            with self.subTest(arm=arm, seed=seed), self.assertRaises(ValueError):
                pre.settings(arm, seed)

    def test_alias_and_global_restore_after_normal_and_exception(self):
        original = (pre.z2.FIXTURES, pre.z2b.ARMS, pre.z2b.SEEDS,
                    pre.z2b.settings)
        original_sha = pre._canonical_sha(pre.z2.FIXTURES)
        self.assertIs(pre.z2, pre.z2b.z2)
        with pre.configured():
            self.assertEqual(len(pre.z2.FIXTURES), 6)
            self.assertEqual(pre.z2b.SEEDS, pre.SEEDS)
            self.assertEqual(set(pre.z2b.ARMS), set(pre.ARMS))
            self.assertIs(pre.z2b.settings, pre.settings)
            with self.assertRaisesRegex(RuntimeError, "ALREADY_ACTIVE"):
                with pre.configured():
                    pass
        for before, after in zip(original, (pre.z2.FIXTURES, pre.z2b.ARMS,
                                            pre.z2b.SEEDS, pre.z2b.settings)):
            self.assertIs(before, after)
        with self.assertRaisesRegex(ValueError, "synthetic"):
            with pre.configured():
                raise ValueError("synthetic")
        self.assertFalse(pre._active)
        self.assertEqual(pre._canonical_sha(pre.z2.FIXTURES), original_sha)
        self.assertIs(pre.z2.FIXTURES, original[0])

    def test_no_mutation_of_frozen_z2_or_fresh_oracles(self):
        before = corpus.inspect()
        frozen = pre._canonical_sha(pre.z2.FIXTURES)
        with pre.configured():
            self.assertEqual(pre._canonical_sha(pre.z2.FIXTURES),
                             before["fixture_sha256"])
            pre.z2.FIXTURES[0]["rules"]["budget"] = -1
        self.assertEqual(pre._canonical_sha(pre.z2.FIXTURES), frozen)
        self.assertEqual(corpus.inspect()["fixture_sha256"], before["fixture_sha256"])
        self.assertTrue(all(corpus.inspect()["checks"].values()))

    def test_source_drift_fail_closed(self):
        with patch.dict(pre.FROZEN_BLOBS, {"scripts/step2_z2_timescale.py":
                                           "0" * 40}):
            with self.assertRaisesRegex(ValueError, "FROZEN_SOURCE_DRIFT"):
                pre.verify_frozen()
        with patch.dict(pre.MODEL_SHA256, {"body": "0" * 64}):
            with self.assertRaisesRegex(ValueError, "MODEL_PIN_DRIFT"):
                pre.verify_frozen()

    def test_cli_requires_fresh_path_and_never_executes_native(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run111.json"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(pre.main(["--dry-run", "--out", str(out)]), 0)
            report = json.loads(out.read_text())
            self.assertEqual(report["native_calls"], 0)
            self.assertEqual(report["registration_sha256"],
                             pre.dry_run()["registration_sha256"])
            with self.assertRaises(FileExistsError):
                with contextlib.redirect_stdout(io.StringIO()):
                    pre.main(["--out", str(out)])
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                pre.main(["--execute-native"])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
