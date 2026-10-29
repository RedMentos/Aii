"""RED-first WP-T6 trusted cross-skill route ambiguity must not skip C_fast."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from v13.agi import hub
from v13.operator import Operator
from v13.runtime import Runtime


class CrossSkillConflict(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        Operator(self.r).run(":observers off")
        self.lib = hub(self.r).skills
        self.r.pool.get = Mock(return_value=SimpleNamespace(
            role="C3_LANGUAGE", last_metrics={"test_seam": True},
            generate=lambda *a, **k: iter(["ok"])))
        self.r.learner.output_delta = Mock(return_value=None)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def trusted(self, name, route, trigger="weekly plan"):
        self.lib.propose(name, [{"route": route}], trigger=trigger)
        self.lib.set_stage(name, "TRUSTED")

    def turn(self, text):
        self.r.submit(text)
        deadline = time.monotonic() + 10
        while not self.r.idle() and time.monotonic() < deadline:
            time.sleep(.005)
        answer = self.r.last_answer()
        self.assertIsNotNone(answer)
        return json.loads(answer["metadata"])

    def test_two_conflicting_trusted_skills_reenter_real_c_fast(self):
        self.trusted("weekly_detail", "detail")
        self.trusted("weekly_gist", "gist")
        self.r._route = Mock(return_value=("simple", {"source": "BOOT_SCAFFOLD"}))
        meta = self.turn("Make my weekly plan")
        self.assertEqual(meta["route"]["source"], "BOOT_SCAFFOLD")
        self.r._route.assert_called_once()
        self.assertFalse(meta.get("skill", {}).get("automatic", False))

    def test_longer_trigger_does_not_override_conflicting_trusted_route(self):
        self.trusted("specific_detail", "detail", "weekly plan")
        self.trusted("generic_gist", "gist", "plan")
        self.r._route = Mock(return_value=("simple", {"source": "BOOT_SCAFFOLD"}))
        meta = self.turn("Make my weekly plan")
        self.assertEqual(meta["route"]["source"], "BOOT_SCAFFOLD")
        self.r._route.assert_called_once()

    def test_two_agreeing_trusted_skills_preserve_fast_route(self):
        self.trusted("weekly_detail", "detail")
        self.trusted("weekly_detail2", "detail")
        self.r._route = Mock(side_effect=AssertionError("C_fast should be skipped"))
        meta = self.turn("Make my weekly plan")
        self.assertEqual(meta["route"]["source"], "TRUSTED_SKILL_AUTOMATIC")
        self.assertEqual(meta["skill"]["route"], "detail")
        self.r._route.assert_not_called()

    def test_shadow_disagreement_does_not_veto_trusted_route(self):
        self.trusted("weekly_detail", "detail")
        self.lib.propose("weekly_shadow_gist", [{"route": "gist"}],
                         trigger="weekly plan")
        self.r._route = Mock(side_effect=AssertionError("C_fast should be skipped"))
        meta = self.turn("Make my weekly plan")
        self.assertEqual(meta["route"]["source"], "TRUSTED_SKILL_AUTOMATIC")
        self.r._route.assert_not_called()


if __name__ == "__main__":
    unittest.main()
