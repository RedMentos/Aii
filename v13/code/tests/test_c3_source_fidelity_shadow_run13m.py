"""Run13M source-bound C3 grammar SHADOW tests; no model calls."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import run13l_c3_system_native as l
from scripts import run13j_c3_jef_native as j
from v13.agi.c3_source_fidelity_shadow_run13m import audit_source_facts
from v13.runtime import Runtime

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/run13l_c3_system_seed251_20261030.json")

# Literal six already-observed synthetic native SYSTEM_COPY outputs, posthoc only.
OBSERVED = [
    "BEGIN_VERIFIED\nProject Atlas251.\nJuniper leaves 531 euros remaining.\nSilver finishes sooner.",
    "Cobalt leaves 465 Euro remaining.\nHazel leaves 303 Euro\n\nEND_VERIFIED",
    "BEGIN_VERIFIED\nProject Canyon251\nBasil leaves 529 Euro remaining\nLark leaves 312 Euro remaining\nLark finishes sooner\n",
    "BEGIN_VERIFIED\nProject Delta251\nMarble leaves 427 Euro remaining\nTopaz leaves 266 Euro remaining\nMarble finishes sooner\n",
    "BEGIN_VERIFIED\nProject Ember251. Olive leaves 325 Euro remaining. Copper leaves 386 Euro remaining. Copper finishes sooner.\nEND_VERIFIED",
    "BEGIN_VERIFIED\nProject Forest251. Plum leaves 348 Euro remaining. Frost leaves 435 Euro remaining. Frost finishes sooner.\nEND_VERIFIED",
]


class Run13MShadow(unittest.TestCase):
    def test_source_verified_link_no_native_and_exact_facts(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                runtime.sleep.cycle.set_policy("enabled", "off")
                case = l.load_fixture(FIXTURE)[0]
                before = runtime.store.one(
                    "SELECT count(*) AS n FROM messages WHERE role='assistant'")["n"]
                with patch.object(runtime.pool, "get",
                                  side_effect=AssertionError("NATIVE_CALLED")):
                    linked = j.prepare_case(runtime, case)["linked"]
                    good = audit_source_facts(linked, linked["answer"])
                    bad = audit_source_facts(linked, "ABSTAIN.")
                self.assertEqual(good["result"], "FACTS_EXACT")
                self.assertEqual(bad["result"], "ABSTAIN")
                for result in (good, bad):
                    self.assertEqual(result["delivery_authority"], 0)
                    self.assertEqual(result["context_authority"], 0)
                    self.assertEqual(result["native_calls"], 0)
                    self.assertEqual(result["step2_status"], "UTILITY_FAIL")
                    self.assertEqual(result["jepa_weight"], 0)
                    self.assertFalse(result["whole_system_complete"])
                self.assertEqual(before, runtime.store.one(
                    "SELECT count(*) AS n FROM messages WHERE role='assistant'")["n"])
            finally:
                runtime.close()

    def test_original_six_posthoc_outputs_reject_wrong_and_accept_four(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                runtime.sleep.cycle.set_policy("enabled", "off")
                for i, case in enumerate(l.load_fixture(FIXTURE)):
                    linked = j.prepare_case(runtime, case)["linked"]
                    result = audit_source_facts(linked, OBSERVED[i])
                    self.assertEqual(result["result"],
                                     "FACTS_EXACT" if i >= 2 else "ABSTAIN")
                    self.assertEqual(audit_source_facts(linked, "ABSTAIN.")["result"],
                                     "ABSTAIN")
            finally:
                runtime.close()

    def test_swapped_missing_extra_duplicate_wrong_faster_fail_closed(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                linked = j.prepare_case(runtime, l.load_fixture(FIXTURE)[0])["linked"]
                answer = linked["answer"]
                cases = [
                    answer.replace("Juniper leaves 531", "Juniper leaves 345"),
                    answer.replace("Silver leaves 345", "Silver leaves 531"),
                    answer.replace("Silver leaves 345 Euro remaining.\n", ""),
                    answer.replace("Silver finishes sooner.", "Juniper finishes sooner."),
                    answer.replace("Project Atlas251.", "Project Beacon251."),
                    answer + "\nUnknown fact.",
                    answer + "\n1234",
                    answer.replace("Silver finishes sooner.",
                                   "Silver finishes sooner. Silver finishes sooner."),
                    "BEGIN_VERIFIED\n" + answer + "\nEND_VERIFIED\nextra",
                    "ABSTAIN\n" + answer,
                ]
                for candidate in cases:
                    with self.subTest(candidate=candidate[:50]):
                        self.assertEqual(audit_source_facts(linked, candidate)["result"],
                                         "ABSTAIN")
            finally:
                runtime.close()

    def test_source_integrity_and_bounds_fail_closed(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                linked = j.prepare_case(runtime, l.load_fixture(FIXTURE)[1])["linked"]
                answer = linked["answer"]
                for change in ({"answer_sha256": "0"*64},
                               {"delivery_authority": 1},
                               {"candidate_prompt": "forged"},
                               {"context_authority": 1}):
                    with self.subTest(change=change):
                        self.assertEqual(audit_source_facts(
                            dict(linked, **change), answer)["result"], "ABSTAIN")
                self.assertEqual(audit_source_facts(linked, answer + "X"*1000)["reason"],
                                 "OUTPUT_BUDGET_RED")
                self.assertEqual(audit_source_facts(linked, None)["result"], "ABSTAIN")
                self.assertEqual(audit_source_facts(None, answer)["result"], "ABSTAIN")
                self.assertEqual(audit_source_facts(linked, answer + " ​")["result"],
                                 "ABSTAIN")
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
