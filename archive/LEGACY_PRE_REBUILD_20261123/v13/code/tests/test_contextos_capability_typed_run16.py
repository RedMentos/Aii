"""Run16 test-first G6B typed capability/digest boundary; real SQLite Store."""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13 import context_os as C


class ContextCapabilityTyped(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.c = C.ContextOS(self.r.store, self.r.cfg)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def _plan(self, name="test"):
        event_id = self.r.store.event(self.r.session, name)["event_id"]
        return self.c.plan(
            event_id, "C3_LANGUAGE", "SYSTEM", [("LATENT_STATE", "\\nSTATE:", {"v": 1})],
            [], name,
        )

    def _inject_capability(self, value):
        state, version = self.r.store.state(C.KEY, None)
        if state is None:
            state = C.empty()
        state["capabilities"] = {
            "C3_LANGUAGE": {"consecutive_user": {"value": value, "evidence": "legacy-unverified"}}
        }
        self.r.store.set_state(C.KEY, state, expected=version)

    def test_setter_rejects_truthy_strings_and_nonnumeric_boolean_surrogates(self):
        for value in ("false", "true", "off", "on", 0, 1, None, [], {}, 0.5):
            with self.subTest(value=repr(value)):
                before = self.r.store.state(C.KEY, None)
                with self.assertRaises((ValueError, TypeError)):
                    self.c.set_capability("C3_LANGUAGE", "consecutive_user", value)
                self.assertEqual(self.r.store.state(C.KEY, None), before)

        self.c.set_capability("C3_LANGUAGE", "consecutive_user", True, "operator")
        self.assertTrue(self.c.capability("C3_LANGUAGE", "consecutive_user"))
        self.c.set_capability("C3_LANGUAGE", "consecutive_user", False, "operator")
        self.assertFalse(self.c.capability("C3_LANGUAGE", "consecutive_user"))

    def test_legacy_malformed_capability_fails_closed_in_both_readers(self):
        self.c.set_layout("stable_prefix")
        for value in ("false", "true", 1, 0, [], None, {"value": True}):
            with self.subTest(value=repr(value)):
                self._inject_capability(value)
                self.assertFalse(self.c.capability("C3_LANGUAGE", "consecutive_user"))
                p = self._plan("malformed-" + repr(value))
                self.assertEqual(p["plan"]["layout"], "legacy")
                self.assertEqual(
                    p["plan"]["cache"]["fallback_reason"], "template_capability_unknown"
                )
                self.assertFalse(p["applied"])  # Age0 default SHADOW unchanged

    def test_boolean_capability_persists_across_real_sqlite_restart(self):
        self.c.set_layout("stable_prefix")
        self.c.set_capability("C3_LANGUAGE", "consecutive_user", True, "operator")
        self.assertEqual(self._plan("before")["plan"]["layout"], "stable_prefix")
        self.r.close()
        self.r = Runtime(self.home)
        self.c = C.ContextOS(self.r.store, self.r.cfg)
        self.assertTrue(self.c.capability("C3_LANGUAGE", "consecutive_user"))
        self.assertEqual(self._plan("after")["plan"]["layout"], "stable_prefix")
        self.c.set_capability("C3_LANGUAGE", "consecutive_user", False)
        self.assertEqual(self._plan("disabled")["plan"]["layout"], "legacy")

    def test_digest_rejects_ambiguous_values_without_mutation(self):
        for value in ("off", "false", "on", 0, 1, None, [], {}):
            with self.subTest(value=repr(value)):
                before = self.r.store.state(C.KEY, None)
                with self.assertRaises((ValueError, TypeError)):
                    self.c.set_digest(value)
                self.assertEqual(self.r.store.state(C.KEY, None), before)
        self.assertFalse(self.c.set_digest(False))
        self.assertFalse(self.c.digest_enabled())
        self.assertTrue(self.c.set_digest(True))
        self.assertTrue(self.c.digest_enabled())


if __name__ == "__main__":
    unittest.main()
