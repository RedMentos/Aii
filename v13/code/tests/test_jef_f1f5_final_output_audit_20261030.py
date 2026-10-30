"""Read-only F1/F5 stored assistant FINAL arithmetic discrepancy; software-only."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import p2x_disjoint_receiver_trainset as cohort
from v13 import jef_f1f5_source_admission as admission
from v13 import jef_f1f5_output_audit as audit
from v13.operator import Operator
from v13.runtime import Runtime


class FinalOutputAudit(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)
        self.row = next(x for x in cohort.fixtures()
                        if x["partition"] == "calibration")
        self.ids = self._sources()
        base = json.loads(self.op.run(":jefsource " + " ".join(self.ids)))
        self.arithmetic = base["source_exact_arithmetic"]
        self.good = self._text()

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def _record(self, key, value):
        e = self.r.store.event(self.r.session, "Record: " + key)
        mid = self.r.memory.feedback(e["event_id"], "fact", value,
                                     permission="record", key=key,
                                     scope="session")
        self.r.memory.candidate(mid, self.r.session)
        return mid

    def _sources(self):
        row = self.row
        policy = self._record(
            f'Project {row["id"]} archived {row["domain"]} policy',
            row["b2_source"])
        sheet = self._record(
            f'Project {row["id"]} latest {row["domain"]} option sheet',
            row["b1_source"])
        e = self.r.store.event(self.r.session, row["current"])
        return e["event_id"], policy, sheet

    def _text(self, wrong_b=False):
        a = self.arithmetic
        fields = a["fields"]
        parts = []
        for name in "AB":
            values = a["options"][name]["remaining"][:]
            if name == "B" and wrong_b:
                values[1] += 100
            parts.append(
                f'Option {name} leaves {values[0]} {fields[0]["unit"]}; '
                f'{values[1]} {fields[1]["unit"]} remaining.')
        return " ".join(parts)

    def _final(self, text, *, session=None, status="FINAL"):
        return self.r.store.message(session or self.r.session, self.ids[0],
                                    "assistant", text, status=status,
                                    metadata={"model_generated": True})

    def _command(self):
        return ":jefsource audit " + " ".join(self.ids)

    def _counts(self):
        return tuple(self.r.store.one(
            f"SELECT count(*) AS n FROM {table}")["n"]
            for table in ("sources", "events", "feedback", "packets",
                          "memories", "messages"))

    def test_pure_parser_correct_wrong_contradiction_missing_and_echo(self):
        a = self.arithmetic
        self.assertEqual(audit.diagnose(a, self.good)["status"], "MATCH")
        wrong = audit.diagnose(a, self._text(wrong_b=True))
        self.assertEqual(wrong["status"], "DISCREPANCY")
        self.assertEqual(wrong["options"]["B"][1]["status"], "WRONG")
        f = a["fields"][0]
        val = a["options"]["A"]["remaining"][0]
        conflict = self.good + f" Option A leaves {val+1} {f['unit']}."
        result = audit.diagnose(a, conflict)
        self.assertEqual(result["options"]["A"][0]["status"], "CONTRADICTORY")
        self.assertEqual(result["status"], "DISCREPANCY")
        self.assertEqual(audit.diagnose(a, "Option A costs 55 tokens.")["status"],
                         "INCOMPLETE")
        self.assertEqual(audit.diagnose(a, "Option B leaves 2 ticks.")["status"],
                         "INCOMPLETE")
        self.assertEqual(audit.diagnose(a, "Option A leaves 100000000000 tokens.")["status"],
                         "INCOMPLETE")

    def test_positive_current_session_final_no_writes_or_native(self):
        self._final(self.good)
        before = self._counts()
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("NATIVE_CALLED")):
            result = json.loads(self.op.run(self._command()))
        self.assertEqual(result["audit_status"], "F1F5_STORED_FINAL_SHADOW_ONLY")
        self.assertEqual(result["stored_final_audit"]["status"], "MATCH")
        self.assertFalse(result["native_execution_proven_here"])
        self.assertTrue(result["no_live_answer"])
        self.assertFalse(result["model_called"])
        self.assertEqual(result["native_calls"], 0)
        self.assertEqual(result["jepa_weight"], 0)
        self.assertFalse(result["ag6_approved"])
        self.assertEqual(self._counts(), before)

    def test_wrong_second_option_reported_not_rewritten(self):
        self._final(self._text(wrong_b=True))
        result = json.loads(self.op.run(self._command()))
        self.assertEqual(result["stored_final_audit"]["status"], "DISCREPANCY")
        self.assertEqual(result["stored_final_audit"]["options"]["B"][1]["status"],
                         "WRONG")
        self.assertEqual(result["status"], "SHADOW_NO_AUTHORITY")

    def test_missing_draft_error_duplicate_and_foreign_final(self):
        result = json.loads(self.op.run(self._command()))
        self.assertEqual(result["audit_status"], "NO_SINGLE_CURRENT_FINAL")
        self.assertIsNone(result["stored_final_audit"])
        self._final(self.good, status="DRAFT")
        self.assertEqual(json.loads(self.op.run(self._command()))["audit_status"],
                         "NO_SINGLE_CURRENT_FINAL")
        self._final(self.good, status="ERROR")
        self.assertEqual(json.loads(self.op.run(self._command()))["audit_status"],
                         "NO_SINGLE_CURRENT_FINAL")
        other = self.r.store.new_session("foreign")
        self._final(self.good, session=other)
        self.assertEqual(json.loads(self.op.run(self._command()))["audit_status"],
                         "NO_SINGLE_CURRENT_FINAL")
        self._final(self.good)
        self.assertEqual(json.loads(self.op.run(self._command()))["audit_status"],
                         "F1F5_STORED_FINAL_SHADOW_ONLY")
        self._final(self.good)
        self.assertEqual(json.loads(self.op.run(self._command()))["audit_status"],
                         "NO_SINGLE_CURRENT_FINAL")

    def test_revoked_source_and_midcheck_revocation(self):
        self._final(self.good)
        original = admission.decide
        calls = []
        def revoke_after_first(*args, **kwargs):
            result = original(*args, **kwargs)
            calls.append(result)
            if len(calls) == 1:
                self.r.memory.forget(self.ids[2])
            return result
        with patch.object(admission, "decide", side_effect=revoke_after_first):
            result = json.loads(self.op.run(self._command()))
        self.assertEqual(len(calls), 2)
        self.assertIsNone(result["stored_final_audit"])
        self.assertEqual(result["audit_status"], "SOURCE_NOT_ADMITTED")
        self.assertEqual(result["suggested_action"], "UNKNOWN")

    def test_tampered_human_source_and_current_session_rejected(self):
        self._final(self.good)
        row = self.r.memory.candidate(self.ids[2], self.r.session)
        blob = self.home / "data/blobs" / row["source_ref"]["sha256"]
        blob.write_bytes(b"tampered")
        result = json.loads(self.op.run(self._command()))
        self.assertIsNone(result["stored_final_audit"])
        other = self.r.store.new_session("other")
        foreign = self.r.store.event(other, self.row["current"])
        cmd = ":jefsource audit " + " ".join(
            (foreign["event_id"], self.ids[1], self.ids[2]))
        with self.assertRaisesRegex(ValueError, "CURRENT_SESSION_EVENT_REQUIRED"):
            self.op.run(cmd)

    def test_local_only_idle_age0_and_old_commands_unchanged(self):
        self._final(self.good)
        default_before = self.op.run(":jefsource " + " ".join(self.ids))
        explain_before = self.op.run(":jefsource explain " + " ".join(self.ids))
        self.op.run(self._command())
        self.assertEqual(default_before,
                         self.op.run(":jefsource " + " ".join(self.ids)))
        self.assertEqual(explain_before,
                         self.op.run(":jefsource explain " + " ".join(self.ids)))
        with self.assertRaisesRegex(ValueError, "Nur lokale Operator"):
            self.op.run(self._command(), origin="MODEL")
        with patch.object(self.r, "require_idle", side_effect=ValueError("BUSY")):
            with self.assertRaisesRegex(ValueError, "BUSY"):
                self.op.run(self._command())
        old = dict(self.r.cfg)
        try:
            for field, value in (("system_stage", 1),
                                 ("learning_mode", "SHADOW_UPDATE"),
                                 ("latents_enabled", True),
                                 ("jepa_weight", 1)):
                self.r.cfg[field] = value
                with self.assertRaisesRegex(ValueError, "AGE0_RECORD_ONLY_REQUIRED"):
                    self.op.run(self._command())
                self.r.cfg.clear()
                self.r.cfg.update(old)
        finally:
            self.r.cfg.clear()
            self.r.cfg.update(old)

    def test_restart_persists_exact_diagnostic(self):
        self._final(self.good)
        before = json.loads(self.op.run(self._command()))
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)
        after = json.loads(self.op.run(self._command()))
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
