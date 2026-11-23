"""Run117AR fresh seed1077 source-only C3 paired native preflight."""
from hashlib import sha256
import json
from pathlib import Path
import re
import tempfile
import unittest

from scripts.run117ar_c3_source_only_native import (
    ARMS, IDS, SEED, FIXTURE_SHA, COMPLETE, RED,
    _prompts, _summarize, fixture, run,
)

FIXTURE=Path(__file__).resolve().parents[1]/(
    "docs/fixtures/RUN117AR_C3_SOURCE_ONLY_SEED1077.json")


class C3SourceOnlyPreflight(unittest.TestCase):
    def test_frozen_fresh_fixture_and_disjoint_ids(self):
        self.assertEqual(SEED,1077)
        self.assertEqual(sha256(FIXTURE.read_bytes()).hexdigest(),FIXTURE_SHA)
        rows=fixture(FIXTURE)
        self.assertEqual(len(rows),6)
        self.assertEqual(tuple(r["id"] for r in rows),IDS)
        self.assertEqual(ARMS,("NO_PRIOR","EXACT_SOURCE"))
        self.assertTrue(set(IDS).isdisjoint(
            {"Auric","Beryl","Cobalt","Daphne","Elder","Fable",
             "Halcyon","Iris","Juniper","Kestrel","Lumen","Meridian"}))

    def test_independent_policy_oracles(self):
        for row in fixture(FIXTURE):
            with self.subTest(row=row["id"]):
                budget,deadline=map(int,re.findall(r"\d+",row["policy_span"]))
                local_only=row["policy_span"].endswith("local-only true.")
                offers=re.findall(
                    r"Option [AB]: cost (\d+) euros, duration (\d+) days, local (true|false)\.",
                    row["option_span"])
                self.assertEqual(len(offers),2)
                valid=[(name,int(cost)) for name,(cost,days,local) in
                       zip(("A","B"),offers)
                       if int(cost)<=budget and int(days)<=deadline
                       and (not local_only or local=="true")]
                best=min(valid,key=lambda p:p[1]) if valid else ("NONE",None)
                self.assertEqual(row["oracle"],
                    {"choice":best[0],"remaining":None if best[1] is None
                     else budget-best[1]})

    def test_six_real_store_prompt_pairs_no_typed_answers(self):
        for row in fixture(FIXTURE):
            with self.subTest(row=row["id"]):
                with tempfile.TemporaryDirectory() as d:
                    result=_prompts(row,Path(d)/"fake")
                    self.assertTrue(result["closed_store_ok"])
                    self.assertTrue(result["no_live_output"])
                    self.assertEqual(set(result["messages"]),set(ARMS))
                    self.assertEqual(len(result["source_refs"]),2)
                    self.assertNotEqual(result["prior_event_id"],
                                        result["current_event_id"])
                    for arm,prompt in result["messages"].items():
                        self.assertEqual([x["role"] for x in prompt],
                                         ["system","user"])
                        self.assertNotIn(row["policy_span"],prompt[0]["content"])
                        self.assertNotIn(row["option_span"],prompt[0]["content"])
                        self.assertNotIn('"oracle"',prompt[1]["content"])
                        self.assertNotIn('"typed_jef_candidate":{',prompt[1]["content"])
                        payload=json.loads(prompt[1]["content"])
                        self.assertIsNone(payload["typed_jef_candidate"])
                        self.assertEqual(payload["typed_candidate_authority"],0)
                        excerpts=[x["text"] for x in payload["body_observations"]]
                        self.assertEqual(excerpts,
                            [row["option_span"]] if arm=="NO_PRIOR" else
                            [row["policy_span"],row["option_span"]])
                        self.assertTrue(all(
                            x["source_role"]=="UNTRUSTED_EXACT_USER"
                            for x in payload["body_observations"]))

    def test_tampered_fixture_fails_before_model(self):
        with tempfile.TemporaryDirectory() as d:
            bad=Path(d)/"bad.json";bad.write_text("{}")
            with self.assertRaisesRegex(ValueError,"FIXTURE_SHA_RED"):
                run(bad,Path(d)/"missing",Path(d)/"work",Path(d)/"out")

    def test_existing_work_fails_before_model(self):
        with tempfile.TemporaryDirectory() as d:
            work=Path(d)/"work";work.mkdir()
            with self.assertRaises(FileExistsError):
                run(FIXTURE,Path(d)/"missing",work,Path(d)/"out")

    def test_missing_native_calls_remains_structural_red(self):
        r={"rows":[],"native_c3_calls":0,"native_body_calls":0,
           "native_jef_calls":0,"native_c2_calls":0}
        self.assertEqual(_summarize(r),RED)

    def test_complete_requires_all_twelve_final_reaped(self):
        def item(arm):
            return {"arm":arm,"status":"RECORDED","native_final":True,
                    "process_reaped":True,"native_metrics":{
                        "actual_model":"FORGED_UNPINNED_C3.gguf"},
                    "score":{"correct":1}}
        rows=[{"status":"RECORDED","closed_native_store_ok":True,
               "closed_fake_store_ok":True,
               "arms":[item(ARMS[0]),item(ARMS[1])]}
              for _ in range(6)]
        r={"rows":rows,"native_c3_calls":12,"native_body_calls":0,
           "native_jef_calls":0,"native_c2_calls":0}
        # This structural fake must not pass with an unpinned model name.
        self.assertEqual(_summarize(r),RED)


if __name__=="__main__":
    unittest.main()
