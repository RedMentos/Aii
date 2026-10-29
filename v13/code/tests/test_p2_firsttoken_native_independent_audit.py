"""Adversarial stdlib-only tests for P2 first-token independent raw review."""
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p2_firsttoken_native_independent_audit.py"
spec = importlib.util.spec_from_file_location("p2_native_independent", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def zip_receipt(path, content):
    content = dict(content)
    content["SHA256SUMS"] = "".join(
        hashlib.sha256(data).hexdigest() + "  ./" + name + "\n"
        for name, data in sorted(content.items())).encode()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in content.items():
            z.writestr(name, data)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(directory, *, bad=None):
    d = Path(directory)
    refs = [{"prompt": p, "qad_source_ids": [i + 1, i + 2],
             "gguf_runtime_ids": [i + 1, i + 2], "ids_equal": True}
            for i, p in enumerate(audit.PROMPTS)]
    token = {"schema": "v13.p2.qad_gguf_native_tokenizer_ids.v1",
             "equal_count": 8, "probe_count": 8, "probes": refs}
    tp = d / "token.zip"
    tsha = zip_receipt(tp, {"HEAD.txt": (audit.TOKENIZER_HEAD + "\n").encode(),
                            "RESULT.json": json.dumps(token).encode()})
    rows = [{"prompt": p, "input_ids": [i + 1, i + 2],
             "hf_first": 10 + i, "gguf_first": 10 + i,
             "hf_top5": [10 + i, 20 + i],
             "gguf_top5": [10 + i, 30 + i], "top5_overlap": 1}
            for i, p in enumerate(audit.PROMPTS)]
    result = {"schema": "v13.p2.qad_fp32_gguf_first_token_native.v1",
              "status": "FIRST_TOKEN_MEASURED_NO_PARITY_PROMOTION",
              "probe_count": 8, "model_forward_calls": 8, "training": False,
              "full_logit_greedy_cache_adapter_or_utility_parity_proven": False,
              "rows": rows, "top1_equal_count": 8, "top5_overlap_total": 8,
              "source_pins": {"model.safetensors": audit.MASTER_SHA},
              "gguf_sha256": audit.GGUF_SHA}
    native = {"HEAD.txt": (audit.NATIVE_HEAD + "\n").encode(),
              "RESULT.json": json.dumps(result).encode(),
              "PRIVACY_RAW.log": b"privacy scan: CLEAN\n",
              "SERVER_RAW.log": b"listening on http://127.0.0.1:8080\n",
              "MODEL_SHA_RAW.log": b"file: OK\n" * 6,
              "RUNTIME_SHA_RAW.log": b"runtime: OK\n"}
    for stage in audit.STAGES:
        native[stage + "_EXIT.txt"] = b"0\n"
    if bad == "stage":
        native["AUDIT_EXIT.txt"] = b"2\n"
    if bad == "prompt":
        result["rows"][0]["prompt"] = "foreign"
        native["RESULT.json"] = json.dumps(result).encode()
    if bad == "aggregate":
        result["top1_equal_count"] = 7
        native["RESULT.json"] = json.dumps(result).encode()
    if bad == "training":
        result["training"] = True
        native["RESULT.json"] = json.dumps(result).encode()
    if bad == "ids":
        result["rows"][0]["input_ids"] = [99]
        native["RESULT.json"] = json.dumps(result).encode()
    if bad == "head":
        native["HEAD.txt"] = b"foreign\n"
    np = d / "native.zip"
    zip_receipt(np, native)
    return np, tp, tsha


class IndependentNativeReviewTests(unittest.TestCase):
    def check_bad(self, variant, message):
        with tempfile.TemporaryDirectory() as d:
            n, t, h = fixture(d, bad=variant)
            with patch.object(audit, "TOKENIZER_ZIP_SHA", h):
                with self.assertRaisesRegex(ValueError, message):
                    audit.verify(n, t)

    def test_valid_synthetic_no_promotion(self):
        with tempfile.TemporaryDirectory() as d:
            n, t, h = fixture(d)
            with patch.object(audit, "TOKENIZER_ZIP_SHA", h):
                r = audit.verify(n, t)
            self.assertEqual(r["status"], "EIGHT_FIRSTTOKEN_NATIVE_DESCRIPTIVE_VERIFIED")
            self.assertEqual(r["top1_equal_count"], 8)
            self.assertFalse(r["parity_or_utility_proven"])

    def test_stage_red(self):
        self.check_bad("stage", "native stage")

    def test_prompt_tamper_red(self):
        self.check_bad("prompt", "prompt mismatch")

    def test_aggregate_tamper_red(self):
        self.check_bad("aggregate", "aggregate")

    def test_training_promotion_red(self):
        self.check_bad("training", "promotion")

    def test_token_ids_tamper_red(self):
        self.check_bad("ids", "input IDs mismatch")

    def test_head_tamper_red(self):
        self.check_bad("head", "HEAD")

    def test_wrong_tokenizer_archive_sha_red(self):
        with tempfile.TemporaryDirectory() as d:
            n, t, h = fixture(d)
            with self.assertRaisesRegex(ValueError, "tokenizer-only ZIP SHA"):
                audit.verify(n, t)

    def test_manifest_digest_tamper_red(self):
        with tempfile.TemporaryDirectory() as d:
            n, t, h = fixture(d)
            with zipfile.ZipFile(n, "a") as z:
                z.writestr("INJECTED.txt", "extra")
            with self.assertRaisesRegex(ValueError, "coverage mismatch"):
                audit.closed_zip(n)


if __name__ == "__main__":
    unittest.main()
