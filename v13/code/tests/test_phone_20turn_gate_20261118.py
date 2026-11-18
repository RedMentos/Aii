"""Local SQLite 20-turn acceptance-preflight regressions, synthetic only."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from v13.phone_20turn_gate import check, main, SCHEMA
from v13.native_offer_prompt_receipt import inspect


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
                        (eid, "body_offer_attempt", json.dumps({
                            "role": role, "status": "FINAL",
                            "runner": {"role": role, "status": "FINAL",
                                       "generated_tokens": 5, "prompt_tokens": 60}})))
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
        self.assertEqual(out["both_body_selected_quoted_metadata_receipt_turns"], 20)
        self.assertEqual(out["both_body_native_template_http200_reported_turns"], 20)
        self.assertEqual(out["body_roles"]["B1_DETAIL"]["attempt"], 20)
        self.assertEqual(out["body_roles"]["B2_GIST"]["attempt"], 20)
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
        self.assertEqual(out["both_body_selected_quoted_metadata_receipt_turns"], 0)
        self.assertEqual(out["both_body_native_template_http200_reported_turns"], 0)
        self.assertEqual(out["body_roles"]["B1_DETAIL"]["selected_delivered_quoted_metadata"], 0)
        self.assertEqual(out["local_status"], "NO_BOTH_BODY_SELECTED_QUOTED_RECEIPTS")

    def test_offers_with_no_native_b1_b2_attempt_telemetry_cannot_credit_body(self):
        self.seed()
        self.db.execute("DELETE FROM telemetry WHERE kind='body_offer_attempt'")
        out = check(self.db)
        self.assertEqual(out["native_c3_final_positive_token_turns"], 20)
        self.assertEqual(out["both_body_selected_quoted_metadata_receipt_turns"], 0)
        self.assertEqual(out["both_body_native_template_http200_reported_turns"], 0)
        self.assertEqual(out["local_status"], "NO_BOTH_BODY_SELECTED_QUOTED_RECEIPTS")
        self.assertFalse(out["release_approved"])

    def test_c3_tokens_without_native_template_witness_cannot_reach_ready_status(self):
        def missing(_, m):
            m["runner"].pop("native_offer_prompt_receipt")
            return m
        self.seed(metadata=missing)
        out = check(self.db)
        self.assertEqual(out["both_body_selected_quoted_metadata_receipt_turns"], 20)
        self.assertEqual(out["both_body_native_template_http200_reported_turns"], 0)
        self.assertEqual(out["local_status"],
                         "NO_BOTH_BODY_NATIVE_TEMPLATE_SUBMISSION_WITNESS")
        self.assertFalse(out["release_approved"])

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

    def test_deeply_nested_private_telemetry_fails_closed_without_traceback(self):
        self.seed()
        self.db.execute(
            "INSERT INTO telemetry(event_id,kind,metrics) VALUES(?,?,?)",
            ("event_S1_19", "body_offer_attempt",
             "[" * 1200 + "0" + "]" * 1200))
        out = check(self.db)
        self.assertEqual(out["local_status"],
                         "MALFORMED_OR_AMBIGUOUS_TURN_METADATA")
        self.assertGreater(out["invalid_or_oversized_metadata_turns"], 0)
        self.assertFalse(out["release_approved"])
        self.assertNotIn("SECRET", json.dumps(out))

    def test_readonly_existing_sqlite_cli_preserves_db_and_exposes_no_text(self):
        self.seed()
        self.db.commit()
        with tempfile.TemporaryDirectory(prefix="v13-20turn-readonly-") as tmp:
            home = Path(tmp) / "v13"
            (home / "data/db").mkdir(parents=True)
            dbpath = home / "data/db/brain.sqlite3"
            target = sqlite3.connect(dbpath)
            try:
                self.db.backup(target)
            finally:
                target.close()
            before = hashlib.sha256(dbpath.read_bytes()).hexdigest()
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["--home", str(home)])
            self.assertEqual(code, 0)
            report = json.loads(stdout.getvalue())
            self.assertEqual(report["assistant_turns_scanned"], 20)
            self.assertEqual(report["local_status"],
                             "LOCAL_METADATA_COHORT_COMPLETE_DEVICE_REVIEW_REQUIRED")
            self.assertEqual(before, hashlib.sha256(dbpath.read_bytes()).hexdigest())
            for suffix in ("-wal", "-shm", "-journal"):
                self.assertFalse(dbpath.with_name(dbpath.name + suffix).exists())
            self.assertNotIn("SECRET", stdout.getvalue())
            self.assertNotIn(str(home), stdout.getvalue())

    def test_invalid_local_database_does_not_leak_owner_path(self):
        with tempfile.TemporaryDirectory(prefix="v13-private-path-SECRET-") as tmp:
            home = Path(tmp) / "v13"
            (home / "data/db").mkdir(parents=True)
            (home / "data/db/brain.sqlite3").write_bytes(b"NOT_A_SQLITE_DB")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["--home", str(home)])
            self.assertEqual(code, 2)
            result = json.loads(output.getvalue())
            self.assertEqual(result["local_status"], "LOCAL_READ_UNAVAILABLE_ValueError")
            self.assertFalse(result["release_approved"])
            self.assertNotIn("SECRET", output.getvalue())
            self.assertNotIn(str(home), output.getvalue())

    def test_composed_stage_carries_readonly_gate_and_cli(self):
        code = Path(__file__).resolve().parents[1]
        stage_path = code / "scripts/stage_integrated_candidate.py"
        spec = importlib.util.spec_from_file_location("v13_phone_20turn_stage", stage_path)
        stager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stager)
        with tempfile.TemporaryDirectory(prefix="v13-20turn-stage-") as tmp:
            installed = Path(tmp) / "code"
            stager.stage(code, installed)
            for rel in ("v13/phone_20turn_gate.py",
                        "v13/phone_offer_delivery_audit.py",
                        "v13/native_offer_prompt_receipt.py"):
                self.assertEqual(
                    hashlib.sha256((code / rel).read_bytes()).hexdigest(),
                    hashlib.sha256((installed / rel).read_bytes()).hexdigest())
            no_db = Path(tmp) / "empty-v13"
            proc = subprocess.run(
                [sys.executable, "-P", "-m", "v13.phone_20turn_gate",
                 "--home", str(no_db)],
                cwd=installed,
                env=dict(os.environ, PYTHONPATH=str(installed),
                         PYTHONDONTWRITEBYTECODE="1"),
                text=True, capture_output=True, timeout=60)
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            report = json.loads(proc.stdout)
            self.assertEqual(report["local_status"], "LOCAL_READ_UNAVAILABLE_ValueError")
            self.assertNotIn(str(no_db), proc.stdout)
            self.assertNotIn("SECRET", proc.stdout)

    def test_widened_exact_quote_from_existing_analyst_consumer_is_supported(self):
        # cognition.Cognition.analyst_context also uses this exact typed
        # verification when the excerpt is a widened source sentence.
        # Stacked core #2054 must not silently regress this live producer.
        span = "A longer source sentence around the exact quote."
        body = [{
            "role": "B1_DETAIL", "offer_packet_id": "b1",
            "hypothesis": {"summary": "source hypothesis",
                           "uncertainty": "low", "needs_reentry": False},
            "verified_quotes": [{
                "text": span,
                "source_ref": {"source_id": "src_ref", "sha256": "a" * 64,
                               "char_start": 0, "char_end": len(span),
                               "modality": "text"},
                "verification": "EXACT_SOURCE_SENTENCES_POINTED_BY_QUOTE"}]}]
        head = "Internal hypotheses: "
        system = "trusted-rules" + chr(10) + head + json.dumps(body, sort_keys=True)
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": "Please answer."}]
        output = inspect(messages, system + "Please answer.", head)
        self.assertEqual(output["status"], "RENDERED_WITH_QUOTES")
        self.assertEqual(output["offers"][0]["rendered_quote_count"], 1)
        self.assertNotIn(span, json.dumps(output))

    def test_empty_cohort_is_unavailable(self):
        out = check(self.db)
        self.assertEqual(out["local_status"], "NO_LATEST_CHAT_SESSION")
        self.assertIs(out["release_approved"], False)


if __name__ == "__main__":
    unittest.main()
