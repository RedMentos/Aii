"""Run117AM fresh seed1073 native runner preflight; NO native inference."""
from hashlib import sha256
import json
from pathlib import Path
import re
from types import SimpleNamespace
import tempfile
import unittest

from scripts.run117am_body_source_id_native import (
    COMPLETE, RED, SEED, FIXTURE_SHA, IDS, _summarize, fixture, run,
)
from tests.test_run117ah_body_source_id_candidate import choose
from tests.test_run117s_b2_salient_source_shadow import QuoteRuntime
from v13.body_source_id_prewarm_candidate import select_prewarmed

FIXTURE=Path(__file__).resolve().parents[1]/(
    "docs/fixtures/RUN117AM_BODY_SOURCE_ID_SEED1073.json")


class FreshNativePreflight(unittest.TestCase):
    def test_frozen_disjoint_fixture_and_sha(self):
        self.assertEqual(SEED,1073)
        self.assertEqual(sha256(FIXTURE.read_bytes()).hexdigest(),FIXTURE_SHA)
        rows=fixture(FIXTURE)
        self.assertEqual(len(rows),6)
        self.assertEqual(tuple(r["id"] for r in rows),IDS)
        self.assertTrue(set(IDS).isdisjoint(
            {"Auric","Beryl","Cobalt","Daphne","Elder","Fable"}))

    def test_independent_oracle_from_exact_policy_and_options(self):
        for row in fixture(FIXTURE):
            with self.subTest(row=row["id"]):
                budget,deadline=map(int,re.findall(r"\d+",row["policy_span"]))
                local_only=row["policy_span"].endswith("local-only true.")
                matches=re.findall(
                    r"Option [AB]: cost (\d+) euros, duration (\d+) days, local (true|false)\.",
                    row["option_span"])
                self.assertEqual(len(matches),2)
                eligible=[(name,int(cost)) for name,(cost,days,local) in
                          zip(("A","B"),matches)
                          if int(cost)<=budget and int(days)<=deadline
                          and (not local_only or local=="true")]
                best=min(eligible,key=lambda p:p[1]) if eligible else ("NONE",None)
                self.assertEqual(row["oracle"],
                    {"choice":best[0],"remaining":None if best[1] is None
                     else budget-best[1]})

    def test_real_store_all_six_prewarm_source_ids(self):
        for row in fixture(FIXTURE):
            with self.subTest(row=row["id"]):
                with tempfile.TemporaryDirectory() as d:
                    runtime=QuoteRuntime(Path(d)/"home",row)
                    try:
                        for role,source in (
                            ("B2_GIST",row["prior"]),
                            ("B1_DETAIL",row["current"])):
                            event=runtime.store.event(runtime.session,source)
                            def acquire(r):
                                runtime.store.set_state(
                                    "run117am_bodyport",{"role":r,"state":"ASSIGNED"})
                                return SimpleNamespace(role=r)
                            def release(r):
                                runtime.store.set_state(
                                    "run117am_bodyport",{"role":r.role,"state":"RELEASED"})
                            result=select_prewarmed(
                                runtime,event,role,acquire,
                                lambda runner,messages:choose(runner.role)(messages),
                                release,operator_opt_in=True,callback_opt_in=True)
                            self.assertEqual(result["status"],
                                "SHADOW_SOURCE_ID_SELECTED",result)
                            self.assertFalse(result["native_model_proven"])
                            self.assertEqual(result["delivery_authority"],0)
                            self.assertEqual(result["learning_authority"],0)
                    finally:
                        runtime.close()

    def test_wrong_fixture_fails_before_native(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"bad.json";p.write_text("{}")
            with self.assertRaisesRegex(ValueError,"FIXTURE_SHA_RED"):
                run(p,Path(d)/"missing",Path(d)/"work",Path(d)/"out")

    def test_existing_work_fails_before_native(self):
        with tempfile.TemporaryDirectory() as d:
            work=Path(d)/"work";work.mkdir()
            with self.assertRaises(FileExistsError):
                run(FIXTURE,Path(d)/"missing",work,Path(d)/"out")

    def test_missing_native_calls_red(self):
        r={"rows":[],"native_body_calls":0,"native_c3_calls":0,
           "native_jef_calls":0,"native_c2_calls":0}
        self.assertEqual(_summarize(r),RED)

    def test_complete_requires_closed_packets_and_reaping(self):
        def item(role):
            return {"role":role,"status":"RECORDED","process_reaped":True,
                    "native_metrics":{"status":"FINAL"},
                    "packet_evidence":{"raw":"{}","sha256":
                        "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"}}
        rows=[]
        for _ in range(6):
            rows.append({"status":"RECORDED","closed_store_ok":True,
                         "no_live_output":True,"baseline_quote_ready":True,
                         "id_pair_correct":True,
                         "offers":[item("B2_GIST"),item("B1_DETAIL"),item("B2_GIST")],
                         "id_selections":[item("B2_GIST"),item("B1_DETAIL")]})
        r={"rows":rows,"native_body_calls":30,"native_c3_calls":0,
           "native_jef_calls":0,"native_c2_calls":0}
        self.assertEqual(_summarize(r),COMPLETE)
        rows[0]["id_selections"][0]["process_reaped"]=False
        self.assertEqual(_summarize(r),RED)


if __name__=="__main__":
    unittest.main()
