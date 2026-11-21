"""Real SQLite checks for bounded, private phone last-turn diagnostics."""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest import mock

from v13 import mobile_dashboard as ui
from v13 import phone_runtime_diagnostics as diagnostic


class LastTurnTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "v13"
        self.path = self.home / "data/db/brain.sqlite3"
        patch = mock.patch.object(diagnostic, "DATA_HOME", self.home)
        patch.start()
        self.addCleanup(patch.stop)

    def database(self, *, wal=False):
        self.path.parent.mkdir(parents=True)
        connection = sqlite3.connect(self.path)
        if wal:
            connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("""CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, text TEXT,
            status TEXT, metadata TEXT, session_id TEXT, event_id TEXT, created REAL)""")
        connection.commit()
        return connection

    def insert(self, connection, *, status="FINAL", metadata=None, role="assistant", created=0):
        connection.execute("""INSERT INTO messages
            (role,text,status,metadata,session_id,event_id,created) VALUES (?,?,?,?,?,?,?)""",
            (role, "PRIVATE_CHAT_TEXT", status, json.dumps(metadata if metadata is not None else {}),
             "PRIVATE_SESSION_ID", "PRIVATE_EVENT_ID", created))
        connection.commit()

    def snapshot(self):
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.path.parent.iterdir() if not p.name.endswith("-shm")}

    def test_latest_assistant_uses_id_and_excludes_newer_user_teacher_and_private_fields(self):
        connection = self.database()
        self.insert(connection, status="FINAL", created=10000)
        self.insert(connection, status="DEADLINE", metadata={
            "error": "Limits", "detail": "PRIVATE_TRACEBACK /private/device/path",
            "failure_stage": "memory_recall", "turn_stage": "finished", "duration_s": 90.2,
            "stage_marks_s": {"ingress": 0, "memory_recall": 2.5, "finished": 90.2},
            "effective_config": {"deadline_seconds": 90, "threads": 4,
                                 "context_tokens": 2048, "answer_tokens": 256,
                                 "prompts": "PRIVATE_PROMPT"},
            "runner": {"last_phase": "prefill", "status": "DEADLINE", "duration_s": 87.7,
                       "generated_tokens": 0, "requested_tokens": 256,
                       "stage_durations_s": {"load_s": 2.1, "template_s": .2},
                       "actual_model": "/private/model", "resource_samples": ["PRIVATE_SAMPLE"]},
            "context_source_refs": ["PRIVATE_SOURCE_REF"], "event_id": "PRIVATE_EVENT_ID",
        }, created=-1)
        self.insert(connection, role="user", status="FINAL", created=20000)
        self.insert(connection, role="teacher", status="FINAL", created=30000)
        connection.close()
        before = self.snapshot()
        result = diagnostic.last_turn()
        self.assertEqual(result["availability"], "AVAILABLE")
        self.assertEqual(result["status"], "DEADLINE")
        self.assertEqual(result["error_class"], "Limits")
        self.assertEqual(result["error_kind"], "MODEL_TIMEOUT")
        self.assertEqual(result["failure_stage"], "memory_recall")
        self.assertEqual(result["stage_marks_s"]["finished"], 90.2)
        self.assertEqual(result["effective_config"]["deadline_seconds"], 90)
        self.assertEqual(result["runner"]["last_phase"], "prefill")
        self.assertEqual(result["runner"]["generated_tokens"], 0)
        self.assertNotIn("PRIVATE", json.dumps(result))
        self.assertNotIn("/private", json.dumps(result))
        self.assertEqual(self.snapshot(), before)

    def test_real_prompt_admission_receipts_are_metadata_only_and_allowlisted(self):
        connection=self.database()
        self.insert(connection,status="DEADLINE",metadata={
            "runner":{"status":"DEADLINE","prompt_tokens":270,"generated_tokens":0,
                "prompt_admission":{
                    "revision":"v13.native-prompt-admission/1",
                    "status":"PROTECTED_CONTEXT_EXCEEDS_TIME_TARGET",
                    "original_prompt_tokens":617,"prompt_tokens":270,
                    "target_tokens":260,
                    "removed_layers":["C3_LAYER_TASK_CONTEXT","PRIVATE_SOURCE_PATH",
                                      "OLD_NATIVE_HISTORY"]+["OLD_NATIVE_HISTORY"]*100,
                    "source_text_rewritten":False,
                    "private_text":"PRIVATE_CHAT_BODY","source_ref":"PRIVATE_REF"}}})
        connection.close()
        before=self.snapshot()
        item=diagnostic.last_turn()
        admission=item["runner"]["prompt_admission"]
        self.assertEqual(admission["original_prompt_tokens"],617)
        self.assertEqual(admission["target_tokens"],260)
        self.assertEqual(admission["removed_layers"][0],"C3_LAYER_TASK_CONTEXT")
        self.assertLessEqual(len(admission["removed_layers"]),12)
        self.assertFalse(admission["source_text_rewritten"])
        self.assertNotIn("PRIVATE",json.dumps(item))
        self.assertEqual(self.snapshot(),before)

    def test_unknown_prompt_admission_revision_does_not_cross_private_boundary(self):
        connection=self.database()
        self.insert(connection,status="FINAL",metadata={"runner":{
            "prompt_admission":{"revision":"v13.native-prompt-admission/PRIVATE",
                "source_text":"PRIVATE_TEXT","removed_layers":["PRIVATE"]}}})
        connection.close()
        result=diagnostic.last_turn()
        self.assertNotIn("prompt_admission",result["runner"])
        self.assertNotIn("PRIVATE",json.dumps(result))

    def test_live_wal_includes_uncheckpointed_latest_turn_without_changing_db_or_wal(self):
        connection = self.database(wal=True)
        try:
            self.insert(connection, status="FINAL")
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            main_before = self.path.read_bytes()
            self.insert(connection, status="ERROR", metadata={"error": "MemoryError",
                                                              "failure_stage": "native_answer"})
            self.assertEqual(self.path.read_bytes(), main_before, "new row exists only in WAL")
            before = self.snapshot()
            names = sorted(p.name for p in self.path.parent.iterdir())
            result = diagnostic.last_turn()
            self.assertEqual(result["status"], "ERROR")
            self.assertEqual(result["error_kind"], "OUT_OF_MEMORY")
            self.assertEqual(self.snapshot(), before)
            self.assertEqual(sorted(p.name for p in self.path.parent.iterdir()), names)
        finally:
            connection.close()

    def test_missing_does_not_create_database_or_directories(self):
        before = list(self.root.iterdir())
        self.assertEqual(diagnostic.last_turn()["reason"], "DATABASE_MISSING")
        self.assertEqual(list(self.root.iterdir()), before)

    def test_stopped_wal_store_does_not_create_coordination_files(self):
        connection = self.database(wal=True)
        self.insert(connection)
        connection.close()
        before = self.snapshot()
        self.assertEqual(diagnostic.last_turn()["reason"], "WAL_COORDINATION_UNAVAILABLE")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(sorted(p.name for p in self.path.parent.iterdir()), ["brain.sqlite3"])

    def test_database_and_parent_and_sidecar_symlinks_are_rejected(self):
        connection = self.database()
        connection.close()
        target = self.root / "target.sqlite3"
        self.path.replace(target)
        self.path.symlink_to(target)
        with mock.patch.object(diagnostic.sqlite3, "connect") as connect:
            self.assertEqual(diagnostic.last_turn()["reason"], "UNSAFE_PATH")
            connect.assert_not_called()
        self.path.unlink()
        target.replace(self.path)
        sidecar = self.path.with_name(self.path.name + "-wal")
        sidecar.symlink_to(self.path)
        self.assertEqual(diagnostic.last_turn()["reason"], "UNSAFE_PATH")
        sidecar.unlink()
        actual = self.root / "actual-db"
        self.path.parent.rename(actual)
        self.path.parent.symlink_to(actual, target_is_directory=True)
        self.assertEqual(diagnostic.last_turn()["reason"], "UNSAFE_PATH")

    def test_locked_database_returns_busy_with_short_timeout(self):
        connection = self.database()
        try:
            self.insert(connection)
            before = self.snapshot()
            connection.execute("BEGIN EXCLUSIVE")
            started = time.monotonic()
            with mock.patch.object(diagnostic, "READ_TIMEOUT_SECONDS", .03):
                result = diagnostic.last_turn()
            self.assertEqual(result["reason"], "DATABASE_BUSY")
            self.assertLess(time.monotonic() - started, 1)
            self.assertEqual(self.snapshot(), before)
        finally:
            connection.rollback()
            connection.close()

    def test_oversize_and_invalid_metadata_are_explicitly_unavailable(self):
        connection = self.database()
        for value, reason in ((json.dumps({"detail": "PRIVATE" * 1000}), "METADATA_TOO_LARGE"),
                              ("not json PRIVATE", "INVALID_METADATA"),
                              ('{"duration_s":NaN}', "INVALID_METADATA"),
                              ('{"runner":{"duration_s":Infinity}}', "INVALID_METADATA"),
                              ("[]", "INVALID_METADATA")):
            with self.subTest(reason=reason):
                connection.execute("DELETE FROM messages")
                connection.execute("INSERT INTO messages (role,status,metadata) VALUES ('assistant','ERROR',?)", (value,))
                connection.commit()
                with mock.patch.object(diagnostic, "MAX_METADATA_BYTES", 1024):
                    result = diagnostic.last_turn()
                self.assertEqual(result["availability"], "UNAVAILABLE")
                self.assertEqual(result["reason"], reason)
                self.assertNotIn("PRIVATE", json.dumps(result))
        connection.close()

    def test_malicious_metadata_exports_only_known_enums_and_bounded_finite_numbers(self):
        connection = self.database()
        self.insert(connection, status="ERROR", metadata={
            "error": "PRIVATE_EXCEPTION", "failure_stage": "PRIVATE_STAGE", "turn_stage": "finished",
            "stage_marks_s": {"PRIVATE_STAGE": 7, "finished": 90, "ingress": True,
                              "policy_check": -1, "native_answer": 1e100},
            "effective_config": {"threads": "PRIVATE_THREADS", "answer_tokens": 1e100,
                                 "deadline_seconds": 90, "context_tokens": True,
                                 "unknown": 123, "body_residency_mb": 1800},
            "runner": {"last_phase": "PRIVATE_PHASE", "status": "PRIVATE_STATUS",
                       "generated_tokens": "PRIVATE_TOKEN_TEXT", "ttft_s": -1,
                       "duration_s": 10**400, "requested_tokens": 256,
                       "stage_durations_s": {"load_s": 2, "PRIVATE_STAGE": 1},
                       "token_ids": [1, 2, 3]},
        })
        connection.close()
        result = diagnostic.last_turn()
        self.assertEqual(result["availability"], "AVAILABLE")
        self.assertEqual(result["error_kind"], "OTHER_EXCEPTION")
        self.assertNotIn("error_class", result)
        self.assertNotIn("failure_stage", result)
        self.assertEqual(result["stage_marks_s"], {"finished": 90})
        self.assertEqual(result["effective_config"], {"deadline_seconds": 90, "body_residency_mb": 1800})
        self.assertEqual(result["runner"], {"requested_tokens": 256, "stage_durations_s": {"load_s": 2}})
        self.assertNotIn("PRIVATE", json.dumps(result))

    def test_read_scan_is_bounded_and_empty_or_invalid_database_is_explicit(self):
        connection = self.database()
        self.assertEqual(diagnostic.last_turn()["reason"], "NO_ASSISTANT_MESSAGES")
        self.insert(connection)
        connection.executemany("INSERT INTO messages (role,status,metadata) VALUES ('user','FINAL','{}')",
                               [()] * 2000)
        connection.commit()
        with mock.patch.object(diagnostic, "MAX_VM_STEPS", 1000):
            self.assertEqual(diagnostic.last_turn()["reason"], "READ_LIMIT")
        connection.close()
        self.path.write_bytes(b"PRIVATE_INVALID_DATABASE")
        self.assertEqual(diagnostic.last_turn()["reason"], "INVALID_DATABASE")

    def test_query_is_read_only_and_never_reads_text_or_identifiers(self):
        connection = self.database()
        self.insert(connection)
        connection.close()
        original_connect = sqlite3.connect
        original_authorizer = diagnostic._authorizer
        columns, statements, options = [], [], []
        def connect(*args, **kwargs):
            options.append((args, kwargs))
            result = original_connect(*args, **kwargs)
            result.set_trace_callback(statements.append)
            return result
        def authorizer(action, arg1, arg2, database, source):
            if action == sqlite3.SQLITE_READ:
                columns.append(arg2)
            return original_authorizer(action, arg1, arg2, database, source)
        before = self.snapshot()
        with mock.patch.object(diagnostic.sqlite3, "connect", side_effect=connect), \
             mock.patch.object(diagnostic, "_authorizer", side_effect=authorizer):
            self.assertEqual(diagnostic.last_turn()["availability"], "AVAILABLE")
        self.assertIn("mode=ro", options[0][0][0])
        self.assertTrue(options[0][1]["uri"])
        self.assertTrue(any(statement == "PRAGMA query_only=ON" for statement in statements))
        self.assertEqual(set(columns), {"status", "metadata", "role", "id"})
        self.assertTrue(all(statement.startswith(("SELECT", "PRAGMA")) for statement in statements))
        self.assertEqual(self.snapshot(), before)

    def test_summary_includes_current_turn_when_native_probe_is_missing(self):
        connection = self.database()
        self.insert(connection, status="DEADLINE", metadata={"error": "Limits", "failure_stage": "routing"})
        connection.close()
        with mock.patch.object(ui, "DATA", self.home), \
             mock.patch.object(ui, "PRIVATE", self.root / "private"), \
             mock.patch("v13.chat_service.call", return_value={"running": True}):
            result = ui.summary()
        self.assertEqual(result["native_probe"], "NO_PROBE")
        self.assertEqual(result["last_turn"]["status"], "DEADLINE")
        self.assertEqual(result["last_turn"]["failure_stage"], "routing")
        self.assertNotIn("PRIVATE", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
