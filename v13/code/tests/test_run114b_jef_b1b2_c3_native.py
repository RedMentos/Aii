"""Run114B disjoint source-bound JEF + B1/B2 + C3 paired preflight."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run114b_jef_b1b2_c3_native as pilot
from scripts.run47_jef_c3_typed_receiver_native import score
from v13.cognition import Cognition
from v13.common import dumps

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/RUN114B_JEF_B1B2_C3_SEED947.json")


class Run114BJefBodyC3(unittest.TestCase):
    def test_frozen_three_disjoint_projects(self):
        rows = pilot.fixture(FIXTURE)
        self.assertEqual([r["id"] for r in rows],
                         ["Meridian", "Orion", "Zenith"])
        self.assertEqual([r["oracle"]["choice"] for r in rows],
                         ["A", "B", "NONE"])
        self.assertTrue(all(r["prior_quote"] in r["prior"] for r in rows))

    def test_mutated_fixture_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "mutated.json"
            p.write_bytes(FIXTURE.read_bytes().replace(
                b"180 euros", b"181 euros", 1))
            with self.assertRaisesRegex(ValueError, "FIXTURE_SHA_RED"):
                pilot.fixture(p)

    def test_real_store_context_jef_three_projects_preflight(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            result = pilot.run(FIXTURE, root / "work", root / "evidence")
            self.assertEqual(result["status"],
                             "MODEL_FREE_THREE_PROJECT_PREFLIGHT_PASS",
                             [(r["id"], r.get("error")) for r in result["rows"]])
            self.assertEqual(len(result["rows"]), 3)
            self.assertEqual(result["native_body_calls"], 0)
            self.assertEqual(result["native_c3_calls"], 0)
            self.assertTrue(result["synthetic_body_observers"])
            self.assertFalse(result["native_c2"])
            self.assertFalse(result["native_jef_model"])
            self.assertEqual(result["learning_authority"], 0)
            self.assertEqual(result["delivery_authority"], 0)
            self.assertEqual(result["step2_exit"], "EVIDENCE_NOT_PASSING")
            for row in result["rows"]:
                self.assertEqual(row["status"], "MODEL_FREE_PREFLIGHT_PASS")
                self.assertTrue(row["b1_current_verified"])
                self.assertTrue(row["b2_prior_verified"])
                self.assertTrue(row["jef_matches_oracle"])
                self.assertTrue(row["closed_store_ok"])
                self.assertTrue(row["no_live_output"])
                self.assertEqual(len(row["offers"]), 3)
                self.assertEqual(len(row["arms"]), 2)
                by_arm = {x["arm"]: x for x in row["arms"]}
                self.assertEqual(set(by_arm), set(pilot.ARMS))
                self.assertNotEqual(
                    by_arm["RAW_BODY"]["messages_sha256"],
                    by_arm["TYPED_JEF"]["messages_sha256"])
                raw = dumps(by_arm["RAW_BODY"]["messages"])
                typed = dumps(by_arm["TYPED_JEF"]["messages"])
                self.assertNotIn("typed_jef_candidate", raw)
                self.assertIn("Source-verified zero-authority typed JEF", typed)
                self.assertNotIn('"oracle"', raw + typed)

    def test_new_authoritative_user_correction_blocks_old_case(self):
        original = Cognition.offer
        fired = []

        def correction(self, role, event, *args, **kwargs):
            result = original(self, role, event, *args, **kwargs)
            if (role == "B2_GIST" and not fired
                    and "Meridian. Apply" in self.s.read_source(
                        event["source_ref"])):
                self.r.store.event(
                    self.r.session,
                    "Project Meridian. New binding USER correction: all options revoked.")
                fired.append(True)
            return result

        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            with patch.object(Cognition, "offer", correction):
                report = pilot.run(FIXTURE, root / "work", root / "evidence")
            self.assertEqual(fired, [True])
            self.assertEqual(report["status"], "STRUCTURAL_RED")
            self.assertEqual(report["rows"][0]["status"], "STRUCTURAL_RED")
            self.assertTrue(report["rows"][0]["closed_store_ok"])
            self.assertTrue(report["rows"][0]["no_live_output"])
            self.assertEqual(report["native_c3_calls"], 0)

    def test_strict_choice_remaining_score(self):
        self.assertEqual(score('{"choice":"A","remaining":4}',
                               {"choice": "A", "remaining": 4})["correct"], 1)
        for raw in ('{"choice":"A","remaining":5}',
                    '{"choice":"A","remaining":4,"extra":true}',
                    '{"choice":"A","choice":"B","remaining":4}',
                    '{"choice":"A","remaining":false}', "A"):
            self.assertEqual(score(raw, {"choice": "A", "remaining": 4})["correct"], 0)


if __name__ == "__main__":
    unittest.main()
