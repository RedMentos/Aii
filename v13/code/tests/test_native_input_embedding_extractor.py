import json
import os
from pathlib import Path
import tempfile
import textwrap
import unittest

from v13.native_input_embedding_extractor import (
    NativeInputEmbeddingError,
    extract_native_input_embedding_rows,
)


class NativeInputEmbeddingExtractorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.model = self.root / "model fixture.gguf"
        self.model.write_bytes(b"synthetic model bytes; never loaded by fake extractor")
        self.binary = self.root / "native extractor fixture"
        self._write_binary("valid")

    def tearDown(self):
        self.temp.cleanup()

    def _write_binary(self, mode):
        source = r'''#!/usr/bin/env python3
import json
import sys
import time
args = sys.argv[1:]
if args and args[0] == "--extract":
    args = args[1:]
opts = {args[i]: args[i + 1] for i in range(0, len(args), 2)}
mode = MODE
if mode == "timeout":
    time.sleep(3)
if mode == "fail":
    sys.exit(7)
ids = [int(value) for value in opts["--token-ids"].split(",")]
if mode == "reorder":
    ids = list(reversed(ids))
receipt = {
    "schema": "v14.llama-token-embedding-rows-receipt/1",
    "api_symbol": "llama_model_get_tok_embd_rows",
    "api_header": "src/llama-ext.h",
    "api_stability": "STAGING_WIP",
    "llama_cpp_revision": "2851b3bcbf8d993a2243ae751c0a7dfa8e944a40",
    "extractor_binary_sha256": opts["--extractor-sha256"],
    "model_revision": opts["--model-revision"],
    "model_sha256": opts["--model-sha256"],
    "source_tensor_type": "q4_0",
    "output_dtype": "f32",
    "vocab_size": 128,
    "embedding_dim": 2,
    "requested_token_ids": ids,
    "elements_written": len(ids) * 2,
}
rows = [[float(token + 1), float(token + 2)] for token in ids]
if mode == "wrong_model_sha":
    receipt["model_sha256"] = "0" * 64
elif mode == "short_count":
    receipt["elements_written"] -= 1
elif mode == "zero_row":
    rows[0] = [0.0, 0.0]
elif mode == "nonfinite":
    print('{"schema":"v14.native-input-embedding-extractor/1","status":"COMPLETE","receipt":' +
          json.dumps(receipt) + ',"rows":[[NaN,1.0],[1.0,2.0]]}')
    sys.exit(0)
elif mode == "mutate_model":
    with open(opts["--model"], "ab") as handle:
        handle.write(b"changed")
print(json.dumps({
    "schema": "v14.native-input-embedding-extractor/1",
    "status": "COMPLETE",
    "receipt": receipt,
    "rows": rows,
}))
'''
        source = source.replace("MODE", repr(mode))
        self.binary.write_text(textwrap.dedent(source), encoding="utf-8")
        self.binary.chmod(0o700)

    def _extract(self, **kwargs):
        return extract_native_input_embedding_rows(
            self.binary,
            self.model,
            "installed-model-rev-1",
            [7, 12, 12],
            model_root=self.root,
            **kwargs,
        )

    def test_valid_native_receipt_and_rows_are_bound_to_installed_files(self):
        result = self._extract()
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["receipt"]["requested_token_ids"], [7, 12, 12])
        self.assertEqual(result["receipt"]["elements_written"], 6)
        self.assertEqual(len(result["rows"]), 3)
        self.assertEqual(result["rows"][0], [8.0, 9.0])
        self.assertEqual(result["model_sha256"], result["receipt"]["model_sha256"])
        self.assertEqual(result["extractor_binary_sha256"], result["receipt"]["extractor_binary_sha256"])

    def test_expected_model_manifest_hash_is_enforced(self):
        with self.assertRaises(NativeInputEmbeddingError):
            self._extract(expected_model_sha256="0" * 64)

    def test_receipt_model_hash_mismatch_is_rejected(self):
        self._write_binary("wrong_model_sha")
        with self.assertRaises(NativeInputEmbeddingError):
            self._extract()

    def test_token_order_drift_is_rejected(self):
        self._write_binary("reorder")
        with self.assertRaises(NativeInputEmbeddingError):
            self._extract()

    def test_short_element_count_is_rejected(self):
        self._write_binary("short_count")
        with self.assertRaises(NativeInputEmbeddingError):
            self._extract()

    def test_zero_rows_are_rejected(self):
        self._write_binary("zero_row")
        with self.assertRaises(NativeInputEmbeddingError):
            self._extract()

    def test_nonfinite_json_values_are_rejected(self):
        self._write_binary("nonfinite")
        with self.assertRaises(NativeInputEmbeddingError):
            self._extract()

    def test_model_change_during_extraction_is_rejected(self):
        self._write_binary("mutate_model")
        with self.assertRaises(NativeInputEmbeddingError):
            self._extract()

    def test_symlink_model_and_extractor_are_rejected(self):
        model_link = self.root / "model-link.gguf"
        model_link.symlink_to(self.model)
        with self.assertRaises(NativeInputEmbeddingError):
            extract_native_input_embedding_rows(
                self.binary, model_link, "rev", [1, 2], model_root=self.root,
            )
        binary_link = self.root / "binary-link"
        binary_link.symlink_to(self.binary)
        with self.assertRaises(NativeInputEmbeddingError):
            extract_native_input_embedding_rows(
                binary_link, self.model, "rev", [1, 2], model_root=self.root,
            )

    def test_invalid_token_ids_and_timeout_are_rejected(self):
        with self.assertRaises(NativeInputEmbeddingError):
            extract_native_input_embedding_rows(self.binary, self.model, "rev", [1])
        with self.assertRaises(NativeInputEmbeddingError):
            extract_native_input_embedding_rows(self.binary, self.model, "rev", [1, True])
        self._write_binary("timeout")
        with self.assertRaises(NativeInputEmbeddingError):
            self._extract(timeout_seconds=1)

    def test_failed_native_process_does_not_leak_stderr(self):
        self._write_binary("fail")
        with self.assertRaisesRegex(NativeInputEmbeddingError, "extractor failed"):
            self._extract()


if __name__ == "__main__":
    unittest.main()
