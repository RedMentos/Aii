"""Run105: contradictory trusted route procedures cannot bypass JEF C2.
Real persisted Runtime/SkillLibrary, no native model, no tool execution.
"""
import tempfile
import unittest
from pathlib import Path

from v13 import skilllive
from v13.agi import hub
from v13.runtime import Runtime


class TrustedRouteConsistencyRun105(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.lib = hub(self.r).skills

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def add(self, name, steps, stage="TRUSTED"):
        self.lib.propose(name, steps, trigger="weekly plan")
        if stage != "CANDIDATE":
            self.lib.set_stage(name, stage)
        return self.lib.get(name)

    def automatic(self):
        e = self.r.store.event(self.r.session, "Make a weekly plan")
        meta = {}
        result = skilllive.automatic(self.r, e, "Make a weekly plan", meta)
        return result, meta

    def test_conflicting_trusted_routes_cannot_skip_c2(self):
        self.add("conflict", [{"route": "simple"}, {"route": "detail"}])
        self.assertEqual(skilllive.matches(self.lib, "Make a weekly plan", skilllive.LIVE), [])
        result, meta = self.automatic()
        self.assertIsNone(result)
        self.assertNotIn("skill", meta)

    def test_invalid_later_route_cannot_skip_c2(self):
        self.add("invalid", [{"route": "simple"}, {"route": "not-a-route"}])
        self.assertEqual(skilllive.matches(self.lib, "Make a weekly plan", skilllive.LIVE), [])
        self.assertIsNone(self.automatic()[0])

    def test_conflicting_route_remains_ineligible_after_restart(self):
        self.add("persisted", [{"route": "gist"}, {"route": "detail"}])
        self.r.close()
        self.r = Runtime(self.home)
        self.lib = hub(self.r).skills
        self.assertEqual(self.lib.get("persisted")["stage"], "TRUSTED")
        self.assertEqual(skilllive.matches(self.lib, "Make a weekly plan", skilllive.LIVE), [])
        self.assertIsNone(self.automatic()[0])

    def test_single_route_keeps_automatic_fast_path(self):
        self.add("single", [{"route": "gist"}])
        result, meta = self.automatic()
        self.assertEqual(result[0], "gist")
        self.assertEqual(result[1]["source"], "TRUSTED_SKILL_AUTOMATIC")
        self.assertTrue(meta["skill"]["automatic"])

    def test_repeated_identical_routes_keep_automatic_fast_path(self):
        self.add("same", [{"route": "detail"}, {"route": "detail"}])
        result, meta = self.automatic()
        self.assertEqual(result[0], "detail")
        self.assertEqual(meta["skill"]["route"], "detail")

    def test_mixed_tool_route_procedure_cannot_skip_tool_gates(self):
        self.add("mixed", [{"route": "gist"}, {"tool": "calculator", "args": {}}])
        self.assertEqual(skilllive.matches(self.lib, "Make a weekly plan", skilllive.LIVE), [])
        self.assertIsNone(self.automatic()[0])

    def test_conflicting_candidate_is_not_reported_as_shadow_route(self):
        self.add("shadow_bad", [{"route": "simple"}, {"route": "both"}], "CANDIDATE")
        e = self.r.store.event(self.r.session, "Make a weekly plan")
        meta = {}
        self.assertEqual(skilllive.shadow_candidates(self.r, e, "Make a weekly plan", meta), [])
        self.assertNotIn("skill_shadow", meta)


if __name__ == "__main__":
    unittest.main()
