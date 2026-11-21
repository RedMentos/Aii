"""Real Runtime/SQLite arithmetic path; native runners are forbidden spies."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock

from v13.runtime import Runtime


class ArithmeticTurn(unittest.TestCase):
    def test_source_bound_final_restart_and_normal_route_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            runtime = Runtime(home)
            try:
                runtime.pool.get = Mock(side_effect=AssertionError("native runner invoked"))
                runtime.needle.control = Mock(side_effect=AssertionError("native control invoked"))
                event_id = runtime.submit("Was ist 2+2?")
                until = time.monotonic() + 8
                while not runtime.idle() and time.monotonic() < until:
                    time.sleep(.01)
                self.assertTrue(runtime.idle())
                row = runtime.last_answer()
                self.assertEqual((row["text"], row["status"]), ("4", "FINAL"))
                meta = json.loads(row["metadata"])
                self.assertEqual(meta["output_authority"], "LOCAL_EXACT_ARITHMETIC")
                self.assertFalse(meta["model_generated"])
                self.assertEqual(meta["route"]["source"], "EXACT_ARITHMETIC_REFLEX")
                self.assertEqual(runtime.store.read_source(meta["arithmetic_reflex"]["source_ref"]), "Was ist 2+2?")
                runtime.pool.get.assert_not_called()
                runtime.needle.control.assert_not_called()
                self.assertEqual(runtime.store.integrity(True), [])
            finally:
                runtime.close()
            runtime = Runtime(home)
            try:
                self.assertEqual(runtime.last_answer()["text"], "4")
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
