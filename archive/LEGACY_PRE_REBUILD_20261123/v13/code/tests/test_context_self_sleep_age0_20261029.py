"""Real Store/Runtime ContextOS + Self/World + Sleep Age0 source integration (no models)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13 import context_os as C
from v13 import selfmodel as SELF
from v13 import sleep as SLEEP
from v13.runtime import Runtime


class ContextSelfSleepAge0Tests(unittest.TestCase):
    def test_source_and_mixed_attribution_survive_restart_without_authority(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            r = Runtime(home)
            source = "Intro.\n```python\nopaque_method_should_survive = 'literal'\n" + "Context text stays unchanged. " * 35
            query = "Please preserve the literal source."
            try:
                r.sleep.cycle.set_policy("enabled", "off")
                self.assertEqual(r.cfg["learning_mode"], "RECORD_ONLY")
                self.assertEqual(r.cfg["system_stage"], 0)
                self.assertIs(r.cfg["latents_enabled"], False)
                self.assertEqual(r.cfg.get("jepa_weight", 0), 0)

                with patch.object(r.pool, "get", side_effect=AssertionError("NATIVE_MODEL_CALLED")):
                    event = r.store.event(r.session, source)
                    ref = event["source_ref"]
                    self.assertEqual(r.store.read_source(ref), source)
                    raw, _, compressible = C.compress(source, 140)
                    self.assertFalse(compressible)
                    self.assertEqual(raw, source)

                    qe = r.store.event(r.session, query)
                    history = [{"event_id": event["event_id"], "role": "user", "text": source}]
                    ctx = C.controller(r).plan(qe["event_id"], "C3_LANGUAGE", "SYS", [], history, query)
                    self.assertFalse(ctx["applied"])
                    self.assertEqual(ctx["plan"]["mode"], "SHADOW")
                    self.assertTrue(any(source == m["content"] for m in ctx["planned"]))

                    selfsys = SELF.controller(r)
                    issued = selfsys.issue(
                        qe["event_id"], "age0-test-action", "local diagnostic",
                        [{"channel": "duration_s", "value": 1.0, "tolerance": 0.0}],
                        refs=[ref])
                    outcome = selfsys.observe(
                        qe["event_id"],
                        [{"channel": "duration_s", "value": True, "t": issued["issued_at"] + .01}],
                        close=["age0-test-action"])
                    self.assertEqual(len(outcome), 1)
                    self.assertEqual(outcome[0]["class"], "MIXED")
                    self.assertEqual(outcome[0]["residual"], {"expected": 1.0, "actual": True})
                    stored = r.store.rows(
                        "SELECT payload FROM packets WHERE kind='SelfWorldAttribution' AND event_id=?",
                        (qe["event_id"],))
                    self.assertEqual(len(stored), 1)
                    self.assertEqual(json.loads(stored[0]["payload"])["attribution"], "MIXED")

                    before = r.store.state(SLEEP.POLICY_KEY, None)
                    for bad in ("nan", "inf"):
                        with self.assertRaises(ValueError):
                            r.sleep.cycle.set_policy("mix.recent", bad)
                        self.assertEqual(r.store.state(SLEEP.POLICY_KEY, None), before)
                    r.sleep.cycle.set_policy("mix.recent", "0.4")
                    self.assertEqual(r.sleep.cycle.policy()["mix"]["recent"], 0.4)
                    self.assertEqual(r.store.one("SELECT COUNT(*) AS n FROM updates")["n"], 0)
            finally:
                r.close()

            r = Runtime(home)
            try:
                r.sleep.cycle.set_policy("enabled", "off")
                self.assertEqual(r.store.read_source(ref), source)
                self.assertEqual(C.controller(r).report()["mode"], "SHADOW")
                view = SELF.controller(r).corollary_view()
                self.assertEqual(view["authority"], "SELF_STATE_NOT_FACT")
                self.assertEqual(view["recent_own_action_outcomes"][0]["attribution"], "MIXED")
                self.assertEqual(r.sleep.cycle.policy()["mix"]["recent"], 0.4)
                self.assertEqual(r.store.one("SELECT COUNT(*) AS n FROM updates")["n"], 0)
                self.assertEqual(r.cfg["learning_mode"], "RECORD_ONLY")
                self.assertEqual(r.cfg["system_stage"], 0)
                self.assertIs(r.cfg["latents_enabled"], False)
            finally:
                r.close()


if __name__ == "__main__":
    unittest.main()
