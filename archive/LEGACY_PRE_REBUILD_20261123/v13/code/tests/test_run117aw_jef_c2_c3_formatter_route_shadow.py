"""Run117AW JEF/C2/C3 formatter route real-Store software tests; no native."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.run63_jef_c3_native import cohort
from scripts.jef_c3_c5_c6_operator_cli import Runtime
from v13.control_calibration_worker import observation
from v13.jef_c2_c3_formatter_route_shadow_candidate import (
    propose, READY, NEGATIVE,
)

def control(route="both"):
    return {"success":True,
            "validation":{"negation":False,"ungrounded":False},
            "confidence":.91,
            "function_calls":[{"name":"select_processing",
                               "arguments":{"route":route}}]}

def approved(c):
    return observation(c) | {
        "in_support":True,"calibrated_confidence":.9,
        "route_observation_count":8,
        "calibration_scope":"HELD_OUT_NATIVE_ROUTE_AGREEMENT_ONLY",
        "semantic_truth_authority":False,
    }

class JefC2C3RouteShadow(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def make(self,row):
        r=Runtime(self.root/row["id"])
        self.addCleanup(r.close)
        def record(key,value):
            e=r.store.event(r.session,"Record: "+key)
            mid=r.memory.feedback(e["event_id"],"fact",value,
                                  permission="record",key=key,scope="session")
            r.memory.candidate(mid,r.session)
            return mid
        p=record("Project "+row["id"]+" archived "+row["domain"]+" policy",
                 row["b2_source"])
        s=record("Project "+row["id"]+" latest "+row["domain"]+" option sheet",
                 row["b1_source"])
        event=r.store.event(r.session,row["current"])
        return r,event,[p,s]

    def call(self,r,event,ids,**kwargs):
        return propose(r,event,ids,operator_opt_in=True,
                       callback_opt_in=True,**kwargs)

    def safe(self,out):
        self.assertEqual(out["negative_gates"],NEGATIVE)
        self.assertEqual(out["delivery_authority"],0)
        self.assertEqual(out["learning_authority"],0)
        self.assertEqual(out["tool_dispatches"],0)
        self.assertFalse(out["output_committed"])
        self.assertFalse(out["native_model_called"])
        self.assertFalse(out["c2_native_proof"])
        self.assertFalse(out["c3_native_proof"])
        self.assertFalse(out["route_applied"])
        self.assertFalse(out["real_tty_approved"])
        self.assertFalse(out["independent_c3_reasoning_proven"])

    def test_off_before_any_runtime_or_source_access(self):
        for opts in ({},{ "operator_opt_in":1,"callback_opt_in":True},
                     {"operator_opt_in":True,"callback_opt_in":1}):
            out=propose(None,None,None,**opts)
            self.assertEqual(out["status"],"OFF")
            self.safe(out)

    def test_three_real_human_source_jef_formatter_routes(self):
        for row in cohort():
            with self.subTest(id=row["id"]):
                r,e,ids=self.make(row)
                with patch.object(r.pool,"get",side_effect=AssertionError(
                        "NO_NATIVE_INFERENCE_ALLOWED")):
                    out=self.call(r,e,ids)
                self.assertEqual(out["status"],READY,out)
                self.assertEqual(out["formatter_route"],
                                 "JEF_TYPED_C3_FORMATTER_ONLY")
                self.assertEqual(out["typed_jef_action"],row["oracle_action"])
                self.assertTrue(out["source_rechecked"])
                self.assertEqual(out["c2_advisory"]["status"],"NOT_SUPPLIED")
                self.assertEqual([m["role"] for m in out["messages"]],
                                 ["system","user"])
                self.assertEqual(json.loads(out["messages"][1]["content"])[
                    "typed_jef_action"],row["oracle_action"])
                self.assertEqual(r.store.one(
                    "SELECT COUNT(*) AS n FROM actions")["n"],0)
                self.assertEqual(r.store.one(
                    "SELECT COUNT(*) AS n FROM messages WHERE role='assistant'")["n"],0)
                self.safe(out)

    def test_valid_c2_is_advisory_not_a_route_override(self):
        row=cohort()[0];r,e,ids=self.make(row)
        c=control();out=self.call(
            r,e,ids,native_control=c,calibration=approved(c),
            effort_band="FOCAL_TARGETED",resource_wake_ceiling="both")
        self.assertEqual(out["status"],READY,out)
        self.assertEqual(out["c2_advisory"]["status"],
                         "MONOTONE_UPGRADE_SHADOW")
        self.assertEqual(out["c2_advisory"]["proposed_body_route"],"both")
        self.assertTrue(out["c2_advisory"]["changed"])
        self.assertTrue(out["c2_cannot_override_jef"])
        self.assertEqual(out["formatter_route"],"JEF_TYPED_C3_FORMATTER_ONLY")
        self.safe(out)

    def test_invalid_c2_calibration_never_launders_jef(self):
        row=cohort()[0];r,e,ids=self.make(row)
        for c,cal in ((control(),None),
                      (control(),approved(control())|{"in_support":False}),
                      ({"function_calls":"forged"},None),
                      ({"huge":"x"*10000},None)):
            with self.subTest(c=repr(c)[:60]):
                out=self.call(r,e,ids,native_control=c,calibration=cal,
                              effort_band="FOCAL_TARGETED",
                              resource_wake_ceiling="both")
                self.assertEqual(out["status"],READY,out)
                self.assertFalse(out["c2_advisory"]["changed"])
                self.assertEqual(out["formatter_route"],
                                 "JEF_TYPED_C3_FORMATTER_ONLY")
                self.safe(out)

    def test_wrong_memory_order_or_missing_source_abstains(self):
        row=cohort()[0];r,e,ids=self.make(row)
        out=self.call(r,e,ids[::-1])
        self.assertEqual(out["status"],"JEF_SOURCE_ADMISSION_RED",out)
        self.assertIsNone(out["formatter_route"])
        self.safe(out)
        with r.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (e["source_ref"]["source_id"],))
        out=self.call(r,e,ids)
        self.assertNotEqual(out["status"],READY)
        self.safe(out)

    def test_newer_user_event_invalidates_source(self):
        row=cohort()[0];r,e,ids=self.make(row)
        r.store.event(r.session,"Project "+row["id"]+". Newer user turn.")
        out=self.call(r,e,ids)
        self.assertEqual(out["status"],"JEF_SOURCE_ADMISSION_RED",out)
        self.safe(out)

    def test_executive_approval_cancel_and_resource_guards(self):
        row=cohort()[0];r,e,ids=self.make(row)
        for kw,status in (
            ({"approval_receipt":{}}, "REAL_TTY_APPROVAL_UNSUPPORTED"),
            ({"executive_admissible":False},"EXECUTIVE_VETO"),
            ({"executive_admissible":1},"EXECUTIVE_VETO"),
            ({"cancelled":True},"CANCELLED_OR_INVALID"),
            ({"resource_wake_ceiling":"unlimited"},"ROUTE_OR_RESOURCE_INPUT_RED"),
        ):
            with self.subTest(kw=kw):
                out=self.call(r,e,ids,**kw)
                self.assertEqual(out["status"],status)
                self.safe(out)

    def test_source_changed_during_second_recheck_abstains(self):
        row=cohort()[0];r,e,ids=self.make(row)
        from v13 import jef_c2_c3_formatter_route_shadow_candidate as module
        original=module.build_jef_c3_typed_envelope
        calls=[0]
        def changed(*args,**kwargs):
            calls[0]+=1
            result=original(*args,**kwargs)
            if calls[0]==2:
                result=dict(result,messages_sha256="0"*64)
            return result
        with patch.object(module,"build_jef_c3_typed_envelope",
                          side_effect=changed):
            out=self.call(r,e,ids)
        self.assertEqual(out["status"],"SOURCE_CHANGED_DURING_ROUTE",out)
        self.safe(out)

if __name__=="__main__":
    unittest.main()
