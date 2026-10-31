"""Source-bound JSON-schema C3->C5 DRAFT software SHADOW tests; no model."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.run63_jef_c3_native import cohort
from scripts import jef_c3_c5_c6_operator_cli as cli
from v13 import jef_c3_schema_draft_candidate as schema
from v13.jef_c3_c5_c6_fallback_draft_candidate import preflight, STAGED


class SchemaDraftTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.row = cohort()[0]

    def tearDown(self):
        self.tmp.cleanup()

    def _input(self):
        row = self.row
        p = self.root / "input.json"
        p.write_text(json.dumps({
            "project": row["id"], "domain": row["domain"],
            "policy_source": row["b2_source"],
            "sheet_source": row["b1_source"],
            "current": row["current"],
        }), encoding="utf-8")
        return p

    def _store(self):
        r = cli.Runtime(self.root / "store")
        row = self.row
        ids = []
        for key, value in (
            (f'Project {row["id"]} archived {row["domain"]} policy', row["b2_source"]),
            (f'Project {row["id"]} latest {row["domain"]} option sheet', row["b1_source"]),
        ):
            e = r.store.event(r.session, "Record: " + key)
            mid = r.memory.feedback(e["event_id"], "fact", value,
                                    permission="record", key=key, scope="session")
            r.memory.candidate(mid, r.session)
            ids.append(mid)
        event = r.store.event(r.session, row["current"])
        return r, ids, event

    def _stage(self, r, ids, event, callback, **kwargs):
        return schema.stage_schema(
            r.memory, r.session, event["event_id"], event["source_ref"],
            ids, callback, **kwargs)

    def _counts(self, r, event):
        eid = event["event_id"]
        draft = r.store.one("SELECT COUNT(*) AS n FROM messages WHERE event_id=? AND role='assistant'", (eid,))["n"]
        actions = r.store.one("SELECT COUNT(*) AS n FROM actions WHERE event_id=?", (eid,))["n"]
        return draft, actions

    def test_exact_parser_and_bounded_refusals(self):
        for action in ("A", "B", "NONE"):
            self.assertEqual(schema.decode_action(json.dumps({"action": action})), action)
        for raw in (
            None, b'{"action":"A"}', "", "A", "Option A",
            '{"action":"A","action":"B"}', '{"action":"A","extra":1}',
            '{"action":1}', '{"action":"C"}', '["A"]',
            '{"action":NaN}', '{"action":"A"} trailing',
            '{"action":"A"}' + " " * 1025,
            '{"action":"\\ud800"}',
        ):
            with self.subTest(raw=repr(raw)[:30]):
                self.assertIsNone(schema.decode_action(raw))
        self.assertEqual(schema.SCHEMA["additionalProperties"], False)

    def test_explicit_optins_and_tty_refusal_before_callback(self):
        r, ids, event = self._store()
        try:
            calls = []
            cb = lambda *_: calls.append(1)
            for opts, expected in (
                ({}, "OFF"),
                ({"operator_opt_in": 1, "callback_opt_in": True}, "OFF"),
                ({"operator_opt_in": True, "callback_opt_in": 1}, "OFF"),
                ({"operator_opt_in": True, "callback_opt_in": True,
                  "approval_receipt": {"approved": True}},
                 "REAL_TTY_APPROVAL_UNSUPPORTED"),
            ):
                result = self._stage(r, ids, event, cb, **opts)
                self.assertEqual(result["status"], expected)
                self.assertEqual(result["delivery_authority"], 0)
            self.assertEqual(calls, [])
            self.assertEqual(self._counts(r, event), (0, 0))
        finally:
            r.close()

    def test_real_store_exact_draft_and_c6_no_delivery(self):
        r, ids, event = self._store()
        try:
            expected = self.row["oracle_action"]
            result = self._stage(
                r, ids, event, lambda messages, spec: json.dumps({"action": expected}),
                operator_opt_in=True, callback_opt_in=True)
            self.assertEqual(result["status"], STAGED)
            self.assertEqual(result["schema_formatter_status"], "SCHEMA_EXACT_SHADOW")
            self.assertEqual(result["schema_sha256"], schema.SCHEMA_SHA256)
            self.assertFalse(result["schema_receipt_persisted"])
            self.assertFalse(result["source_only_fallback"])
            self.assertFalse(result["native_proof"])
            self.assertEqual(self._counts(r, event), (1, 1))
            c6 = preflight(r.memory, r.session, event["event_id"],
                           event["source_ref"], ids, result, operator_opt_in=True)
            self.assertEqual(c6["status"], "NEEDS_REAL_TTY_APPROVAL")
            self.assertEqual(c6["delivery_authority"], 0)
            self.assertFalse(c6["output_committed"])
            self.assertEqual(r.store.one(
                "SELECT COUNT(*) AS n FROM messages WHERE event_id=? AND status='FINAL'",
                (event["event_id"],))["n"], 0)
            invoked = []
            again = self._stage(r, ids, event,
                                lambda *_: invoked.append(True),
                                operator_opt_in=True, callback_opt_in=True)
            self.assertEqual(again["status"], "EXISTING_OUTPUT_OR_ACTION_RED")
            self.assertEqual(invoked, [])
            self.assertEqual(self._counts(r, event), (1, 1))
        finally:
            r.close()

    def test_malformed_mismatch_and_mutation_leave_no_draft(self):
        callbacks = [
            lambda m, s: "Option A",
            lambda m, s: '{"action":"A","action":"B"}',
            lambda m, s: json.dumps({"action": "B" if self.row["oracle_action"] != "B" else "A"}),
            lambda m, s: '{"action":NaN}',
            lambda m, s: "x" * 1025,
            lambda m, s: 1,
            lambda m, s: s.update({"additionalProperties": True}) or '{"action":"A"}',
        ]
        for i, cb in enumerate(callbacks):
            with self.subTest(case=i):
                r, ids, event = self._store()
                try:
                    result = self._stage(r, ids, event, cb,
                                         operator_opt_in=True, callback_opt_in=True)
                    self.assertEqual(result["status"], "JEF_C3_GENERATION_RED")
                    self.assertEqual(result["schema_formatter_status"],
                                     "SCHEMA_REJECTED_OR_SOURCE_RED")
                    self.assertEqual(self._counts(r, event), (0, 0))
                finally:
                    r.close()
                # Subsequent subtests need a clean Store.
                import shutil
                shutil.rmtree(self.root / "store")

    def test_stale_user_and_revoked_source_fail_after_callback(self):
        for mode in ("stale", "revoked"):
            with self.subTest(mode=mode):
                r, ids, event = self._store()
                try:
                    def cb(messages, spec):
                        if mode == "stale":
                            r.store.event(r.session, "Newer authoritative USER")
                        else:
                            r.memory.forget(ids[1])
                        return json.dumps({"action": self.row["oracle_action"]})
                    result = self._stage(r, ids, event, cb,
                                         operator_opt_in=True, callback_opt_in=True)
                    self.assertEqual(result["status"], "JEF_C3_GENERATION_RED")
                    self.assertEqual(self._counts(r, event), (0, 0))
                finally:
                    r.close()
                import shutil
                shutil.rmtree(self.root / "store")

    def test_cli_schema_modes_and_old_mode_preserved(self):
        inp = self._input()
        for mode, expected_status in (
            ("synthetic_schema_exact", "SHADOW_DRAFT_PREFLIGHT_READY"),
            ("synthetic_schema_wrong", "DRAFT_STAGE_RED"),
            ("synthetic_schema_duplicate", "DRAFT_STAGE_RED"),
            ("synthetic_exact", "SHADOW_DRAFT_PREFLIGHT_READY"),
            ("synthetic_wrong", "SHADOW_DRAFT_PREFLIGHT_READY"),
        ):
            with self.subTest(mode=mode):
                result = cli.run(self.root / ("home_" + mode), inp, mode,
                                 operator_opt_in=True, callback_opt_in=True)
                self.assertEqual(result["status"], expected_status)
                self.assertFalse(result["native_model_called"])
                self.assertFalse(result["native_proof"])
                self.assertFalse(result["output_committed"])
                self.assertEqual(result["delivery_authority"], 0)
                self.assertEqual(result["tool_dispatches"], 0)
                self.assertEqual(result["learning_authority"], 0)
                self.assertNotIn(self.row["current"], json.dumps(result))
                if mode == "synthetic_schema_exact":
                    self.assertEqual(result["schema_formatter_status"], "SCHEMA_EXACT_SHADOW")
                    self.assertFalse(result["source_only_fallback"])
                if mode in ("synthetic_schema_wrong", "synthetic_schema_duplicate"):
                    self.assertEqual(result["stage_status"], "JEF_C3_GENERATION_RED")
        missing = cli.run(self.root / "no_native", inp, "native_schema",
                          operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(missing["status"], "NATIVE_BINDING_RED")
        self.assertFalse(missing["native_model_called"])


if __name__ == "__main__":
    unittest.main()
