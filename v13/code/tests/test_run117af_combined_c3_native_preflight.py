"""Run117AF seed1067 frozen disjoint combined native prompt preflight."""
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest

from scripts.run52_b1b2_cross_turn_native import OVERRIDES
from tests.test_run117s_b2_salient_source_shadow import QuoteRuntime
from v13.agi.eligibility import recipe
from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from v13.b1b2_jef_span_c3_bridge_candidate import build_b1b2_jef_span_c3_bridge
from v13.jef_span_budget_shadow_candidate import build_jef_span_budget_shadow
from v13.context_os import controller

FIXTURE = Path(__file__).resolve().parents[1] / (
    "docs/fixtures/RUN117AF_COMBINED_C3_NATIVE_SEED1067.json")
SHA = "cbaa2e2f8e92c994a63f12fdb9ff165c5082dcd8a33ef2c7c311e512749f29cf"
IDS = ("Orion", "Petra", "Quill", "Rowan", "Sable", "Topaz")
ARMS = ("REAL_STORE_JEF_ONLY", "B1B2_JEF_CONTEXTOS")


def frozen_rows():
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == SHA
    data = json.loads(FIXTURE.read_text())
    assert set(data) == {"schema", "seed", "arms", "rows"}
    assert data["schema"] == "v13.run117af.combined_c3_native_seed1067.v1"
    assert data["seed"] == 1067 and data["arms"] == list(ARMS)
    assert [r["id"] for r in data["rows"]] == list(IDS)
    for row in data["rows"]:
        assert set(row) == {
            "id", "prior", "current", "policy_span", "option_span", "oracle"}
        assert row["prior"].count(row["policy_span"]) == 1
        assert row["current"].count(row["option_span"]) == 1
        assert row["prior"].startswith("Project " + row["id"])
        assert row["current"].startswith("Project " + row["id"])
        import re
        m = re.fullmatch(
            r"Binding policy: budget (\d+) euros; deadline (\d+) days; local-only (true|false)\.",
            row["policy_span"])
        options = re.findall(
            r"Option ([AB]): cost (\d+) euros, duration (\d+) days, local (true|false)\.",
            row["option_span"])
        assert m and len(options) == 2
        assert [o[0] for o in options] == ["A", "B"]
        choice, evaluated = recipe(
            int(m[1]), int(m[2]), m[3] == "true",
            [{"entity":o[0], "cost":int(o[1]), "days":int(o[2]),
              "local":o[3]=="true"} for o in options])
        remaining = next((x["remaining"] for x in evaluated
                          if x["entity"] == choice), None)
        assert row["oracle"] == {"choice":choice, "remaining":remaining}
    return data["rows"]


def make(row):
    tmp = tempfile.TemporaryDirectory()
    r = QuoteRuntime(Path(tmp.name) / "home", row)
    r.cfg.update(OVERRIDES)
    prior = r.store.event(r.session, row["prior"])
    current = r.store.event(r.session, row["current"])
    consumer = TopicPartitionOfferConsumer(r)
    ids = {}
    for role in ("B1_DETAIL", "B2_GIST"):
        offer = consumer.guarded_offer(
            role, current, 0, time.monotonic()+30, operator_opt_in=True)
        assert offer["status"] == "SHADOW_OFFER_PRODUCED", offer
        ids[role] = offer["offer_packet_id"]
    return tmp,r,prior,current,ids


class Preflight(unittest.TestCase):
    def test_six_frozen_rows_both_prompts(self):
        for row in frozen_rows():
            with self.subTest(row=row["id"]):
                tmp,r,prior,current,ids = make(row)
                try:
                    jef = build_jef_span_budget_shadow(
                        r, prior, current, operator_opt_in=True)
                    bridge = build_b1b2_jef_span_c3_bridge(
                        r, prior, current, ids, operator_opt_in=True)
                    self.assertEqual(jef["status"],
                                     "SHADOW_SOURCE_BOUND_JEF_BUDGET_VERIFIED")
                    self.assertEqual(bridge["status"],
                                     "SHADOW_B1B2_JEF_SPAN_C3_BRIDGE_VERIFIED")
                    self.assertEqual(jef["typed_jef_candidate"],row["oracle"])
                    self.assertEqual(bridge["typed_jef_candidate"],row["oracle"])
                    self.assertEqual(bridge["verified_quote_count"] >= 0, True)
                    self.assertEqual([x["role"] for x in bridge["messages"]],
                                     ["system","user"])
                    self.assertNotIn(row["policy_span"],bridge["messages"][0]["content"])
                    self.assertNotIn('"oracle"',bridge["messages"][1]["content"])
                    self.assertFalse(bridge["body_hypotheses_are_facts"])
                    self.assertFalse(bridge["output_committed"])
                    self.assertEqual(bridge["tool_dispatches"],0)
                    self.assertEqual(bridge["jepa_weight"],0)
                    self.assertEqual(r.store.one(
                        "SELECT COUNT(*) AS n FROM actions")["n"],0)
                finally:
                    r.close();tmp.cleanup()

    def test_off_and_stale_refuse(self):
        row=frozen_rows()[0]
        tmp,r,prior,current,ids=make(row)
        try:
            off=build_b1b2_jef_span_c3_bridge(r,prior,current,ids)
            self.assertEqual(off["status"],"OFF")
            r.store.event(r.session,"Project Orion correction: cancel previous.")
            stale=build_b1b2_jef_span_c3_bridge(
                r,prior,current,ids,operator_opt_in=True)
            self.assertEqual(stale["status"],"TWO_SOURCE_POINTER_RED")
        finally:
            r.close();tmp.cleanup()

    def test_active_and_swapped_offer_refuse(self):
        row=frozen_rows()[0]
        tmp,r,prior,current,ids=make(row)
        try:
            wrong={"B1_DETAIL":ids["B2_GIST"],"B2_GIST":ids["B1_DETAIL"]}
            self.assertEqual(build_b1b2_jef_span_c3_bridge(
                r,prior,current,wrong,operator_opt_in=True)["status"],
                "B1B2_OFFER_OR_SOURCE_RED")
            controller(r).set_mode("ACTIVE",authority="EXPLICIT_HUMAN")
            self.assertEqual(build_b1b2_jef_span_c3_bridge(
                r,prior,current,ids,operator_opt_in=True)["status"],
                "CONTEXT_OS_NOT_SHADOW_RED")
        finally:
            r.close();tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
