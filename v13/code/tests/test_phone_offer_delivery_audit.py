"""Offline SQLite regressions for metadata-only B1/B2/C3 receipt attribution."""
import json
import sqlite3
from pathlib import Path
import tempfile
import unittest

from v13.phone_offer_delivery_audit import audit, connect_readonly, SCHEMA


class PhoneOfferAudit(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.executescript("""
            CREATE TABLE messages(
                id INTEGER PRIMARY KEY, event_id TEXT, status TEXT,
                metadata TEXT, role TEXT, text TEXT
            );
            CREATE TABLE packets(
                id TEXT PRIMARY KEY, event_id TEXT, kind TEXT, payload TEXT
            );
            CREATE TABLE telemetry(
                id INTEGER PRIMARY KEY, event_id TEXT, kind TEXT, metrics TEXT
            );
        """)

    def tearDown(self):
        self.db.close()

    def record(self, table, columns, values):
        self.db.execute(
            "INSERT INTO " + table + "(" + ",".join(columns) + ") VALUES (" +
            ",".join("?" for _ in columns) + ")", values)

    def message(self, event, *, ids=(), role="C3_LANGUAGE", status="FINAL"):
        self.record("messages", ("event_id","status","metadata","role","text"), (
            event,status,json.dumps({"selected_offer_ids":list(ids),
            "runner":{"role":role,"generated_tokens":12,
                      "prompt_tokens":521,"stage_durations_s":{
                          "load_s":2.2,"prefill_to_first_token_s":12.39}}}),
            "assistant","PRIVATE HUMAN CHAT NEVER OUTPUT"))

    def packet(self, event, role, pid, kind="OfferPacket"):
        self.record("packets", ("id","event_id","kind","payload"),
                    (pid,event,kind,json.dumps({
                        "role":role,"target_role":role,
                        "evidence_refs":[{"source_id":"PRIVATE_SOURCE"}],
                        "offer":{"summary":"PRIVATE MODEL THOUGHT"}})))

    def log(self, event, kind, role, **metrics):
        self.record("telemetry", ("event_id","kind","metrics"),
                    (event,kind,json.dumps({"role":role,**metrics})))

    def test_timeout_has_no_phantom_b1_and_b2_reaches_single_c3(self):
        event="evt_protected"
        self.message(event,ids=("pkt_b2",))
        self.packet(event,"B1_DETAIL","pkt_q1","QueryPacket")
        self.packet(event,"B2_GIST","pkt_q2","QueryPacket")
        self.packet(event,"B2_GIST","pkt_b2")
        self.log(event,"body_offer_attempt","B1_DETAIL",status="DEADLINE",
                 runner={"last_phase":"prefill","duration_s":43.1,
                         "prompt_tokens":0,"generated_tokens":0,
                         "stage_durations_s":{"load_s":2.1,"template_s":.6}})
        self.log(event,"body_offer_attempt","B2_GIST",status="FINAL",
                 runner={"last_phase":"stream","duration_s":9.2})
        self.log(event,"body_offer_delivered","B2_GIST",status="FINAL",
                 packet_id="pkt_b2",count=1)
        result=audit(self.db)
        self.assertEqual(result["schema"],SCHEMA)
        self.assertEqual(result["turn_count"],1)
        self.assertEqual(result["roles"]["B1_DETAIL"]["native_failed_turns"],1)
        self.assertEqual(result["roles"]["B2_GIST"]["in_final_c3_report_turns"],1)
        row=result["turns"][0]
        self.assertEqual(row["roles"]["B1_DETAIL"]["delivery"],"NATIVE_FAILED_NO_OFFER")
        self.assertEqual(row["roles"]["B1_DETAIL"]["last_native"]["last_phase"],"prefill")
        self.assertEqual(row["roles"]["B1_DETAIL"]["last_native"]["duration_s"],43.1)
        self.assertEqual(row["roles"]["B2_GIST"]["delivery"],"IN_FINAL_C3_REPORT")
        self.assertEqual(row["c3_phase_seconds"]["prefill_to_first_token_s"],12.39)
        self.assertNotIn("PRIVATE",json.dumps(result))
        self.assertNotIn(event,json.dumps(result))

    def test_native_final_without_valid_packet_is_not_a_delivered_offer(self):
        self.message("e2")
        self.log("e2","body_offer_attempt","B1_DETAIL",status="FINAL",
                 runner={"status":"FINAL","generated_tokens":80})
        result=audit(self.db,1)
        self.assertEqual(result["turns"][0]["roles"]["B1_DETAIL"]["delivery"],
                         "NATIVE_COMPLETED_NO_VALID_OFFER")
        self.assertEqual(result["turns"][0]["roles"]["B1_DETAIL"]["delivery_receipts"],0)

    def test_legacy_packet_without_receipt_distinguished(self):
        self.message("e3")
        self.packet("e3","B2_GIST","pkt_legacy")
        result=audit(self.db,1)
        self.assertEqual(result["turns"][0]["roles"]["B2_GIST"]["delivery"],
                         "LEGACY_PACKET_NO_RECEIPT")

    def test_only_selected_source_bound_offers_count_as_report(self):
        self.message("e4",ids=("pkt_b1",),status="ERROR")
        self.packet("e4","B1_DETAIL","pkt_b1")
        self.packet("e4","B2_GIST","pkt_b2")
        self.log("e4","body_offer_delivered","B1_DETAIL",packet_id="pkt_b1")
        self.log("e4","body_offer_delivered","B2_GIST",packet_id="pkt_b2")
        roles=audit(self.db,1)["turns"][0]["roles"]
        self.assertEqual(roles["B1_DETAIL"]["delivery"],"SELECTED_BUT_REPORT_UNFINISHED")
        self.assertEqual(roles["B2_GIST"]["delivery"],"DELIVERED_NOT_SELECTED")

    def test_bounded_limit_and_bad_private_metadata_are_ignored(self):
        self.message("e5")
        self.db.execute("UPDATE messages SET metadata=?",('{"secret":"PRIVATE"}',))
        self.assertNotIn("PRIVATE",json.dumps(audit(self.db)))
        for bad in (0,21,True,-1,"1"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                audit(self.db,bad)

    def test_connection_is_read_only_and_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp)
            folder=home/"data"/"db"
            folder.mkdir(parents=True)
            path=folder/"brain.sqlite3"
            with sqlite3.connect(path) as db:
                db.execute("CREATE TABLE safe(x INTEGER)")
            with connect_readonly(home) as db:
                with self.assertRaises(sqlite3.OperationalError):
                    db.execute("INSERT INTO safe VALUES (1)")
            path.rename(folder/"original")
            path.symlink_to(folder/"original")
            with self.assertRaises(ValueError):
                connect_readonly(home)


if __name__=="__main__":
    unittest.main()
