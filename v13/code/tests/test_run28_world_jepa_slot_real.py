"""Run28 orchestration tests use mocks; no file-world or JEPA utility evidence."""
from __future__ import annotations

from argparse import Namespace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run28_world_jepa_slot_real as pilot


def args(root, **overrides):
    base = dict(
        out=root / "result.json", work_root=root / "work",
        registered=True, seeds="101,102,103",
        train=4000, cf=150, attr=300, steps=3000,
    )
    base.update(overrides)
    return Namespace(**base)


def fake_seed(seed, a, work):
    return {"seed": seed, "n_train": a.train,
            "_conf_err": [[0.2, 0.1]], "status": "SYNTHETIC_MOCK_ONLY"}


class Run28RegisteredOrchestration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()

    def test_registered_seed_and_cohort_mutation_vetoed_before_io(self):
        for change in (dict(seeds="101,102"), dict(train=3999),
                       dict(cf=151), dict(attr=301), dict(steps=2999)):
            with self.subTest(change=change):
                a = args(self.root, **change)
                with patch.object(pilot, "run_seed", side_effect=AssertionError("must not run")):
                    with self.assertRaisesRegex(ValueError, "REGISTERED_COHORT_MUTATION"):
                        pilot.run(a)
                self.assertFalse(a.work_root.exists())
                self.assertFalse(a.out.exists())

    def test_smoke_mock_does_not_claim_registered_measurement(self):
        a = args(self.root, registered=False, seeds="7", train=120, cf=2, attr=2, steps=4)
        with patch.object(pilot, "run_seed", side_effect=fake_seed):
            r = pilot.run(a)
        self.assertEqual(r["status"], "SMOKE_ONLY_NOT_EVIDENCE")
        self.assertEqual(r["evidence_kind"], "SMOKE_ONLY")
        self.assertFalse(r["whole_system_complete"])
        self.assertEqual(r["jepa_weight"], 0)
        self.assertTrue((a.work_root / "seed-7-RESULT.json").exists())
        self.assertNotIn("_conf_err", json.dumps(r))

    def test_second_seed_failure_keeps_first_checkpoint_and_red(self):
        a = args(self.root, registered=False, seeds="7,8", train=120, cf=2, attr=2, steps=4)
        def fail_second(seed, a, work):
            if seed == 8:
                raise RuntimeError("synthetic interruption")
            return fake_seed(seed, a, work)
        with patch.object(pilot, "run_seed", side_effect=fail_second):
            with self.assertRaisesRegex(RuntimeError, "RED_OR_INCOMPLETE"):
                pilot.run(a)
        r = json.loads(a.out.read_text())
        self.assertEqual(r["status"], "RED")
        self.assertEqual([s["seed"] for s in r["seeds"]], [7])
        self.assertTrue((a.work_root / "seed-7-RESULT.json").exists())
        self.assertFalse(r["whole_system_complete"])

    def test_mocked_failed_criteria_stays_shadow_fail(self):
        a = args(self.root)
        with patch.object(pilot, "run_seed", side_effect=fake_seed), \
             patch.object(pilot.original, "criteria", return_value=(
                 {"W1": False, "W2": True},
                 {"spearman_conf_err_covered": -0.1, "pooled_cf": {"jepa_covered": 0.75}})):
            r = pilot.run(a)
        self.assertEqual(r["status"], "SHADOW_CANDIDATE_FAIL")
        self.assertFalse(r["criteria"]["W1"])
        self.assertTrue(r["capacity_confounded"])
        self.assertEqual(r["world_jepa_authority"], "SHADOW")

    def test_mocked_pass_never_promotes_age_or_jepa(self):
        a = args(self.root)
        with patch.object(pilot, "run_seed", side_effect=fake_seed), \
             patch.object(pilot.original, "criteria", return_value=(
                 {"W1": True, "W2": True},
                 {"spearman_conf_err_covered": -0.4, "pooled_cf": {"jepa_covered": 0.82}})):
            r = pilot.run(a)
        self.assertEqual(r["status"], "SHADOW_CANDIDATE_PASS_NOT_PROMOTED")
        self.assertEqual(r["step2"], "UTILITY_FAIL")
        self.assertEqual(r["b3"], "NO_PROMOTION")
        self.assertEqual(r["jepa_weight"], 0)
        self.assertFalse(r["redmi_measured"])
        self.assertFalse(r["whole_system_complete"])


if __name__ == "__main__":
    unittest.main()
