"""STEP2 long-note runner: reversible control binding, no native execution."""
import contextlib
import io
import json
import unittest
from unittest.mock import patch

from scripts import step2_z2b_seeds as z2b
z2 = z2b.z2
from scripts import step2_longnote_runner_preflight as run


class LongNoteRunnerPreflight(unittest.TestCase):
    def test_four_arms_and_new_seeds_have_distinct_registered_controls(self):
        self.assertEqual(run.SEEDS, (27, 28, 29))
        self.assertTrue(set(run.SEEDS).isdisjoint({13, 14, 15, 16, 17, 18, 19}))
        self.assertEqual(set(run.ARMS), {"TC", "TP", "SC", "SP"})
        for arm in run.ARMS:
            for seed in run.SEEDS:
                with self.subTest(arm=arm, seed=seed):
                    s = run.candidate_settings(arm, seed)
                    self.assertEqual(s["seed"], seed)
                    self.assertEqual(s["b2_quote_select"],
                                     "pointer" if arm.endswith("P") else "off")
                    self.assertEqual(s["b2_control"],
                                     "two_body" if arm.startswith("T")
                                     else "shared_body_dual_state")
                    self.assertFalse(s["b2_offer_body_state"])
                    self.assertEqual(s["offer_quote_context_chars"], 200)
                    self.assertEqual(s["b1_recent_source_chars"], 600)
        for arm, seed in (("X", 27), ("TP", 17), ("TP", True)):
            with self.assertRaises(ValueError):
                run.candidate_settings(arm, seed)

    def test_context_restores_original_objects_even_after_exception(self):
        self.assertIs(run.z2, z2b.z2)
        originals = (z2.FIXTURES, z2b.ARMS, z2b.SEEDS, z2b.settings)
        with self.assertRaisesRegex(RuntimeError, "injected"):
            with run.configured():
                self.assertEqual(tuple(z2b.SEEDS), run.SEEDS)
                self.assertEqual(len(z2.FIXTURES), 10)
                self.assertIs(z2b.z2.FIXTURES, z2.FIXTURES)
                self.assertEqual(set(z2b.ARMS), set(run.ARMS))
                self.assertTrue(all(z2b.ARMS[a]["query"] for a in run.ARMS))
                raise RuntimeError("injected")
        self.assertIs(z2.FIXTURES, originals[0])
        self.assertIs(z2b.ARMS, originals[1])
        self.assertIs(z2b.SEEDS, originals[2])
        self.assertIs(z2b.settings, originals[3])

    def test_dry_run_is_deterministic_and_never_calls_native_runner(self):
        originals = (z2.FIXTURES, z2b.ARMS, z2b.SEEDS, z2b.settings)
        with patch.object(z2b, "run_one", side_effect=AssertionError("native runner called")):
            first = run.dry_run()
            second = run.dry_run()
        self.assertEqual(first, second)
        self.assertFalse(first["native_execution"])
        self.assertFalse(first["models_loaded"])
        self.assertFalse(first["gate_promotion"])
        self.assertEqual(len(first["registered"]["source_sha256"]), 5)
        self.assertEqual(len(first["registered"]["fixture_sha256"]), 64)
        self.assertEqual(len(first["registration_sha256"]), 64)
        self.assertEqual(first["registered"]["seeds"], [27, 28, 29])
        self.assertEqual(len(first["registered"]["arms"]), 4)
        for actual, expected in zip(
                (z2.FIXTURES, z2b.ARMS, z2b.SEEDS, z2b.settings), originals):
            self.assertIs(actual, expected)

    def test_cli_only_allows_dry_run_and_rejects_native_execution(self):
        with io.StringIO() as output, contextlib.redirect_stdout(output):
            self.assertEqual(run.main(["--dry-run"]), 0)
            manifest = json.loads(output.getvalue())
        self.assertFalse(manifest["native_execution"])
        with io.StringIO() as errors, contextlib.redirect_stderr(errors):
            with self.assertRaises(SystemExit) as ctx:
                run.main(["--execute-native"])
            self.assertEqual(ctx.exception.code, 2)
            self.assertIn("not implemented/authorized", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
