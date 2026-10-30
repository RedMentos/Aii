"""Run13H: SQLite read failures must not escape read-only JEF diagnostics."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from v13.agi.context_source_link_budget_run13e import propose_pointer
from v13.operator import Operator
from v13.runtime import Runtime

PACKET = "pkt_" + "a" * 32
QUERY = "evt_" + "b" * 32
SOURCE = "evt_" + "c" * 32


class Run13HSqliteFailureContainment(unittest.TestCase):
    def _assert_denied(self, value):
        self.assertEqual(value["status"], "SHADOW_NO_AUTHORITY")
        self.assertIsNone(value["answer"])
        self.assertIsNone(value["candidate"])
        self.assertEqual(value["delivery_authority"], 0)
        self.assertEqual(value["native_calls"], 0)
        self.assertFalse(value["weight_updates"])
        self.assertEqual(value["learning_mode"], "RECORD_ONLY")
        self.assertEqual(value["step2_status"], "UTILITY_FAIL")
        self.assertEqual(value["b3_status"], "NO_PROMOTION")
        self.assertEqual(value["jepa_weight"], 0)
        self.assertFalse(value["whole_system_complete"])

    def _fault(self, runtime, prefix, error_type):
        real_one = runtime.store.one
        def fail_selected_query(sql, args=()):
            if sql.startswith(prefix):
                raise error_type("selected SQLite read failure")
            return real_one(sql, args)
        return patch.object(runtime.store, "one", side_effect=fail_selected_query)

    def test_last_sqlite_errors_fail_closed(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                runtime.sleep.cycle.set_policy("enabled", "off")
                for cls in (sqlite3.DatabaseError, sqlite3.OperationalError):
                    with self.subTest(error=cls.__name__):
                        with self._fault(runtime, "SELECT p.id,p.event_id,p.payload", cls):
                            got = json.loads(Operator(runtime).run(":jeflink last"))
                        self._assert_denied(got)
            finally:
                runtime.close()

    def test_explicit_sqlite_errors_fail_closed(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                runtime.sleep.cycle.set_policy("enabled", "off")
                for cls in (sqlite3.DatabaseError, sqlite3.OperationalError):
                    with self.subTest(error=cls.__name__):
                        with self._fault(runtime, "SELECT session_id FROM events", cls):
                            got = json.loads(Operator(runtime).run(
                                f":jeflink {PACKET} {QUERY} {SOURCE}"))
                        self._assert_denied(got)
            finally:
                runtime.close()

    def test_proposer_sqlite_errors_fail_closed(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                for cls in (sqlite3.DatabaseError, sqlite3.OperationalError):
                    with self.subTest(error=cls.__name__):
                        with self._fault(runtime, "SELECT event_id,payload FROM packets", cls):
                            got = propose_pointer(runtime.store, PACKET, QUERY, SOURCE)
                        self._assert_denied(got)
            finally:
                runtime.close()

    def test_idle_preflight_sqlite_error_is_contained(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                with patch.object(runtime.store, "one",
                                  side_effect=sqlite3.OperationalError("idle read failure")):
                    got = json.loads(Operator(runtime).run(":jeflink last"))
                self._assert_denied(got)
            finally:
                runtime.close()

    def test_malformed_explicit_ids_still_rejected_before_store_read(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                with patch.object(runtime.store, "one", side_effect=AssertionError("DB touched")):
                    with self.assertRaises(ValueError):
                        Operator(runtime).run(":jeflink not-a-packet " + QUERY + " " + SOURCE)
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
