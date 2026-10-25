"""Run331 RED-first learned-wake effort band containment (software-only)."""
import unittest

from v13 import effort


def signals():
    return {"detail_need": .8, "gist_need": .6, "uncertainty": .2, "conflict": 0.,
            "novelty": .1, "salience": 0., "epistemic_risk": .1}


def plan(value, **limits):
    p = effort.constrain(effort.plan_for(value, signals()), **limits)
    p["learned_wake_allowed"] = True
    return p


class Run331LearnedWakeBudget(unittest.TestCase):
    def test_direct_band_cannot_be_overridden_into_body_wake(self):
        p = plan(.1)
        self.assertEqual(p["band"], "DIRECT_C_NATIVE")
        self.assertEqual(p["wake_ceiling"], "both")  # hard ceiling alone is not the effort ceiling
        for action in effort.WAKES:
            with self.subTest(action=action):
                self.assertEqual(effort.resolve_wake(p, action)[0], "none")

    def test_one_body_band_caps_learned_both_to_one(self):
        p = plan(.3)
        self.assertEqual(p["band"], "C_NATIVE_ONE_BODY")
        self.assertEqual(p["wake_ceiling"], "both")
        self.assertEqual(effort.resolve_wake(p, "both"), ("detail", "LEARNED_WAKE_CAPPED"))
        self.assertEqual(effort.resolve_wake(p, "gist"), ("gist", "LEARNED_WAKE"))

    def test_focal_bands_still_allow_both_when_hard_ceiling_allows(self):
        for value in (.6, .9):
            p = plan(value)
            self.assertEqual(effort.resolve_wake(p, "both"), ("both", "LEARNED_WAKE"))

    def test_resource_pressure_caps_learned_both_to_one(self):
        p = plan(.9, resource_state="PRESSURE")
        self.assertEqual(effort.resolve_wake(p, "both"), ("detail", "LEARNED_WAKE_CAPPED"))

    def test_observers_off_or_red_resource_blocks_any_learned_body(self):
        for limits in ({"observers": False}, {"resource_state": "CRITICAL"}):
            p = plan(.9, **limits)
            self.assertEqual(effort.resolve_wake(p, "both"), ("none", "LEARNED_WAKE_CAPPED"))

    def test_deadline_specific_body_cap_not_bypassed(self):
        p = plan(.9, observer_window_s=3.)
        self.assertEqual(p["wake_ceiling"], "detail")
        self.assertEqual(effort.resolve_wake(p, "gist"), ("none", "LEARNED_WAKE_CAPPED"))

    def test_user_fixed_mode_cannot_be_overridden(self):
        p = effort.decide("low", signals())
        self.assertFalse(p["learned_wake_allowed"])
        self.assertEqual(effort.resolve_wake(p, "both"), ("none", "EFFORT_POLICY"))

    def test_unknown_band_and_unknown_learned_action_fail_closed(self):
        p = plan(.3)
        with self.assertRaises(ValueError):
            effort.resolve_wake(p, "four")
        p["band"] = "UNREGISTERED_BAND"
        with self.assertRaises(ValueError):
            effort.resolve_wake(p, "both")

    def test_learned_wake_never_exceeds_band_body_budget(self):
        for value, max_bodies in ((.1, 0), (.3, 1), (.6, 2), (.9, 2)):
            for action in effort.WAKES:
                p = plan(value)
                wake, _ = effort.resolve_wake(p, action)
                with self.subTest(band=p["band"], action=action):
                    self.assertLessEqual(len(effort.roles(wake)), max_bodies)

    def test_no_learned_action_uses_existing_plan_unchanged(self):
        for value in (.1, .3, .6, .9):
            p = plan(value)
            self.assertEqual(effort.resolve_wake(p, None), (p["wake"], "EFFORT_POLICY"))


if __name__ == "__main__":
    unittest.main()
