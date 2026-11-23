"""Run117AU fresh seed1081 real-Store C3 source-presentation model-free tests."""
from hashlib import sha256
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from scripts import run117au_c3_plain_source_native as native

FIXTURE=Path(__file__).resolve().parents[1]/(
    "docs/fixtures/RUN117AU_C3_PLAIN_SOURCE_SEED1081.json")

class C3PlainSourcePreflight(unittest.TestCase):
    def test_frozen_fixture_oracles_and_disjoint(self):
        self.assertEqual(native.SEED,1081)
        self.assertEqual(sha256(FIXTURE.read_bytes()).hexdigest(),native.FIXTURE_SHA)
        rows=native.fixture(FIXTURE)
        self.assertEqual(tuple(r["id"] for r in rows),native.IDS)
        self.assertEqual(native.ARMS,("NO_PRIOR_JSON","EXACT_JSON","EXACT_PLAIN"))
        self.assertTrue(set(native.IDS).isdisjoint(
            {"Orion","Polaris","Quasar","Radian","Solstice","Tundra",
             "Halcyon","Iris","Juniper","Kestrel","Lumen","Meridian"}))
        for r in rows:
            with self.subTest(id=r["id"]):
                budget,deadline=map(int,re.findall(r"\d+",r["policy_span"]))
                local_only=r["policy_span"].endswith("local-only true.")
                offers=re.findall(
                    r"Option ([AB]): cost (\d+) euros, duration (\d+) days, local (true|false)\.",
                    r["option_span"])
                self.assertEqual(len(offers),2)
                valid=[(name,int(cost)) for name,cost,days,local in offers
                       if int(cost)<=budget and int(days)<=deadline
                       and (not local_only or local=="true")]
                best=min(valid,key=lambda p:p[1]) if valid else ("NONE",None)
                self.assertEqual(r["oracle"],{"choice":best[0],
                    "remaining":None if best[1] is None else budget-best[1]})

    def test_six_real_store_three_arm_source_prompts(self):
        for row in native.fixture(FIXTURE):
            with self.subTest(id=row["id"]):
                with tempfile.TemporaryDirectory() as d:
                    p=native._prompts(row,Path(d)/"fake")
                    self.assertTrue(p["closed_store_ok"])
                    self.assertTrue(p["no_live_output"])
                    self.assertEqual(set(p["messages"]),set(native.ARMS))
                    self.assertEqual(len(p["source_refs"]),2)
                    systems=set()
                    for arm,msg in p["messages"].items():
                        self.assertEqual([m["role"] for m in msg],["system","user"])
                        systems.add(msg[0]["content"])
                        self.assertNotIn(row["policy_span"],msg[0]["content"])
                        self.assertNotIn(row["option_span"],msg[0]["content"])
                        self.assertNotIn('"oracle"',msg[1]["content"])
                        if arm=="EXACT_PLAIN":
                            self.assertIn(row["policy_span"],msg[1]["content"])
                            self.assertIn(row["option_span"],msg[1]["content"])
                            self.assertNotIn("typed_jef_candidate",msg[1]["content"])
                            for ref in p["source_refs"]:
                                self.assertIn(ref["source_id"],msg[1]["content"])
                        else:
                            payload=json.loads(msg[1]["content"])
                            self.assertIsNone(payload["typed_jef_candidate"])
                            self.assertEqual(payload["typed_candidate_authority"],0)
                            excerpts=[x["text"] for x in payload["body_observations"]]
                            self.assertEqual(excerpts,
                                [row["option_span"]] if arm=="NO_PRIOR_JSON" else
                                [row["policy_span"],row["option_span"]])
                            self.assertTrue(all(
                                x["source_role"]=="UNTRUSTED_EXACT_USER"
                                for x in payload["body_observations"]))
                            self.assertEqual([x["source_ref"] for x in
                                payload["body_observations"]],
                                [p["source_refs"][1]] if arm=="NO_PRIOR_JSON" else
                                p["source_refs"])
                    self.assertEqual(len(systems),1)

    def test_ambiguous_prior_source_ref_fails_closed(self):
        row=dict(native.fixture(FIXTURE)[0])
        row["prior"]+=" "+row["policy_span"]
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"SOURCE_SPAN_AMBIGUOUS_RED"):
                native._prompts(row,Path(d)/"fake")

    def test_forged_event_snapshot_fails_closed(self):
        real=native._event_snapshot
        def forged(*args,**kwargs):
            snap=real(*args,**kwargs)
            snap=dict(snap);snap["generation"]="forged_generation"
            return snap
        with tempfile.TemporaryDirectory() as d:
            with patch.object(native,"_event_snapshot",side_effect=forged):
                with self.assertRaisesRegex(ValueError,"EVENT_SOURCE_RED"):
                    native._prompts(native.fixture(FIXTURE)[0],Path(d)/"fake")

    def test_tampered_fixture_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"fixture.json";f.write_text("{}")
            with self.assertRaisesRegex(ValueError,"FIXTURE_SHA_RED"):
                native.fixture(f)

    def test_existing_work_refused_before_native(self):
        with tempfile.TemporaryDirectory() as d:
            work=Path(d)/"work";work.mkdir()
            with self.assertRaises(FileExistsError):
                native.run(FIXTURE,Path(d)/"no-model",work,Path(d)/"out")

    def test_missing_eighteen_calls_stays_red(self):
        r={"rows":[],"native_c3_calls":0,"native_body_calls":0,
           "native_jef_calls":0,"native_c2_calls":0}
        self.assertEqual(native._summarize(r),native.RED)

    def test_forged_native_model_stays_red(self):
        def item(arm):
            return {"arm":arm,"status":"RECORDED","native_final":True,
                    "process_reaped":True,"native_metrics":{
                        "actual_model":"FORGED_MODEL.gguf"},"score":{"correct":1}}
        r={"rows":[{"status":"RECORDED","closed_native_store_ok":True,
                    "closed_fake_store_ok":True,
                    "arms":[item(arm) for arm in native.ARMS]} for _ in range(6)],
           "native_c3_calls":18,"native_body_calls":0,"native_jef_calls":0,
           "native_c2_calls":0}
        self.assertEqual(native._summarize(r),native.RED)

if __name__=="__main__":
    unittest.main()
