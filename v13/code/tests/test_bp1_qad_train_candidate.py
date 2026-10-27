"""BP1 QAD train-only candidate software tests; no model weights or heldout files."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import bp1_qad_train_candidate as T


def manifest():
    return {
        "schema": T.MANIFEST_SCHEMA,
        "scope": "LINUX_NATIVE_B2_INPUT_SOFTWARE_DATASET_ONLY",
        "source_report_sha256": "ea379b52c7b95c2bb30cd6725f539f443521a64210fdf6bf6fa726c413126880",
        "source_corpus_sha256": "1872a3adf6e51e05e604053539d50ae05c955b221f78f1951d1f68e2a12f926c",
        "b2_model_sha256": "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf",
        "train_projects": list(T.TRAIN_PROJECTS),
        "heldout_projects": list(T.HELDOUT_PROJECTS),
        "train_rows": 25, "heldout_rows": 22, "heldout_pairs": 11,
        "dropped_invalid_b2_quotes": 10,
        "files_sha256": {
            "train_offer.jsonl": T.TRAIN_SHA,
            "heldout_paired.jsonl": "7238a0220255cbccbcf1f9ccfad8dc03febfc37f7bc1d9d0aa645618f006508c",
            "diagnostics.jsonl": "d120463497e722b10ee5f7d5b5065fe8f84140b819182fe169a1ab9e32d813cb",
        },
        "production_weight_authority": 0,
        "native_c3_training_executed": False,
        "redmi_measured": False,
        "gates": dict(T.GATES),
    }


def rows():
    result = []
    for i in range(25):
        q = "Where is source key?"
        quote = "Original source contains KEY"
        result.append({
            "row_id": f"RUN181-{i:02d}",
            "source_project": T.TRAIN_PROJECTS[i % 4],
            "source_sha256": "a" * 64,
            "question": q,
            "prompt": q + "\n" + quote,
            "answer_keys": ["KEY"],
            "target": json.dumps({"answer": "KEY", "evidence_quote": quote, "uncertainty": ""}),
            "arm": "offer", "kind": "synthetic",
        })
    return result


def receipt():
    return {
        "schema": "V13_BP1_QAD_NATIVE_AUDIT_RECEIPT_V1",
        "status": "PASS_CLOSED_RAW",
        "model_revision": T.N.REVISION,
        "hf_master_sha256": T.N.MASTER_SHA,
        "gguf_sha256": T.N.GGUF_SHA,
        "source_commit": "fb7b440a319817a5665fabb4fb2d1ad60de62c4a",
        "exits": {key: 0 for key in ("BUDGET", "VENV", "PIP_TORCH", "PIP_HF",
            "HF_FETCH", "MASTER_SHA", "GGUF_SHA", "RUNNER_FETCH",
            "HF_NATIVE", "GGUF_NATIVE", "COMPARE")},
        "raw_zip_sha256": "a" * 64,
        "independently_crc_head_hash_verified": True,
    }


class TrainCandidateTests(unittest.TestCase):
    def test_pinned_config_is_shadow_and_1024(self):
        self.assertEqual(T.CFG["max_tokens"], 1024)
        self.assertEqual(T.CFG["jepa_weight"], 0)
        self.assertEqual(T.CFG["max_steps"], 2)
        self.assertEqual(T.CFG["seed"], 13)
        self.assertEqual(T.GATES["STEP2"], "UTILITY_FAIL")

    def test_manifest_accepts_original_bound_structure(self):
        self.assertEqual(T.validate_manifest(manifest())["train_rows"], 25)

    def test_manifest_rejects_heldout_leak_and_gate_change(self):
        for field, value in (("heldout_projects", list(T.TRAIN_PROJECTS)),
                             ("train_rows", 24), ("gates", {"jepa_weight": 1}),
                             ("native_c3_training_executed", True),
                             ("production_weight_authority", 1)):
            with self.subTest(field=field):
                m = manifest()
                m[field] = value
                with self.assertRaisesRegex(ValueError, "manifest mismatch"):
                    T.validate_manifest(m)

    def test_train_only_rows_are_valid(self):
        self.assertEqual(len(T.validate_train(rows())), 25)

    def test_train_project_leak_rejected(self):
        r = rows()
        r[0]["source_project"] = T.HELDOUT_PROJECTS[0]
        with self.assertRaisesRegex(ValueError, "heldout project"):
            T.validate_train(r)

    def test_duplicate_train_row_rejected(self):
        r = rows()
        r[1]["row_id"] = r[0]["row_id"]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            T.validate_train(r)

    def test_target_not_source_supported_rejected(self):
        r = rows()
        r[0]["target"] = json.dumps({"answer": "KEY", "evidence_quote": "made up", "uncertainty": ""})
        with self.assertRaisesRegex(ValueError, "unsupported train target"):
            T.validate_train(r)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            T.strict_json('{"answer":"a","answer":"b"}')

    def test_train_hash_mismatch_fails_before_tokenizer(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "manifest.json").write_text(json.dumps(manifest()))
            (p / "train.jsonl").write_text(json.dumps(rows()[0]) + "\n")
            with self.assertRaisesRegex(ValueError, "source SHA|train_offer"):
                T.load_inputs(p / "train.jsonl", p / "manifest.json")

    def test_master_wrong_hash_fails_before_model_import(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "model.safetensors").write_bytes(b"not QAD")
            with self.assertRaisesRegex(ValueError, "master SHA"):
                T.verify_master(d)

    def test_smoke_receipt_accepts_only_complete_closed_native(self):
        self.assertEqual(T.verify_smoke_receipt(receipt())["status"], "PASS_CLOSED_RAW")
        for field, value in (("status", "RED"), ("source_commit", "wrong"),
                             ("raw_zip_sha256", "missing"),
                             ("independently_crc_head_hash_verified", False)):
            with self.subTest(field=field):
                r = receipt()
                r[field] = value
                with self.assertRaises(ValueError):
                    T.verify_smoke_receipt(r)
        r = receipt()
        r["exits"]["HF_NATIVE"] = 1
        with self.assertRaisesRegex(ValueError, "exit codes"):
            T.verify_smoke_receipt(r)

    def test_preflight_does_not_read_heldout(self):
        class TinyTokenizer:
            def apply_chat_template(self, messages, **kwargs):
                return "fixed user prompt"
            def __call__(self, text, **kwargs):
                return {"input_ids": list(range(len(text.split())))}
        stats = T.verify_prompt_budget(rows(), TinyTokenizer())
        self.assertTrue(stats["all_train_prompts_preserved"])

    def test_overlong_training_prompt_rejected(self):
        class LongTokenizer:
            def apply_chat_template(self, messages, **kwargs):
                return "long"
            def __call__(self, text, **kwargs):
                return {"input_ids": list(range(2000))}
        with self.assertRaisesRegex(ValueError, "truncation"):
            T.verify_prompt_budget(rows(), LongTokenizer())


if __name__ == "__main__":
    unittest.main()
