"""Synthetic structural verifier unit tests only; NOT native evidence."""
import copy
import json
import unittest

from scripts import jef_c3_source_reasoning_fixture_743 as f
from scripts import run70_c3_source_reasoning_verify as verify


def synthetic_report():
    rows=f.fixtures()
    report={
        "schema":"v13.run70.c3_source_reasoning_native.v1",
        "seed":f.SEED,"table_sha256":f.TABLE_SHA256,
        "model_sha256_required":f.MODEL_SHA256,
        "runner_sha256_required":f.RUNNER_SHA256,
        "model_sha256_observed":f.MODEL_SHA256,
        "runner_sha256_observed":f.RUNNER_SHA256,
        "native_call_count":12,"closed_store_ok":True,
        "no_live_output":True,"source_only_oracle_hidden":True,
        "delivery_authority":0,"tool_dispatches":0,"learning_authority":0,
        "tty_approved":False,"output_committed":False,
        "age0":"RECORD_ONLY","step2":"UTILITY_FAIL","b3":"NO_PROMOTION",
        "jepa_weight":0,"redmi_measured":False,"whole_system_complete":False,
        "cases":[],"strict":{"TYPED_SCHEMA":6,"SOURCE_SCHEMA":6},
        "status":"SOURCE_REASONING_SMALL_SYNTHETIC_PASS",
    }
    for row in rows:
        arms=[]
        order=f.ARMS if row["index"]%2==0 else f.ARMS[::-1]
        for arm in order:
            output=json.dumps({"action":row["expected"]})
            arms.append({
                "arm":arm,"output":output,"output_sha256":f.sha(output.encode()),
                "output_bytes":len(output.encode()),"parsed_action":row["expected"],
                "strict":1,"input_sha256":f.sha((arm+row["project"]).encode()),
                "typed_answer_visible":arm=="TYPED_SCHEMA",
                "native_final":True,"process_reaped":True,
                "actual_model":verify.EXPECTED_MODEL,"status":"RECORDED",
            })
        report["cases"].append({
            "index":row["index"],"expected":row["expected"],
            "project_sha256":f.sha(row["project"].encode()),
            "source_sha256":{k:f.sha(row[k].encode())
                for k in ("current","policy_source","sheet_source")},
            "arms":arms,
        })
    return report


class VerifierSoftware(unittest.TestCase):
    def test_synthetic_structural_fixture_not_native_evidence(self):
        self.assertEqual(verify.verify(synthetic_report())["status"],
                         "INDEPENDENT_RUN70_NATIVE_REPARSE_PASS")

    def test_output_hash_tamper_rejected(self):
        r=synthetic_report()
        r["cases"][0]["arms"][0]["output_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"NATIVE_ARM_RED"):
            verify.verify(r)

    def test_score_tamper_rejected(self):
        r=synthetic_report()
        r["strict"]["SOURCE_SCHEMA"]=5
        with self.assertRaisesRegex(ValueError,"SCORE_REPARSE_RED"):
            verify.verify(r)

    def test_native_final_missing_rejected(self):
        r=synthetic_report()
        r["cases"][1]["arms"][1]["native_final"]=False
        with self.assertRaisesRegex(ValueError,"NATIVE_ARM_RED"):
            verify.verify(r)

    def test_hidden_oracle_flag_rejected(self):
        r=synthetic_report()
        r["cases"][2]["arms"][0]["typed_answer_visible"]=not r["cases"][2]["arms"][0]["typed_answer_visible"]
        with self.assertRaisesRegex(ValueError,"NATIVE_ARM_RED"):
            verify.verify(r)

    def test_status_forgery_rejected(self):
        r=synthetic_report()
        r["status"]="WHOLE_SYSTEM_COMPLETE"
        with self.assertRaisesRegex(ValueError,"STATUS_REPARSE_RED"):
            verify.verify(r)

    def test_missing_source_hash_rejected(self):
        r=synthetic_report()
        r["cases"][3]["source_sha256"]["policy_source"]="0"*64
        with self.assertRaisesRegex(ValueError,"CASE_BINDING_RED"):
            verify.verify(r)

    def test_invalid_arm_order_rejected(self):
        r=synthetic_report()
        r["cases"][0]["arms"].reverse()
        with self.assertRaisesRegex(ValueError,"ARM_ORDER_RED"):
            verify.verify(r)


if __name__=="__main__":
    unittest.main()
