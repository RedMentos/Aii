"""Run70 disjoint source-only schema fixture software tests, no native model."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import jef_c3_source_reasoning_fixture_743 as f
from scripts import jef_c3_schema_fixture_727 as old
from scripts import p2x_disjoint_receiver_trainset as p2x
from scripts import jef_c3_c5_c6_operator_cli as cli
from v13 import jef_typed_source_shadow as typed
from v13.jef_c3_typed_envelope_candidate import build_jef_c3_typed_envelope
from v13.common import dumps


class SourceReasoningFixtureTests(unittest.TestCase):
    def test_six_balanced_new_sources(self):
        rows=f.fixtures()
        self.assertEqual([r["expected"] for r in rows],["A","B","NONE"]*2)
        self.assertEqual(len({r["project"] for r in rows}),6)
        prior=old.fixtures()
        self.assertFalse({r["project"] for r in rows}&{r["project"] for r in prior})
        p2x_rows=p2x.fixtures()
        p2x.validate(p2x_rows)
        self.assertFalse({r["project"] for r in rows}&{r["id"] for r in p2x_rows})
        for r in rows:
            self.assertIsNotNone(typed.CURRENT.fullmatch(r["current"]))
            self.assertIsNotNone(typed.POLICY.fullmatch(r["policy_source"]))
            self.assertIsNotNone(typed.SHEET.fullmatch(r["sheet_source"]))
            self.assertEqual(p2x.decide_sources(
                r["current"],[r["policy_source"],r["sheet_source"]]),r["expected"])
            self.assertEqual(p2x.decide_sources(r["current"],[r["policy_source"]]),"UNKNOWN")
            self.assertEqual(p2x.decide_sources(r["current"],[r["sheet_source"]]),"UNKNOWN")

    def test_table_and_oracle_tamper_refuse(self):
        original=f.TABLE[0]
        try:
            f.TABLE[0]=original[:-1]+("B",)
            with self.assertRaisesRegex(ValueError,"TABLE_CHANGED"):
                f.fixtures()
        finally:
            f.TABLE[0]=original

    def test_schema_exact_scoring(self):
        self.assertEqual(f.SCHEMA,old.SCHEMA)
        for a in ("A","B","NONE"):
            self.assertEqual(f.score(json.dumps({"action":a}),a),1)
        for malformed in ("Option A", '{"action":"A","action":"B"}',
                          '{"action":"A","other":1}', '{"action":NaN}'):
            self.assertEqual(f.score(malformed,"A"),0)

    def test_real_store_authenticated_envelope_no_answer_leak(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=cli.Runtime(Path(tmp))
            try:
                with patch.object(r.pool,"get",side_effect=AssertionError("NATIVE_CALLED")):
                    for row in f.fixtures():
                        project,domain=row["project"],row["domain"]
                        ids=[]
                        for key,val in (
                            (f"Project {project} archived {domain} policy",row["policy_source"]),
                            (f"Project {project} latest {domain} option sheet",row["sheet_source"]),
                        ):
                            event=r.store.event(r.session,"Record: "+key)
                            mid=r.memory.feedback(event["event_id"],"fact",val,
                                                  permission="record",key=key,scope="session")
                            r.memory.candidate(mid,r.session)
                            ids.append(mid)
                        current=r.store.event(r.session,row["current"])
                        envelope=build_jef_c3_typed_envelope(
                            r.memory,r.session,current["event_id"],
                            current["source_ref"],ids,operator_opt_in=True)
                        self.assertEqual(envelope["status"],
                                         "JEF_C3_TYPED_ENVELOPE_SHADOW_NO_MODEL_CALL")
                        self.assertEqual(envelope["typed_jef_action"],row["expected"])
                        typed_arm=f.model_messages(envelope,"TYPED_SCHEMA")
                        source_arm=f.model_messages(envelope,"SOURCE_SCHEMA")
                        self.assertEqual(typed_arm,envelope["messages"])
                        self.assertNotEqual(source_arm,typed_arm)
                        payload=json.loads(source_arm[1]["content"])
                        self.assertNotIn("typed_jef_action",payload)
                        self.assertNotIn("expected",payload)
                        self.assertNotIn("oracle_action",payload)
                        self.assertEqual(payload["current_source"],row["current"])
                        self.assertEqual(payload["policy_source"],row["policy_source"])
                        self.assertEqual(payload["sheet_source"],row["sheet_source"])
                        self.assertEqual(payload["source_ref_sha256"],
                                         envelope["source_ref_sha256"])
                        self.assertNotIn("typed_jef_action",dumps(source_arm))
                        self.assertEqual(r.store.one(
                            "SELECT COUNT(*) AS n FROM actions")["n"],0)
            finally:
                r.close()

    def test_forged_envelope_and_unknown_arm_rejected(self):
        from hashlib import sha256
        messages=[{"role":"system","content":"copy"},
                  {"role":"user","content":dumps({"typed_jef_action":"A"})}]
        envelope={"status":"JEF_C3_TYPED_ENVELOPE_SHADOW_NO_MODEL_CALL",
                  "typed_jef_action":"A","messages":messages,
                  "messages_sha256":sha256(dumps(messages).encode()).hexdigest()}
        self.assertNotIn("typed_jef_action",dumps(f.model_messages(envelope,"SOURCE_SCHEMA")))
        for invalid in ("UNKNOWN","BASELINE"):
            with self.assertRaisesRegex(ValueError,"ARM_RED"):
                f.model_messages(envelope,invalid)
        forged=dict(envelope,messages_sha256="0"*64)
        with self.assertRaisesRegex(ValueError,"PROMPT_HASH_RED"):
            f.model_messages(forged,"SOURCE_SCHEMA")
        bad=dict(envelope,typed_jef_action="B")
        with self.assertRaisesRegex(ValueError,"TYPED_ACTION_MISSING"):
            f.model_messages(bad,"SOURCE_SCHEMA")


if __name__=="__main__":
    unittest.main()
