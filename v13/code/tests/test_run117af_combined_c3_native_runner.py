"""Run117AF model-free structural native runner guards (no model calls)."""
import tempfile
from pathlib import Path
import unittest

from scripts.run117af_combined_c3_native import (
    ARMS, COMPLETE, RED, _summarize, run,
)
from tests.test_run117af_combined_c3_native_preflight import FIXTURE, frozen_rows


class RunnerStructural(unittest.TestCase):
    def test_frozen_six_rows(self):
        self.assertEqual(len(frozen_rows()), 6)

    def test_partial_or_missing_native_is_red(self):
        r = {"rows": [], "native_c3_calls": 0,
             "native_body_calls": 0, "native_jef_calls": 0,
             "native_c2_calls": 0, "scores": {}}
        self.assertEqual(_summarize(r), RED)
        r["native_c3_calls"] = 12
        r["rows"] = [
            {"status":"RECORDED", "closed_native_store_ok":True,
             "closed_fake_store_ok":True, "arms":[]} for _ in range(6)]
        self.assertEqual(_summarize(r), RED)

    def test_complete_requires_all_reaped_and_native_metrics(self):
        def item(arm):
            return {"arm":arm, "status":"RECORDED", "native_final":True,
                    "process_reaped":True, "native_metrics":{
                        "actual_model":"LFM2.5-350M-QAD-Q4_0.gguf"},
                    "score":{"correct":1}}
        rows = [
            {"status":"RECORDED", "closed_native_store_ok":True,
             "closed_fake_store_ok":True,
             "arms":[item(ARMS[0]),item(ARMS[1])]}
            for _ in range(6)]
        report={"rows":rows,"native_c3_calls":12,
                "native_body_calls":0,"native_jef_calls":0,
                "native_c2_calls":0}
        self.assertEqual(_summarize(report), COMPLETE)
        self.assertEqual(report["scores"],{a:6 for a in ARMS})
        rows[0]["arms"][1]["process_reaped"]=False
        self.assertEqual(_summarize(report), RED)

    def test_invalid_fixture_refused_before_install(self):
        with tempfile.TemporaryDirectory() as d:
            wrong=Path(d)/"wrong.json"
            wrong.write_text("{}")
            with self.assertRaisesRegex(ValueError, "FIXTURE_SHA_RED"):
                run(wrong, Path(d)/"not-installed", Path(d)/"work",
                    Path(d)/"out")

    def test_existing_work_refused_before_native(self):
        with tempfile.TemporaryDirectory() as d:
            work=Path(d)/"work"
            work.mkdir()
            with self.assertRaises(FileExistsError):
                run(FIXTURE, Path(d)/"not-installed", work,
                    Path(d)/"out")


if __name__=="__main__":
    unittest.main()
