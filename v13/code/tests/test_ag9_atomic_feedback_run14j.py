"""Run14J test-first atomic bounded AG12 -> AG9 feedback and replay protection."""
from __future__ import annotations

import json
import math
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13.agi import hub
from v13.agi.generality import null_solver
from v13.agi.metacog import Metacognition, WINDOW
from v13.agi import solver as solver_module


class AG9AtomicFeedback(unittest.TestCase):
    def test_batch_matches_existing_sequential_pav_in_one_store_write(self):
        pairs = [(0.1 if i % 3 else 0.9, int(i % 7 == 0)) for i in range(88)]
        with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
            r1 = Runtime(Path(td1))
            r2 = Runtime(Path(td2))
            try:
                sequential = Metacognition(r1.store)
                for c, correct in pairs:
                    sequential.record("ag12:c3", c, correct)
                batch = Metacognition(r2.store)
                with patch.object(r2.store, "set_state", wraps=r2.store.set_state) as writes:
                    result = batch.record_batch("ag12:c3", pairs, receipt="a" * 64)
                self.assertEqual(result["status"], "RECORDED")
                self.assertEqual(writes.call_count, 1)
                self.assertEqual(batch.report("ag12:c3"), sequential.report("ag12:c3"))
                self.assertEqual(batch.box.load()[0]["components"]["ag12:c3"]["pairs"],
                                 sequential.box.load()[0]["components"]["ag12:c3"]["pairs"])
                self.assertEqual(len(batch.box.load()[0]["components"]["ag12:c3"]["receipts"]), 1)
            finally:
                r1.close()
                r2.close()

    def test_same_exact_ag12_run_replayed_twice_only_counts_once(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            runtime = Runtime(home)
            try:
                growth = hub(runtime)
                out = growth.eval.run(null_solver, include_results=True)
                self.assertIn("_feedback_nonce", out)
                self.assertEqual(len(out["_results"]), len(growth.eval.suite["items"]))
                solver_module._feed_metacog(growth, "c3", out)
                solver_module._feed_metacog(growth, "c3", out)
                comp = growth.metacog.box.load()[0]["components"]["ag12:c3"]
                self.assertEqual(len(comp["pairs"]), 88)
                self.assertEqual(len(comp["receipts"]), 1)
                newer = growth.eval.run(null_solver, include_results=True)
                self.assertNotEqual(out["_feedback_nonce"], newer["_feedback_nonce"])
                solver_module._feed_metacog(growth, "c3", newer)
                comp = growth.metacog.box.load()[0]["components"]["ag12:c3"]
                self.assertEqual(len(comp["pairs"]), 176)
                self.assertEqual(len(comp["receipts"]), 2)
                self.assertNotIn("_feedback_nonce", growth.eval.box.load()[0]["runs"][-1])
                self.assertNotIn("_feedback_nonce", json.loads((home / "exports/generality-last.json").read_text()))
                self.assertNotIn("_results", growth.eval.box.load()[0]["runs"][-1])
            finally:
                runtime.close()

    def test_sqlite_error_aborts_entire_atomic_batch_without_partial_rows(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                growth = hub(runtime)
                out = growth.eval.run(null_solver, include_results=True)
                original = runtime.store.set_state
                def fail_ag9(*args, **kwargs):
                    if args and args[0] == "G9_METACOGNITION":
                        raise sqlite3.OperationalError("injected AG9 write failure")
                    return original(*args, **kwargs)
                with patch.object(runtime.store, "set_state", side_effect=fail_ag9):
                    solver_module._feed_metacog(growth, "c3", out)
                self.assertNotIn("ag12:c3", growth.metacog.box.load()[0]["components"])
            finally:
                runtime.close()

    def test_invalid_batch_and_receipt_do_not_mutate_store(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                m = Metacognition(runtime.store)
                cases = [
                    ([], "a" * 64),
                    ([(0.1, 1)] * (WINDOW + 1), "a" * 64),
                    ([(math.nan, 1)], "a" * 64),
                    ([(0.1, True)], "a" * 64),
                    ([(0.1, 2)], "a" * 64),
                    ([(0.1, 1)], "not-a-receipt"),
                    ([(0.1, 1)], None),
                ]
                for pairs, receipt in cases:
                    with self.subTest(length=len(pairs), receipt=receipt):
                        with self.assertRaises(ValueError):
                            m.record_batch("ag12:c3", pairs, receipt=receipt)
                self.assertEqual(m.box.load()[0]["components"], {})
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
