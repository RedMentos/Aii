"""Local SQLite 20-turn acceptance-preflight regressions, synthetic only."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from v13.phone_20turn_gate import check, main, SCHEMA


class TwentyTurnCohort(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.executescript("""
            CREATE TABLE messages(
                id INTEGER PRIMARY KEY, session_id TEXT, event_id TEXT,
                status TEXT, metadata TEXT, role TEXT, text TEXT);
            CREATE TABLE packets(
                id TEXT PRIMARY KEY, event_id TEXT, kind TEXT, payload TEXT);
            CREATE TABLE telemetry(
                id INTEGER PRIMARY KEY, event_id TEXT, kind TEXT, metrics TEXT);
        """)

    def tearDown(self):
        self.db.close()

    def seed(self, *, count=20, session="S1", metadata=None,
             status="FINAL", start=0, offers=True):
        for n in range(start, start + count):
            eid = f"event_{session}_{n}"
            def native():
                return {"role": "C3_LANGUAGE", "status": "FINAL", "generated_tokens": 9,
                        "ttft_s": .8, "prompt_tokens": 60,
                        "sampled_peak_rss_bytes": 1024 * 1024 * 200,
                        "native_offer_prompt_receipt": {
                            "revision": "v13.native-offer-prompt-receipt/1",
                            "status": "RENDERED_WITH_QUOTES", "native_template_rendered": True,
                            "native_template_submitted": True, "native_completion_http_200": True,
                            "source_span_revalidated_here": False,
                            "native_semantic_use_proven": False,
                            "offers": [{"role": r, "packet_id": f"{r}_{eid}",
                                        "rendered_quote_count": 1}
                                       for r in ("B1_DETAIL", "B2_GIST")]}}
            data = {"model_generated": True, "runner": native(), "duration_s": 5.,
                    "effective_config": {"deadline_seconds": 30},
                    "selected_offer_ids": [f"{r}_{eid}" for r in ("B1_DETAIL", "B2_GIST")],
                    "model_private_note": "SECRET_MESSAGE_SHOULD_NOT_EXPORT"}
            if metadata:
                data = metadata(n, data)
            self.db.execute(
                "INSERT INTO messages(session_id,event_id,status,metadata,role,text) "
                "VALUES(?,?,?,?,?,?)",
                (session, eid, status, json.dumps(data), "assistant", "SECRET_MODEL_TEXT"))
            if offers:
                for role in ("B1_DETAIL", "B2_GIST"):
                    packet_id = f"{role}_{eid}"
                    self.db.execute(
                        "INSERT INTO packets(id,event_id,kind,payload) VALUES(?,?,?,?)",
                        (packet_id, eid, "OfferPacket", json.dumps({
                            "role": role, "evidence_refs": [{"source_id": "SECRET_REF"}],
                            "offer": {"summary": "PRIVATE_HYPOTHESIS"}})))
                    self.db.execute(
                        "INSERT INTO telemetry(event_id,kind,metrics) VALUES(?,?,?)",
                        (eid, "body_offer_delivered",
                         json.dumps({"role": role, "packet_id": packet_id})))

    def test_twenty_synthetic_rows_are_only_metadata_ready_not_phone_proof(self):
        self.seed()
        before = self.db.total_changes
        out = check(self.db)
        self.assertEqual(self.db.total_changes, before)
        self.assertEqual(out["schema"], SCHEMA)
        self.assertEqual(out["local_status"],
                         "LOCAL_METADATA_COHORT_COMPLETE_DEVICE_REVIEW_REQUIRED")
        self.assertEqual(out["assistant_turns_scanned"], 20)
        self.assertEqual(out["native_c3_final_positive_token_turns"], 20)
        self.assertEqual(out["both_body_selected_source_quote_receipt_turns"], 20)
        self.assertEqual(out["both_body_native_template_http200_reported_turns"], 20)
        self.assertEqual(out["native_within_declared_deadline_turns"], 20)
        self.assertEqual(out["native_ttft_sampled_turns"], 20)
        self.assertEqual(out["maximum_turn_seconds"], 5.)
        self.assertEqual(out["maximum_runner_reported_rss_mib"], 200.)
        for field in ("release_approved", "answer_quality_verified",
                      "mixed_task_suite_verified", "native_latent_communication_verified",
                      "device_physical_execution_independently_verified"):
            self.assertIs(out[field], False)
        raw = json.dumps(out)
        for secret in ("SECRET", "event_S1_", "PRIVATE_HYPOTHESIS",
                       '"session_id": "S1"', "src_identifier", "model_private_note"):
            self.assertNotIn(secret, raw)

    def test_latest_session_only_does_not_combine_old_successes(self):
        self.seed(count=20, session="OLD")
        self.seed(count=1, session="LATEST", start=40)
        out = check(self.db)
        self.assertEqual(out["assistant_turns_scanned"], 1)
        self.assertEqual(out["local_status"], "FEWER_THAN_20_ASSISTANT_EVENTS")
        self.assertEqual(out["native_c3_final_positive_token_turns"], 1)

    def test_latest_user_session_without_answer_blocks_stale_success(self):
        self.seed(count=20, session="OLD")
        self.db.execute(
            "INSERT INTO messages(session_id,event_id,status,metadata,role,text) "
            "VALUES(?,?,?,?,?,?)",
            ("NEW", "pending_new", "FINAL", "{}", "user", "SECRET_NEW_PROMPT"))
        out = check(self.db)
        self.assertEqual(out["local_status"], "NO_ASSISTANT_EVENTS_IN_LATEST_SESSION")
        self.assertEqual(out["assistant_turns_scanned"], 0)

    def test_boolean_token_false_and_non_model_system_answer_cannot_pass(self):
        def bad(_, m):
            m["runner"]["generated_tokens"] = False
            return m
        self.seed(metadata=bad)
        out = check(self.db)
        self.assertEqual(out["native_c3_final_positive_token_turns"], 0)
        self.assertEqual(out["local_status"],
                         "NATIVE_C3_EXECUTION_NOT_RECORDED_FOR_ALL_TURNS")
        self.db.execute("DELETE FROM messages")
        self.db.execute("DELETE FROM packets")
        self.db.execute("DELETE FROM telemetry")
        def report(_, m):
            m["output_authority"] = "SOURCE_SYSTEM_REPORT"
            return m
        self.seed(metadata=report)
        self.assertEqual(check(self.db)["native_c3_final_positive_token_turns"], 0)

    def test_nonfinal_answer_never_counts_even_with_native_tokens(self):
        self.seed(status="DEADLINE")
        out = check(self.db)
        self.assertEqual(out["native_c3_final_positive_token_turns"], 0)
        self.assertEqual(out["local_status"], "NONFINAL_TURNS_IN_COHORT")
        self.assertEqual(out["status_counts"]["DEADLINE"], 20)

    def test_missing_native_timings_or_budget_is_not_ready(self):
        self.seed(metadata=lambda _, m: (m["runner"].pop("ttft_s"), m)[1])
        out = check(self.db)
        self.assertEqual(out["local_status"], "MISSING_NATIVE_FIRST_TOKEN_TIMINGS")
        self.db.execute("DELETE FROM messages")
        self.db.execute("DELETE FROM packets")
        self.db.execute("DELETE FROM telemetry")
        self.seed(metadata=lambda _, m: (m.pop("effective_config"), m)[1])
        self.assertEqual(check(self.db)["local_status"], "MISSING_NATIVE_DEADLINE_EVIDENCE")

    def test_deadline_overrun_without_changing_final_status(self):
        self.seed(metadata=lambda _, m: (m.update(duration_s=30.01), m)[1])
        out = check(self.db)
        self.assertEqual(out["local_status"], "NATIVE_DEADLINE_EXCEEDED")
        self.assertEqual(out["native_within_declared_deadline_turns"], 0)

    def test_missing_or_tampered_quote_receipts_stay_separate(self):
        self.seed(offers=False)
        out = check(self.db)
        self.assertEqual(out["native_c3_final_positive_token_turns"], 20)
        self.assertEqual(out["both_body_selected_source_quote_receipt_turns"], 0)
        self.assertEqual(out["both_body_native_template_http200_reported_turns"], 0)
        self.assertEqual(out["body_roles"]["B1_DETAIL"]["selected_delivered"], 0)

    def test_duplicate_event_ids_and_malformed_metadata_fail_closed(self):
        self.seed()
        row = self.db.execute(
            "SELECT id,event_id FROM messages WHERE role='assistant' "
            "ORDER BY id DESC LIMIT 1").fetchone()
        self.db.execute("UPDATE messages SET event_id=? WHERE id=?", (row[1], row[0]-1))
        self.assertEqual(check(self.db)["local_status"],
                         "MALFORMED_OR_AMBIGUOUS_TURN_METADATA")
        self.assertGreater(check(self.db)["duplicate_assistant_event_ids"], 0)
        self.db.execute("DELETE FROM messages")
        self.db.execute("DELETE FROM packets")
        self.db.execute("DELETE FROM telemetry")
        self.seed()
        self.db.execute("UPDATE messages SET metadata=? WHERE id=1",
                        ("{secret:" + "SECRET" * 100_000 + "}",))
        out = check(self.db)
        self.assertEqual(out["local_status"], "MALFORMED_OR_AMBIGUOUS_TURN_METADATA")
        self.assertGreater(out["invalid_or_oversized_metadata_turns"], 0)
        self.assertNotIn("SECRET", json.dumps(out))

    def test_empty_cohort_is_unavailable(self):
        out = check(self.db)
        self.assertEqual(out["local_status"], "NO_LATEST_CHAT_SESSION")
        self.assertIs(out["release_approved"], False)


if __name__ == "__main__":
    unittest.main()
