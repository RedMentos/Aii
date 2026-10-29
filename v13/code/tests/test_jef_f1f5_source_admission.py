"""Real F1/F5 HumanDecision and session-bound JEF typed source SHADOW tests."""
from __future__ import annotations
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import p2x_disjoint_receiver_trainset as cohort
from v13 import jef_f1f5_source_admission as admit
from v13.runtime import Runtime


class JefF1F5Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        rows = cohort.fixtures()
        cohort.validate(rows)
        self.rows = rows
        self.calibration = sorted(
            (x for x in rows if x["partition"] == "calibration"),
            key=lambda x: x["id"])

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def record(self, key, value, scope="session", materialize=True):
        e = self.r.store.event(self.r.session, "Record: " + key)
        mid = self.r.memory.feedback(
            e["event_id"], "fact", value, permission="record",
            key=key, scope=scope)
        if materialize:
            self.r.memory.candidate(mid, self.r.session)
        return mid

    def setup_sources(self, row, foreign=False):
        project = row["id"]
        domain = row["domain"]
        policy_key = f"Project {project} archived {domain} policy"
        sheet_key = f"Project {project} latest {domain} option sheet"
        policy = self.record(policy_key, row["b2_source"])
        sheet = self.record(sheet_key, row["b1_source"])
        foreign_id = None
        if foreign:
            foreign_text = cohort.foreign_sheet(row, self.rows)
            foreign_project = re.match(r"Project (P2X[0-9A-F]{16})", foreign_text).group(1)
            foreign_id = self.record(
                f"Project {foreign_project} latest {domain} option sheet",
                foreign_text)
        query = self.r.store.event(self.r.session, row["current"])
        return query["event_id"], query["source_ref"], policy, sheet, foreign_id

    def decision(self, event_id, current_ref, ids):
        return admit.decide(self.r.memory, self.r.session,
                            event_id, current_ref, ids)

    def test_36_human_f1f5_full_and_144_negative_real_store(self):
        full, negatives = [], []
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("NATIVE_MODEL_CALLED")):
            for row in self.calibration:
                event, ref, policy, sheet, foreign = self.setup_sources(row, foreign=True)
                cases = {
                    "c3_only": [], "b1_only": [sheet],
                    "b2_only": [policy], "both_exact": [policy, sheet],
                    "shuffled": [policy, foreign],
                }
                before = self.r.store.one("SELECT count(*) AS n FROM sources")["n"]
                for arm, ids in cases.items():
                    result = self.decision(event, ref, ids)
                    self.assertEqual(result["status"], "SHADOW_NO_AUTHORITY")
                    self.assertEqual((result["model_called"], result["native_calls"]),
                                     (False, 0))
                    self.assertEqual(result["authority"], 0)
                    self.assertFalse(result["user_approved"])
                    self.assertEqual(self.r.store.one(
                        "SELECT count(*) AS n FROM sources")["n"], before)
                    if arm == "both_exact":
                        full.append(result["suggested_action"] == row["oracle_action"])
                        self.assertTrue(result["human_source_lineage_verified"])
                        self.assertEqual(result["admission_status"],
                                         "F1F5_SESSION_VERIFIED_SHADOW")
                    else:
                        negatives.append(result["suggested_action"] == "UNKNOWN")
        self.assertEqual((len(full), sum(full)), (36, 36))
        self.assertEqual((len(negatives), sum(negatives)), (144, 144))

    def test_restart_then_actual_forget_revokes(self):
        row = self.calibration[0]
        event, ref, policy, sheet, _ = self.setup_sources(row)
        before = self.decision(event, ref, [policy, sheet])
        self.assertTrue(before["human_source_lineage_verified"])
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        after = self.decision(event, ref, [policy, sheet])
        self.assertEqual(before, after)
        self.r.memory.forget(sheet)
        revoked = self.decision(event, ref, [policy, sheet])
        self.assertEqual(revoked["suggested_action"], "UNKNOWN")
        self.assertFalse(revoked["human_source_lineage_verified"])

    def test_superseded_old_memory_denied(self):
        row = self.calibration[0]
        event, ref, policy, sheet, _ = self.setup_sources(row)
        key = f"Project {row['id']} latest {row['domain']} option sheet"
        replacement = self.record(key, row["b1_source"])
        self.assertNotEqual(sheet, replacement)
        self.assertEqual(self.decision(event, ref, [policy, sheet])["suggested_action"],
                         "UNKNOWN")
        self.assertEqual(self.decision(event, ref, [policy, replacement])["suggested_action"],
                         row["oracle_action"])

    def test_cross_session_and_global_conflict_denied(self):
        row = self.calibration[0]
        event, ref, policy, sheet, _ = self.setup_sources(row)
        self.assertTrue(self.decision(event, ref, [policy, sheet])[
            "human_source_lineage_verified"])
        # A second active global correction to the same topic must veto admission.
        key = f"Project {row['id']} archived {row['domain']} policy"
        self.record(key, row["b2_source"], scope="global")
        self.assertEqual(self.decision(event, ref, [policy, sheet])["suggested_action"],
                         "UNKNOWN")
        other_session = self.r.store.new_session("Other")
        other_event = self.r.store.event(other_session, row["current"])
        result = admit.decide(self.r.memory, other_session, other_event["event_id"],
                              other_event["source_ref"], [policy, sheet])
        self.assertEqual(result["suggested_action"], "UNKNOWN")

    def test_missing_f5_packet_or_feedback_denied(self):
        row = self.calibration[0]
        event, ref, policy, sheet, _ = self.setup_sources(row)
        memory = self.r.memory.candidate(sheet, self.r.session)
        sid = memory["source_id"]
        packets = self.r.store.rows("SELECT id,payload FROM packets WHERE kind='HumanDecision'")
        matching = [p["id"] for p in packets
                    if json.loads(p["payload"]).get("source_ref", {}).get("source_id") == sid]
        self.assertEqual(len(matching), 1)
        with self.r.store.tx() as c:
            c.execute("DELETE FROM packets WHERE id=?", (matching[0],))
        result = self.decision(event, ref, [policy, sheet])
        self.assertEqual(result["suggested_action"], "UNKNOWN")
        self.assertFalse(result["human_source_lineage_verified"])

    def test_missing_key_ref_does_not_create_source_during_admission(self):
        row = self.calibration[0]
        project, domain = row["id"], row["domain"]
        policy = self.record(
            f"Project {project} archived {domain} policy", row["b2_source"],
            materialize=False)
        sheet = self.record(
            f"Project {project} latest {domain} option sheet", row["b1_source"],
            materialize=False)
        query = self.r.store.event(self.r.session, row["current"])
        before = self.r.store.one("SELECT count(*) AS n FROM sources")["n"]
        result = self.decision(query["event_id"], query["source_ref"], [policy, sheet])
        self.assertEqual(result["suggested_action"], "UNKNOWN")
        self.assertEqual(result["reason"], "F1F5_KEY_PROVENANCE_NOT_MATERIALIZED")
        self.assertEqual(self.r.store.one(
            "SELECT count(*) AS n FROM sources")["n"], before)

    def test_wrong_event_ref_and_stale_event_denied(self):
        row = self.calibration[0]
        event, ref, policy, sheet, _ = self.setup_sources(row)
        other = self.r.store.event(self.r.session, "Project Another. Irrelevant.")
        for eid, source in ((event, dict(ref, char_end=ref["char_end"] - 1)),
                            (other["event_id"], ref),
                            ("evt_" + "0" * 32, ref)):
            with self.subTest(eid=eid):
                self.assertEqual(self.decision(eid, source,
                                               [policy, sheet])["suggested_action"],
                                 "UNKNOWN")

    def test_no_authority_no_learning_no_native_calls(self):
        row = self.calibration[0]
        event, ref, policy, sheet, _ = self.setup_sources(row)
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("NATIVE_MODEL_CALLED")):
            result = self.decision(event, ref, [policy, sheet])
        self.assertEqual(result["admission_status"], "F1F5_SESSION_VERIFIED_SHADOW")
        self.assertFalse(result["weight_updates"])
        self.assertEqual(result["jepa_weight"], 0)
        self.assertEqual(result["step2_status"], "UTILITY_FAIL")
        self.assertFalse(result["whole_system_complete"])


if __name__ == "__main__":
    unittest.main()
