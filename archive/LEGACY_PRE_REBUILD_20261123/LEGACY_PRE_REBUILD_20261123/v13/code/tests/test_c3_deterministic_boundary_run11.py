"""Preregistered C3 deterministic one-question contract and seeded source robustness.

Software SHADOW only. The seed and five negative fixtures are frozen in
C3_DETERMINISTIC_BOUNDARY_PREREG_RUN11_20261030.md.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random
import stat
import tempfile
import unittest
from unittest.mock import patch

from scripts import listarith_de_operator_shadow as operator
from scripts import c3_typedread_paired109_native as cohort

NEGATIVE_MULTI_SENTENCE = (
    "Inventar: Birnbaum 4, Glimmer 13, Ranke 8. Wie hoch ist die Summe? Welche Farbe hat die Kiste?",
    "Inventar: Birnbaum 4, Glimmer 13, Ranke 8. Wie hoch ist die Summe. Und welche Farbe?",
    "Inventar: Birnbaum 4, Glimmer 13, Ranke 8. Welche Farbe? Wie hoch ist die Summe?",
    "Inventar: Birnbaum 4, Glimmer 13, Ranke 8. Wie hoch ist die Summe? Wie lautet die Uhrzeit?",
    "Inventar: Birnbaum 4, Glimmer 13, Ranke 8. Wie hoch ist die Summe! Und welche Farbe?",
)
NAMES = ("Birnbaum", "Glimmer", "Ranke", "Komet", "Welle", "Sonne", "Stern", "Kiefer")
NUMBERS = (-999999, -200, -1, 0, 1, 7, 7, 19, 999999)
TOTAL_Q = "Wie hoch ist die Summe?"
DIFF_Q = "Wie groß ist der Unterschied zwischen dem höchsten und dem niedrigsten Wert?"


class DeterministicBoundaryRun11(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.source = self.root / "source.txt"
        self.out = self.root / "private.json"

    def evaluate(self, text):
        self.source.write_text(text, encoding="utf-8")
        with patch.object(operator, "_native_one", side_effect=AssertionError("NATIVE_FORBIDDEN")):
            summary = operator.run(self.source, self.out, deterministic=True)
        report = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(report["source_sha256"], hashlib.sha256(text.encode("utf-8")).hexdigest())
        self.assertEqual(report["evidence_level"], "SOFTWARE_DETERMINISTIC_SOURCE_BOUND")
        self.assertFalse(report["native_attempted"])
        self.assertFalse(report["native_final"])
        self.assertFalse(report["live_tool_execution"])
        self.assertFalse(report["external_action_authority"])
        self.assertFalse(report["step2_gate_promoted"])
        self.assertFalse(report["b3_promoted"])
        self.assertFalse(report["body_jepa_available"])
        self.assertFalse(report["redmi_measured"])
        self.assertFalse(report["whole_system_complete"])
        self.assertEqual(report["learning_mode"], "RECORD_ONLY")
        self.assertEqual(report["jepa_weight"], 0)
        self.assertEqual(stat.S_IMODE(self.out.stat().st_mode), 0o600)
        self.out.unlink()
        return summary, report

    def test_five_frozen_multisentence_ambiguous_questions_abstain(self):
        for source in NEGATIVE_MULTI_SENTENCE:
            with self.subTest(source=source):
                summary, report = self.evaluate(source)
                self.assertEqual(summary["status"], "SHADOW_ABSTAIN")
                self.assertIsNone(report["closedworld"])
                self.assertIsNone(report["raw_output"])
                self.assertIsNone(report["raw_sha256"])

    def test_frozen_eight_original_positive_controls_unchanged(self):
        for row in cohort.frozen_rows():
            with self.subTest(row=row["id"]):
                summary, report = self.evaluate(row["text"])
                self.assertEqual(summary["status"], "SHADOW_RESULT")
                self.assertEqual(report["closedworld"]["value"], row["expected_answer"])
                self.assertEqual(report["closedworld"]["operation"], row["expected_operation"])
                self.assertTrue(report["closedworld"]["closed_world_checked"])

    def test_seed117_forty_generated_narrow_sources_exact(self):
        rng = random.Random(117)
        for case_id in range(40):
            count = rng.randint(2, 8)
            names = rng.sample(NAMES, count)
            nums = [rng.choice(NUMBERS) for _ in range(count)]
            operation = "total" if case_id % 2 == 0 else "difference_max_min"
            question = TOTAL_Q if operation == "total" else DIFF_Q
            source = "Inventar: " + ", ".join(
                f"{name} {number}" for name, number in zip(names, nums)
            ) + ". " + question
            expected = sum(nums) if operation == "total" else max(nums) - min(nums)
            with self.subTest(case_id=case_id, count=count, operation=operation):
                summary, report = self.evaluate(source)
                self.assertEqual(summary["status"], "SHADOW_RESULT")
                self.assertEqual(report["closedworld"]["operation"], operation)
                self.assertEqual(report["closedworld"]["value"], expected)
                self.assertEqual(report["closedworld"]["input_count"], count)
                self.assertTrue(report["closedworld"]["closed_world_checked"])


if __name__ == "__main__":
    unittest.main()
