"""Synthetic twelve-way sealed native format tests; no real model execution."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts import step2_staged12_assemble as assembler
from scripts import step2_longnote_staged12_native as stage
from scripts import step2_longnote_fourarm_io as io
from scripts import step2_z2_timescale as z2
from scripts.step2_fourarm_native_collector_candidate import canonical, sha
from tests.test_step2_longnote_staged12_native import Staged12Guards
from v13.common import digest, dumps


class Staged12AssemblerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.runs = self.root / "runs"
        self.out = self.root / "assembled"
        self.runs.mkdir()
        self.helper = Staged12Guards()

    def populate(self):
        source_pin = stage.source_hashes()
        fixtures = list(stage.pre.corpus.FIXTURES)
        self.assertEqual(sha(canonical(fixtures)), stage.FIXTURE_SHA256)
        for arm in stage.ARMS:
            for seed in stage.SEEDS:
                source, tool, _, summary, base = self.helper.fake(arm, seed)
                expected = copy.deepcopy(base)
                expected["model_sha256"] = stage.expected_models(
                    arm, base["model_sha256"])
                if arm.startswith("S"):
                    expected["model_revisions"]["B2_GIST"] = (
                        expected["model_revisions"]["B1_DETAIL"])
                source["fixtures"] = fixtures
                source["preparations"] = [
                    {"fixture": fid, "status": "RECORDED",
                     "model_sha256": expected["model_sha256"],
                     "runner_sha256": stage.RUNNER_SHA256}
                    for fid in stage.FIXTURE_IDS]
                for row in tool["rows"]:
                    row["score"] = {"utility": 0.5, "field_checks": {
                        "action": True, "A.remaining": True, "A.eligible": True,
                        "B.remaining": True, "B.eligible": True,
                        "A.cost": True, "A.days": True, "A.local": True,
                        "B.cost": True, "B.days": True, "B.local": True}}
                    tool["row_sha256"][row["fixture"] + ":" + row["variant"]] = (
                        digest(dumps(row)))
                summary["error_profile_tool"] = z2.error_profile(
                    tool["rows"], {f["id"]: f for f in fixtures})
                raw, sealed = stage.sealed_summary(
                    summary, dumps(source).encode(), dumps(tool).encode(),
                    arm, seed, expected["model_sha256"], source_pin)
                rid = f"{arm}_s{seed}"
                folder = self.runs / rid
                folder.mkdir()
                (folder / "RAW_PAIR.bin").write_bytes(raw)
                (folder / "SEALED_SUMMARY.json").write_bytes(canonical(sealed))
                receipt = {
                    "schema": "v13.step2.staged12.single_arm.v1",
                    "status": "PASS_SCOPED_ONE_OF_TWELVE_NO_CANON_GATE",
                    "arm": arm, "seed": seed,
                    "fixture_ids": list(stage.FIXTURE_IDS),
                    "registration_sha256": stage.REGISTRATION_SHA256,
                    "source_sha256": source_pin,
                    "source_model_runner_unchanged": True,
                    "native_rows": 70, "tool_rows": 70,
                    "native_c3_final": 70, "tool_c3_final": 70,
                    "all_native_processes_reaped": True,
                    "model_hashes_before": base["model_sha256"],
                    "model_hashes_after": base["model_sha256"],
                    "installed_artifacts_before": base,
                    "age_authority": 0, "jepa_weight": 0,
                    "weight_updates": False, "redmi_measured": False,
                    "canonical_gate_pass": False, "whole_system_complete": False,
                    "raw_pair_sha256": sha(raw),
                    "sealed_summary_sha256": sha(canonical(sealed)),
                }
                (folder / "RECEIPT.json").write_bytes(canonical(receipt))

    def test_all_twelve_synthetic_pairs_roundtrip_original_scorer(self):
        self.populate()
        result = assembler.assemble(self.runs, self.out)
        self.assertEqual(result["runs"], 12)
        self.assertFalse(result["canonical_gate_pass"])
        self.assertFalse(result["analysis"]["candidate_supported"])
        self.assertEqual(result["status"],
                         "VERIFIED_CLOSED_TWELVE_RUN_DIAGNOSTIC_ONLY")
        self.assertEqual(sha((self.out / "manifest.json").read_bytes()),
                         result["manifest_sha256"])
        replay = io.load(self.out, "manifest.json",
                         result["manifest_sha256"],
                         stage.FIXTURE_IDS, stage.FIXTURE_SHA256)
        self.assertFalse(replay["canonical_gate_pass"])
        self.assertEqual(len(list(self.out.glob("*.raw"))), 12)
        self.assertEqual(len(list(self.out.glob("*.json"))), 14)

    def test_missing_arm_fails_without_output(self):
        self.populate()
        shutil.rmtree(self.runs / "SP_s29")
        with self.assertRaises(ValueError):
            assembler.assemble(self.runs, self.out)
        self.assertFalse(self.out.exists())

    def test_raw_tamper_fails_before_manifest(self):
        self.populate()
        p = self.runs / "TP_s27" / "RAW_PAIR.bin"
        p.write_bytes(p.read_bytes() + b"x")
        with self.assertRaises(ValueError):
            assembler.assemble(self.runs, self.out)
        self.assertFalse(self.out.exists())

    def test_symlinked_arm_directory_is_refused(self):
        self.populate()
        p = self.runs / "TP_s27"
        dest = self.root / "moved"
        p.rename(dest)
        p.symlink_to(dest, target_is_directory=True)
        with self.assertRaises((ValueError, OSError)):
            assembler.assemble(self.runs, self.out)
        self.assertFalse(self.out.exists())

    def test_existing_output_is_never_overwritten(self):
        self.populate()
        self.out.mkdir()
        (self.out / "keep.txt").write_text("untouched")
        with self.assertRaises(ValueError):
            assembler.assemble(self.runs, self.out)
        self.assertEqual((self.out / "keep.txt").read_text(), "untouched")

    def test_promoted_receipt_fails(self):
        self.populate()
        p = self.runs / "TC_s27" / "RECEIPT.json"
        receipt = json.loads(p.read_bytes())
        receipt["canonical_gate_pass"] = True
        p.write_bytes(canonical(receipt))
        with self.assertRaises(ValueError):
            assembler.assemble(self.runs, self.out)
        self.assertFalse(self.out.exists())

    def test_source_pin_mismatch_fails(self):
        self.populate()
        p = self.runs / "SC_s28" / "SEALED_SUMMARY.json"
        summary = json.loads(p.read_bytes())
        summary["source_sha256"]["v13/runtime.py"] = "0" * 64
        p.write_bytes(canonical(summary))
        with self.assertRaises(ValueError):
            assembler.assemble(self.runs, self.out)
        self.assertFalse(self.out.exists())

    def test_duplicate_json_keys_fail(self):
        self.populate()
        p = self.runs / "TC_s27" / "RECEIPT.json"
        p.write_bytes(b'{"status":"RUNNING","status":"PASS_SCOPED_ONE_OF_TWELVE_NO_CANON_GATE"}')
        with self.assertRaises(ValueError):
            assembler.assemble(self.runs, self.out)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
