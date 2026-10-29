"""Explicit local operator JEF F1/F5 SHADOW diagnostic; no live output or model."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import p2x_disjoint_receiver_trainset as cohort
from v13.operator import Operator
from v13.runtime import Runtime


class JefF1F5OperatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)
        self.row = next(r for r in cohort.fixtures()
                        if r["partition"] == "calibration")

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def record(self, key, value):
        event = self.r.store.event(self.r.session, "Record: " + key)
        mid = self.r.memory.feedback(
            event["event_id"], "fact", value, permission="record",
            key=key, scope="session")
        self.r.memory.candidate(mid, self.r.session)
        return mid

    def sources(self):
        row = self.row
        project, domain = row["id"], row["domain"]
        policy = self.record(
            f"Project {project} archived {domain} policy", row["b2_source"])
        sheet = self.record(
            f"Project {project} latest {domain} option sheet", row["b1_source"])
        event = self.r.store.event(self.r.session, row["current"])
        return event["event_id"], policy, sheet

    def cmd(self, event, policy, sheet):
        return f":jefsource {event} {policy} {sheet}"

    def counts(self):
        return tuple(self.r.store.one(
            f"SELECT count(*) AS n FROM {table}")["n"]
            for table in ("sources", "events", "feedback", "packets", "memories"))

    def test_explicit_command_full_source_no_native_no_mutation(self):
        event, policy, sheet = self.sources()
        before = self.counts()
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("NATIVE_MODEL_CALLED")):
            result = json.loads(self.op.run(self.cmd(event, policy, sheet)))
        self.assertEqual(result["suggested_action"], self.row["oracle_action"])
        self.assertEqual(result["admission_status"], "F1F5_SESSION_VERIFIED_SHADOW")
        self.assertEqual(result["status"], "SHADOW_NO_AUTHORITY")
        self.assertTrue(result["operator_diagnostic"])
        self.assertTrue(result["no_live_answer"])
        self.assertFalse(result["model_called"])
        self.assertEqual(result["native_calls"], 0)
        self.assertEqual(result["jepa_weight"], 0)
        self.assertFalse(result["ag6_approved"])
        self.assertEqual(self.counts(), before)
        self.assertIn(":jefsource", self.op.run(":help"))

    def test_revoked_source_fails_closed(self):
        event, policy, sheet = self.sources()
        self.r.memory.forget(sheet)
        result = json.loads(self.op.run(self.cmd(event, policy, sheet)))
        self.assertEqual(result["suggested_action"], "UNKNOWN")
        self.assertFalse(result["human_source_lineage_verified"])

    def test_foreign_session_event_rejected(self):
        event, policy, sheet = self.sources()
        other = self.r.store.new_session("other")
        foreign = self.r.store.event(other, self.row["current"])
        with self.assertRaisesRegex(ValueError, "CURRENT_SESSION_EVENT_REQUIRED"):
            self.op.run(self.cmd(foreign["event_id"], policy, sheet))
        self.assertEqual(json.loads(self.op.run(
            self.cmd(event, policy, sheet)))["suggested_action"],
            self.row["oracle_action"])

    def test_invalid_ids_and_missing_arguments_rejected(self):
        event, policy, sheet = self.sources()
        invalid = (":jefsource", ":jefsource " + event,
                   ":jefsource " + event + " " + policy,
                   ":jefsource " + event + " " + policy + " invalid",
                   ":jefsource " + event + " " + policy + " " + sheet + " extra",
                   ":jefsource " + event + " " + policy + " " + sheet + " --active")
        for command in invalid:
            with self.subTest(command=command), self.assertRaises(ValueError):
                self.op.run(command)

    def test_non_tty_and_nonidle_rejected(self):
        event, policy, sheet = self.sources()
        with self.assertRaisesRegex(ValueError, "Nur lokale Operator"):
            self.op.run(self.cmd(event, policy, sheet), origin="MODEL")
        with patch.object(self.r, "require_idle",
                          side_effect=ValueError("BUSY")):
            with self.assertRaisesRegex(ValueError, "BUSY"):
                self.op.run(self.cmd(event, policy, sheet))

    def test_age0_gate_rejects_nonrecord_and_latents(self):
        event, policy, sheet = self.sources()
        original = dict(self.r.cfg)
        try:
            for field, value in (("system_stage", 1),
                                 ("learning_mode", "SHADOW_UPDATE"),
                                 ("latents_enabled", True),
                                 ("jepa_weight", 1)):
                with self.subTest(field=field):
                    self.r.cfg[field] = value
                    with self.assertRaisesRegex(ValueError, "AGE0_RECORD_ONLY_REQUIRED"):
                        self.op.run(self.cmd(event, policy, sheet))
                    self.r.cfg[field] = original[field]
        finally:
            self.r.cfg.clear()
            self.r.cfg.update(original)

    def test_restart_persisted_command(self):
        event, policy, sheet = self.sources()
        before = json.loads(self.op.run(self.cmd(event, policy, sheet)))
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)
        after = json.loads(self.op.run(self.cmd(event, policy, sheet)))
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
