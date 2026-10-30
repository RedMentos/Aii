"""Source-pinned seed73 German v2 SHADOW candidate, no native model/tool."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.listarith_de_v2_seed73_paired_eval import (
    validate, score, decision, evaluate, PINS, blob_sha, FIXTURE, SEED71, SEED67,
)
from v13.agi import listarith_de_shadow as original
from v13.agi import listarith_de_shadow_v2_candidate as candidate
from v13.agi import listarith


class GermanV2Candidate(unittest.TestCase):
    def test_holdout_frozen_before_candidate_source(self):
        rows = validate()
        self.assertEqual(len(rows), 36)
        self.assertEqual(blob_sha(FIXTURE), PINS["fixture"])
        self.assertEqual(blob_sha(SEED71), PINS["seed71"])
        self.assertEqual(blob_sha(SEED67), PINS["seed67"])
        self.assertEqual(blob_sha(Path(original.__file__)), PINS["original"])
        self.assertEqual(blob_sha(Path(candidate.__file__)), PINS["candidate"])

    def test_exposed_seed71_negation_and_meta_development_failures(self):
        rows = json.loads(SEED71.read_text())["rows"]
        for row in rows:
            if row["id"] in ("N01", "N04", "N08", "N09"):
                got = candidate.propose(row["text"])
                self.assertIsNone(got["proposal"], row["id"])
                self.assertEqual(got["authority"], "SHADOW_ONLY")

    def test_exposed_seed71_supported_development_paraphrases(self):
        rows = json.loads(SEED71.read_text())["rows"]
        for row in rows:
            if row["id"] in ("T03", "T04", "T10", "T11", "D05", "D07", "D11"):
                got = candidate.propose(row["text"])
                self.assertEqual(got["proposal"], row["expected"], row["id"])

    def test_pair_count_average_refused(self):
        for q in ("Was ist die Differenz zwischen A und B?",
                  "Wie viele Werte stehen in der Liste?",
                  "Wie groß ist der Durchschnitt?",
                  "Nenne den höchsten Betrag."):
            self.assertIsNone(candidate.propose("Daten: A 11, B 29, C 8. " + q)["proposal"], q)

    def test_conflict_and_negation_refused(self):
        for q in ("Addiere die Summe und berechne die Differenz zwischen Maximum und Minimum.",
                  "Berechne die Summe ausdrücklich nicht.",
                  "Warum ist die Summe falsch?"):
            self.assertIsNone(candidate.propose("Daten: A 11, B 29, C 8. " + q)["proposal"], q)

    def test_invalid_inputs_fail_closed(self):
        for v in ("", None, 3, "x" * 2100):
            got = candidate.propose(v)
            self.assertIsNone(got["proposal"])
            self.assertEqual(got["authority"], "SHADOW_ONLY")

    def test_synthetic_decision_thresholds(self):
        rows = [{"expected": r["expected"], "candidate": r["expected"],
                 "original": r["expected"]} for r in validate()]
        base = score(rows, "original")
        cand = score(rows, "candidate")
        self.assertEqual(base["correct"], 36)
        self.assertEqual(decision(base, cand), "V2_SHADOW_CANDIDATE_NOT_SUPPORTED")
        for row in rows[:8]:
            row["original"] = None if row["expected"] else "total"
        base = score(rows, "original")
        self.assertEqual(decision(base, cand), "V2_SHADOW_CANDIDATE_SUPPORTED")
        rows[-1]["candidate"] = "total"
        self.assertEqual(decision(base, score(rows, "candidate")),
                         "V2_SHADOW_CANDIDATE_NOT_SUPPORTED")

    def test_actual_paired_report_and_negative_gates(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "paired.json"
            report = evaluate(out)
            self.assertEqual(report, json.loads(out.read_text()))
            self.assertEqual(len(report["rows"]), 36)
            self.assertEqual(report["live_consumers"], 0)
            self.assertFalse(report["native_model_inference"])
            self.assertFalse(report["redmi_measured"])
            self.assertFalse(report["step2_gate_promoted"])
            self.assertFalse(report["b3_promoted"])
            self.assertFalse(report["body_jepa_available"])
            self.assertFalse(report["whole_system_complete"])
            self.assertEqual(report["jepa_weight"], 0)
            self.assertEqual(report["learning_mode"], "RECORD_ONLY")
            self.assertIn(report["decision"],
                          ("V2_SHADOW_CANDIDATE_SUPPORTED", "V2_SHADOW_CANDIDATE_NOT_SUPPORTED"))
            self.assertTrue(all(r["authority"] == "SHADOW_ONLY" for r in report["rows"]))
            with self.assertRaises(FileExistsError):
                evaluate(out)

    def test_unwired_original_english_unchanged(self):
        self.assertEqual(candidate.AUTHORITY, "SHADOW_ONLY")
        self.assertFalse(hasattr(candidate, "tool"))
        self.assertFalse(hasattr(candidate, "run"))
        self.assertEqual(listarith.operation("A 12 B 14. What is the total?"), "total")
        self.assertIsNone(listarith.operation("A 12 B 14. What is the average?"))


if __name__ == "__main__":
    unittest.main()
