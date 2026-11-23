"""Run74 human F1/F5 mixed-range JEF source admission: real SQLite only."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import jef_c3_c5_c6_operator_cli as cli
from tests.test_jef_range_policy_shadow import TABLE, texts
from v13 import jef_f1f5_range_admission_shadow as admission


class HumanRangeAdmission(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = cli.Runtime(Path(self.tmp.name))

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def prepare(self, row):
        current, policy, sheet = texts(row)
        project, domain = row[:2]
        ids = []
        for key, value in (
            (f"Project {project} archived {domain} policy", policy),
            (f"Project {project} latest {domain} option sheet", sheet),
        ):
            e = self.r.store.event(self.r.session, "Record: " + key)
            mid = self.r.memory.feedback(e["event_id"], "fact", value,
                                         permission="record", key=key,
                                         scope="session")
            self.r.memory.candidate(mid, self.r.session)
            ids.append(mid)
        event = self.r.store.event(self.r.session, current)
        return event, ids

    def invoke(self, event, ids, **kw):
        return admission.decide(
            self.r.memory, self.r.session, event["event_id"],
            event["source_ref"], ids, operator_opt_in=True, **kw)

    def assert_no_authority(self, result):
        self.assertEqual(result["status"], "SHADOW_NO_AUTHORITY")
        self.assertEqual(result["authority"], 0)
        self.assertEqual(result["delivery_authority"], 0)
        self.assertEqual(result["learning_authority"], 0)
        self.assertFalse(result["user_approved"])
        self.assertFalse(result["model_called"])
        self.assertFalse(result["output_committed"])
        self.assertFalse(result["real_tty_approved"])
        self.assertFalse(result["native_proof"])
        self.assertEqual(result["jepa_weight"], 0)
        self.assertFalse(result["whole_system_complete"])
        self.assertNotIn("policy_source", result)
        self.assertNotIn("sheet_source", result)

    def test_six_real_human_records_mixed_range_and_no_model(self):
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("NATIVE_CALLED")):
            for row in TABLE:
                with self.subTest(project=row[0]):
                    event, ids = self.prepare(row)
                    before = self.r.store.one(
                        "SELECT COUNT(*) AS n FROM actions")["n"]
                    result = self.invoke(event, ids)
                    self.assertEqual(result["admission_status"],
                                     admission.READY)
                    self.assertTrue(result["human_source_lineage_verified"])
                    self.assertEqual(result["suggested_action"], row[-1])
                    self.assertEqual(len(result["memory_id_hashes"]), 2)
                    self.assertEqual(self.r.store.one(
                        "SELECT COUNT(*) AS n FROM actions")["n"], before)
                    self.assert_no_authority(result)

    def test_default_off_and_tty_receipt_denied(self):
        event, ids = self.prepare(TABLE[0])
        result = admission.decide(
            self.r.memory, self.r.session, event["event_id"],
            event["source_ref"], ids)
        self.assertEqual(result["reason"], "OFF")
        self.assertFalse(result["human_source_lineage_verified"])
        self.assert_no_authority(result)
        result = self.invoke(event, ids, approval_receipt={"approved": True})
        self.assertEqual(result["reason"], "REAL_TTY_APPROVAL_UNSUPPORTED")
        self.assert_no_authority(result)

    def test_newer_user_event_denied(self):
        event, ids = self.prepare(TABLE[0])
        self.r.store.event(self.r.session, "New unrelated user request")
        result = self.invoke(event, ids)
        self.assertEqual(result["suggested_action"], "UNKNOWN")
        self.assertFalse(result["human_source_lineage_verified"])
        self.assert_no_authority(result)

    def test_revoked_source_denied(self):
        event, ids = self.prepare(TABLE[1])
        self.r.memory.forget(ids[1])
        result = self.invoke(event, ids)
        self.assertEqual(result["suggested_action"], "UNKNOWN")
        self.assertFalse(result["human_source_lineage_verified"])
        self.assert_no_authority(result)

    def test_duplicate_missing_and_foreign_memory_denied(self):
        event, ids = self.prepare(TABLE[2])
        for mids in ([ids[0]], [ids[0], ids[0]], ["mem_invalid", ids[1]]):
            result = self.invoke(event, mids)
            self.assertEqual(result["suggested_action"], "UNKNOWN")
            self.assertFalse(result["human_source_lineage_verified"])
            self.assert_no_authority(result)

    def test_other_session_and_forged_ref_denied(self):
        event, ids = self.prepare(TABLE[3])
        other = self.r.store.new_session("foreign")
        result = admission.decide(
            self.r.memory, other, event["event_id"], event["source_ref"],
            ids, operator_opt_in=True)
        self.assertEqual(result["suggested_action"], "UNKNOWN")
        self.assert_no_authority(result)
        forged = dict(event["source_ref"], sha256="0" * 64)
        result = admission.decide(
            self.r.memory, self.r.session, event["event_id"], forged,
            ids, operator_opt_in=True)
        self.assertEqual(result["suggested_action"], "UNKNOWN")
        self.assert_no_authority(result)

    def test_hidden_same_key_conflict_denied(self):
        event, ids = self.prepare(TABLE[4])
        key = f"Project {TABLE[4][0]} archived {TABLE[4][1]} policy"
        e = self.r.store.event(self.r.session, "Record: " + key)
        new_id = self.r.memory.feedback(e["event_id"], "fact",
                                        texts(TABLE[4])[1],
                                        permission="record", key=key,
                                        scope="session")
        self.r.memory.candidate(new_id, self.r.session)
        # Restore an authoritative latest current event so this test does
        # not pass solely due to the stale-user veto.
        current = self.r.store.event(self.r.session, texts(TABLE[4])[0])
        result = self.invoke(current, ids)
        self.assertEqual(result["suggested_action"], "UNKNOWN")
        self.assertFalse(result["human_source_lineage_verified"])
        self.assert_no_authority(result)

    def test_wrong_project_memory_denied(self):
        event, ids = self.prepare(TABLE[5])
        other = TABLE[0]
        other_key = f"Project {other[0]} archived {other[1]} policy"
        e = self.r.store.event(self.r.session, "Record: " + other_key)
        other_mid = self.r.memory.feedback(
            e["event_id"], "fact", texts(other)[1],
            permission="record", key=other_key, scope="session")
        self.r.memory.candidate(other_mid, self.r.session)
        current = self.r.store.event(self.r.session, texts(TABLE[5])[0])
        result = self.invoke(current, [other_mid, ids[1]])
        self.assertEqual(result["suggested_action"], "UNKNOWN")
        self.assert_no_authority(result)


if __name__ == "__main__":
    unittest.main()
