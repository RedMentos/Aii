"""Run302 RED/GREEN: :learning status is a read-only Age/approval-aware report.

Actual production Runtime/Store SQLite; no native model or learning promotion.
"""
import json
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime
from v13.operator import Operator


class LearningOperatorStatusRun302(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)

    def tearDown(self):
        if self.r is not None:
            self.r.close()
        self.tmp.cleanup()

    def report(self, command=":learning"):
        return json.loads(self.op.run(command))

    def test_no_arg_and_status_are_identical_and_do_not_mutate(self):
        config_path = self.home / "config/settings.json"
        before = config_path.read_bytes()
        generation = self.r.store.generation_id
        states = self.r.store.one("SELECT COUNT(*) n FROM states")["n"]
        a = self.report()
        b = self.report(":learning status")
        self.assertEqual(a, b)
        self.assertEqual(a["mode"], "RECORD_ONLY")
        self.assertEqual(a["age_stage"], 0)
        self.assertTrue(a["approval_required"])
        self.assertTrue(a["mode_is_not_approval"])
        self.assertEqual(config_path.read_bytes(), before)
        self.assertEqual(self.r.store.generation_id, generation)
        self.assertEqual(self.r.store.one("SELECT COUNT(*) n FROM states")["n"], states)
        self.assertEqual(json.loads(self.op.run(":status"))["learning"], a["mode"])

    def test_explicit_setter_still_works_but_does_not_grant_approval(self):
        self.assertIn("SHADOW_UPDATE", self.op.run(":learning shadow"))
        a = self.report()
        self.assertEqual(a["mode"], "SHADOW_UPDATE")
        self.assertTrue(a["approval_required"])
        self.assertEqual(a["age_stage"], 0)
        self.assertIn("APPROVED_COMMIT", self.op.run(":learning commit"))
        b = self.report(":learning status")
        self.assertEqual(b["mode"], "APPROVED_COMMIT")
        self.assertTrue(b["mode_is_not_approval"])
        self.assertEqual(self.r.store.one("SELECT COUNT(*) n FROM updates")["n"], 0)
        self.assertEqual(json.loads(self.op.run(":status"))["age"], 0)

    def test_invalid_argument_is_rejected_without_mutating_mode(self):
        before = (self.home / "config/settings.json").read_bytes()
        with self.assertRaises(ValueError):
            self.op.run(":learning status extra")
        self.assertEqual((self.home / "config/settings.json").read_bytes(), before)

    def test_readonly_report_survives_restart(self):
        self.op.run(":learning shadow")
        before = self.report()
        self.r.close()
        self.r = Runtime(self.home)
        self.op = Operator(self.r)
        self.assertEqual(self.report(), before)


if __name__ == "__main__":
    unittest.main()
