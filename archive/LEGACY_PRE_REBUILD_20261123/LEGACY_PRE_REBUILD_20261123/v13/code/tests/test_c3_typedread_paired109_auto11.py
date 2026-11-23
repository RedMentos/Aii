"""Frozen C3 paired109 preflight and software-stub contract; no model run."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from scripts import c3_typedread_paired109_native as experiment


class C3Paired109Software(unittest.TestCase):
    def test_frozen_eight_disjoint_and_exact_deterministic_baseline(self):
        rows = experiment.frozen_rows()
        self.assertEqual(len(rows), 8)
        self.assertEqual(len({r["text"] for r in rows}), 8)
        self.assertEqual([r["expected_answer"] for r in rows],
                         [25, 11, 26, 13, 24, 12, 25, 15])
        for row in rows:
            self.assertEqual(experiment.deterministic_pairs(row["text"]),
                             row["expected_values"])
            self.assertNotIn("Birke 4, Komet 13, Welle 8", row["text"])

    def test_prompt_arms_distinct_and_source_hashes(self):
        from v13.agi import listarith
        self.assertNotEqual(experiment.EXPLICIT_SYSTEM, listarith.READ_SYSTEM)
        self.assertIn("Do not number items by position", experiment.EXPLICIT_SYSTEM)
        self.assertEqual(len(experiment.sha(experiment.EXPLICIT_SYSTEM.encode())), 64)

    def test_fake_native_only_generates_software_report_not_native_proof(self):
        rows = experiment.frozen_rows()
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.json"
            def fake_read(home, cfg, model_path, text, system):
                calls.append((text, system))
                return {
                    "native_attempted": True, "native_final": False,
                    "postclose_process_reaped": False, "native_pid": None,
                    "native_metrics": None, "release": None,
                    "error_type": "SOFTWARE_STUB_NO_NATIVE", "raw_output": None,
                    "admitted": False}
            with patch.object(experiment.operator, "_native_preflight",
                              return_value=(Path(tmp), {}, Path(tmp) / "fake.gguf")), \
                 patch.object(experiment, "native_read", side_effect=fake_read):
                counts = experiment.run(Path(tmp), output)
            self.assertEqual(len(calls), 16)
            self.assertEqual(counts["D_exact"], 8)
            self.assertEqual(counts["native_admitted"], 0)
            self.assertEqual(counts["A_exact"], 0)
            self.assertEqual(counts["B_exact"], 0)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(report["rows"]), 8)
            self.assertFalse(report["step2_gate_promoted"])
            self.assertFalse(report["whole_system_complete"])
            self.assertEqual(report["jepa_weight"], 0)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            for i, row in enumerate(rows):
                pair = calls[i*2:i*2+2]
                self.assertEqual([x[0] for x in pair], [row["text"]]*2)
                self.assertEqual([x[1] == experiment.EXPLICIT_SYSTEM for x in pair],
                                 [False, True] if i % 2 == 0 else [True, False])

    def test_wrong_frozen_fixture_blob_rejected(self):
        with patch.object(experiment, "FIXTURE_BLOB", "0"*40):
            with self.assertRaisesRegex(ValueError, "FROZEN_109_FIXTURE_CHANGED"):
                experiment.frozen_rows()


if __name__ == "__main__":
    unittest.main()
