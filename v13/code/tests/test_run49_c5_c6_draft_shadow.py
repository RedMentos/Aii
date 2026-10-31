"""Run49 disjoint real Store/SQLite C5->C6 DRAFT SHADOW integration tests."""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from v13.agi import jef_c3_c5_c6_draft_shadow_run49 as gate
from v13.config import initialize
from v13.store import Store

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run49_c5_c6_draft_shadow_seed431.json"
SHA256 = "dd7f99895ebb3c425cfa86d9c3dfc18fde0e55a5303ed226aed4c4b9644c02ee"


class C5C6DraftShadowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        initialize(self.home)
        self.store = Store(self.home)
        self.session = self.store.new_session()
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), SHA256)
        self.fixtures = json.loads(FIXTURE.read_text())["fixtures"]

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def setup_case(self, f):
        prior = self.store.event(self.session, f["prior"])
        current = self.store.event(self.session, f["current"])
        event_id = current["event_id"]
        action_id = self.store.start_action(event_id, current["brain_generation_id"])
        raw = json.dumps(f["oracle"], separators=(",", ":"))
        mid = self.store.message(self.session, event_id, "assistant", raw, "DRAFT")
        args = (self.store, prior["source_ref"], current["source_ref"],
                event_id, self.session, raw, mid, action_id)
        return args

    def call(self, args):
        return gate.check_draft(*args)

    def counts(self):
        return {t: self.store.one("SELECT COUNT(*) AS n FROM " + t)["n"]
                for t in ("sources", "events", "messages", "packets", "actions", "states", "telemetry")}

    def test_three_disjoint_projects_and_no_writes_or_delivery(self):
        self.assertEqual([f["id"] for f in self.fixtures], ["Cedar", "Quartz", "Moss"])
        for f in self.fixtures:
            with self.subTest(project=f["id"]):
                args = self.setup_case(f)
                before, total = self.counts(), self.store.db.total_changes
                result = self.call(args)
                self.assertEqual(result["result"], "DRAFT_BOUND_SHADOW_NO_COMMIT")
                self.assertEqual(result["draft_sha256"], hashlib.sha256(args[5].encode()).hexdigest())
                self.assertEqual(result["matched_candidate_sha256"],
                                 gate.agreement._sha(gate.agreement._canonical(f["oracle"])))
                self.assertRegex(result["c5_binding_sha256"], r"^[0-9a-f]{64}$")
                self.assertEqual(result["delivery_authority"], 0)
                self.assertEqual(result["status"], "SHADOW_NO_AUTHORITY")
                self.assertFalse(result["live_enabled"])
                self.assertFalse(result["user_approved"])
                self.assertFalse(result["model_called"])
                self.assertEqual(result["store_writes"], 0)
                self.assertEqual(result["tool_dispatches"], 0)
                self.assertEqual(result["native_calls"], 0)
                self.assertEqual(result["step2"], "UTILITY_FAIL")
                self.assertEqual(result["jepa_weight"], 0)
                self.assertEqual(self.counts(), before)
                self.assertEqual(self.store.db.total_changes, total)
                self.assertEqual(self.store.one("SELECT status FROM messages WHERE id=?", (args[6],))["status"], "DRAFT")

    def test_wrong_or_foreign_draft_binding(self):
        args = self.setup_case(self.fixtures[0])
        other = self.store.new_session("foreign")
        wrong = self.store.message(other, args[3], "assistant", args[5], "DRAFT")
        self.assertEqual(self.call(args[:6] + (wrong, args[7]))["result"], "C6_DRAFT_RED")
        self.assertEqual(self.call(args[:6] + (args[6] + 9999, args[7]))["result"], "C6_DRAFT_RED")
        self.assertEqual(self.call(args[:5] + ('{"choice":"A","remaining":20} ',) + args[6:])["result"], "C6_DRAFT_RED")

    def test_committed_streaming_final_or_nonassistant_draft_refused(self):
        for field, value in (("status", "OUTPUT_COMMITTED"), ("status", "STREAMING"),
                             ("status", "FINAL"), ("role", "user")):
            with self.subTest(field=field, value=value):
                args = self.setup_case(self.fixtures[0])
                with self.store.tx() as db:
                    db.execute("UPDATE messages SET " + field + "=? WHERE id=?", (value, args[6]))
                self.assertEqual(self.call(args)["result"], "C6_DRAFT_RED")

    def test_forged_output_authority_metadata_rejected(self):
        for metadata in ({"output_authority": "APPROVED"}, {"user_approved": True},
                         {"delivery_authority": 1}, {"tool_result": "ran"}):
            with self.subTest(metadata=metadata):
                args = self.setup_case(self.fixtures[0])
                with self.store.tx() as db:
                    db.execute("UPDATE messages SET metadata=? WHERE id=?", (json.dumps(metadata), args[6]))
                self.assertEqual(self.call(args)["result"], "C6_DRAFT_RED")

    def test_wrong_c3_decision_and_source_revocation(self):
        args = self.setup_case(self.fixtures[0])
        with self.store.tx() as db:
            db.execute("UPDATE messages SET text=? WHERE id=?", ('{"choice":"B","remaining":50}', args[6]))
        bad = args[:5] + ('{"choice":"B","remaining":50}',) + args[6:]
        self.assertEqual(self.call(bad)["result"], "FINAL_AGREEMENT_RED")
        args = self.setup_case(self.fixtures[0])
        with self.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?", (args[1]["source_id"],))
        self.assertEqual(self.call(args)["result"], "FINAL_AGREEMENT_RED")

    def test_missing_wrong_or_foreign_c5_action(self):
        args = self.setup_case(self.fixtures[0])
        self.assertEqual(self.call(args[:-1] + ("act_missing",))["result"], "C5_INTENT_RED")
        other = self.setup_case(self.fixtures[1])
        self.assertEqual(self.call(args[:-1] + (other[7],))["result"], "C5_INTENT_RED")
        with self.store.tx() as db:
            db.execute("UPDATE actions SET status='SUCCEEDED' WHERE id=?", (args[7],))
        self.assertEqual(self.call(args)["result"], "C5_INTENT_RED")

    def test_tampered_corollary_and_intent_rejected(self):
        args = self.setup_case(self.fixtures[0])
        action = self.store.one("SELECT corollary_id FROM actions WHERE id=?", (args[7],))
        with self.store.tx() as db:
            db.execute("UPDATE packets SET payload='{}' WHERE id=?", (action["corollary_id"],))
        self.assertEqual(self.call(args)["result"], "C5_INTENT_RED")
        args = self.setup_case(self.fixtures[1])
        rows = self.store.rows("SELECT id,payload FROM packets WHERE kind='ActionIntent' AND event_id=?", (args[3],))
        self.assertEqual(len(rows), 1)
        p = json.loads(rows[0]["payload"])
        p["permission"] = "NETWORK"
        with self.store.tx() as db:
            db.execute("UPDATE packets SET payload=? WHERE id=?", (json.dumps(p), rows[0]["id"]))
        self.assertEqual(self.call(args)["result"], "C5_INTENT_RED")

    def test_wrong_input_types_fail_closed(self):
        args = self.setup_case(self.fixtures[0])
        for idx, value in ((6, True), (6, 0), (7, None), (7, 4), (3, ""), (4, ""), (5, None)):
            with self.subTest(index=idx, value=value):
                mutated = list(args)
                mutated[idx] = value
                self.assertEqual(self.call(tuple(mutated))["result"], "INPUT_BINDING_RED")

    def test_restart_invalidates_draft_without_resuming_output(self):
        args = self.setup_case(self.fixtures[0])
        self.store.close()
        self.store = Store(self.home)
        self.assertEqual(self.store.one("SELECT status FROM messages WHERE id=?", (args[6],))["status"], "INTERRUPTED")
        self.assertEqual(self.call((self.store,) + args[1:])["result"], "C6_DRAFT_RED")

    def test_concurrent_sqlite_source_revocation_is_blocked_during_preflight(self):
        args = self.setup_case(self.fixtures[0])
        original = gate.agreement.check
        observed = []
        def concurrent_attempt(*a):
            db = sqlite3.connect(self.home / "data/db/brain.sqlite3", timeout=.05, isolation_level=None)
            try:
                with self.assertRaises(sqlite3.OperationalError) as ctx:
                    db.execute("UPDATE sources SET deleted=1 WHERE id=?", (args[1]["source_id"],))
                observed.append("locked" in str(ctx.exception).lower())
            finally:
                db.close()
            return original(*a)
        with patch.object(gate.agreement, "check", side_effect=concurrent_attempt):
            result = self.call(args)
        self.assertEqual(observed, [True])
        self.assertEqual(result["result"], "DRAFT_BOUND_SHADOW_NO_COMMIT")
        self.assertEqual(self.store.one("SELECT deleted FROM sources WHERE id=?", (args[1]["source_id"],))["deleted"], 0)


if __name__ == "__main__":
    unittest.main()
