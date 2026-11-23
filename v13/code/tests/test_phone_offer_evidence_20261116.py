"""Adversarial metadata-only end-to-end offer attribution (no native/device claim)."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.phone_offer_delivery_audit import SCHEMA, audit, connect_readonly


class OfferEvidence(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.executescript("""
            CREATE TABLE messages(id INTEGER PRIMARY KEY, event_id TEXT,
                status TEXT, metadata TEXT, role TEXT, text TEXT);
            CREATE TABLE packets(id TEXT PRIMARY KEY, event_id TEXT,
                kind TEXT, payload TEXT);
            CREATE TABLE telemetry(id INTEGER PRIMARY KEY, event_id TEXT,
                kind TEXT, metrics TEXT);
        """)

    def tearDown(self):
        self.db.close()

    def assistant(self, event="E", selected=(), status="FINAL", tokens=12,
                  runner_role="C3_LANGUAGE", metadata=None):
        meta = metadata if metadata is not None else {
            "selected_offer_ids": list(selected),
            "runner": {"role": runner_role, "generated_tokens": tokens,
                       "prompt_tokens": 541},
        }
        self.db.execute(
            "INSERT INTO messages(event_id,status,metadata,role,text) VALUES(?,?,?,?,?)",
            (event, status, json.dumps(meta), "assistant", "SECRET USER TEXT"))

    def packet(self, role, pid, *, evidence=True, event="E"):
        data = {"role": role, "offer": {"summary": "SECRET HYPOTHESIS"},
                "evidence_refs": [{"source_id": "SECRET_REF"}] if evidence else []}
        self.db.execute("INSERT INTO packets(id,event_id,kind,payload) VALUES(?,?,?,?)",
                        (pid, event, "OfferPacket", json.dumps(data)))

    def receipt(self, role, pid, event="E"):
        self.db.execute(
            "INSERT INTO telemetry(event_id,kind,metrics) VALUES(?,?,?)",
            (event, "body_offer_delivered",
             json.dumps({"role": role, "status": "FINAL", "packet_id": pid})))

    def test_selected_packet_without_matching_receipt_is_not_proven(self):
        self.assistant(selected=("b1-selected",))
        self.packet("B1_DETAIL", "b1-selected")
        self.packet("B1_DETAIL", "b1-other")
        self.receipt("B1_DETAIL", "b1-other")
        t = audit(self.db)["turns"][0]
        role = t["roles"]["B1_DETAIL"]
        self.assertEqual(role["delivery"], "SELECTED_WITHOUT_DELIVERY_RECEIPT")
        self.assertEqual(role["delivery_receipts"], 1)
        self.assertEqual(role["selected_delivery_receipts"], 0)
        self.assertEqual(audit(self.db)["end_to_end_gate"]["status"],
                         "B1_B2_TO_C3_CHAIN_NOT_OBSERVED")

    def test_selected_packet_with_no_receipt_wont_pass_from_final_c3(self):
        self.assistant(selected=("b2",))
        self.packet("B2_GIST", "b2")
        r = audit(self.db)
        self.assertEqual(r["roles"]["B2_GIST"]["in_final_c3_report_turns"], 0)
        self.assertEqual(r["turns"][0]["roles"]["B2_GIST"]["delivery"],
                         "SELECTED_WITHOUT_DELIVERY_RECEIPT")

    def test_zero_token_final_or_wrong_reporter_never_passes(self):
        for tokens, role in ((0, "C3_LANGUAGE"), (12, "B2_GIST"),
                             (False, "C3_LANGUAGE"), (None, "C3_LANGUAGE")):
            with self.subTest(tokens=tokens, role=role):
                self.db.execute("DELETE FROM messages")
                self.db.execute("DELETE FROM packets")
                self.db.execute("DELETE FROM telemetry")
                self.assistant(selected=("b1",), tokens=tokens, runner_role=role)
                self.packet("B1_DETAIL", "b1")
                self.receipt("B1_DETAIL", "b1")
                out = audit(self.db)["turns"][0]
                self.assertNotEqual(out["roles"]["B1_DETAIL"]["delivery"],
                                    "IN_FINAL_C3_REPORT")
                self.assertFalse(out["c3_native_output_observed"])

    def test_selected_receipt_c3_output_is_still_not_prompt_proof(self):
        self.assistant(selected=("b1", "b2"))
        self.packet("B1_DETAIL", "b1", evidence=True)
        self.packet("B2_GIST", "b2", evidence=False)
        self.receipt("B1_DETAIL", "b1")
        self.receipt("B2_GIST", "b2")
        r = audit(self.db)
        self.assertEqual(r["schema"], SCHEMA)
        self.assertEqual(r["evidence_boundary"],
                         "METADATA_RECEIPTS_AND_NATIVE_TOKEN_COUNTS_ONLY")
        self.assertEqual(r["roles"]["B1_DETAIL"]["in_final_c3_report_turns"], 1)
        self.assertEqual(r["roles"]["B2_GIST"]["in_final_c3_report_turns"], 1)
        self.assertEqual(r["turns"][0]["roles"]["B1_DETAIL"]["selected_quoted_receipts"], 1)
        self.assertEqual(r["turns"][0]["roles"]["B2_GIST"]["selected_quoted_receipts"], 0)
        self.assertFalse(r["turns"][0]["c3_prompt_inclusion_proven"])
        self.assertFalse(r["turns"][0]["c3_semantic_use_proven"])
        self.assertFalse(r["turns"][0]["native_latent_exchange_proven"])
        # B2 has an unquoted hypothesis: matching delivery receipts and C3
        # tokens are insufficient for a positive two-hemisphere evidence gate.
        self.assertEqual(
            r["end_to_end_gate"]["both_body_selected_delivered_and_c3_generated_turns"], 0)
        self.assertEqual(r["end_to_end_gate"]["status"],
                         "B1_B2_TO_C3_CHAIN_NOT_OBSERVED")
        self.assertFalse(r["end_to_end_gate"]["native_prompt_offer_inclusion_verified"])
        self.assertNotIn("SECRET", json.dumps(r))

    def test_two_quote_bearing_receipts_with_c3_output_still_only_metadata(self):
        self.assistant(selected=("b1", "b2"))
        self.packet("B1_DETAIL", "b1", evidence=True)
        self.packet("B2_GIST", "b2", evidence=True)
        self.receipt("B1_DETAIL", "b1")
        self.receipt("B2_GIST", "b2")
        out = audit(self.db)
        gate = out["end_to_end_gate"]
        self.assertEqual(gate["status"], "BOTH_BODY_C4_C3_METADATA_ONLY")
        self.assertEqual(gate["both_body_selected_delivered_and_c3_generated_turns"], 1)
        self.assertFalse(gate["source_span_revalidated_by_audit"])
        self.assertFalse(gate["native_prompt_offer_inclusion_verified"])
        self.assertFalse(gate["learned_latent_exchange_verified"])
        self.assertNotIn("SECRET", json.dumps(out))

    def test_untrusted_metadata_does_not_crash_or_leak(self):
        cases = [
            {"selected_offer_ids": 123,
             "runner": {"role": "C3_LANGUAGE", "generated_tokens": 4}},
            {"selected_offer_ids": [{"id": "SECRET"}, False, None, []],
             "runner": {"role": "C3_LANGUAGE", "generated_tokens": 4}},
            {"selected_offer_ids": ["b1"], "runner": {
                "role": "C3_LANGUAGE", "generated_tokens": 0,
                "prompt_admission": {"revision": "v13.native-prompt-admission/1",
                   "status": {"private": "SECRET"},
                   "removed_layers": [{"private": "SECRET"}, "OLD_NATIVE_HISTORY"]}}},
        ]
        for meta in cases:
            with self.subTest(meta=str(type(meta.get("selected_offer_ids")))):
                self.db.execute("DELETE FROM messages")
                self.assistant(metadata=meta)
                got = audit(self.db)
                self.assertEqual(got["turn_count"], 1)
                self.assertNotIn("SECRET", json.dumps(got))

    def test_malformed_native_status_and_receipt_ids_fail_closed(self):
        self.assistant(selected=("b1",), status="FINAL", tokens=12)
        self.packet("B1_DETAIL", "b1")
        self.db.execute(
            "INSERT INTO telemetry(event_id,kind,metrics) VALUES(?,?,?)",
            ("E", "body_offer_attempt",
             json.dumps({"role": "B1_DETAIL", "status": {"x": "SECRET"},
                         "runner": {"last_phase": "prefill"}})))
        self.db.execute(
            "INSERT INTO telemetry(event_id,kind,metrics) VALUES(?,?,?)",
            ("E", "body_offer_delivered",
             json.dumps({"role": "B1_DETAIL", "packet_id": ["SECRET"]})))
        t = audit(self.db)["turns"][0]
        self.assertEqual(t["roles"]["B1_DETAIL"]["delivery"],
                         "SELECTED_WITHOUT_DELIVERY_RECEIPT")
        self.assertEqual(t["roles"]["B1_DETAIL"]["last_native"]["native_status"],
                         "UNKNOWN")
        self.assertNotIn("SECRET", json.dumps(t))


    def test_metadata_and_packet_payloads_are_bounded_before_json_parse(self):
        self.assistant(metadata={"selected_offer_ids": ["p"],
                                 "padding": "SECRET" * 70000,
                                 "runner": {"role": "C3_LANGUAGE",
                                            "generated_tokens": 1}})
        self.packet("B1_DETAIL", "p")
        self.receipt("B1_DETAIL", "p")
        result = audit(self.db)
        self.assertEqual(result["turn_count"], 1)
        self.assertNotIn("SECRET", json.dumps(result))
        self.assertEqual(result["turns"][0]["roles"]["B1_DETAIL"]["delivery"],
                         "DELIVERED_NOT_SELECTED")

    def test_row_cap_never_reports_partial_evidence_as_success(self):
        self.assistant(selected=("p",))
        self.packet("B1_DETAIL", "p")
        self.receipt("B1_DETAIL", "p")
        self.receipt("B1_DETAIL", "p")
        self.receipt("B1_DETAIL", "p")
        with patch("v13.phone_offer_delivery_audit.MAX_ROWS_PER_TURN", 2):
            out = audit(self.db)
        self.assertTrue(out["turns"][0]["audit_incomplete"])
        self.assertEqual(out["turns"][0]["roles"]["B1_DETAIL"]["delivery"],
                         "INCOMPLETE_AUDIT_ROW_CAP")
        self.assertEqual(out["roles"]["B1_DETAIL"]["in_final_c3_report_turns"], 0)
        self.assertEqual(out["end_to_end_gate"]["status"],
                         "BOUNDED_METADATA_INCOMPLETE")

    def test_deadline_without_first_native_token_is_not_success(self):
        self.assistant(selected=(), status="DEADLINE", tokens=0)
        gate = audit(self.db)["end_to_end_gate"]
        self.assertEqual(gate["c3_deadline_zero_token_turns"], 1)
        self.assertEqual(gate["status"], "B1_B2_TO_C3_CHAIN_NOT_OBSERVED")
        self.assertEqual(gate["device_functional_acceptance"], "NOT_VERIFIED")

    def test_empty_database_is_not_a_successful_native_run(self):
        gate = audit(self.db)["end_to_end_gate"]
        self.assertEqual(gate["status"], "NO_ASSISTANT_TURNS")
        self.assertEqual(gate["both_body_selected_delivered_and_c3_generated_turns"], 0)

    def test_missing_wal_sidecars_and_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            dbdir = home / "data" / "db"
            dbdir.mkdir(parents=True)
            file = dbdir / "brain.sqlite3"
            with sqlite3.connect(file) as db:
                db.execute("CREATE TABLE sample(x INTEGER)")
            raw = bytearray(file.read_bytes())
            raw[18:20] = b"\x02\x02"
            file.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, "WAL coordination"):
                connect_readonly(home)
            wal = dbdir / "brain.sqlite3-wal"
            wal.symlink_to(file)
            with self.assertRaisesRegex(ValueError, "sidecar"):
                connect_readonly(home)


if __name__ == "__main__":
    unittest.main()
