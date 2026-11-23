"""Seed59 simple-scaffold native route experiment: software-only guards."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import c2_simple_scaffold_native_seed59_20261030 as m
from scripts import c2_body_controlled_utility_seed53_20261030 as base
from v13.cognition import scaffold_route


class SimpleScaffoldSoftware(unittest.TestCase):
    def sample(self, route, source, role):
        info = {"source": source}
        if source != "OPERATOR_ROUTE_OVERRIDE":
            info["native_control_metrics"] = {"memory": {"pid": 4321}}
        roles = base.expected_roles(route)
        return ({"checks": {"source_refs_valid": True, "final_output": True},
                 "source_errors": [], "offers": [{"role": r} for r in roles],
                 "output": "Citrine: 375 - 218 = 157\nSparrow: 375 - 332 = 43",
                 "output_metadata": {"route": info, "c2_packet": {"route": route},
                                     "runner": {"role": role,
                                                "actual_model": base.LANGUAGE_MODEL if role == "C3_LANGUAGE"
                                                else base.GIST_MODEL if role == "B2_GIST"
                                                else base.BODY_MODEL},
                                     "model_generated": True}},
                [{"role": r, "process_reaped": True} for r in roles])

    def test_four_frozen_unseen_simple_prompts(self):
        self.assertEqual(m.SEED, 59)
        self.assertTrue(m.validate_fixtures())
        self.assertEqual(m.fixture_hash(), m.FIXTURE_SHA256)
        self.assertEqual(len(m.FIXTURES), 4)
        for f in m.FIXTURES:
            self.assertEqual(scaffold_route(m.prompt(f)), "simple")
            self.assertIn("no cloud", m.prompt(f))
            self.assertNotIn("Compare options", m.prompt(f))

    def test_cyclic_twelve_arms(self):
        self.assertEqual(len(m.ARM_ORDER), 4)
        self.assertEqual(sum(len(x) for x in m.ARM_ORDER), 12)
        for order in m.ARM_ORDER:
            self.assertEqual(set(order), set(m.ARMS))

    def test_answer_leak_rejected(self):
        fs = list(m.FIXTURES)
        f = dict(fs[0])
        f["b_cost"] = f["budget"] - f["a_cost"]
        fs[0] = f
        with patch.object(m, "FIXTURES", tuple(fs)):
            with patch.object(m, "FIXTURE_SHA256", m.fixture_hash()):
                with self.assertRaisesRegex(ValueError, "ANSWER_LEAKED_IN_PROMPT"):
                    m.validate_fixtures()

    def test_non_simple_scaffold_rejected(self):
        fs = list(m.FIXTURES)
        f = dict(fs[0])
        f["project"] = "Compare"
        fs[0] = f
        with patch.object(m, "FIXTURES", tuple(fs)):
            with patch.object(m, "FIXTURE_SHA256", m.fixture_hash()):
                with self.assertRaisesRegex(ValueError, "SCAFFOLD_NOT_SIMPLE"):
                    m.validate_fixtures()

    def test_exact_option_source_score(self):
        self.assertEqual(m.score_pair(m.FIXTURES[0],
                         "Citrine: 375 - 218 = 157\nSparrow: 375 - 332 = 43")["correct"], 2)
        self.assertEqual(m.score_pair(m.FIXTURES[0],
                         "Citrine costs 218 Euro; Sparrow costs 332 Euro.")["correct"], 0)

    def test_forced_simple_and_both_are_not_native_c2(self):
        a, release = self.sample("simple", "OPERATOR_ROUTE_OVERRIDE", "C3_LANGUAGE")
        fa = m.row_evidence(a, m.EVIDENCE_ARM["A_FORCED_SIMPLE"], release)
        self.assertTrue(fa["valid_native"])
        self.assertFalse(fa["native_c2_invocation"])
        c, release = self.sample("both", "OPERATOR_ROUTE_OVERRIDE", "B1_DETAIL")
        fc = m.row_evidence(c, m.EVIDENCE_ARM["C_FORCED_BOTH"], release)
        self.assertTrue(fc["valid_native"])
        self.assertFalse(fc["native_c2_selected"])

    def test_native_c2_selected_on_simple_scaffold(self):
        audit, releases = self.sample("detail", "NATIVE_C2_ADVISORY", "B1_DETAIL")
        with patch.object(base, "valid_control_evidence", return_value=True):
            f = m.row_evidence(audit, m.EVIDENCE_ARM["B_NATIVE_AUTO"], releases,
                               native_context={"query_ref": {"source_id": "s"}},
                               native_alive=True, native_reaped=True, native_pid=4321,
                               source_exact=True, session="session", event_id="event",
                               source_text="source")
        self.assertTrue(f["native_c2_invocation"])
        self.assertTrue(f["native_c2_selected"])
        self.assertTrue(f["valid_native"])
        self.assertEqual(f["route"], "detail")

    def test_native_c2_invoked_but_not_selected(self):
        audit, releases = self.sample("simple", "BOOT_SCAFFOLD", "C3_LANGUAGE")
        with patch.object(base, "valid_control_evidence", return_value=True):
            f = m.row_evidence(audit, m.EVIDENCE_ARM["B_NATIVE_AUTO"], releases,
                               native_context={"query_ref": {"source_id": "s"}},
                               native_alive=True, native_reaped=True, native_pid=4321,
                               source_exact=True, session="session", event_id="event",
                               source_text="source")
        self.assertTrue(f["native_c2_invocation"])
        self.assertFalse(f["native_c2_selected"])
        self.assertTrue(f["valid_native"])

    def test_native_pid_or_source_mismatch_veto(self):
        audit, releases = self.sample("detail", "NATIVE_C2_ADVISORY", "B1_DETAIL")
        with patch.object(base, "valid_control_evidence", return_value=True):
            f = m.row_evidence(audit, m.EVIDENCE_ARM["B_NATIVE_AUTO"], releases,
                               native_context={"query_ref": {"source_id": "s"}},
                               native_alive=True, native_reaped=True, native_pid=999,
                               source_exact=True, session="session", event_id="event",
                               source_text="source")
        self.assertFalse(f["valid_native"])
        self.assertFalse(f["native_c2_selected"])

    def test_pilot_signal_requires_selection_and_gain(self):
        t = {"A_FORCED_SIMPLE": 1, "B_NATIVE_AUTO": 3, "C_FORCED_BOTH": 3}
        self.assertTrue(m.pilot_signal(t, True, 1))
        self.assertFalse(m.pilot_signal(t, True, 0))
        self.assertFalse(m.pilot_signal(t, False, 1))
        self.assertFalse(m.pilot_signal({**t, "C_FORCED_BOTH": 4}, True, 1))
        self.assertFalse(m.pilot_signal({**t, "B_NATIVE_AUTO": 9}, True, 1))

    def test_existing_output_directory_refused(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileExistsError):
                m.run(Path(td), Path(td))


if __name__ == "__main__":
    unittest.main()
