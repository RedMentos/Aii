"""Run11V seed181 preregistered software-only native runner contracts."""
from __future__ import annotations

import inspect
from pathlib import Path
import re
import tempfile
import unittest

from scripts import c2_body_disjoint_paired181_run11v as m
from scripts import c2_body_observer_closed_run11r as frozen


class DisjointPaired181Run11V(unittest.TestCase):
    def test_new_frozen_fixture_hash_and_source_no_answer_leak(self):
        self.assertEqual(m.SEED, 181)
        self.assertEqual(m.fixture_hash(),
                         "ae4799f60316cf51412d228547662de8cb4b6523dedffd5fc02b2862d84477e3")
        self.assertTrue(m.validate_fixtures())
        self.assertEqual([f["project"] for f in m.FIXTURES],
                         ["Aurora181", "Beacon181", "Cobalt181", "Delta181"])
        self.assertTrue({f["project"] for f in m.FIXTURES}.isdisjoint(
            {f["project"] for f in frozen.FIXTURES}))
        for f in m.FIXTURES:
            source = m.prompt(f)
            self.assertEqual(m.scaffold_route(source), "simple")
            self.assertIn("Everything stays local on my device; no cloud.", source)
            for value in (f["budget"] - f["a_cost"],
                          f["budget"] - f["b_cost"]):
                self.assertIsNone(re.search(rf"(?<!\d){value}(?!\d)", source))

    def test_six_arms_and_counterbalanced_24_turn_order(self):
        self.assertEqual(m.ARMS, frozen.ARMS)
        self.assertEqual(m.ARM_ORDER, frozen.ARM_ORDER)
        self.assertEqual(len(m.ARMS), 6)
        self.assertEqual(len(m.FIXTURES) * len(m.ARMS), 24)
        for order in m.ARM_ORDER:
            self.assertEqual(set(order), set(m.ARMS))
            self.assertEqual(len(order), 6)

    def test_frozen_scorers_are_not_modified(self):
        f = m.FIXTURES[0]
        output = ("Fern: 396 - 243 = 153 Euro remaining.\n"
                  "Slate: 396 - 352 = 44 Euro remaining.")
        self.assertEqual(m.score_pair(f, output),
                         frozen.score_pair(f, output))
        self.assertEqual(m.score_primary(f, output),
                         frozen.score_primary(f, output))
        pair = m.score_pair(f, output)
        self.assertEqual(pair["correct"], 2)
        self.assertEqual(pair["equation"]["a"]["status"], "CORRECT")
        self.assertEqual(pair["equation"]["b"]["status"], "CORRECT")

    def test_precommitted_primary_secondary_positions_in_runner(self):
        code = inspect.getsource(m.fresh_turn)
        self.assertIn('record["score"] = (score_pair(', code)
        self.assertIn('record["secondary_score"] = (score_primary(', code)
        self.assertIn('release_capture_phase"] = "after_close"', code)
        self.assertIn('runtime.close()', code)

    def test_equation_contradiction_is_not_a_free_point(self):
        f = m.FIXTURES[0]
        correct = ("Fern: 396 - 243 = 153 Euro remaining.\n"
                   "Slate: 396 - 352 = 44 Euro remaining.")
        wrong = ("Fern: 396 - 243 = 154 Euro remaining.\n"
                 "Slate: 396 - 352 = 44 Euro remaining.")
        self.assertEqual(m.score_pair(f, correct)["correct"], 2)
        self.assertEqual(m.score_pair(f, wrong)["a"], False)
        self.assertEqual(m.score_pair(f, wrong)["b"], True)

    def test_no_native_flags_from_synthetic_c2_or_missing_release(self):
        f = m.FIXTURES[0]
        audit = {
            "output": "Fern: 153 Euro remaining.",
            "checks": {"source_refs_valid": True},
            "source_errors": [],
            "offers": [],
            "output_metadata": {
                "route": {"source": "OPERATOR_ROUTE_OVERRIDE"},
                "c2_packet": {"route": "simple"},
                "runner": {"role": "C3_LANGUAGE",
                           "actual_model": m.LANGUAGE_MODEL},
                "model_generated": True,
            },
        }
        flags = m.row_evidence(audit, "A_C3_ONLY", [])
        self.assertFalse(flags["valid_native"])
        self.assertFalse(flags["process_release_valid"])
        self.assertFalse(flags["native_c2_invocation"])
        flags = m.row_evidence(audit, "A_C3_ONLY", [
            {"role": "C3_LANGUAGE", "process_reaped": True}],
            release_capture_phase="after_close")
        self.assertTrue(flags["valid_native"])  # synthetic protocol, NOT native proof
        self.assertFalse(flags["native_c2_invocation"])

    def test_pilot_signals_never_promote_any_gate(self):
        totals = {a: 0 for a in m.ARMS}
        self.assertFalse(m.pilot_signal(totals, False))
        totals["D_DISTINCT_BOTH"] = 3
        self.assertTrue(m.pilot_signal(totals, True))
        totals["E_SHARED_DUAL_COLD"] = 2
        self.assertFalse(m.pilot_signal(totals, True))

    def test_existing_output_directory_refused_before_native(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            out = root / "pilot"
            out.mkdir()
            with self.assertRaisesRegex(FileExistsError,
                                        "FRESH_OUTPUT_DIRECTORY_REQUIRED"):
                m.run(root, out)


if __name__ == "__main__":
    unittest.main()
