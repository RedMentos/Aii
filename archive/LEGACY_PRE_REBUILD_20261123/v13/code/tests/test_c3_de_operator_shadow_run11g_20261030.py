"""One-source C3 arithmetic SHADOW operator probe: software-only, no native."""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from scripts import listarith_de_operator_shadow as cli


class C3GermanOperatorShadow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.txt"
        self.raw = self.root / "typed.json"
        self.out = self.root / "result.json"
        self.set_case("Inventar: Dohle 7, Esche 12, Falke 9. Wie hoch ist die Summe?",
                      [("Dohle", 7), ("Esche", 12), ("Falke", 9)])

    def tearDown(self):
        self.tmp.cleanup()

    def set_case(self, text, pairs):
        self.source.write_text(text, encoding="utf-8")
        self.raw.write_text(json.dumps(
            {"values": [{"name": name, "number": n} for name, n in pairs]}),
            encoding="utf-8")

    def run_replay(self):
        return cli.run(self.source, self.out, raw_json_file=self.raw)

    def report(self):
        return json.loads(self.out.read_text(encoding="utf-8"))

    def test_exact_sum_and_private_raw_evidence(self):
        summary = self.run_replay()
        report = self.report()
        self.assertEqual(summary["status"], "SHADOW_RESULT")
        self.assertEqual(report["baseline"]["value"], 28)
        self.assertEqual(report["closedworld"]["value"], 28)
        self.assertEqual(report["closedworld"]["operation"], "total")
        self.assertEqual(report["source_sha256"],
                         hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertEqual(report["raw_sha256"],
                         hashlib.sha256(self.raw.read_bytes()).hexdigest())
        self.assertEqual(report["evidence_level"], "SOFTWARE_USER_SUPPLIED_RAW")
        self.assertFalse(report["native_attempted"])
        self.assertFalse(report["native_final"])
        self.assertFalse(report["live_tool_execution"])
        self.assertFalse(report["external_action_authority"])
        self.assertFalse(report["step2_gate_promoted"])
        self.assertFalse(report["b3_promoted"])
        self.assertFalse(report["body_jepa_available"])
        self.assertEqual(report["jepa_weight"], 0)
        self.assertFalse(report["redmi_measured"])
        self.assertFalse(report["whole_system_complete"])
        self.assertEqual(stat.S_IMODE(self.out.stat().st_mode), 0o600)

    def test_exact_max_minus_min(self):
        self.set_case("Stufen: Grau 6, Violett 24, Orange 11. "
                      "Wie groß ist der Unterschied zwischen dem höchsten "
                      "und dem niedrigsten Wert?",
                      [("Grau", 6), ("Violett", 24), ("Orange", 11)])
        self.run_replay()
        self.assertEqual(self.report()["closedworld"]["value"], 18)

    def test_omitted_item_abstains_even_if_baseline_accepts(self):
        self.set_case("Inventar: Dohle 7, Esche 12, Falke 9. Wie hoch ist die Summe?",
                      [("Dohle", 7), ("Esche", 12)])
        self.run_replay()
        self.assertEqual(self.report()["baseline"]["status"], "SHADOW_RESULT")
        self.assertEqual(self.report()["closedworld"]["status"], "SHADOW_ABSTAIN")
        self.assertEqual(self.report()["status"], "SHADOW_ABSTAIN")

    def test_unsupported_question_abstains(self):
        self.set_case("Inventar: Dohle 7, Esche 12, Falke 9. Wie viele Einträge?",
                      [("Dohle", 7), ("Esche", 12), ("Falke", 9)])
        self.run_replay()
        self.assertEqual(self.report()["status"], "SHADOW_ABSTAIN")

    def test_malformed_raw_abstains_without_native_claim(self):
        self.raw.write_text('{"values": [}', encoding="utf-8")
        self.run_replay()
        self.assertEqual(self.report()["status"], "SHADOW_ABSTAIN")
        self.assertFalse(self.report()["native_final"])

    def test_existing_output_never_overwritten(self):
        self.out.write_text("sentinel", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.run_replay()
        self.assertEqual(self.out.read_text(encoding="utf-8"), "sentinel")

    def test_oversized_source_rejected_before_output(self):
        self.source.write_text("X" * 2001, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SOURCE_OUT_OF_SCOPE"):
            self.run_replay()
        self.assertFalse(self.out.exists())

    def test_mode_requires_exactly_one_source(self):
        with self.assertRaisesRegex(ValueError, "EXACTLY_ONE"):
            cli.run(self.source, self.out)
        with self.assertRaisesRegex(ValueError, "EXACTLY_ONE"):
            cli.run(self.source, self.out, raw_json_file=self.raw, home=self.root)

    def test_fake_native_failure_is_explicitly_not_native_evidence(self):
        fake = {"native_attempted": True, "native_final": False,
                "postclose_process_reaped": False, "raw_output": None,
                "error_type": "TEST_NATIVE_BLOCKED"}
        with patch.object(cli, "_native_one", return_value=fake):
            summary = cli.run(self.source, self.out, home=self.root)
        self.assertEqual(summary["status"], "SHADOW_ABSTAIN")
        self.assertEqual(self.report()["reason"], "TEST_NATIVE_BLOCKED")
        self.assertIsNone(self.report()["raw_output"])
        self.assertFalse(self.report()["native_final"])
        self.assertFalse(self.report()["whole_system_complete"])

    def test_cli_stdout_does_not_leak_raw_or_source(self):
        out = StringIO()
        with redirect_stdout(out):
            code = cli.main(["--source-file", str(self.source),
                             "--raw-json-file", str(self.raw),
                             "--out", str(self.out)])
        self.assertEqual(code, 0)
        self.assertNotIn("Dohle", out.getvalue())
        self.assertNotIn("Falke", out.getvalue())
        self.assertNotIn('"values"', out.getvalue())
        self.assertIn("SOFTWARE_USER_SUPPLIED_RAW", out.getvalue())


if __name__ == "__main__":
    unittest.main()
