"""Run11R adversarial software-only evidence checks; never native proof."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import c2_body_observer_closed_run11r as m
from v13.models import model_key


class ObserverClosedRun11R(unittest.TestCase):
    def sample(self, route="both", arm="D_DISTINCT_BOTH",
               source="OPERATOR_ROUTE_OVERRIDE", role="B1_DETAIL",
               shared=False, offers=None, releases=None):
        if offers is None:
            offers = ([] if arm in ("A_C3_ONLY", "B_B1_ONLY", "C_B2_ONLY")
                      else sorted(m.expected_roles(route)))
        if releases is None:
            releases = sorted(m.expected_roles(route))
        route_info = {"source": source}
        if source != "OPERATOR_ROUTE_OVERRIDE":
            route_info["native_control_metrics"] = {"memory": {"pid": 1234}}
        model = (m.LANGUAGE_MODEL if role == "C3_LANGUAGE" else
                 m.GIST_MODEL if role == "B2_GIST" and not shared
                 else m.BODY_MODEL)
        audit = {
            "checks": {"source_refs_valid": True, "final_output": True},
            "source_errors": [], "offers": [{"role": x} for x in offers],
            "output": "Cedar: 149 Euro remaining. Garnet: 41 Euro remaining.",
            "output_metadata": {
                "route": route_info, "c2_packet": {"route": route},
                "runner": {"role": role, "actual_model": model},
                "model_generated": True,
            },
        }
        receipts = [{"role": x, "process_reaped": True} for x in releases]
        return audit, receipts

    def test_preregistered_disjoint_fixture_and_scaffold(self):
        self.assertTrue(m.validate_fixtures())
        self.assertEqual(m.SEED, 163)
        self.assertEqual(m.fixture_hash(), m.FIXTURE_SHA256)
        self.assertEqual(len(m.FIXTURES), 4)
        self.assertEqual(len(m.ARMS), 6)
        self.assertEqual(sum(map(len, m.ARM_ORDER)), 24)
        self.assertEqual({a for order in m.ARM_ORDER for a in order}, set(m.ARMS))

    def test_answer_leak_and_scaffold_preflight_fail_closed(self):
        with patch.object(m, "scaffold_route", return_value="both"):
            with self.assertRaisesRegex(ValueError, "SCAFFOLD_NOT_SIMPLE"):
                m.validate_fixtures()
        fixtures = list(m.FIXTURES)
        f = dict(fixtures[0])
        f["b_cost"] = f["budget"] - f["a_cost"]
        fixtures[0] = f
        with patch.object(m, "FIXTURES", tuple(fixtures)):
            with patch.object(m, "FIXTURE_SHA256", m.fixture_hash()):
                with self.assertRaisesRegex(ValueError, "ANSWER_LEAKED_IN_SOURCE"):
                    m.validate_fixtures()

    def test_frozen_run11q_primary_claims_and_conflicts(self):
        f = m.FIXTURES[0]
        correct = "Cedar: 149 Euro remaining. Garnet: 41 Euro remaining."
        self.assertEqual(m.score_primary(f, correct)["correct"], 2)
        self.assertEqual(m.score_primary(f, "Cedar costs 219 Euro; Garnet costs 327 Euro.")["correct"], 0)
        swapped = m.score_primary(f, "Cedar: 41 Euro remaining. Garnet: 149 Euro remaining.")
        self.assertEqual(swapped["correct"], 0)
        conflict = m.score_primary(f, "Cedar: 149 Euro remaining. Cedar: 150 Euro remaining.")
        self.assertEqual(conflict["correct"], 0)
        self.assertEqual(conflict["source_bound"]["a"]["status"], "CONTRADICTORY_CLAIMS")

    def test_single_body_observer_off_valid_after_close(self):
        for arm, route, role in (
            ("B_B1_ONLY", "detail", "B1_DETAIL"),
            ("C_B2_ONLY", "gist", "B2_GIST"),
        ):
            audit, receipts = self.sample(route, arm, role=role)
            flags = m.row_evidence(audit, arm, receipts)
            self.assertTrue(flags["valid_native"], flags)
            self.assertEqual(flags["body_offer_roles"], [])
            self.assertEqual(flags["release_capture_phase"], "after_close")
            self.assertEqual(flags["expected_offer_roles"], [])

    def test_single_body_rejects_observer_contamination(self):
        audit, receipts = self.sample("detail", "B_B1_ONLY", role="B1_DETAIL",
                                      offers=["B1_DETAIL", "B2_GIST"],
                                      releases=["B1_DETAIL", "B2_GIST"])
        flags = m.row_evidence(audit, "B_B1_ONLY", receipts)
        self.assertFalse(flags["valid_native"])
        self.assertFalse(flags["process_release_valid"])

    def test_preclose_release_not_a_proof(self):
        audit, receipts = self.sample("gist", "C_B2_ONLY", role="B2_GIST")
        self.assertFalse(m.row_evidence(
            audit, "C_B2_ONLY", receipts,
            release_capture_phase="before_close")["valid_native"])

    def test_postclose_missing_unreaped_and_wrong_role_fail(self):
        audit, receipts = self.sample("detail", "B_B1_ONLY", role="B1_DETAIL")
        self.assertFalse(m.row_evidence(audit, "B_B1_ONLY", [])["valid_native"])
        self.assertFalse(m.row_evidence(audit, "B_B1_ONLY",
                         [{"role": "B1_DETAIL", "process_reaped": False}])["valid_native"])
        self.assertFalse(m.row_evidence(audit, "B_B1_ONLY",
                         [{"role": "B2_GIST", "process_reaped": True}])["valid_native"])

    def test_c3_only_no_body_process_or_offer(self):
        audit, receipts = self.sample("simple", "A_C3_ONLY",
                                      role="C3_LANGUAGE", releases=[])
        self.assertTrue(m.row_evidence(audit, "A_C3_ONLY", receipts)["valid_native"])
        self.assertFalse(m.row_evidence(audit, "A_C3_ONLY",
                         [{"role": "B1_DETAIL", "process_reaped": True}])["valid_native"])

    def test_distinct_both_requires_two_offers_and_releases(self):
        audit, receipts = self.sample()
        self.assertTrue(m.row_evidence(audit, "D_DISTINCT_BOTH", receipts)["valid_native"])
        audit["offers"].pop()
        self.assertFalse(m.row_evidence(audit, "D_DISTINCT_BOTH", receipts)["valid_native"])
        audit, receipts = self.sample()
        receipts[1]["process_reaped"] = False
        self.assertFalse(m.row_evidence(audit, "D_DISTINCT_BOTH", receipts)["valid_native"])

    def test_b2_distinct_qwen_and_shared_cold_model(self):
        self.assertNotEqual(model_key("B1_DETAIL", "two_body"),
                            model_key("B2_GIST", "two_body"))
        self.assertEqual(model_key("B1_DETAIL", "shared_body_dual_state"),
                         model_key("B2_GIST", "shared_body_dual_state"))
        audit, receipts = self.sample(role="B2_GIST")
        self.assertTrue(m.row_evidence(audit, "D_DISTINCT_BOTH", receipts)["valid_native"])
        shared, receipts = self.sample(role="B2_GIST", shared=True)
        self.assertTrue(m.row_evidence(shared, "E_SHARED_DUAL_COLD", receipts)["valid_native"])
        self.assertFalse(m.row_evidence(shared, "D_DISTINCT_BOTH", receipts)["valid_native"])

    def test_auto_native_invocation_not_selected_route(self):
        context = {"query_ref": {"source_id": "synthetic"}}
        audit, receipts = self.sample(route="simple", arm="F_NATIVE_AUTO",
                                      source="BOOT_SCAFFOLD", role="C3_LANGUAGE",
                                      offers=[], releases=[])
        with patch.object(m, "valid_control_evidence", return_value=True):
            kw = dict(native_context=context, native_alive=True, native_reaped=True,
                      native_pid=1234, source_exact=True, session="s", event_id="e",
                      source_text="synthetic")
            flags = m.row_evidence(audit, "F_NATIVE_AUTO", receipts, **kw)
            self.assertTrue(flags["native_c2_invocation"])
            self.assertFalse(flags["native_c2_selected"])
            audit["output_metadata"]["route"]["source"] = "NATIVE_C2_ADVISORY"
            flags = m.row_evidence(audit, "F_NATIVE_AUTO", receipts, **kw)
            self.assertFalse(flags["native_c2_selected"])  # same simple route
            audit["output_metadata"]["c2_packet"]["route"] = "both"
            audit["offers"] = [{"role": "B1_DETAIL"}, {"role": "B2_GIST"}]
            audit["output_metadata"]["runner"] = {
                "role": "B1_DETAIL", "actual_model": m.BODY_MODEL}
            receipts = [{"role": x, "process_reaped": True}
                        for x in ("B1_DETAIL", "B2_GIST")]
            flags = m.row_evidence(audit, "F_NATIVE_AUTO", receipts, **kw)
            self.assertTrue(flags["native_c2_selected"])
            self.assertTrue(flags["valid_native"])
            kw["native_reaped"] = False
            self.assertFalse(m.row_evidence(audit, "F_NATIVE_AUTO", receipts, **kw)["valid_native"])

    def test_auto_wrong_pid_or_forged_native_rejected(self):
        audit, receipts = self.sample(source="NATIVE_C2_ADVISORY")
        context = {"query_ref": {"source_id": "synthetic"}}
        with patch.object(m, "valid_control_evidence", return_value=True):
            flags = m.row_evidence(audit, "F_NATIVE_AUTO", receipts,
                native_context=context, native_alive=True, native_reaped=True,
                native_pid=9999, source_exact=True, session="s", event_id="e",
                source_text="synthetic")
        self.assertFalse(flags["native_c2_invocation"])
        self.assertFalse(flags["valid_native"])

    def test_missing_source_or_model_proof_fails(self):
        audit, receipts = self.sample()
        audit.pop("source_errors")
        self.assertFalse(m.row_evidence(audit, "D_DISTINCT_BOTH", receipts)["valid_native"])
        audit, receipts = self.sample()
        audit["output_metadata"]["runner"]["actual_model"] = "UNPINNED"
        self.assertFalse(m.row_evidence(audit, "D_DISTINCT_BOTH", receipts)["valid_native"])

    def test_pilot_signal_not_a_gate(self):
        totals = {a: 1 for a in m.ARMS}
        totals["D_DISTINCT_BOTH"] = 3
        self.assertTrue(m.pilot_signal(totals, True))
        self.assertFalse(m.pilot_signal(totals, False))
        self.assertFalse(m.pilot_signal({**totals, "B_B1_ONLY": 2}, True))
        self.assertFalse(m.pilot_signal({**totals, "A_C3_ONLY": 9}, True))

    def test_existing_directory_fails_without_native(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileExistsError):
                m.run(Path(d), Path(d))


if __name__ == "__main__":
    unittest.main()
