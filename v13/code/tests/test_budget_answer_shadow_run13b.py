"""Run13B prospective real-Store SHADOW answer-form and adversarial controls."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import c2_body_disjoint_paired181_run11v as frozen
from scripts.c2_body_run12n_fulltask_readonly import explicit_faster_claim
from v13.agi import budget_answer_shadow_run13b as answer
from v13.agi import budget_en_source_shadow as jef
from v13.runtime import Runtime

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/c2_body_fulltask_run13a_seed211_20261030.json")
FROZEN_SHA = "e6718093ccd83d556019223eca2d5317668d1ada25659519a699aee681a8b97f"


def query(case):
    return (f"Calculate both remaining budgets and faster option "
            f"for Project {case['project']}.")


def cases():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert data["seed"] == 211
    assert hashlib.sha256(json.dumps(
        tuple(data["cases"]), sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest() == FROZEN_SHA
    return data["cases"]


class Run13BJefAnswerShadow(unittest.TestCase):
    def test_eight_exact_human_answers_frozen_scorer_and_no_model(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                runtime.sleep.cycle.set_policy("enabled", "off")
                with patch.object(runtime.pool, "get",
                                  side_effect=AssertionError("NATIVE_MODEL_CALLED")):
                    for case in cases():
                        q = runtime.store.source(query(case), "USER")
                        s = runtime.store.source(frozen.prompt(case), "USER")
                        before = runtime.store.one(
                            "SELECT count(*) AS n FROM sources")["n"]
                        got = answer.propose_text(runtime.store, q, s)
                        after = runtime.store.one(
                            "SELECT count(*) AS n FROM sources")["n"]
                        self.assertEqual(before, after)
                        self.assertEqual(got["reason"],
                                         "SOURCE_EXACT_ANSWER_FORM_SHADOW")
                        text = got["answer"]
                        self.assertEqual(text, (
                            f"Project {case['project']}.\n"
                            f"{case['a']} leaves {case['budget'] - case['a_cost']} Euro remaining.\n"
                            f"{case['b']} leaves {case['budget'] - case['b_cost']} Euro remaining.\n"
                            f"{case['a'] if case['a_days'] < case['b_days'] else case['b']} finishes sooner."))
                        self.assertEqual(frozen.score_pair(case, text)["correct"], 2)
                        self.assertEqual(explicit_faster_claim(
                            text, case["a"], case["b"]),
                            case["a"] if case["a_days"] < case["b_days"] else case["b"])
                        self.assertEqual(got["answer_sha256"],
                                         hashlib.sha256(text.encode()).hexdigest())
                        for k, v in {
                            "status": "SHADOW_NO_AUTHORITY",
                            "answer_kind": "SOURCE_EXACT_SHADOW_ONLY",
                            "delivery_authority": 0, "operator_only": True,
                            "authority": 0, "user_approved": False,
                            "model_called": False, "native_calls": 0,
                            "weight_updates": False,
                            "learning_mode": "RECORD_ONLY",
                            "step2_status": "UTILITY_FAIL",
                            "b3_status": "NO_PROMOTION",
                            "body_jepa_status": "UNAVAILABLE",
                            "jepa_weight": 0, "redmi_measured": False,
                            "whole_system_complete": False,
                        }.items():
                            self.assertEqual(got[k], v, k)
            finally:
                runtime.close()

    def test_foreign_query_unsupported_source_and_alias_abstain(self):
        case = cases()[0]
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                s = runtime.store.source(frozen.prompt(case), "USER")
                wrong = runtime.store.source(
                    query({**case, "project": "OtherProject"}), "USER")
                changed = runtime.store.source(
                    frozen.prompt(case) + " Send a copy to the cloud.", "USER")
                q = runtime.store.source(query(case), "USER")
                for qr, sr in ((wrong, s), (q, changed), (s, s)):
                    got = answer.propose_text(runtime.store, qr, sr)
                    self.assertIsNone(got["answer"])
                    self.assertIsNone(got["candidate"])
                    self.assertEqual(got["authority"], 0)
                    self.assertEqual(got["native_calls"], 0)
            finally:
                runtime.close()

    def test_changed_between_two_verified_reads_abstains(self):
        case = cases()[0]
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                q = runtime.store.source(query(case), "USER")
                s = runtime.store.source(frozen.prompt(case), "USER")
                first = jef.propose(runtime.store, q, s)
                self.assertIsNotNone(first["candidate"])
                altered = dict(first, candidate=dict(
                    first["candidate"], remaining_a_eur=12345))
                with patch.object(jef, "propose", side_effect=[first, altered]) as p:
                    got = answer.propose_text(runtime.store, q, s)
                self.assertEqual(p.call_count, 2)
                self.assertEqual(got["reason"], "SOURCE_CHANGED_BEFORE_SHADOW_RENDER")
                self.assertIsNone(got["answer"])
                self.assertIsNone(got["candidate"])
                self.assertEqual(got["delivery_authority"], 0)
            finally:
                runtime.close()

    def test_invalid_candidate_cannot_render_or_leak(self):
        case = cases()[0]
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                q = runtime.store.source(query(case), "USER")
                s = runtime.store.source(frozen.prompt(case), "USER")
                good = jef.propose(runtime.store, q, s)
                for modified in (
                    {"remaining_a_eur": True},
                    {"remaining_b_eur": -1},
                    {"faster_option": "Foreign"},
                    {"option_a": "Bad\nInjected"},
                    {"project": "Wrong Project"},
                    {"unexpected": "field"},
                ):
                    fake = dict(good, candidate={**good["candidate"], **modified})
                    with patch.object(jef, "propose", return_value=fake):
                        got = answer.propose_text(runtime.store, q, s)
                    self.assertEqual(got["reason"],
                                     "CANDIDATE_RENDER_INTEGRITY_RED")
                    self.assertIsNone(got["answer"])
                    self.assertIsNone(got["candidate"])
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
