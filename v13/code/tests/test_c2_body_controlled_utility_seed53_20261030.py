"""Adversarial software-only seed53 controls; never native proof."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import c2_body_controlled_utility_seed53_20261030 as m


class ControlledUtilitySoftware(unittest.TestCase):
    def sample(self, route="both", source="OPERATOR_ROUTE_OVERRIDE", role="B1_DETAIL"):
        offers = [{"role": k} for k in m.expected_roles(route)]
        audit = {"checks": {"source_refs_valid": True, "final_output": True},
                 "source_errors": [], "offers": offers,
                 "output": "Option Sable: 382 - 241 = 141\nOption Tern: 382 - 317 = 65",
                 "output_metadata": {"route": {"source": source},
                                     "c2_packet": {"route": route},
                                     "runner": {"role": role,
                                                "actual_model": m.LANGUAGE_MODEL if role == "C3_LANGUAGE" else m.BODY_MODEL},
                                     "model_generated": True}}
        releases = [{"role": k, "process_reaped": True} for k in m.expected_roles(route)]
        return audit, releases

    def test_frozen_fixtures_and_cyclic_24_arms(self):
        self.assertTrue(m.validate_fixtures())
        self.assertEqual(m.fixture_hash(), m.FIXTURE_SHA256)
        self.assertEqual(m.SEED, 53)
        self.assertEqual(len(m.ARM_ORDER), 4)
        self.assertEqual(sum(len(a) for a in m.ARM_ORDER), 24)
        for order in m.ARM_ORDER:
            self.assertEqual(set(order), set(m.ARMS))

    def test_source_answer_leak_detected_with_digit_boundaries(self):
        fixtures = list(m.FIXTURES)
        f = dict(fixtures[0])
        f["b_cost"] = f["budget"] - f["a_cost"]
        fixtures[0] = f
        with patch.object(m, "FIXTURES", tuple(fixtures)):
            with patch.object(m, "FIXTURE_SHA256", m.fixture_hash()):
                with self.assertRaisesRegex(ValueError, "ANSWER_LEAKED_IN_SOURCE"):
                    m.validate_fixtures()

    def test_exact_equations_accepted_with_source_operands(self):
        f = m.FIXTURES[0]
        answer = "Sable: 382 - 241 = 141\nTern: 382 - 317 = 65"
        score = m.score_pair(f, answer)
        self.assertEqual(score["correct"], 2)
        self.assertTrue(score["a"] and score["b"])

    def test_wrong_equation_or_ambiguous_line_veto(self):
        f = m.FIXTURES[0]
        wrong = "Sable: 382 - 241 = 141\nSable: 382 - 241 = 140\nTern: 382 - 317 = 65"
        self.assertFalse(m.score_pair(f, wrong)["a"])
        ambiguous = "Sable Tern: 382 - 241 = 141\nTern: 382 - 317 = 65"
        self.assertFalse(m.score_pair(f, ambiguous)["a"])

    def test_cost_echo_not_correct(self):
        f = m.FIXTURES[0]
        self.assertEqual(m.score_pair(f, "Sable 241 Euro. Tern 317 Euro.")["correct"], 0)

    def test_forced_dual_requires_both_offers_and_reaping(self):
        audit, releases = self.sample()
        good = m.row_evidence(audit, "D_DISTINCT_BOTH", releases)
        self.assertTrue(good["valid_native"])
        self.assertFalse(good["native_c2_invocation"])
        self.assertFalse(good["native_c2_selected"])
        self.assertEqual(good["body_offer_roles"], ["B1_DETAIL", "B2_GIST"])
        bad = m.row_evidence(audit, "D_DISTINCT_BOTH",
                             [{**releases[0], "process_reaped": False}, releases[1]])
        self.assertFalse(bad["valid_native"])
        audit["offers"].pop()
        self.assertFalse(m.row_evidence(audit, "D_DISTINCT_BOTH", releases)["valid_native"])

    def test_forced_single_role_and_wrong_runner(self):
        audit, releases = self.sample(route="detail", role="B1_DETAIL")
        self.assertTrue(m.row_evidence(audit, "B_B1_ONLY", releases)["valid_native"])
        self.assertFalse(m.row_evidence(audit, "C_B2_ONLY", releases)["valid_native"])
        audit["output_metadata"]["runner"]["role"] = "C3_LANGUAGE"
        self.assertFalse(m.row_evidence(audit, "B_B1_ONLY", releases)["valid_native"])

    def test_auto_invocation_not_selection(self):
        audit, releases = self.sample(source="BOOT_SCAFFOLD")
        context = {"query_ref": {"source_id": "synthetic"}}
        with patch.object(m, "valid_control_evidence", return_value=True):
            flags = m.row_evidence(audit, "F_NATIVE_AUTO", releases,
                                   native_context=context, native_alive=True,
                                   native_reaped=True, source_exact=True,
                                   session="chat_1", event_id="event_1", source_text="synthetic")
            self.assertTrue(flags["native_c2_invocation"])
            self.assertFalse(flags["native_c2_selected"])
            self.assertTrue(flags["valid_native"])
            audit["output_metadata"]["route"]["source"] = "NATIVE_C2_ADVISORY"
            selected = m.row_evidence(audit, "F_NATIVE_AUTO", releases,
                                      native_context=context, native_alive=True,
                                      native_reaped=True, source_exact=True,
                                      session="chat_1", event_id="event_1", source_text="synthetic")
            self.assertTrue(selected["native_c2_selected"])
            missing = m.row_evidence(audit, "F_NATIVE_AUTO", releases,
                                     native_context=context, native_alive=True,
                                     native_reaped=False, source_exact=True,
                                     session="chat_1", event_id="event_1", source_text="synthetic")
            self.assertFalse(missing["valid_native"])
            self.assertFalse(missing["native_c2_invocation"])

    def test_auto_forged_native_rejected(self):
        audit, releases = self.sample(source="NATIVE_C2_ADVISORY")
        with patch.object(m, "valid_control_evidence", return_value=False):
            flags = m.row_evidence(audit, "F_NATIVE_AUTO", releases,
                                   native_context={"query_ref": {"source_id": "synthetic"}},
                                   native_alive=True, native_reaped=True,
                                   source_exact=True, session="s", event_id="e",
                                   source_text="synthetic")
        self.assertFalse(flags["native_c2_invocation"])
        self.assertFalse(flags["native_c2_selected"])
        self.assertFalse(flags["valid_native"])

    def test_pilot_signal_requires_valid_and_2_point_gain(self):
        t = {arm: 1 for arm in m.ARMS}
        t["D_DISTINCT_BOTH"] = 3
        self.assertTrue(m.pilot_signal(t, True))
        self.assertFalse(m.pilot_signal(t, False))
        self.assertFalse(m.pilot_signal({**t, "A_C3_ONLY": 2}, True))
        self.assertFalse(m.pilot_signal({**t, "A_C3_ONLY": 9}, True))
        self.assertFalse(m.pilot_signal({**t, "F_NATIVE_AUTO": True}, True))

    def test_existing_output_directory_fails_before_native(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileExistsError):
                m.run(Path(td), Path(td))


if __name__ == "__main__":
    unittest.main()
