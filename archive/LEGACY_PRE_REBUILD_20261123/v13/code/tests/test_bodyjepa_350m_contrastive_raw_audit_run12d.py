"""Run12D independent original native ZIP auditor: synthetic fixtures only."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts import bodyjepa_350m_contrastive_raw_audit_run12d as a


def synthetic_report():
    d = {
        "schema": a.SCHEMA, "model_id": "LiquidAI/LFM2.5-350M",
        "model_revision": a.REVISION, "master_sha256": a.MASTER_SHA256,
        "fixture_sha256": a.FIXTURE_SHA256, "license_sha256": a.LICENSE_SHA256,
        "body_jepa_source_git_blob": a.PINS["BJEPA_BLOB.txt"],
        "run11p_source_git_blob": a.PINS["ORIGINAL_RUN11P_BLOB.txt"],
        "baseline_method": "post_fit_disable_adapter_frozen_master",
        "evidence_class": "LINUX_FP32_TORCH_SYNTHETIC_HELDOUT",
        "contrastive_trainer_source_git_blob": a.PINS["TRAINER_BLOB.txt"],
        "seeds": [227, 229, 233], "arms": list(a.ARMS),
        "config": {"rank": 2, "alpha": 4., "lr": .0005,
                   "max_steps": 8, "min_steps": 8,
                   "targets": ["w1", "w2", "w3"],
                   "jepa_ema_decay": .9, "jepa_target_eval": True,
                   "contrastive_temperature": .1, "checkpoint_resume": False},
        "completed_arms": 12, "failures": [],
        "runtime_jepa_weight": 0, "age_authority": 0,
        "redmi_measured": False, "step2_utility_pass": False,
        "body_jepa_available": False, "production_activation": False,
        "whole_system_complete": False, "b1_b2_utility_proven": False,
        "results": {},
    }
    fixture = a.expected_fixture()
    for seed in a.SEEDS:
        arms = {}
        for arm in a.ARMS:
            value = {"CE": 1.0, "COS_EMA": .95,
                     "CONTRAST_EMA": .80, "CONTRAST_SHUFFLED": 1.0}[arm]
            rows = {}
            baseline_rows = {}
            for category in a.CATEGORIES:
                val = value if category in ("train", "paraphrase") else (
                    2.0 if category == "near_miss_leak_proxy" else 1.0)
                rows[category] = [{"q": q, "answer": answer, "nll": val}
                                  for q, answer in fixture[category]]
                baseline_rows[category] = [{"q": q, "answer": answer, "nll": 1.0}
                                           for q, answer in fixture[category]]
            arms[arm] = {
                "metrics": {
                    "steps": 8, "jepa_weight": 0. if arm == "CE" else .25,
                    "jepa_target": "shuffled" if arm == "CONTRAST_SHUFFLED" else "ema",
                    "loss_history": [{"step": i, "jepa": None if arm == "CE" else .4}
                                     for i in range(1, 9)],
                },
                "summary": {k: v[0]["nll"] for k, v in rows.items()},
                "baseline": {k: 1.0 for k in a.CATEGORIES},
                "rows": rows, "baseline_rows": baseline_rows,
                "elapsed_s": 1.0, "exported_adapter": False,
            }
        d["results"][seed] = arms
    d.update(a.independent_verdict(d["results"]))
    return d


def make_zip(path, report=None, *, bad_stage=None, corrupt_inner=False,
             extra=None, duplicate=False):
    content = {"HEAD.txt": (a.LAUNCH_HEAD + "\n").encode()}
    content.update({name: (sha + "\n").encode() for name, sha in a.PINS.items()})
    content.update({stage + "_EXIT.txt": ("1" if stage == bad_stage else "0").encode()
                    for stage in a.STAGES})
    if report is not None:
        content["REPORT.json"] = json.dumps(report, sort_keys=True).encode()
    if extra is not None:
        content.update(extra)
    lines = [f"{hashlib.sha256(v).hexdigest()}  ./{k}" for k, v in sorted(content.items())]
    if corrupt_inner:
        lines[0] = "0" * 64 + lines[0][64:]
    content["SHA256SUMS"] = ("\n".join(lines) + "\n").encode()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, raw in content.items():
            z.writestr(name, raw)
        if duplicate:
            z.writestr("HEAD.txt", content["HEAD.txt"])
    return hashlib.sha256(path.read_bytes()).hexdigest()


class OriginalRawIndependentAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "original.zip"

    def tearDown(self):
        self.tmp.cleanup()

    def test_complete_synthetic_zip_is_consistent_but_never_utility_gate(self):
        sha = make_zip(self.path, synthetic_report())
        result = a.audit(self.path, sha)
        self.assertEqual(result["status"], "RAW_REPORT_CONSISTENT_NOT_UTILITY_GATE")
        self.assertTrue(result["native_report_consistent"])
        self.assertFalse(result["utility_gate_pass"])
        self.assertFalse(result["production_activation"])
        self.assertFalse(result["whole_system_complete"])
        self.assertEqual(result["diagnostic"]["seed_wins"], 3)
        self.assertEqual(result["inner_sha256_verified"], len(a.STAGES) + len(a.PINS) + 2)

    def test_missing_native_report_preserves_original_red_without_promoting(self):
        sha = make_zip(self.path, bad_stage="NATIVE")
        result = a.audit(self.path, sha)
        self.assertEqual(result["status"], "ORIGINAL_RED_OR_PARTIAL_PRESERVED")
        self.assertIn("NATIVE", result["bad_stages"])
        self.assertFalse(result["native_report_consistent"])
        self.assertTrue(result["raw_preserved"])

    def test_wrong_original_zip_sha_is_rejected_before_read(self):
        make_zip(self.path, synthetic_report())
        with self.assertRaisesRegex(ValueError, "ORIGINAL_ZIP_SHA256_MISMATCH"):
            a.audit(self.path, "0" * 64)

    def test_inner_hash_mismatch_and_duplicate_entry_are_rejected(self):
        sha = make_zip(self.path, synthetic_report(), corrupt_inner=True)
        with self.assertRaisesRegex(ValueError, "INNER_SHA256_MISMATCH"):
            a.audit(self.path, sha)
        sha = make_zip(self.path, synthetic_report(), duplicate=True)
        with self.assertRaisesRegex(ValueError, "ZIP_DUPLICATE_OR_MEMBER_COUNT"):
            a.audit(self.path, sha)

    def test_path_traversal_and_wrong_launch_head_are_rejected(self):
        sha = make_zip(self.path, synthetic_report(), extra={"../escape": b"bad"})
        with self.assertRaisesRegex(ValueError, "ZIP_PATH_UNSAFE"):
            a.audit(self.path, sha)
        sha = make_zip(self.path, synthetic_report())
        with self.assertRaisesRegex(ValueError, "LAUNCH_HEAD_RED"):
            a.audit(self.path, sha, expected_head="0" * 40)

    def test_fabricated_summary_or_promoted_gate_rejected(self):
        d = synthetic_report()
        d["results"]["227"]["CE"]["summary"]["paraphrase"] += .01
        sha = make_zip(self.path, d)
        with self.assertRaisesRegex(ValueError, "NLL_MEAN_MISMATCH"):
            a.audit(self.path, sha)
        d = synthetic_report()
        d["body_jepa_available"] = True
        sha = make_zip(self.path, d)
        with self.assertRaisesRegex(ValueError, "PROMOTION_OR_MISSING_GATE"):
            a.audit(self.path, sha)

    def test_missing_arm_or_posthoc_verdict_rejected(self):
        d = synthetic_report()
        del d["results"]["229"]["CONTRAST_SHUFFLED"]
        sha = make_zip(self.path, d)
        with self.assertRaisesRegex(ValueError, "INCOMPLETE_ARMS"):
            a.audit(self.path, sha)
        d = synthetic_report()
        d["seed_wins"] = 0
        sha = make_zip(self.path, d)
        with self.assertRaisesRegex(ValueError, "VERDICT_REPLAY_RED"):
            a.audit(self.path, sha)

    def test_exact_fixture_identity_rejects_question_and_answer_rewrites(self):
        d = synthetic_report()
        d["results"]["227"]["CE"]["rows"]["paraphrase"][0]["q"] = "A fabricated paraphrase"
        sha = make_zip(self.path, d)
        with self.assertRaisesRegex(ValueError, "FIXTURE_ROW_IDENTITY_RED"):
            a.audit(self.path, sha)
        d = synthetic_report()
        d["results"]["233"]["CONTRAST_EMA"]["baseline_rows"]["retention"][1]["answer"] = "999"
        sha = make_zip(self.path, d)
        with self.assertRaisesRegex(ValueError, "FIXTURE_ROW_IDENTITY_RED"):
            a.audit(self.path, sha)

    def test_evidence_class_and_baseline_provenance_cannot_be_relabelled(self):
        d = synthetic_report()
        d["baseline_method"] = "independent_pre_fit_measured"
        sha = make_zip(self.path, d)
        with self.assertRaisesRegex(ValueError, "BASELINE_METHOD_RED"):
            a.audit(self.path, sha)
        d = synthetic_report()
        d["evidence_class"] = "REDMI_NATIVE"
        sha = make_zip(self.path, d)
        with self.assertRaisesRegex(ValueError, "EVIDENCE_CLASS_RED"):
            a.audit(self.path, sha)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_JSON_KEY"):
            a.strict_json(b'{"x":1,"x":2}')
        with self.assertRaisesRegex(ValueError, "NONFINITE_JSON"):
            a.strict_json(b'{"x":NaN}')


if __name__ == "__main__":
    unittest.main()
