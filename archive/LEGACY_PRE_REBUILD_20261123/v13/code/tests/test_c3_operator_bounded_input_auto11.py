"""Bounded C3 operator file inputs and lossless failed native error, software-only."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import listarith_de_operator_shadow as cli


class C3OperatorBoundedInput(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.txt"
        self.raw = self.root / "typed.json"
        self.out = self.root / "out.json"
        self.source.write_text(
            "Inventar: Dohle 7, Esche 12, Falke 9. Wie hoch ist die Summe?",
            encoding="utf-8")
        self.raw.write_text(json.dumps({"values": [
            {"name": "Dohle", "number": 7},
            {"name": "Esche", "number": 12},
            {"name": "Falke", "number": 9}]}), encoding="utf-8")

    def test_regular_utf8_exact_limit_is_accepted(self):
        p = self.root / "unicode.txt"
        p.write_text("Grün −4", encoding="utf-8")
        self.assertEqual(cli._read_text(p, max_bytes=len(p.read_bytes())), "Grün −4")

    def test_oversized_sparse_file_never_calls_unbounded_read_bytes(self):
        p = self.root / "huge.txt"
        with p.open("wb") as f:
            f.truncate(64 * 1024 * 1024)
        with patch.object(Path, "read_bytes",
                          side_effect=AssertionError("UNBOUNDED_READ_CALLED")):
            with self.assertRaisesRegex(ValueError, "INPUT_SIZE_OUT_OF_SCOPE"):
                cli._read_text(p, max_bytes=8000)

    def test_symlink_source_is_not_followed(self):
        link = self.root / "source-link.txt"
        link.symlink_to(self.source)
        with self.assertRaisesRegex(ValueError, "INPUT_REGULAR_FILE_REQUIRED"):
            cli.run(link, self.out, raw_json_file=self.raw)
        self.assertFalse(self.out.exists())

    def test_symlink_typed_json_is_not_followed(self):
        link = self.root / "raw-link.json"
        link.symlink_to(self.raw)
        with self.assertRaisesRegex(ValueError, "INPUT_REGULAR_FILE_REQUIRED"):
            cli.run(self.source, self.out, raw_json_file=link)
        self.assertFalse(self.out.exists())

    def test_quarantine_preserves_original_native_error_type(self):
        raw = self.raw.read_text(encoding="utf-8")
        receipt = {
            "native_attempted": True, "native_final": True,
            "postclose_process_reaped": False, "native_pid": 12345,
            "native_metrics": {"status": "FINAL"},
            "release": {"process_reaped": False},
            "error_type": "NATIVE_RELEASE_RED",
            "raw_output": raw,
        }
        with patch.object(cli, "_native_one", return_value=receipt):
            result = cli.run(self.source, self.out, home=self.root)
        report = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "SHADOW_ABSTAIN")
        self.assertEqual(report["reason"], "NATIVE_RECEIPT_UNVERIFIED")
        self.assertEqual(report["native_reported_error_type"], "NATIVE_RELEASE_RED")
        self.assertEqual(report["quarantined_raw_sha256"],
                         hashlib.sha256(raw.encode()).hexdigest())
        self.assertIsNone(report["raw_output"])
        self.assertFalse(report["step2_gate_promoted"])


if __name__ == "__main__":
    unittest.main()
