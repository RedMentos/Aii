"""Operator deterministic German list SHADOW: frozen utility and adversarial abstention."""
from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from scripts import listarith_de_operator_shadow as cli
from scripts import c3_typedread_paired109_native as cohort


class DeterministicGermanOperator(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.txt"
        self.out = self.root / "out.json"

    def evaluate(self, text):
        self.source.write_text(text, encoding="utf-8")
        with patch.object(cli, "_native_one",
                          side_effect=AssertionError("NATIVE_MUST_NOT_RUN")):
            summary = cli.run(self.source, self.out, deterministic=True)
        return summary, json.loads(self.out.read_text(encoding="utf-8"))

    def test_frozen_eight_narrow_sources_exact_without_model(self):
        for row in cohort.frozen_rows():
            with self.subTest(row=row["id"]):
                if self.out.exists():
                    self.out.unlink()
                summary, report = self.evaluate(row["text"])
                self.assertEqual(summary["status"], "SHADOW_RESULT")
                self.assertEqual(report["closedworld"]["operation"],
                                 row["expected_operation"])
                self.assertEqual(report["closedworld"]["value"],
                                 row["expected_answer"])
                self.assertEqual(report["closedworld"]["input_count"], 3)
                self.assertEqual(report["evidence_level"],
                                 "SOFTWARE_DETERMINISTIC_SOURCE_BOUND")
                self.assertEqual(report["source_sha256"],
                                 hashlib.sha256(row["text"].encode()).hexdigest())
                self.assertEqual(report["raw_sha256"],
                                 hashlib.sha256(report["raw_output"].encode()).hexdigest())
                self.assertIs(report["native_attempted"], False)
                self.assertIs(report["native_final"], False)
                self.assertIs(report["live_tool_execution"], False)
                self.assertIs(report["external_action_authority"], False)
                self.assertIs(report["step2_gate_promoted"], False)
                self.assertIs(report["b3_promoted"], False)
                self.assertIs(report["body_jepa_available"], False)
                self.assertIs(report["whole_system_complete"], False)
                self.assertEqual(report["jepa_weight"], 0)
                self.assertEqual(stat.S_IMODE(self.out.stat().st_mode), 0o600)

    def test_unicode_minus_signed_integer(self):
        summary, report = self.evaluate(
            "Inventar: Birnbaum −4, Glimmer 13, Ranke 8. Wie hoch ist die Summe?")
        self.assertEqual(summary["status"], "SHADOW_RESULT")
        self.assertEqual(report["closedworld"]["value"], 17)

    def test_adversarial_out_of_domain_inputs_abstain(self):
        cases = [
            "Inventar: Birnbaum 4, Glimmer 13, Ranke 8. Wie viele Einträge?",
            "Inventar: Birnbaum 4, Glimmer 13, Ranke 8. Bitte nicht summieren.",
            "Inventar: Birnbaum 4, Glimmer 13, Ranke 8. Ist die Summe 25 richtig?",
            "Inventar: Birnbaum 4, Glimmer 13, Ranke 8. Wie hoch ist die Summe 25?",
            "Inventar: Birnbaum 4; Glimmer 13; Ranke 8. Wie hoch ist die Summe?",
            "Inventar: Birnbaum 4, Glimmer 13, Ranke 8 Wie hoch ist die Summe?",
            "Inventar: Birnbaum 4, birnbaum 13, Ranke 8. Wie hoch ist die Summe?",
            "Inventar: Birnbaum 04, Glimmer 13, Ranke 8. Wie hoch ist die Summe?",
            "Inventar: Birnbaum 4, Glimmer 13.5, Ranke 8. Wie hoch ist die Summe?",
            "Inventar 2026: Birnbaum 4, Glimmer 13, Ranke 8. Wie hoch ist die Summe?",
            "Inventar: Birnbaum 4, Glimmer 13, Ranke 8, Gesamt 25. Wie hoch ist die Summe?",
            "Inventar: Birnbaum 4, Glimmer 13, Ranke 8.",
            "Inventar: A 4, Glimmer 13, Ranke 8. Wie hoch ist die Summe?",
            "Inventar: Birnbaum 4, Glimmer 13, Ranke 8. Wie hoch ist der Durchschnitt?",
            "Inventar: Birnbaum 4, Glimmer 13, Ranke 8. Wie groß ist der Unterschied zwischen Birnbaum und Ranke?",
        ]
        for case in cases:
            with self.subTest(case=case):
                if self.out.exists():
                    self.out.unlink()
                summary, report = self.evaluate(case)
                self.assertEqual(summary["status"], "SHADOW_ABSTAIN")
                self.assertIsNone(report["closedworld"])
                self.assertFalse(report["whole_system_complete"])

    def test_mode_exclusivity(self):
        self.source.write_text(
            "Inventar: Birnbaum 4, Glimmer 13. Wie hoch ist die Summe?",
            encoding="utf-8")
        raw = self.root / "raw.json"
        raw.write_text('{"values":[]}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "EXACTLY_ONE"):
            cli.run(self.source, self.out, raw_json_file=raw, deterministic=True)
        with self.assertRaisesRegex(ValueError, "EXACTLY_ONE"):
            cli.run(self.source, self.out, home=self.root, deterministic=True)

    def test_cli_stdout_private_and_no_overwrite(self):
        self.source.write_text(
            "Inventar: Birnbaum 4, Glimmer 13, Ranke 8. Wie hoch ist die Summe?",
            encoding="utf-8")
        output = StringIO()
        with redirect_stdout(output):
            exit_code = cli.main(["--source-file", str(self.source),
                                  "--deterministic", "--out", str(self.out)])
        self.assertEqual(exit_code, 0)
        self.assertNotIn("Birnbaum", output.getvalue())
        self.assertNotIn('"values"', output.getvalue())
        self.assertIn("SOFTWARE_DETERMINISTIC_SOURCE_BOUND", output.getvalue())
        with self.assertRaises(FileExistsError):
            cli.run(self.source, self.out, deterministic=True)

    def test_symlink_and_oversized_source_rejected(self):
        self.source.write_text(
            "Inventar: Birnbaum 4, Glimmer 13. Wie hoch ist die Summe?",
            encoding="utf-8")
        link = self.root / "link.txt"
        link.symlink_to(self.source)
        with self.assertRaisesRegex(ValueError, "INPUT_REGULAR_FILE_REQUIRED"):
            cli.run(link, self.out, deterministic=True)
        self.assertFalse(self.out.exists())
        self.source.write_text("X" * 2001, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SOURCE_OUT_OF_SCOPE"):
            cli.run(self.source, self.out, deterministic=True)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
