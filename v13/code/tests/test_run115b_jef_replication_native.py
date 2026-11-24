"""Run115B six-case preregistered replication model-free preflight."""
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run115b_jef_replication_native as pilot
from scripts import run114b_jef_b1b2_c3_native as parent
from v13.cognition import Cognition
from v13.common import dumps

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/RUN115B_JEF_B1B2_C3_SEED971.json")


class Run115BReplication(unittest.TestCase):
    def test_frozen_six_disjoint_two_grammar_cohort(self):
        rows = pilot.fixture(FIXTURE)
        self.assertEqual([x["id"] for x in rows], list(pilot.IDS))
        self.assertEqual([x["oracle"]["choice"] for x in rows],
                         ["A", "B", "NONE", "B", "A", "NONE"])
        self.assertTrue(any("Spending limit:" in x["prior"] for x in rows))
        self.assertTrue(any("Budget " in x["prior"] for x in rows))
        self.assertTrue(any("Local-only requirement: false" in x["prior"]
                            for x in rows))
        self.assertEqual(parent.SEED, 947)
        self.assertEqual(sha256(Path(parent.__file__).read_bytes()).hexdigest(),
                         pilot.PARENT_PIPELINE_SHA)

    def test_frozen_fixture_mutation_red(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "bad.json"
            p.write_bytes(FIXTURE.read_bytes().replace(
                b"160 euros", b"161 euros", 1))
            with self.assertRaisesRegex(ValueError, "FIXTURE_SHA_RED"):
                pilot.fixture(p)

    def test_six_real_stores_twelve_source_plans_no_native(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            result = pilot.run(FIXTURE, root / "work", root / "evidence")
            self.assertEqual(result["status"],
                             "MODEL_FREE_SIX_PROJECT_PREFLIGHT_PASS",
                             [(x["id"], x.get("error")) for x in result["rows"]])
            self.assertEqual(parent.SEED, 947)
            self.assertEqual(result["native_body_calls"], 0)
            self.assertEqual(result["native_c3_calls"], 0)
            self.assertTrue(result["synthetic_body_observers"])
            self.assertFalse(result["native_c2"])
            self.assertFalse(result["native_jef_model"])
            self.assertEqual(result["step2_exit"], "EVIDENCE_NOT_PASSING")
            self.assertEqual(len(result["rows"]), 6)
            for row in result["rows"]:
                self.assertTrue(row["b1_current_verified"])
                self.assertTrue(row["b2_prior_verified"])
                self.assertTrue(row["jef_matches_oracle"])
                self.assertTrue(row["closed_store_ok"])
                self.assertTrue(row["no_live_output"])
                self.assertEqual(row["status"], "MODEL_FREE_PREFLIGHT_PASS")
                self.assertEqual(len(row["offers"]), 3)
                self.assertEqual(len(row["arms"]), 2)
                self.assertEqual(set(a["arm"] for a in row["arms"]),
                                 set(pilot.ARMS))
                for arm in row["arms"]:
                    self.assertNotIn('"oracle"', dumps(arm["messages"]))

    def test_later_authoritative_user_correction_vetoes_old_case(self):
        original = Cognition.offer
        fired = []

        def inject(self, role, event, *args, **kwargs):
            result = original(self, role, event, *args, **kwargs)
            if (role == "B2_GIST" and not fired
                    and "Lumen. Apply" in self.s.read_source(
                        event["source_ref"])):
                self.r.store.event(
                    self.r.session,
                    "Project Lumen. Binding USER correction: all options cancelled.")
                fired.append(True)
            return result

        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            with patch.object(Cognition, "offer", inject):
                report = pilot.run(FIXTURE, root / "work", root / "evidence")
            self.assertEqual(fired, [True])
            self.assertEqual(report["status"], "STRUCTURAL_RED")
            self.assertEqual(report["rows"][0]["status"], "STRUCTURAL_RED")
            self.assertTrue(report["rows"][0]["closed_store_ok"])
            self.assertTrue(report["rows"][0]["no_live_output"])
            self.assertEqual(report["native_c3_calls"], 0)
            self.assertEqual(parent.SEED, 947)

    def test_parent_strict_scorer_not_modified(self):
        self.assertEqual(parent.score('{"choice":"B","remaining":10}',
                                      {"choice":"B","remaining":10})["correct"], 1)
        self.assertEqual(parent.score('{"choice":"B","remaining":9}',
                                      {"choice":"B","remaining":10})["correct"], 0)


if __name__ == "__main__":
    unittest.main()
