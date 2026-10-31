"""Run71 cross-package real Store software: read-only Run69 + C5 Run11."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts import jef_c3_c5_c6_operator_cli as cli
from scripts.run63_jef_c3_native import cohort
from v13.jef_c3_schema_source_recheck_shadow import (
    format_schema_shadow, SCHEMA_SHA256 as DIAGNOSTIC_SCHEMA_SHA)
from v13.jef_c3_schema_draft_candidate import (
    stage_schema, SCHEMA_SHA256 as DRAFT_SCHEMA_SHA)
from v13.jef_c3_c5_c6_fallback_draft_candidate import preflight, STAGED


class CrossPackageSourceStore(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.r=cli.Runtime(Path(self.tmp.name))
        self.row=cohort()[0]
        row=self.row
        self.ids=[]
        for key,value in (
            (f'Project {row["id"]} archived {row["domain"]} policy',row["b2_source"]),
            (f'Project {row["id"]} latest {row["domain"]} option sheet',row["b1_source"]),
        ):
            e=self.r.store.event(self.r.session,"Record: "+key)
            mid=self.r.memory.feedback(e["event_id"],"fact",value,
                                       permission="record",key=key,scope="session")
            self.r.memory.candidate(mid,self.r.session)
            self.ids.append(mid)
        self.event=self.r.store.event(self.r.session,row["current"])

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def _args(self):
        e=self.event
        return (self.r.memory,self.r.session,e["event_id"],e["source_ref"],self.ids)

    def _counts(self):
        eid=self.event["event_id"]
        return (
            self.r.store.one("SELECT COUNT(*) AS n FROM messages WHERE event_id=? AND role='assistant'",(eid,))["n"],
            self.r.store.one("SELECT COUNT(*) AS n FROM actions WHERE event_id=?",(eid,))["n"],
        )

    def test_read_only_diagnostic_then_atomic_c5_draft_same_source(self):
        self.assertEqual(DIAGNOSTIC_SCHEMA_SHA,DRAFT_SCHEMA_SHA)
        expected=self.row["oracle_action"]
        cb=lambda messages,schema:json.dumps({"action":expected})
        diagnostic=format_schema_shadow(*self._args(),cb,
                                         operator_opt_in=True,callback_opt_in=True)
        self.assertEqual(diagnostic["status"],"FORMATTER_MATCH_SHADOW")
        self.assertTrue(diagnostic["source_rechecked"])
        self.assertFalse(diagnostic["source_only_fallback"])
        self.assertEqual(self._counts(),(0,0))
        staged=stage_schema(*self._args(),cb,
                            operator_opt_in=True,callback_opt_in=True)
        self.assertEqual(staged["status"],STAGED)
        self.assertEqual(staged["schema_formatter_status"],"SCHEMA_EXACT_SHADOW")
        self.assertEqual(staged["schema_output_sha256"],diagnostic["output_sha256"])
        self.assertEqual(staged["schema_sha256"],diagnostic["schema_sha256"])
        self.assertEqual(self._counts(),(1,1))
        c6=preflight(*self._args(),staged,operator_opt_in=True)
        self.assertEqual(c6["status"],"NEEDS_REAL_TTY_APPROVAL")
        self.assertEqual(c6["delivery_authority"],0)
        self.assertFalse(c6["output_committed"])

    def test_mismatched_model_action_never_becomes_c5_fallback(self):
        expected=self.row["oracle_action"]
        wrong="B" if expected!="B" else "A"
        cb=lambda messages,schema:json.dumps({"action":wrong})
        diagnostic=format_schema_shadow(*self._args(),cb,
                                         operator_opt_in=True,callback_opt_in=True)
        self.assertEqual(diagnostic["status"],"FORMATTER_ACTION_MISMATCH_RED")
        self.assertTrue(diagnostic["source_only_fallback"])
        self.assertEqual(self._counts(),(0,0))
        staged=stage_schema(*self._args(),cb,
                            operator_opt_in=True,callback_opt_in=True)
        self.assertEqual(staged["status"],"JEF_C3_GENERATION_RED")
        self.assertEqual(staged["schema_formatter_status"],"SCHEMA_REJECTED_OR_SOURCE_RED")
        self.assertEqual(self._counts(),(0,0))

    def test_revoked_source_after_readonly_diagnostic_blocks_draft(self):
        expected=self.row["oracle_action"]
        cb=lambda messages,schema:json.dumps({"action":expected})
        diagnostic=format_schema_shadow(*self._args(),cb,
                                         operator_opt_in=True,callback_opt_in=True)
        self.assertEqual(diagnostic["status"],"FORMATTER_MATCH_SHADOW")
        self.r.memory.forget(self.ids[1])
        staged=stage_schema(*self._args(),cb,
                            operator_opt_in=True,callback_opt_in=True)
        self.assertNotEqual(staged["status"],STAGED)
        self.assertEqual(self._counts(),(0,0))
        self.assertEqual(staged["delivery_authority"],0)


if __name__=="__main__":
    unittest.main()
