"""Run14O test-first C2 deadline wake selection; pure software, no model."""
import unittest

from v13 import effort

CFG = {"max_reentry": 1, "focal_slots": 4}


def signals(preferred):
    s = effort.signals(
        "Compare planning and numerical detail for this task", route="both",
        route_info={"source": "BOOT_SCAFFOLD", "scaffold": "both"})
    s.update(detail_need=0.9 if preferred == "detail" else 0.4,
             gist_need=0.9 if preferred == "gist" else 0.4,
             conflict=0.8, uncertainty=0.7, novelty=0.5)
    return s


class C2DeadlinePreferredWake(unittest.TestCase):
    def test_deadline_one_body_respects_gist_preference(self):
        p = effort.decide("max", signals("gist"), cfg=CFG,
                          observer_window_s=3.0)
        self.assertEqual(p["one_body"], "gist")
        self.assertEqual(p["wake"], "gist")
        self.assertEqual(p["wake_ceiling"], "one")
        self.assertEqual(p["max_reentry"], 0)
        self.assertIn("DEADLINE_ONE_BODY", p["constraints"])
        self.assertEqual(p["age_stage"], 0)
        self.assertEqual(p["tool_steps"], 0)
        self.assertFalse(p["verify"])

    def test_detail_preference_remains_detail(self):
        p = effort.decide("max", signals("detail"), cfg=CFG,
                          observer_window_s=3.0)
        self.assertEqual(p["one_body"], "detail")
        self.assertEqual(p["wake"], "detail")
        self.assertEqual(p["wake_ceiling"], "one")
        self.assertEqual(p["max_reentry"], 0)

    def test_resource_orange_and_hard_denials_unchanged(self):
        s = signals("gist")
        orange = effort.decide("max", s, cfg=CFG, resource_state="PRESSURE")
        self.assertEqual((orange["wake"], orange["wake_ceiling"]),
                         ("gist", "one"))
        for kwargs in ({"observer_window_s": 1.0},
                       {"observers": False},
                       {"resource_state": "CRITICAL"},
                       {"direct": True}):
            with self.subTest(kwargs=kwargs):
                p = effort.decide("max", s, cfg=CFG, **kwargs)
                self.assertEqual(p["wake"], "none")
                self.assertEqual(p["max_reentry"], 0)

    def test_user_forced_one_body_modes_remain_forced(self):
        s = signals("gist")
        for mode in ("detail", "gist"):
            p = effort.decide(mode, s, cfg=CFG, observer_window_s=3.0)
            self.assertEqual(p["wake"], mode)
            self.assertEqual(p["max_reentry"], 0)
            self.assertFalse(p["learned_wake_allowed"])

    def test_learned_wake_cannot_override_deadline_one_body(self):
        p = effort.decide("adaptive", signals("gist"), cfg=CFG,
                          observer_window_s=3.0)
        self.assertEqual(p["wake_ceiling"], "one")
        self.assertEqual(p["wake"], "gist")
        self.assertEqual(effort.resolve_wake(p, "both"),
                         ("gist", "LEARNED_WAKE_CAPPED"))
        self.assertEqual(effort.resolve_wake(p, "none"),
                         ("none", "LEARNED_WAKE"))


if __name__ == "__main__":
    unittest.main()
