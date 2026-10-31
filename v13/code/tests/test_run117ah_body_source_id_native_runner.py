"""Run117AH native Body runner structural model-free preflight."""
from pathlib import Path
import tempfile
import unittest

from scripts.run117ah_body_source_id_native import (
    COMPLETE, RED, _summarize, fixture, run,
)
from tests.test_run117ah_body_source_id_candidate import FIXTURE


class NativeRunnerStatic(unittest.TestCase):
    def test_frozen_six_disjoint_cases(self):
        rows=fixture(FIXTURE)
        self.assertEqual(len(rows),6)
        self.assertEqual([r["id"] for r in rows],
                         ["Auric","Beryl","Cobalt","Daphne","Elder","Fable"])

    def test_wrong_fixture_fails_before_native(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"bad.json"
            p.write_text("{}")
            with self.assertRaisesRegex(ValueError,"FIXTURE_SHA_RED"):
                run(p,Path(d)/"missing",Path(d)/"work",Path(d)/"out")

    def test_existing_work_fails_before_native(self):
        with tempfile.TemporaryDirectory() as d:
            work=Path(d)/"work"
            work.mkdir()
            with self.assertRaises(FileExistsError):
                run(FIXTURE,Path(d)/"missing",work,Path(d)/"out")

    def test_missing_native_calls_red(self):
        r={"rows":[],"native_body_calls":0,"native_c3_calls":0,
           "native_jef_calls":0,"native_c2_calls":0}
        self.assertEqual(_summarize(r),RED)

    def test_full_pinned_receipts_needed_for_complete(self):
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
                         "offers":[item("B2_GIST"),item("B1_DETAIL"),
                                   item("B2_GIST")],
                         "id_selections":[item("B2_GIST"),item("B1_DETAIL")]})
        r={"rows":rows,"native_body_calls":30,"native_c3_calls":0,
           "native_jef_calls":0,"native_c2_calls":0}
        self.assertEqual(_summarize(r),COMPLETE)
        self.assertEqual(r["baseline_quote_ready_count"],6)
        self.assertEqual(r["model_id_pair_correct_count"],6)
        rows[0]["offers"][0]["process_reaped"]=False
        self.assertEqual(_summarize(r),RED)


if __name__=="__main__":
    unittest.main()
