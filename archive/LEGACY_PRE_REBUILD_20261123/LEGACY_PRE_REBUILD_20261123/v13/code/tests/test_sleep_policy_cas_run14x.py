"""Run14X test-first: F9 Sleep policy booleans and concurrent updates fail closed."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13.sleep import POLICY_KEY, default_policy


class SleepPolicyCASRun14X(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.c = self.r.sleep.cycle
        self.c.set_policy("enabled", "off")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def test_explicit_boolean_aliases_reload_and_unknown_rejected(self):
        for value in ("on", "true", "1", "ja", "yes"):
            with self.subTest(value=value):
                self.assertTrue(self.c.set_policy("enabled", value)["enabled"])
        for value in ("off", "false", "0", "nein", "no"):
            with self.subTest(value=value):
                self.assertFalse(self.c.set_policy("enabled", value)["enabled"])
        self.c.set_policy("enabled", "on")
        for bad in ("maybe", "", "True-ish", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    self.c.set_policy("enabled", bad)
                self.assertTrue(self.c.policy()["enabled"])
        self.r.close()
        self.r = Runtime(self.home)
        self.c = self.r.sleep.cycle
        self.assertTrue(self.c.policy()["enabled"])
        self.c.set_policy("enabled", "off")

    def test_cas_retries_preserve_independent_interleaved_policy_update(self):
        original = self.r.store.set_state
        injected = [False]

        def raced(key, payload, expected=None):
            if key == POLICY_KEY and not injected[0]:
                injected[0] = True
                prior, version = self.r.store.state(POLICY_KEY, None)
                concurrent = default_policy() | (prior or {})
                concurrent["wake_batch"] = 3
                original(POLICY_KEY, concurrent, expected=version)
            return original(key, payload, expected=expected)

        with patch.object(self.r.store, "set_state", side_effect=raced):
            self.c.set_policy("batch", "7")
        self.assertTrue(injected[0])
        self.assertEqual(self.c.policy()["batch"], 7)
        self.assertEqual(self.c.policy()["wake_batch"], 3)

    def test_continuous_conflicts_stop_after_bounded_retries(self):
        with patch.object(self.r.store, "set_state", side_effect=ValueError("Stale state write")) as mocked:
            with self.assertRaises(ValueError):
                self.c.set_policy("batch", "7")
        self.assertEqual(mocked.call_count, 8)
        self.assertEqual(self.c.policy()["batch"], default_policy()["batch"])


if __name__ == "__main__":
    unittest.main()
