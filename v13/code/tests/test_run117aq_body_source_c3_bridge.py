"""Run117AQ real-SQLite B1/B2 persisted source-ID -> C3 SHADOW tests."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from scripts.run117am_body_source_id_native import fixture
from tests.test_run117ah_body_source_id_candidate import choose
from tests.test_run117s_b2_salient_source_shadow import QuoteRuntime
from v13.body_source_id_bound_prewarm_candidate import select_bound_prewarmed
from v13.body_source_id_c3_evidence_bridge_candidate import build_source_id_c3_bridge
from v13.common import dumps

FIXTURE=Path(__file__).resolve().parents[1]/(
    "docs/fixtures/RUN117AM_BODY_SOURCE_ID_SEED1073.json")


def select_event(runtime,event,role,callback=None):
    def acquire(r):
        runtime.store.set_state("run117aq_bodyport",{"role":r,"state":"ASSIGNED"})
        return SimpleNamespace(role=r)
    def release(runner):
        runtime.store.set_state("run117aq_bodyport",{"role":runner.role,"state":"RELEASED"})
    result=select_bound_prewarmed(
        runtime,event,role,acquire,
        lambda runner,messages:(
            callback(messages) if callback else choose(runner.role)(messages)),
        release,operator_opt_in=True,callback_opt_in=True)
    return result


class SourceIdC3BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.row=fixture(FIXTURE)[0]
        self.r=QuoteRuntime(Path(self.tmp.name)/"home",self.row)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def prepare(self,runtime=None,row=None,b2_callback=None,b1_callback=None):
        runtime=runtime or self.r
        row=row or self.row
        prior=runtime.store.event(runtime.session,row["prior"])
        b2=select_event(runtime,prior,"B2_GIST",b2_callback)
        self.assertTrue(b2.get("packet_id"),b2)
        current=runtime.store.event(runtime.session,row["current"])
        b1=select_event(runtime,current,"B1_DETAIL",b1_callback)
        self.assertTrue(b1.get("packet_id"),b1)
        return prior,current,{"B2_GIST":b2["packet_id"],
                             "B1_DETAIL":b1["packet_id"]}

    def assert_safe(self,result):
        self.assertFalse(result["output_committed"])
        self.assertEqual(result["tool_dispatches"],0)
        self.assertEqual(result["delivery_authority"],0)
        self.assertEqual(result["learning_authority"],0)
        self.assertEqual(result["jepa_weight"],0)
        self.assertFalse(result["native_proof"])
        self.assertFalse(result["whole_system_complete"])

    def test_six_rows_exact_causal_source_only_c3_prompts(self):
        for row in fixture(FIXTURE):
            with self.subTest(project=row["id"]):
                with tempfile.TemporaryDirectory() as d:
                    runtime=QuoteRuntime(Path(d)/"home",row)
                    try:
                        prior,current,ids=self.prepare(runtime,row)
                        before=runtime.store.db.total_changes
                        result=build_source_id_c3_bridge(
                            runtime,prior,current,ids,operator_opt_in=True)
                        self.assertEqual(result["status"],
                                         "SHADOW_C3_SOURCE_ID_EVIDENCE_READY",result)
                        self.assertEqual(runtime.store.db.total_changes,before)
                        self.assertEqual(result["messages_sha256"],
                            hashlib.sha256(dumps(result["messages"]).encode()).hexdigest())
                        self.assertEqual([x["role"] for x in result["messages"]],
                                         ["system","user"])
                        payload=json.loads(result["messages"][1]["content"])
                        self.assertIsNone(payload["typed_jef_candidate"])
                        self.assertEqual(payload["typed_candidate_authority"],0)
                        self.assertNotIn("oracle",payload)
                        self.assertEqual([x["role"] for x in payload["body_observations"]],
                                         ["B2_GIST","B1_DETAIL"])
                        self.assertEqual(
                            [x["exact_source_excerpt"] for x in payload["body_observations"]],
                            [row["policy_span"],row["option_span"]])
                        self.assertTrue(all(
                            x["selection_authority"]=="MODEL_HYPOTHESIS_NOT_FACT"
                            and x["source_role"]=="UNTRUSTED_EXACT_USER"
                            for x in payload["body_observations"]))
                        self.assertEqual(runtime.store.one(
                            "SELECT COUNT(*) AS n FROM actions")["n"],0)
                        self.assertFalse(result["answer_computed"])
                        self.assertFalse(result["model_called"])
                        self.assert_safe(result)
                    finally:
                        runtime.close()

    def test_wrong_model_id_not_laundered_into_c3(self):
        def wrong(messages):
            data=json.loads(messages[1]["content"])
            return json.dumps({"span_id":next(
                x["span_id"] for x in data["candidates"]
                if not x["text"].startswith("Binding policy:"))})
        prior,current,ids=self.prepare(b2_callback=wrong)
        result=build_source_id_c3_bridge(
            self.r,prior,current,ids,operator_opt_in=True)
        self.assertEqual(result["status"],"SOURCE_ID_C3_BRIDGE_RED")
        self.assertNotIn("messages",result)
        self.assert_safe(result)

    def test_abstaining_body_id_not_laundered(self):
        prior,current,ids=self.prepare(
            b2_callback=lambda _: '{"span_id":"NONE"}')
        result=build_source_id_c3_bridge(
            self.r,prior,current,ids,operator_opt_in=True)
        self.assertEqual(result["status"],"SOURCE_ID_C3_BRIDGE_RED")
        self.assertNotIn("messages",result)
        self.assert_safe(result)

    def test_forged_current_event_prior_source_ref_rejected(self):
        prior,current,ids=self.prepare()
        forged=dict(current,source_ref=prior["source_ref"])
        result=build_source_id_c3_bridge(
            self.r,prior,forged,ids,operator_opt_in=True)
        self.assertEqual(result["status"],"SOURCE_ID_C3_BRIDGE_RED")
        self.assert_safe(result)

    def test_stale_current_and_intermediate_user_rejected(self):
        prior,current,ids=self.prepare()
        self.r.store.event(self.r.session,"Project Halcyon correction: cancel.")
        result=build_source_id_c3_bridge(
            self.r,prior,current,ids,operator_opt_in=True)
        self.assertEqual(result["status"],"SOURCE_ID_C3_BRIDGE_RED")
        self.assert_safe(result)

    def test_swapped_and_duplicate_packet_ids_rejected(self):
        prior,current,ids=self.prepare()
        swapped={"B2_GIST":ids["B1_DETAIL"],"B1_DETAIL":ids["B2_GIST"]}
        r=build_source_id_c3_bridge(self.r,prior,current,swapped,
                                    operator_opt_in=True)
        self.assertEqual(r["status"],"SOURCE_ID_C3_BRIDGE_RED")
        duplicate={"B2_GIST":ids["B2_GIST"],"B1_DETAIL":ids["B2_GIST"]}
        r=build_source_id_c3_bridge(self.r,prior,current,duplicate,
                                    operator_opt_in=True)
        self.assertEqual(r["status"],"INVALID_SELECTION_IDS_RED")

    def test_tampered_persisted_selected_span_rejected(self):
        prior,current,ids=self.prepare()
        row=self.r.store.one("SELECT payload FROM packets WHERE id=?",
                             (ids["B2_GIST"],))
        packet=json.loads(row["payload"])
        packet["selected_span"]["text"]="forged"
        with self.r.store.tx() as db:
            db.execute("UPDATE packets SET payload=? WHERE id=?",
                       (dumps(packet),ids["B2_GIST"]))
        result=build_source_id_c3_bridge(
            self.r,prior,current,ids,operator_opt_in=True)
        self.assertEqual(result["status"],"SOURCE_ID_C3_BRIDGE_RED")
        self.assert_safe(result)

    def test_model_revision_change_rejected(self):
        prior,current,ids=self.prepare()
        original=self.r.models.revision
        self.r.models.revision=lambda role:"SWAPPED_REVISION"
        try:
            result=build_source_id_c3_bridge(
                self.r,prior,current,ids,operator_opt_in=True)
            self.assertEqual(result["status"],"SOURCE_ID_C3_BRIDGE_RED")
        finally:
            self.r.models.revision=original

    def test_intermediate_user_before_current_breaks_causal_pair(self):
        prior=self.r.store.event(self.r.session,self.row["prior"])
        b2=select_event(self.r,prior,"B2_GIST")
        self.r.store.event(self.r.session,"Project Halcyon unrelated note.")
        current=self.r.store.event(self.r.session,self.row["current"])
        b1=select_event(self.r,current,"B1_DETAIL")
        result=build_source_id_c3_bridge(
            self.r,prior,current,{"B2_GIST":b2["packet_id"],
                                  "B1_DETAIL":b1["packet_id"]},
            operator_opt_in=True)
        self.assertEqual(result["status"],"SOURCE_ID_C3_BRIDGE_RED")

    def test_default_off_and_no_source_writes(self):
        prior,current,ids=self.prepare()
        before=self.r.store.db.total_changes
        r=build_source_id_c3_bridge(self.r,prior,current,ids)
        self.assertEqual(r["status"],"OFF")
        self.assertEqual(self.r.store.db.total_changes,before)
        self.assert_safe(r)


if __name__=="__main__":
    unittest.main()
