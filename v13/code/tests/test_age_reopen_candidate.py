"""Software-only tests of an opt-in, non-runtime Age candidate."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from age_reopen_candidate import plasticity_candidate
from v13.age import AgeControl, default_state


class MemoryStore:
    def __init__(self):
        self.data = default_state()

    def state(self, key, default):
        return self.data, 0


class AgeReopeningCandidateTests(unittest.TestCase):
    def controller(self, policy, independent_count, *, old_noise_count=0):
        store = MemoryStore()
        sub = store.data["system"]
        sub["stage"] = 3
        sub["maturity"]["stability"] = 0.7
        sub["noise"] = {"n": old_noise_count, "mad": 0.05}
        if independent_count is not None:
            sub["noise_ind"] = {"n": independent_count, "sd": 0.03}
        return store, AgeControl(
            store, {"age_plasticity_policy": policy, "user_stage_cap": 5},
            build_ceiling=5,
        )

    def test_explicit_novelty_floors_for_each_policy_and_noise_readiness(self):
        for policy in ("boot", "stable_reopen", "noise_aware"):
            for n in (None, 0, 3, 4):
                for old_n in (0, 4):
                    with self.subTest(policy=policy, independent=n, old=old_n):
                        _, age = self.controller(policy, n, old_noise_count=old_n)
                        self.assertGreaterEqual(plasticity_candidate(age, novel_domain=True), 0.8)
                        self.assertEqual(plasticity_candidate(age, new_modality=True), 1.0)
                        self.assertEqual(plasticity_candidate(age, novel_domain=True, new_modality=True), 1.0)

    def test_without_explicit_novelty_original_error_and_hold_logic_is_exact(self):
        for policy in ("boot", "stable_reopen", "noise_aware"):
            for n in (None, 3, 4):
                store, age = self.controller(policy, n, old_noise_count=4)
                store.data["system"]["plasticity_hold"] = {"stage": 4, "until": 9}
                store.data["system"]["evidence_count"] = 2
                for errors in (0, 1, 2, 5):
                    with self.subTest(policy=policy, independent=n, errors=errors):
                        self.assertEqual(
                            plasticity_candidate(age, repeated_errors=errors),
                            age.plasticity(repeated_errors=errors),
                        )

    def test_missing_evidence_does_not_signal_novelty_or_mutate_state(self):
        for policy in ("boot", "stable_reopen", "noise_aware"):
            store = MemoryStore()
            age = AgeControl(store, {"age_plasticity_policy": policy, "user_stage_cap": 0})
            before = copy.deepcopy(store.data)
            self.assertEqual(plasticity_candidate(age), age.plasticity())
            self.assertEqual(store.data, before)
            self.assertEqual(age.build_ceiling, 0)

    def test_novelty_must_be_explicit_booleans(self):
        _, age = self.controller("boot", 4)
        for kw in ({"novel_domain": "false"}, {"new_modality": 1}, {"novel_domain": None}):
            with self.subTest(value=kw), self.assertRaises(ValueError):
                plasticity_candidate(age, **kw)

    def test_explicit_requests_do_not_modify_state_or_rights(self):
        store, age = self.controller("noise_aware", 4)
        before = copy.deepcopy(store.data)
        rights_before = age.allowed("tool_learning")
        plasticity_candidate(age, novel_domain=True, repeated_errors=2)
        plasticity_candidate(age, new_modality=True)
        self.assertEqual(store.data, before)
        self.assertEqual(age.allowed("tool_learning"), rights_before)


if __name__ == "__main__":
    unittest.main()
