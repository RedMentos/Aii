"""Run72 atomic schema provenance real SQLite DRAFT/C6 tests; no native."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.run63_jef_c3_native import cohort
from scripts import jef_c3_c5_c6_operator_cli as cli
from v13.jef_c3_schema_draft_candidate import stage_schema, SCHEMA_SHA256
from v13.jef_c3_c5_c6_fallback_draft_candidate import stage, preflight, STAGED


class AtomicSchemaReceipt(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.r=cli.Runtime(Path(self.tmp.name))
        row=cohort()[0]
        self.expected=row["oracle_action"]
        self.ids=[]
        for key,value in (
            (f'Project {row["id"]} archived {row["domain"]} policy',row["b2_source"]),
            (f'Project {row["id"]} latest {row["domain"]} option sheet',row["b1_source"]),
        ):
            event=self.r.store.event(self.r.session,"Record: "+key)
            mid=self.r.memory.feedback(event["event_id"],"fact",value,
                                       permission="record",key=key,scope="session")
            self.r.memory.candidate(mid,self.r.session)
            self.ids.append(mid)
        self.event=self.r.store.event(self.r.session,row["current"])

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def args(self):
        e=self.event
        return (self.r.memory,self.r.session,e["event_id"],e["source_ref"],self.ids)

    def counts(self):
        eid=self.event["event_id"]
        return (
            self.r.store.one("SELECT COUNT(*) AS n FROM messages WHERE event_id=? AND role='assistant'",(eid,))["n"],
            self.r.store.one("SELECT COUNT(*) AS n FROM actions WHERE event_id=?",(eid,))["n"],
        )

    def cb(self,messages,schema):
        return json.dumps({"action":self.expected})

    def stage_schema(self):
        return stage_schema(*self.args(),self.cb,
                            operator_opt_in=True,callback_opt_in=True)

    def test_receipt_atomically_stored_and_c6_rechecks(self):
        staged=self.stage_schema()
        self.assertEqual(staged["status"],STAGED)
        self.assertTrue(staged["schema_receipt_persisted"])
        self.assertEqual(self.counts(),(1,1))
        receipt=staged["schema_receipt"]
        raw=self.cb(None,None).encode()
        self.assertEqual(receipt,{
            "schema_sha256":SCHEMA_SHA256,
            "output_sha256":hashlib.sha256(raw).hexdigest(),
            "output_bytes":len(raw),
            "prompt_sha256":staged["prompt_sha256"],
        })
        row=self.r.store.one("SELECT metadata,status FROM messages WHERE id=?",
                             (staged["draft_message_id"],))
        self.assertEqual(row["status"],"DRAFT")
        meta=json.loads(row["metadata"])
        self.assertEqual(meta["schema_receipt"],receipt)
        self.assertNotIn(self.cb(None,None),row["metadata"])
        c6=preflight(*self.args(),staged,operator_opt_in=True)
        self.assertEqual(c6["status"],"NEEDS_REAL_TTY_APPROVAL")
        self.assertFalse(c6["output_committed"])
        self.assertEqual(c6["delivery_authority"],0)

    def test_persisted_receipt_tamper_fails_c6(self):
        staged=self.stage_schema()
        row=self.r.store.one("SELECT metadata FROM messages WHERE id=?",
                             (staged["draft_message_id"],))
        meta=json.loads(row["metadata"])
        meta["schema_receipt"]["output_sha256"]="0"*64
        with self.r.store.tx() as db:
            db.execute("UPDATE messages SET metadata=? WHERE id=?",
                       (json.dumps(meta),staged["draft_message_id"]))
        c6=preflight(*self.args(),staged,operator_opt_in=True)
        self.assertEqual(c6["status"],"DRAFT_METADATA_OR_SOURCE_RED")
        self.assertEqual(self.counts(),(1,1))

    def test_forged_staged_receipt_fails_c6(self):
        staged=self.stage_schema()
        forged=copy.deepcopy(staged)
        forged["schema_receipt"]["output_sha256"]="f"*64
        c6=preflight(*self.args(),forged,operator_opt_in=True)
        self.assertEqual(c6["status"],"DRAFT_METADATA_OR_SOURCE_RED")

    def test_missing_receipt_reference_fails_c6(self):
        staged=self.stage_schema()
        forged=copy.deepcopy(staged)
        forged.pop("schema_receipt")
        c6=preflight(*self.args(),forged,operator_opt_in=True)
        self.assertEqual(c6["status"],"SCHEMA_RECEIPT_REFERENCE_RED")

    def test_old_token_mode_stays_without_receipt(self):
        staged=stage(*self.args(),lambda messages:self.expected,
                     operator_opt_in=True,callback_opt_in=True)
        self.assertEqual(staged["status"],STAGED)
        self.assertNotIn("schema_receipt",staged)
        row=self.r.store.one("SELECT metadata FROM messages WHERE id=?",
                             (staged["draft_message_id"],))
        self.assertNotIn("schema_receipt",json.loads(row["metadata"]))
        c6=preflight(*self.args(),staged,operator_opt_in=True)
        self.assertEqual(c6["status"],"NEEDS_REAL_TTY_APPROVAL")

    def test_provider_exception_no_draft(self):
        def broken():
            raise TimeoutError("simulated receipt crash")
        result=stage(*self.args(),lambda messages:self.expected,
                     operator_opt_in=True,callback_opt_in=True,
                     formatter_receipt=broken)
        self.assertEqual(result["status"],"SCHEMA_RECEIPT_RED")
        self.assertEqual(self.counts(),(0,0))

    def test_wrong_receipt_json_no_draft(self):
        result=stage(*self.args(),lambda messages:self.expected,
                     operator_opt_in=True,callback_opt_in=True,
                     formatter_receipt=lambda: '{"action":"B","action":"A"}')
        self.assertEqual(result["status"],"SCHEMA_RECEIPT_RED")
        self.assertEqual(self.counts(),(0,0))

    def test_source_revoked_inside_receipt_no_draft(self):
        def revoke():
            self.r.memory.forget(self.ids[1])
            return self.cb(None,None)
        result=stage(*self.args(),lambda messages:self.expected,
                     operator_opt_in=True,callback_opt_in=True,
                     formatter_receipt=revoke)
        self.assertEqual(result["status"],"SOURCE_CHANGED_BEFORE_DRAFT")
        self.assertEqual(self.counts(),(0,0))

    def test_invalid_model_json_does_not_persist_anything(self):
        result=stage_schema(*self.args(),
                            lambda messages,schema:'{"action":"A","action":"B"}',
                            operator_opt_in=True,callback_opt_in=True)
        self.assertEqual(result["status"],"JEF_C3_GENERATION_RED")
        self.assertEqual(self.counts(),(0,0))

    def test_duplicate_c5_stage_blocks_callback(self):
        staged=self.stage_schema()
        invoked=[]
        again=stage_schema(*self.args(),
                           lambda messages,schema:invoked.append(True),
                           operator_opt_in=True,callback_opt_in=True)
        self.assertEqual(staged["status"],STAGED)
        self.assertEqual(again["status"],"EXISTING_OUTPUT_OR_ACTION_RED")
        self.assertEqual(invoked,[])
        self.assertEqual(self.counts(),(1,1))


if __name__=="__main__":
    unittest.main()
