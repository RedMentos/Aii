"""Run117AH six frozen real SQLite source-ID selection software tests."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.run52_b1b2_cross_turn_native import OVERRIDES
from tests.test_run117s_b2_salient_source_shadow import QuoteRuntime
from v13.agi.eligibility import recipe
from v13.b1b2_source_id_quote_candidate import select, KIND, SYSTEM

FIXTURE=Path(__file__).resolve().parents[1]/(
    "docs/fixtures/RUN117AH_BODY_SOURCE_ID_SEED1069.json")
SHA="cff778da793fbab2d456143b5d8290176b1097cc0e4d867eabbd9fbc2e05f67a"


def rows():
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest()==SHA
    d=json.loads(FIXTURE.read_text())
    assert d["schema"]=="v13.run117ah.body_source_id_seed1069.v1"
    assert d["seed"]==1069
    assert d["roles"]==["B1_DETAIL","B2_GIST"]
    assert [r["id"] for r in d["rows"]]==[
        "Auric","Beryl","Cobalt","Daphne","Elder","Fable"]
    for r in d["rows"]:
        assert r["prior"].count(r["policy_span"])==1
        assert r["current"].count(r["option_span"])==1
        assert r["prior"].startswith("Project "+r["id"])
        assert r["current"].startswith("Project "+r["id"])
    return d["rows"]


def choose(role):
    def callback(messages):
        assert [m["role"] for m in messages]==["system","user"]
        data=json.loads(messages[1]["content"])
        assert "oracle" not in data
        assert data["source_role"]=="UNTRUSTED_EXACT_USER"
        assert len(data["candidates"])==2
        anchor="Option A:" if role=="B1_DETAIL" else "Binding policy:"
        selected=next(x["span_id"] for x in data["candidates"]
                      if anchor in x["text"])
        return json.dumps({"span_id":selected})
    return callback


class SourceIdTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.row=rows()[0]
        self.r=QuoteRuntime(Path(self.tmp.name)/"home",self.row)
        self.r.cfg.update(OVERRIDES)
        self.prior=self.r.store.event(self.r.session,self.row["prior"])

    def tearDown(self):
        self.r.close();self.tmp.cleanup()

    def call(self,event,role,callback=None,**kw):
        flags={"operator_opt_in":True,"callback_opt_in":True}
        flags.update(kw)
        return select(self.r,event,role,callback or choose(role),**flags)

    def assert_safe(self,result):
        self.assertFalse(result["output_committed"])
        self.assertEqual(result["tool_dispatches"],0)
        self.assertEqual(result["delivery_authority"],0)
        self.assertEqual(result["learning_authority"],0)
        self.assertEqual(result["jepa_weight"],0)
        self.assertFalse(result["native_model_proven"])
        self.assertFalse(result["source_semantic_truth_authority"])
        self.assertFalse(result["whole_system_complete"])

    def test_six_disjoint_rows_persist_exact_source_spans(self):
        for i,row in enumerate(rows()):
            with self.subTest(row=row["id"]):
                if i:
                    self.tearDown()
                    self.tmp=tempfile.TemporaryDirectory()
                    self.row=row
                    self.r=QuoteRuntime(Path(self.tmp.name)/"home",row)
                    self.r.cfg.update(OVERRIDES)
                    self.prior=self.r.store.event(self.r.session,row["prior"])
                b2=self.call(self.prior,"B2_GIST")
                self.assertEqual(b2["status"],"SHADOW_SOURCE_ID_SELECTED",b2)
                current=self.r.store.event(self.r.session,row["current"])
                b1=self.call(current,"B1_DETAIL")
                self.assertEqual(b1["status"],"SHADOW_SOURCE_ID_SELECTED",b1)
                for role,result,expected in (
                    ("B2_GIST",b2,row["policy_span"]),
                    ("B1_DETAIL",b1,row["option_span"])):
                    p=self.r.store.one(
                        "SELECT payload FROM packets WHERE id=? AND kind=?",
                        (result["packet_id"],KIND))
                    self.assertIsNotNone(p)
                    packet=json.loads(p["payload"])
                    self.assertEqual(packet["role"],role)
                    self.assertEqual(packet["selected_span"]["text"],expected)
                    self.assertEqual(self.r.store.read_source(
                        packet["selected_span"]["source_ref"]),expected)
                    self.assertTrue(packet["selection_correct_shadow"])
                    self.assertFalse(packet["source_semantic_truth_authority"])
                    self.assertTrue(packet["model_hypothesis_not_fact"])
                    self.assert_safe(result)
                self.assertEqual(self.r.store.one(
                    "SELECT COUNT(*) AS n FROM actions")["n"],0)

    def test_off_does_not_invoke_or_write(self):
        called=[]
        r=self.call(self.prior,"B2_GIST",lambda _:called.append(1),
                    operator_opt_in=False)
        self.assertEqual(r["status"],"OFF")
        self.assertEqual(called,[])
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind=?",(KIND,))["n"],0)
        self.assert_safe(r)

    def test_wrong_selection_persisted_as_fallible_not_fact(self):
        def wrong(messages):
            data=json.loads(messages[1]["content"])
            other=next(x["span_id"] for x in data["candidates"]
                       if "Binding policy:" not in x["text"])
            return json.dumps({"span_id":other})
        r=self.call(self.prior,"B2_GIST",wrong)
        self.assertEqual(r["status"],"SHADOW_WRONG_SOURCE_ID_RECORDED")
        self.assertFalse(r["selection_correct_shadow"])
        self.assert_safe(r)

    def test_abstain_persisted_without_quote(self):
        r=self.call(self.prior,"B2_GIST",lambda _:'{"span_id":"NONE"}')
        self.assertEqual(r["status"],"SHADOW_ABSTAIN_RECORDED")
        p=json.loads(self.r.store.one(
            "SELECT payload FROM packets WHERE id=?",(r["packet_id"],))["payload"])
        self.assertIsNone(p["selected_span"])
        self.assert_safe(r)

    def test_invalid_json_unknown_duplicate_extra(self):
        for raw in ('{"span_id":"forged"}','{"span_id":"s0","approved":true}',
                    '{"span_id":"s0","span_id":"s1"}',
                    '{"span_id":NaN}',"not JSON",
                    '{"span_id":"NONE"}'+" "*300):
            with self.subTest(raw=raw[:25]):
                r=self.call(self.prior,"B2_GIST",lambda _:raw)
                self.assertEqual(r["status"],"MODEL_JSON_RED")
                self.assert_safe(r)

    def test_late_user_correction_rejected(self):
        def late(_):
            self.r.store.event(self.r.session,
                               "Project Auric correction: ignore earlier.")
            return '{"span_id":"NONE"}'
        r=self.call(self.prior,"B2_GIST",late)
        self.assertEqual(r["status"],"CALLBACK_STORE_CHANGED_RED")
        self.assert_safe(r)

    def test_callback_prompt_mutation_rejected(self):
        def change(messages):
            messages[1]["content"]="{}"
            return '{"span_id":"NONE"}'
        r=self.call(self.prior,"B2_GIST",change)
        self.assertEqual(r["status"],"CALLBACK_PROMPT_MUTATED_RED")
        self.assert_safe(r)

    def test_deleted_source_rejected_before_callback(self):
        with self.r.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (self.prior["source_ref"]["source_id"],))
        called=[]
        r=self.call(self.prior,"B2_GIST",lambda _:called.append(1))
        self.assertEqual(r["status"],"SOURCE_PREFLIGHT_RED")
        self.assertEqual(called,[])

    def test_stale_prior_refused(self):
        self.r.store.event(self.r.session,self.row["current"])
        called=[]
        r=self.call(self.prior,"B2_GIST",lambda _:called.append(1))
        self.assertEqual(r["status"],"SOURCE_PREFLIGHT_RED")
        self.assertEqual(called,[])

    def test_exception_and_approval_refused(self):
        def bad(_):
            raise RuntimeError("synthetic failure")
        r=self.call(self.prior,"B2_GIST",bad)
        self.assertEqual(r["status"],"CALLBACK_EXCEPTION_RED")
        self.assertEqual(r["error_type"],"RuntimeError")
        called=[]
        r=self.call(self.prior,"B2_GIST",lambda _:called.append(1),
                    approval_receipt={"approved":True})
        self.assertEqual(r["status"],"REAL_TTY_APPROVAL_UNSUPPORTED_RED")
        self.assertEqual(called,[])

    def test_system_contains_no_source(self):
        self.assertNotIn(self.row["policy_span"],SYSTEM)
        self.assertNotIn(self.row["option_span"],SYSTEM)


if __name__=="__main__":
    unittest.main()
