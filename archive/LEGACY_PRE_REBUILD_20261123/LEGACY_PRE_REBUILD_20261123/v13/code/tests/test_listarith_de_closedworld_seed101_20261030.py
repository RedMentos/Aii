"""Preregistered seed101 closed-world SHADOW candidate regression.

Synthetic software tests only. Original seed79/83 native and seed97 budget
fixtures/scorers remain untouched; this module has no live consumer.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from v13.agi import listarith_de_shadow_pipeline as baseline
from v13.agi import listarith_de_closedworld_candidate as candidate

CODE = Path(__file__).resolve().parents[1]
FIXTURE = CODE / "specs/listarith_de_closedworld_seed101_frozen.json"
FROZEN_BLOB = "71011ba309759931f2cb9afa487d621e66aebdaa"
BASELINE_BLOB = "25cacd7388e5464dd814f4b18c545e2ec2f78b54"


def git_blob(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def rows():
    assert git_blob(FIXTURE) == FROZEN_BLOB, "FROZEN_FIXTURE_CHANGED"
    assert git_blob(Path(baseline.__file__)) == BASELINE_BLOB, "FROZEN_BASELINE_CHANGED"
    d = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert d["schema"] == "v13.de.closedworld.seed101.v1"
    assert d["seed"] == 101 and d["supported"] == 12 and d["negative"] == 12
    assert len(d["rows"]) == 24
    assert len({r["id"] for r in d["rows"]}) == 24
    return d["rows"]


class ClosedWorld101(unittest.TestCase):
    def test_frozen_prereg_and_disjointness(self):
        all_rows = rows()
        self.assertEqual(sum(r["expected_status"] == "SHADOW_RESULT" for r in all_rows), 12)
        self.assertEqual(sum(r["expected_status"] == "SHADOW_ABSTAIN" for r in all_rows), 12)
        seen = {r["text"] for r in all_rows}
        for name in ("listarith_de83_native_shadow_frozen.json",
                     "c3_de_native_typed_read_seed79.json"):
            original = json.loads((CODE / "specs" / name).read_text(encoding="utf-8"))
            self.assertFalse(seen & {r["text"] for r in original["rows"]})

    def test_frozen_24_paired_and_no_wrong_emissions(self):
        counts = {"supported": 0, "abstain": 0, "baseline_unsafe": 0}
        for row in rows():
            with self.subTest(row=row["id"]):
                old = baseline.evaluate(row["text"], row["raw_json"])
                got = candidate.evaluate(row["text"], row["raw_json"])
                self.assertEqual(got["status"], row["expected_status"], got)
                self.assertEqual(got["authority"], "SHADOW_ONLY")
                self.assertFalse(got["live_tool_execution"])
                self.assertFalse(got["external_action_authority"])
                self.assertFalse(got["step2_gate_promoted"])
                self.assertFalse(got["b3_promoted"])
                self.assertFalse(got["body_jepa_available"])
                self.assertEqual(got["jepa_weight"], 0)
                self.assertFalse(got["redmi_measured"])
                self.assertFalse(got["whole_system_complete"])
                if row["expected_status"] == "SHADOW_RESULT":
                    self.assertEqual((got["operation"], got["value"]),
                                     (row["expected_operation"], row["expected_answer"]))
                    self.assertTrue(got["closed_world_checked"])
                    counts["supported"] += 1
                else:
                    self.assertIsNone(got["value"])
                    self.assertFalse(got["closed_world_checked"])
                    counts["abstain"] += 1
                    if old["status"] == "SHADOW_RESULT":
                        counts["baseline_unsafe"] += 1
        self.assertEqual(counts["supported"], 12)
        self.assertEqual(counts["abstain"], 12)
        self.assertGreaterEqual(counts["baseline_unsafe"], 8)

    def test_repeated_value_omission_detected(self):
        source = "Daten: Amsel 5, Drossel 5, Meise 8. Wie hoch ist die Summe?"
        raw = json.dumps({"values": [{"name": "Amsel", "number": 5},
                                     {"name": "Meise", "number": 8}]})
        self.assertEqual(baseline.evaluate(source, raw)["status"], "SHADOW_RESULT")
        got = candidate.evaluate(source, raw)
        self.assertEqual(got["reason"], "SOURCE_NUMBER_COVERAGE_MISMATCH")

    def test_metadata_and_stated_aggregate_abstain(self):
        for source in ("Im Jahr 2024: Amsel 5, Meise 8. Wie hoch ist die Summe?",
                       "Amsel 5, Meise 8. Summe 13. Wie hoch ist die Summe?"):
            with self.subTest(source=source):
                raw = json.dumps({"values": [{"name": "Amsel", "number": 5},
                                             {"name": "Meise", "number": 8}]})
                got = candidate.evaluate(source, raw)
                self.assertEqual(got["status"], "SHADOW_ABSTAIN")
                self.assertEqual(got["reason"], "SOURCE_NUMBER_COVERAGE_MISMATCH")

    def test_unicode_minus_and_explicit_plus(self):
        source = "Werte: Amsel −5, Meise (+8), Drossel 3. Wie hoch ist die Summe?"
        raw = json.dumps({"values": [{"name": "Amsel", "number": -5},
                                     {"name": "Meise", "number": 8},
                                     {"name": "Drossel", "number": 3}]})
        got = candidate.evaluate(source, raw)
        self.assertEqual(got["status"], "SHADOW_RESULT", got)
        self.assertEqual(got["value"], 6)

    def test_question_only_source_or_decimal_fail_closed(self):
        raw = json.dumps({"values": [{"name": "Amsel", "number": 5},
                                     {"name": "Meise", "number": 8}]})
        self.assertEqual(candidate.evaluate("Amsel 5, Meise 8; Summe?", raw)["status"],
                         "SHADOW_ABSTAIN")
        self.assertEqual(candidate.evaluate(
            "Amsel 5, Meise 8, Preis 3,5. Wie hoch ist die Summe?", raw)["status"],
            "SHADOW_ABSTAIN")

    def test_original_abstentions_never_upgraded(self):
        raw = json.dumps({"values": [{"name": "Amsel", "number": 5},
                                     {"name": "Meise", "number": 8}]})
        for source in ("Amsel 5, Meise 8. Wie viele Werte?",
                       "Amsel 5, Meise 8. Bitte keine Summe bilden.",
                       "Amsel 5, Meise 8. Ist die Summe richtig?"):
            with self.subTest(source=source):
                self.assertEqual(baseline.evaluate(source, raw)["status"], "SHADOW_ABSTAIN")
                self.assertEqual(candidate.evaluate(source, raw)["status"], "SHADOW_ABSTAIN")

    def test_no_native_or_live_imports(self):
        self.assertEqual(candidate.AUTHORITY, "SHADOW_ONLY")
        self.assertNotIn("runner", candidate.__dict__)
        self.assertNotIn("toolstep", candidate.__dict__)
        self.assertNotIn("C5", candidate.__dict__)


if __name__ == "__main__":
    unittest.main()
