"""WP-T6 source-only RED-first ambiguous multi-step fast-skill routing tests."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from v13 import skilllive


class Box:
    def __init__(self, skills):
        self.skills = skills

    def load(self):
        return {"skills": self.skills}, 0


def skill(name, steps):
    return {"name": name, "steps": steps, "stage": "TRUSTED",
            "trigger": "weekly plan"}


class MultiStepRouteReview(unittest.TestCase):
    def test_only_unambiguous_route_only_skills_are_automatic(self):
        self.assertEqual(skilllive._route_only(skill("one", [{"route": "detail"}])), "detail")
        self.assertEqual(skilllive._route_only(skill("same", [{"route": "gist"}, {"route": "gist"}])), "gist")
        for steps in (
            [{"route": "detail"}, {"route": "gist"}],
            [{"route": "detail"}, {"route": "nonexistent"}],
            [{"route": "nonexistent"}, {"route": "detail"}],
            [{"route": "detail"}, {"tool": "search", "args": {}}],
            [{"route": "detail"}, {}],
        ):
            with self.subTest(steps=steps):
                self.assertIsNone(skilllive._route_only(skill("bad", steps)))

    def test_conflicting_trusted_skill_never_skips_c2(self):
        bad = skill("ambiguous", [{"route": "detail"}, {"route": "gist"}])
        lib = SimpleNamespace(box=Box({"ambiguous": bad}))
        self.assertEqual(skilllive.matches(lib, "Make my weekly plan", skilllive.LIVE), [])
        with patch("v13.agi.hub", return_value=SimpleNamespace(skills=lib)):
            self.assertIsNone(skilllive.automatic(object(), {}, "Make my weekly plan", {}))

    def test_mixed_tool_procedure_not_fast_route(self):
        mixed = skill("mixed", [{"route": "simple"}, {"tool": "lookup", "args": {}}])
        lib = SimpleNamespace(box=Box({"mixed": mixed}))
        self.assertEqual(skilllive.matches(lib, "weekly plan", skilllive.LIVE), [])


if __name__ == "__main__":
    unittest.main()
