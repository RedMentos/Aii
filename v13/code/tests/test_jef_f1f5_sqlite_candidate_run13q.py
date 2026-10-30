"""Run13Q isolated SQLite fault containment on real F1/F5 Store, SHADOW only."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import p2x_disjoint_receiver_trainset as cohort
from v13 import jef_f1f5_source_admission as admission
from v13.runtime import Runtime


class F1F5SQLiteCandidate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        rows = cohort.fixtures()
        cohort.validate(rows)
        row = next(x for x in rows if x["partition"] == "calibration")
        self.row = row
        project, domain = row["id"], row["domain"]
        self.ids = []
        for key, value in (
            (f"Project {project} archived {domain} policy", row["b2_source"]),
            (f"Project {project} latest {domain} option sheet", row["b1_source"]),
        ):
            event = self.r.store.event(self.r.session, "Record: " + key)
            mid = self.r.memory.feedback(
                event["event_id"], "fact", value, permission="record",
                key=key, scope="session")
            self.r.memory.candidate(mid, self.r.session)
            self.ids.append(mid)
        query = self.r.store.event(self.r.session, row["current"])
        self.event_id = query["event_id"]
        self.ref = query["source_ref"]

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def decision(self):
        return admission.decide(
            self.r.memory, self.r.session, self.event_id, self.ref, self.ids)

    def counts(self):
        return (self.r.store.one("SELECT count(*) AS n FROM sources")["n"],
                self.r.store.one("SELECT count(*) AS n FROM messages")["n"])

    def assert_denied(self, result):
        self.assertEqual(result["status"], "SHADOW_NO_AUTHORITY")
        self.assertEqual(result["admission_status"], "F1F5_DENIED_SHADOW")
        self.assertEqual(result["reason"], "F1F5_SOURCE_OR_LINEAGE_RED")
        self.assertEqual(result["suggested_action"], "UNKNOWN")
        self.assertEqual(result["authority"], 0)
        self.assertEqual(result["native_calls"], 0)
        self.assertFalse(result["model_called"])
        self.assertFalse(result["weight_updates"])
        self.assertFalse(result["human_source_lineage_verified"])
        self.assertEqual(result["jepa_weight"], 0)
        self.assertEqual(result["step2_status"], "UTILITY_FAIL")
        self.assertFalse(result["whole_system_complete"])

    def test_real_store_early_and_late_sqlite_faults_fail_closed(self):
        before = self.counts()
        cases = (
            (self.r.store, "one", sqlite3.OperationalError("DB read unavailable")),
            (self.r.store, "read_source", sqlite3.DatabaseError("source read failed")),
            (self.r.memory, "candidate", sqlite3.ProgrammingError("memory query failed")),
            (self.r.store, "rows", sqlite3.OperationalError("rows query failed")),
        )
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("NATIVE_CALLED")):
            for obj, method, fault in cases:
                with self.subTest(method=method, fault=type(fault).__name__):
                    with patch.object(obj, method, side_effect=fault):
                        result = self.decision()
                    self.assert_denied(result)
                    self.assertEqual(self.counts(), before)

    def test_positive_human_source_still_verified_without_model(self):
        before = self.counts()
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("NATIVE_CALLED")):
            result = self.decision()
        self.assertEqual(result["admission_status"],
                         "F1F5_SESSION_VERIFIED_SHADOW")
        self.assertTrue(result["human_source_lineage_verified"])
        self.assertEqual(result["suggested_action"], self.row["oracle_action"])
        self.assertEqual(result["authority"], 0)
        self.assertEqual(result["native_calls"], 0)
        self.assertEqual(self.counts(), before)


if __name__ == "__main__":
    unittest.main()
