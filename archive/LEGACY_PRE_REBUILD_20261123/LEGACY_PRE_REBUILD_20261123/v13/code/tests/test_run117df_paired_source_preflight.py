"""Run117DF paired real Store source admission and oracle-leak regressions."""
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from scripts import run117df_paired_source_preflight as P
from scripts import run117de_normalized_source_fixture as F
from v13.common import dumps


class Run117DFPairedStorePreflight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = P.preflight()

    def test_all_twelve_exact_source_and_normalized_pairs(self):
        self.assertEqual(self.report["status"], P.STATUS)
        self.assertEqual(self.report["seed"], 117061)
        self.assertEqual(self.report["table_sha256"], F.TABLE_SHA256)
        self.assertEqual(len(self.report["rows"]), 12)
        self.assertEqual(self.report["planned_serial_native_calls"], 48)
        for row, f in zip(self.report["rows"], F.fixtures()):
            with self.subTest(project=f["project"]):
                self.assertEqual(row["source_sha256"], f["source_sha256"])
                self.assertEqual(row["arm_order"], f["arm_order"])
                self.assertTrue(row["store_closed"])
                self.assertTrue(row["no_live_output"])
                self.assertEqual(row["model_calls"], 0)
                self.assertEqual(row["native_calls"], 0)
                self.assertEqual(row["raw_messages_sha256"],
                                 hashlib.sha256(dumps(row["raw_messages"]).encode()).hexdigest())
                self.assertEqual(row["normalized_messages_sha256"],
                                 hashlib.sha256(dumps(row["normalized_messages"]).encode()).hexdigest())
                data = json.loads(row["normalized_messages"][1]["content"])
                self.assertEqual(data["source"], json.loads(row["raw_messages"][1]["content"]))
                self.assertFalse(data["typed_jef_action_visible"])
                self.assertNotIn("expected_for_offline_scorer_only", row)
                self.assertNotIn("suggested_action", row)

    def test_no_model_native_tool_delivery_learning_or_promotion(self):
        r = self.report
        self.assertFalse(r["native_proof"])
        self.assertEqual(r["native_calls_verified"], 0)
        self.assertEqual(r["native_calls"], 0)
        self.assertEqual(r["delivery_authority"], 0)
        self.assertEqual(r["learning_authority"], 0)
        self.assertEqual(r["tool_dispatches"], 0)
        self.assertEqual(r["jepa_weight"], 0)
        self.assertFalse(r["redmi_measured"])
        self.assertFalse(r["whole_system_complete"])
        self.assertEqual(r["step2"], "UTILITY_FAIL")
        self.assertEqual(r["b3"], "NO_PROMOTION")

    def test_same_source_different_message_sha_by_presentation(self):
        for row in self.report["rows"]:
            self.assertNotEqual(row["raw_messages_sha256"],
                                row["normalized_messages_sha256"])
            self.assertEqual(len(row["source_ref_sha256"]), 2)

    def test_source_ref_mismatch_refused(self):
        f = F.fixtures()[0]
        a = {"status": P.raw.STATUS, "oracle_action_visible": False,
             "model_called": False, "native_calls": 0,
             "messages_sha256": "x", "source_ref_sha256": ["a", "b"],
             "current_source_ref_sha256": "c"}
        b = {"status": P.normalized.READY, "oracle_action_visible": False,
             "model_called": False, "native_calls": 0,
             "original_messages_sha256": "x", "source_ref_sha256": ["a", "wrong"],
             "current_source_ref_sha256": "c"}
        with self.assertRaisesRegex(ValueError, "SOURCE_PAIR_BINDING_RED"):
            P._check_pair(f, a, b)

    def test_missing_source_action_oracle_injection_refused(self):
        row = self.report["rows"][0]
        f = F.fixtures()[0]
        a = {"status": P.raw.STATUS, "oracle_action_visible": False,
             "model_called": False, "native_calls": 0,
             "messages": row["raw_messages"],
             "messages_sha256": row["raw_messages_sha256"],
             "source_ref_sha256": row["source_ref_sha256"],
             "current_source_ref_sha256": row["current_source_ref_sha256"],
             "delivery_authority": 0, "learning_authority": 0}
        b = {"status": P.normalized.READY, "oracle_action_visible": False,
             "model_called": False, "native_calls": 0,
             "messages": copy.deepcopy(row["normalized_messages"]),
             "messages_sha256": row["normalized_messages_sha256"],
             "original_messages_sha256": row["raw_messages_sha256"],
             "source_ref_sha256": row["source_ref_sha256"],
             "current_source_ref_sha256": row["current_source_ref_sha256"],
             "delivery_authority": 0, "learning_authority": 0}
        injected = json.loads(b["messages"][1]["content"])
        injected["suggested_action"] = "A"
        b["messages"][1]["content"] = dumps(injected)
        b["messages_sha256"] = hashlib.sha256(dumps(b["messages"]).encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, "ORACLE_LEAK_RED"):
            P._check_pair(f, a, b)

    def test_immutable_frozen_source_rendering(self):
        self.assertEqual([f["project"] for f in F.fixtures()],
                         [f"EB{i:02d}" for i in range(1, 13)])
        self.assertEqual([F.oracle(row) for row in F.TABLE], ["A", "B", "NONE"] * 4)


if __name__ == "__main__":
    unittest.main()
