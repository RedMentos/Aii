"""Run14V test-first: learned C2 wake must obey both effort band and hard resource ceiling."""
import unittest
from v13 import effort as E

CFG = {"max_reentry": 1, "focal_slots": 4}


def signals():
    return E.signals("Vergleiche den Plan und berechne 17 * 23", "both",
                     {"source": "BOOT_SCAFFOLD", "scaffold": "both"})


def band_plan(effort, **limits):
    plan = E.plan_for(effort, signals())
    plan = E.constrain(plan, cfg=CFG, **limits)
    plan["learned_wake_allowed"] = True
    plan["mode"] = "adaptive"
    return plan


class LearnedWakeBandRun14V(unittest.TestCase):
    def test_direct_band_never_wakes_body_despite_open_resource_ceiling(self):
        p = band_plan(.1)
        self.assertEqual(p["band"], "DIRECT_C_NATIVE")
        self.assertEqual(p["wake_ceiling"], "both")
        for learned in ("none", "detail", "gist", "both"):
            with self.subTest(learned=learned):
                chosen, reason = E.resolve_wake(p, learned)
                self.assertEqual(chosen, "none")
                self.assertEqual(reason, "LEARNED_WAKE" if learned == "none" else "LEARNED_WAKE_CAPPED")

    def test_one_body_band_cannot_escalate_to_two_bodies(self):
        p = band_plan(.35)
        self.assertEqual(p["band"], "C_NATIVE_ONE_BODY")
        self.assertEqual(p["wake_ceiling"], "both")
        self.assertEqual(E.resolve_wake(p, "both"), (p["one_body"], "LEARNED_WAKE_CAPPED"))
        self.assertEqual(E.resolve_wake(p, "gist"), ("gist", "LEARNED_WAKE"))
        self.assertEqual(E.resolve_wake(p, "detail"), ("detail", "LEARNED_WAKE"))
        self.assertEqual(E.resolve_wake(p, "none"), ("none", "LEARNED_WAKE"))

    def test_focal_bands_allow_both_when_hard_limits_allow(self):
        for level in (.7, .95):
            with self.subTest(level=level):
                p = band_plan(level)
                self.assertEqual(E.resolve_wake(p, "both"), ("both", "LEARNED_WAKE"))

    def test_hard_resource_and_deadline_ceiling_still_wins(self):
        one = band_plan(.95, resource_state="PRESSURE")
        self.assertEqual(one["wake_ceiling"], "one")
        self.assertEqual(E.resolve_wake(one, "both"), (one["one_body"], "LEARNED_WAKE_CAPPED"))
        none = band_plan(.95, observers=False)
        self.assertEqual(none["wake_ceiling"], "none")
        self.assertEqual(E.resolve_wake(none, "both"), ("none", "LEARNED_WAKE_CAPPED"))
        deadline = band_plan(.95, observer_window_s=.5)
        self.assertEqual(E.resolve_wake(deadline, "both"), ("none", "LEARNED_WAKE_CAPPED"))

    def test_user_forced_mode_and_unknown_band_fail_closed(self):
        forced = E.decide("detail", signals(), cfg=CFG)
        self.assertFalse(forced["learned_wake_allowed"])
        self.assertEqual(E.resolve_wake(forced, "both"), ("detail", "EFFORT_POLICY"))
        p = band_plan(.7)
        with self.assertRaises(ValueError):
            E.resolve_wake(p, "not-a-wake")
        with self.assertRaises(ValueError):
            E.resolve_wake(dict(p, band="UNKNOWN_BAND"), "both")


if __name__ == "__main__":
    unittest.main()
