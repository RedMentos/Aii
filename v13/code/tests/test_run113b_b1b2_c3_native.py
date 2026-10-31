"""Run113B disjoint two-source B1/B2 -> C3 model-free preflight."""
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scripts import run113b_b1b2_c3_native as pilot
from scripts.run111_c3_b2_context_native import score
from v13.common import dumps
from v13.cognition import scaffold_route

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/RUN113B_B1B2_C3_SEED919.json")


class Run113BTwoSource(unittest.TestCase):
    def test_frozen_disjoint_fixture_and_route(self):
        row = pilot.fixture(FIXTURE)
        self.assertEqual(row["project"], "Aster")
        self.assertEqual(row["expected"], "A")
        self.assertEqual(
            scaffold_route("Compare the current options under the earlier policy: "
                           + row["current"]), "both")
        self.assertNotIn("Nova", row["current"])

    def test_fixture_mutation_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "modified.json"
            path.write_bytes(FIXTURE.read_bytes().replace(
                b"139 credits", b"138 credits", 1))
            with self.assertRaisesRegex(ValueError, "FIXTURE_SHA_RED"):
                pilot.fixture(path)

    def test_actual_store_two_source_preflight_no_native(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = pilot.run(FIXTURE, root / "work", root / "evidence")
            self.assertEqual(result["status"],
                             "MODEL_FREE_TWO_SOURCE_PREFLIGHT_PASS",
                             result.get("error"))
            self.assertEqual([x["role"] for x in result["offers"]],
                             ["B2_GIST", "B1_DETAIL", "B2_GIST"])
            self.assertEqual(result["scaffold_route"], "both")
            self.assertTrue(result["b1_current_verified"])
            self.assertTrue(result["b2_prior_verified"])
            self.assertEqual(result["native_body_calls"], 0)
            self.assertEqual(result["native_c3_calls"], 0)
            self.assertFalse(result["native_c2"])
            self.assertFalse(result["native_jef"])
            self.assertTrue(result["synthetic_observers"])
            self.assertTrue(result["no_live_output"])
            self.assertTrue(result["closed_store_ok"])
            self.assertEqual(result["step2_exit"], "EVIDENCE_NOT_PASSING")
            self.assertFalse(result["whole_system_complete"])
            self.assertEqual(result["learning_authority"], 0)
            self.assertEqual(result["delivery_authority"], 0)
            self.assertNotIn('"expected"', dumps(result["c3_messages"]))

    def test_missing_prior_quote_is_structural_red_not_faked(self):
        real = pilot._fake_runner

        def no_prior(row, role, phase):
            if role != "B2_GIST" or phase != "current":
                return real(row, role, phase)
            return SimpleNamespace(
                last_metrics={"status": "FINAL", "synthetic": True},
                generate=lambda *args, **kwargs: iter([dumps({
                    "summary": "Cannot find prior rule.", "quotes": [],
                    "uncertainty": "missing", "needs_reentry": True})]))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(pilot, "_fake_runner", side_effect=no_prior):
                result = pilot.run(FIXTURE, root / "work", root / "evidence")
            self.assertEqual(result["status"], "STRUCTURAL_RED")
            self.assertFalse(result["b2_prior_verified"])
            self.assertEqual(result["native_c3_calls"], 0)
            self.assertTrue(result["no_live_output"])
            self.assertTrue(result["closed_store_ok"])

    def test_strict_receiver_choice(self):
        self.assertEqual(score('{"choice":"A"}', "A")["correct"], 1)
        for text in ('{"choice":"B"}', '{"choice":"A","choice":"B"}',
                     '{"choice":"A","reason":"oracle"}', "A"):
            self.assertEqual(score(text, "A")["correct"], 0)


if __name__ == "__main__":
    unittest.main()
