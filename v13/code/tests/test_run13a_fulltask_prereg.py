"""Run13A prospective source-only frozen seed211 and JEF baseline checks."""
from pathlib import Path
import hashlib
import json
import re
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import c2_body_disjoint_paired181_run11v as frozen
from scripts import c2_body_observer_off_run12n as run12n
from scripts import c2_body_run12n_fulltask_readonly as faster
from v13.agi import budget_en_source_shadow as jef
from v13.cognition import scaffold_route
from v13.runtime import Runtime

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/c2_body_fulltask_run13a_seed211_20261030.json")
HASH = "e6718093ccd83d556019223eca2d5317668d1ada25659519a699aee681a8b97f"
ARMS = ("A_C3_ONLY", "B_B1_ONLY", "C_B2_ONLY", "F_NATIVE_AUTO")


def load():
    data = json.loads(FIXTURE.read_text())
    cases = data["cases"]
    assert data["schema"] == "v13.c2_c3_body.fulltask.run13a.fixture.v1"
    assert data["seed"] == 211 and len(cases) == 8
    got = hashlib.sha256(json.dumps(
        tuple(cases), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert got == HASH
    return cases


class Run13AFrozenPreflight(unittest.TestCase):
    def test_frozen_eight_disjoint_no_leak_simple_sources(self):
        cases = load()
        previous = {frozen.prompt(c) for c in frozen.FIXTURES}
        previous |= {frozen.prompt(c) for c in run12n.load_fixture(
            Path(__file__).resolve().parents[1] /
            "docs/fixtures/c2_body_observer_off_run12n_20261030.json")["cases"]}
        previous |= {frozen.prompt(c) for c in json.loads((
            Path(__file__).resolve().parents[1] /
            "docs/fixtures/c2_body_paired_run12m_20261030.json").read_text())["cases"]}
        names = set()
        for c in cases:
            self.assertEqual(set(c), {
                "project", "budget", "a", "a_cost", "a_days",
                "b", "b_cost", "b_days"})
            self.assertNotIn(c["project"], names)
            names.add(c["project"])
            self.assertNotEqual(c["a"], c["b"])
            self.assertNotEqual(c["a_days"], c["b_days"])
            self.assertTrue(0 < c["a_cost"] < c["budget"])
            self.assertTrue(0 < c["b_cost"] < c["budget"])
            prompt = frozen.prompt(c)
            self.assertNotIn(prompt, previous)
            self.assertEqual(scaffold_route(prompt), "simple")
            for key in ("a", "b"):
                remain = c["budget"] - c[key + "_cost"]
                self.assertIsNone(re.search(
                    rf"(?<!\d){remain}(?!\d)", prompt))
        self.assertEqual(len(names), 8)

    def test_frozen_eight_latin_square_cycles(self):
        orders = tuple(ARMS[i % 4:] + ARMS[:i % 4] for i in range(8))
        self.assertEqual(len(orders), 8)
        self.assertTrue(all(set(o) == set(ARMS) for o in orders))
        for position in range(4):
            self.assertEqual(
                sorted(o[position] for o in orders),
                sorted(list(ARMS) * 2))

    def test_existing_jef_store_source_shadow_eight_of_eight(self):
        cases = load()
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                runtime.sleep.cycle.set_policy("enabled", "off")
                with patch.object(runtime.pool, "get",
                                  side_effect=AssertionError("NATIVE_MODEL_CALLED")):
                    for c in cases:
                        q = runtime.store.source(
                            f"Calculate both remaining budgets and faster option for Project {c['project']}.", "USER")
                        s = runtime.store.source(frozen.prompt(c), "USER")
                        got = jef.propose(runtime.store, q, s)
                        self.assertEqual(got["reason"],
                                         "EXACT_SOURCE_ARITHMETIC_SHADOW")
                        self.assertEqual(got["candidate"]["remaining_a_eur"],
                                         c["budget"] - c["a_cost"])
                        self.assertEqual(got["candidate"]["remaining_b_eur"],
                                         c["budget"] - c["b_cost"])
                        self.assertEqual(got["candidate"]["faster_option"],
                                         c["a"] if c["a_days"] < c["b_days"] else c["b"])
                        self.assertEqual(got["authority"], 0)
                        self.assertEqual(got["native_calls"], 0)
                        self.assertEqual(got["jepa_weight"], 0)
                        self.assertEqual(got["step2_status"], "UTILITY_FAIL")
            finally:
                runtime.close()

    def test_faster_scorer_counterexamples(self):
        self.assertEqual(faster.explicit_faster_claim(
            "Quartz finishes sooner.", "Cedar", "Quartz"), "Quartz")
        self.assertEqual(faster.explicit_faster_claim(
            "Cedar finishes sooner. Quartz finishes first.", "Cedar", "Quartz"),
            "CONTRADICTORY")
        self.assertEqual(faster.explicit_faster_claim(
            "Neither is possible.", "Cedar", "Quartz"), "ABSTAIN")


if __name__ == "__main__":
    unittest.main()
