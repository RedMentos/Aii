"""JEF live-current two HumanDecision source gate: real Store, no native."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import p2x_disjoint_receiver_trainset as cohort
from v13.runtime import Runtime
from v13 import jef_f1f5_source_admission as historical
from v13.jef_f1f5_live_current_candidate import decide_current_turn


class JefLiveCurrentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        rows = cohort.fixtures()
        cohort.validate(rows)
        self.calibration = sorted(
            (x for x in rows if x["partition"] == "calibration"),
            key=lambda x: x["id"])

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def record(self, key, value, scope="session"):
        event = self.r.store.event(self.r.session, "Record: " + key)
        mid = self.r.memory.feedback(
            event["event_id"], "fact", value, permission="record",
            key=key, scope=scope)
        self.r.memory.candidate(mid, self.r.session)
        return mid

    def sources(self, row, conflict=False):
        name, domain = row["id"], row["domain"]
        policy_key = f"Project {name} archived {domain} policy"
        sheet_key = f"Project {name} latest {domain} option sheet"
        policy = self.record(policy_key, row["b2_source"])
        sheet = self.record(sheet_key, row["b1_source"])
        if conflict:
            self.record(policy_key, row["b2_source"], scope="global")
        event = self.r.store.event(self.r.session, row["current"])
        return event, [policy, sheet]

    def live(self, event, ids, **kwargs):
        return decide_current_turn(
            self.r.memory, self.r.session, event["event_id"],
            event["source_ref"], ids, **kwargs)

    def counts(self):
        return tuple(self.r.store.one(
            "SELECT COUNT(*) AS n FROM " + table)["n"]
            for table in ("sources", "packets", "memories", "actions", "messages"))

    def assert_no_authority(self, result):
        self.assertEqual(result["authority"], 0)
        self.assertEqual(result["delivery_authority"], 0)
        self.assertFalse(result["output_committed"])
        self.assertEqual(result["tool_dispatches"], 0)
        self.assertEqual(result["learning_authority"], 0)
        self.assertFalse(result["native_proof"])
        self.assertFalse(result["model_called"])
        self.assertEqual(result["native_calls"], 0)
        self.assertFalse(result["user_approved"])
        self.assertFalse(result["weight_updates"])

    def test_36_live_positive_and_36_stale_negative_historical_control(self):
        live_pass = stale_red = historical_still_available = 0
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("NATIVE_MODEL_CALLED")):
            for row in self.calibration:
                event, ids = self.sources(row)
                before = self.counts()
                current = self.live(event, ids, operator_opt_in=True)
                live_pass += (current["suggested_action"] == row["oracle_action"]
                              and current["live_current_verified"] is True)
                self.assertEqual(current["live_current_status"],
                                 "JEF_LIVE_CURRENT_VERIFIED_SHADOW")
                self.assert_no_authority(current)
                self.assertEqual(self.counts(), before)
                self.r.store.event(self.r.session,
                                   "New authoritative user turn supersedes prior query.")
                before_stale = self.counts()
                stale = self.live(event, ids, operator_opt_in=True)
                stale_red += (stale["suggested_action"] == "UNKNOWN"
                              and stale["live_current_status"] == "STALE_USER_EVENT_RED")
                self.assertFalse(stale["live_current_verified"])
                self.assert_no_authority(stale)
                self.assertEqual(self.counts(), before_stale)
                old = historical.decide(
                    self.r.memory, self.r.session,
                    event["event_id"], event["source_ref"], ids)
                historical_still_available += (
                    old["suggested_action"] == row["oracle_action"])
        self.assertEqual((len(self.calibration), live_pass), (36, 36))
        self.assertEqual(stale_red, 36)
        self.assertEqual(historical_still_available, 36)

    def test_default_off_integer_one_and_forged_tty_refuse(self):
        event, ids = self.sources(self.calibration[0])
        before = self.counts()
        for kwargs in (
            {},
            {"operator_opt_in":1},
            {"operator_opt_in":False},
            {"operator_opt_in":True, "approval_receipt":{"approved":True}},
        ):
            with self.subTest(kwargs=kwargs):
                result = self.live(event, ids, **kwargs)
                self.assertEqual(result["suggested_action"], "UNKNOWN")
                self.assertFalse(result["live_current_verified"])
                self.assert_no_authority(result)
        self.assertEqual(self.counts(), before)

    def test_wrong_ref_and_cross_session_refuse(self):
        event, ids = self.sources(self.calibration[0])
        wrong = dict(event["source_ref"], char_end=event["source_ref"]["char_end"] - 1)
        result = decide_current_turn(
            self.r.memory, self.r.session, event["event_id"], wrong, ids,
            operator_opt_in=True)
        self.assertEqual(result["suggested_action"], "UNKNOWN")
        self.assertFalse(result["live_current_verified"])
        other = self.r.store.new_session("Foreign")
        foreign = decide_current_turn(
            self.r.memory, other, event["event_id"], event["source_ref"], ids,
            operator_opt_in=True)
        self.assertEqual(foreign["suggested_action"], "UNKNOWN")
        self.assert_no_authority(foreign)

    def test_revoked_sheet_and_hidden_conflict_refuse(self):
        event, ids = self.sources(self.calibration[0])
        self.r.memory.forget(ids[1])
        revoked = self.live(event, ids, operator_opt_in=True)
        self.assertEqual(revoked["suggested_action"], "UNKNOWN")
        self.assertFalse(revoked["live_current_verified"])
        row = self.calibration[1]
        conflict_event, conflict_ids = self.sources(row, conflict=True)
        conflicted = self.live(conflict_event, conflict_ids, operator_opt_in=True)
        self.assertEqual(conflicted["suggested_action"], "UNKNOWN")
        self.assertFalse(conflicted["live_current_verified"])

    def test_current_event_packet_tamper_refuses(self):
        event, ids = self.sources(self.calibration[0])
        packet = self.r.store.one(
            "SELECT packet FROM events WHERE id=?", (event["event_id"],))["packet"]
        forged = json.loads(packet)
        forged["source_ref"] = dict(event["source_ref"], char_end=0)
        with self.r.store.tx() as db:
            db.execute("UPDATE events SET packet=? WHERE id=?",
                       (json.dumps(forged), event["event_id"]))
        result = self.live(event, ids, operator_opt_in=True)
        self.assertEqual(result["suggested_action"], "UNKNOWN")
        self.assertFalse(result["live_current_verified"])
        self.assert_no_authority(result)


if __name__ == "__main__":
    unittest.main()
