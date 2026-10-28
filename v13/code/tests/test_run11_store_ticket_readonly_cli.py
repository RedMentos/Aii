"""Real SQLite read-only SHADOW operator CLI; no Runtime/model authority."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from scripts import run18_step2_balanced_controls as balanced
from scripts import run11_store_shadow_use_boundary as boundary
from scripts import run11_store_shadow_ticket_io as ticket_io
from scripts import run11_store_ticket_readonly_cli as cli
from v13.config import initialize
from v13.store import Store


class ReadOnlyTicketCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name) / "home"
        initialize(self.home)
        self.store = Store(self.home)
        self.session = self.store.new_session()
        self.case = next(c for c in balanced.FIXTURES if c["id"] == "Veldora")
        events = [self.store.event(self.session, text) for text in
                  (self.case["history"][0], self.case["history"][2],
                   self.case["current"])]
        self.refs = dict(zip(("old", "sheet", "current"),
                             (e["event_id"] for e in events)))
        self.private = self.home / "private-tickets"
        self.private.mkdir(mode=0o700)
        ticket = boundary.seal_candidate(
            self.store, self.session, self.case["id"], self.refs,
            self.case["temporal_mode"], "sheet")
        ticket_io.save_ticket(self.store, ticket, self.session,
                              self.case["id"], self.private, "candidate.json")

    def tearDown(self):
        if not self.store.closed:
            self.store.close()
        self.temp.cleanup()

    def args(self, **kw):
        fields = dict(home=str(self.home), session=self.session,
                      project=self.case["id"], directory=str(self.private),
                      filename="candidate.json")
        fields.update(kw)
        result = []
        for key, value in fields.items():
            result += ["--" + key, value]
        return result

    def invoke(self, **kw):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cli.main(self.args(**kw))
        return code, output.getvalue(), json.loads(output.getvalue())

    def test_live_coordinator_lock_and_shadow_only(self):
        code, stdout, result = self.invoke()
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "SHADOW_ONLY")
        self.assertEqual(result["action"], self.case["oracle"]["action"])
        self.assertIs(result["authority"], False)
        self.assertIs(result["f5_decision_authority"], False)
        self.assertIs(result["canonical_gate_pass"], False)
        self.assertIs(result["native_executed"], False)
        self.assertIs(result["model_output_used"], False)
        self.assertEqual(result["jepa_weight"], 0)
        self.assertIs(result["post_return_atomic"], False)
        for source in (self.case["history"][0], self.case["history"][2],
                       self.case["current"]):
            self.assertNotIn(source, stdout)
        self.assertNotIn(self.session, stdout)
        self.assertNotIn(str(self.home), stdout)

    def test_no_store_constructor_and_query_only(self):
        with mock.patch.object(Store, "__init__", side_effect=AssertionError("Store opened")):
            self.assertEqual(self.invoke()[0], 0)
        with cli.ReadOnlyStore(self.home) as reader:
            with self.assertRaises(sqlite3.OperationalError):
                reader.db.execute("CREATE TABLE forbidden_write(x INTEGER)")

    def test_closed_store_db_bytes_unchanged(self):
        self.store.close()
        db = self.home / "data/db/brain.sqlite3"
        before = hashlib.sha256(db.read_bytes()).hexdigest()
        self.assertEqual(self.invoke()[0], 0)
        self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(), before)

    def test_source_revocation_refused(self):
        with self.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=("
                       "SELECT source_id FROM events WHERE id=?)",
                       (self.refs["old"],))
        code, stdout, result = self.invoke()
        self.assertEqual(code, 2)
        self.assertEqual(result, {"status": "REFUSED", "authority": False,
                                  "canonical_gate_pass": False})
        self.assertNotIn(self.case["history"][0], stdout)

    def test_wrong_session_and_project_refused(self):
        for change in ({"session": "chat_wrong"}, {"project": "Other"}):
            with self.subTest(change=change):
                self.assertEqual(self.invoke(**change)[0], 2)

    def test_unsafe_directory_and_corrupt_ticket_refused(self):
        self.private.chmod(0o755)
        try:
            self.assertEqual(self.invoke()[0], 2)
        finally:
            self.private.chmod(0o700)
        (self.private / "candidate.json").write_text("{not-json", encoding="utf-8")
        self.assertEqual(self.invoke()[0], 2)

    def test_missing_home_is_not_created(self):
        missing = self.home.parent / "does-not-exist"
        self.assertFalse(missing.exists())
        self.assertEqual(self.invoke(home=str(missing))[0], 2)
        self.assertFalse(missing.exists())

    def test_subprocess_entrypoint_only_emits_sanitized_json(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
        result = subprocess.run(
            [sys.executable, "-m", "scripts.run11_store_ticket_readonly_cli",
             *self.args()], env=env, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "SHADOW_ONLY")
        self.assertEqual(result.stderr, "")
        self.assertNotIn(self.case["current"], result.stdout)


if __name__ == "__main__":
    unittest.main()
