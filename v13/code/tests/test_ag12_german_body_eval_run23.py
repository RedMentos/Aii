"""Run23 test-first explicit German AG12 BodySolver scheduling (software fake runner)."""
from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi import hub, job, operator_command
from v13.agi import solver as sv
from v13.agi.generality import GeneralityEval, KEY, build_suite
from v13.agi.language_compare import compare_languages
from tests.test_agi_solver import FakeRunner, FakePool, FakeModels


class GermanBodyEvalRun23(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.g = hub(self.r)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def fake(self, lang="de", installed=("C3_LANGUAGE",)):
        gold = {i["prompt"]: i["answer"] for i in build_suite(lang=lang)["items"]}
        runner = FakeRunner("C3_LANGUAGE", gold, True, 0.9)
        self.r.pool = FakePool({"C3_LANGUAGE": runner})
        self.r.models = FakeModels(installed)
        return runner

    def test_user_scheduled_german_native_port_88_and_ag9_isolation(self):
        runner = self.fake()
        before_events = self.r.store.one("SELECT COUNT(*) n FROM events")["n"]
        self.assertEqual(self.r.store.state(KEY + "_DE", None), (None, 0))
        message = operator_command(self.r, ["eval", "run", "de", "c3"])
        self.assertIn("de", message)
        events = [x for x in self.r.sleep.scheduler._load()[0]["events"]
                  if x["action"] == "growth_eval"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["payload"], {"solver": "c3", "lang": "de"})
        self.assertEqual(events[0]["origin"], "USER")
        self.assertEqual(self.r.store.state(KEY + "_DE", None), (None, 0))
        result = job(self.r.sleep, events[0])
        self.assertEqual(result["status"], "DONE")
        self.assertEqual(result["lang"], "de")
        self.assertEqual(result["overall"], 1.0)
        self.assertEqual(len(runner.calls), 88)
        self.assertTrue(all(grammar and field == "answer"
                            for _, grammar, field in runner.calls))
        self.assertEqual(self.g.eval.report()["runs"], 0)
        self.assertEqual(GeneralityEval(self.r.store, lang="de").report()["runs"], 1)
        self.assertEqual(self.g.metacog.report("ag12:c3:de")["components"]["ag12:c3:de"]["n"], 88)
        self.assertNotIn("ag12:c3", self.g.metacog.box.load()[0]["components"])
        self.assertTrue((self.home / "exports/generality-last-de.json").exists())
        self.assertFalse((self.home / "exports/generality-last.json").exists())
        self.assertEqual(self.r.store.one("SELECT COUNT(*) n FROM events")["n"], before_events)
        runner.gold = {i["prompt"]: i["answer"] for i in self.g.eval.suite["items"]}
        en = sv.run(self.g, self.r, "c3")
        self.assertEqual(en["status"], "DONE")
        self.assertEqual(compare_languages(self.r.store, solver="c3")["status"], "DIAGNOSTIC_ONLY")
        self.assertEqual(compare_languages(self.r.store, solver="c3")["delta_de_minus_en"]["overall"], 0.0)
        self.assertEqual(self.g.metacog.report("ag12:c3")["components"]["ag12:c3"]["n"], 88)

    def test_legacy_english_payload_and_german_system_origin_veto(self):
        self.fake()
        operator_command(self.r, ["eval", "run", "c3"])
        events = [x for x in self.r.sleep.scheduler._load()[0]["events"]
                  if x["action"] == "growth_eval"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["payload"], {"solver": "c3"})
        system = {"id": "system-fake", "action": "growth_eval",
                  "origin": "SYSTEM", "payload": {"solver": "c3", "lang": "de"}}
        self.assertEqual(job(self.r.sleep, system)["status"], "USER_REQUIRED")
        self.assertEqual(self.r.store.state(KEY + "_DE", None), (None, 0))
        self.assertEqual(job(self.r.sleep, events[0])["status"], "DONE")
        self.assertEqual(self.r.store.state(KEY + "_DE", None), (None, 0))

    def test_no_model_invalid_language_and_cancel_are_explicit(self):
        self.fake(installed=())
        self.assertEqual(sv.run(self.g, self.r, "c3", lang="de")["status"], "NO_SOLVER")
        self.assertEqual(self.r.store.state(KEY + "_DE", None), (None, 0))
        with self.assertRaises(ValueError):
            sv.run(self.g, self.r, "c3", lang="fr")
        with self.assertRaises(ValueError):
            operator_command(self.r, ["eval", "run", "de", "unknown"])
        self.fake()
        ev = threading.Event()
        ev.set()
        self.assertEqual(sv.run(self.g, self.r, "c3", lang="de", cancel=ev)["status"], "INTERRUPTED")
        self.assertNotIn("ag12:c3:de", self.g.metacog.box.load()[0]["components"])


if __name__ == "__main__":
    unittest.main()
