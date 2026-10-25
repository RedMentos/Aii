"""Run387 RED-first: AG7 'held out' must never be training evidence."""
import copy
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi import hub


WORDS = ("abcd", "wxyz", "qwer", "lmno", "pqrs", "tuvw")


def episodes():
    return [
        {"id": f"e{i}", "input": word, "output": word[::-1], "tags": "reverse_cipher"}
        for i, word in enumerate(WORDS)
    ]


class DisjointHoldoutRun387(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.tmp.name))
        self.runtime.sleep.cycle.set_policy("enabled", "off")
        self.a = hub(self.runtime).abstraction

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def rules(self):
        return copy.deepcopy(self.a.box.load()[0]["rules"])

    def test_duplicate_episode_ids_across_split_cannot_validate(self):
        eps = episodes()
        eps[4]["id"] = eps[0]["id"]
        eps[5]["id"] = eps[1]["id"]
        before = self.rules()
        self.assertEqual(self.a.induce(eps, domain="cipher"), [])
        self.assertEqual(self.rules(), before)

    def test_duplicate_inputs_across_split_cannot_validate(self):
        eps = episodes()
        for j, k in ((4, 0), (5, 1)):
            eps[j]["input"] = eps[k]["input"]
            eps[j]["output"] = eps[k]["output"]
        before = self.rules()
        self.assertEqual(self.a.induce(eps, domain="cipher"), [])
        self.assertEqual(self.rules(), before)

    def test_independent_examples_still_validate_without_fact_authority(self):
        out = self.a.induce(episodes(), domain="cipher")
        self.assertEqual(len(out), 1)
        rule = out[0]
        self.assertEqual(rule["program"], "reverse")
        self.assertEqual(rule["status"], "VALIDATED")
        self.assertEqual(rule["fact_write_authority"], 0)
        self.assertFalse(set(rule["support"]) & set(rule["tests"]))
        self.assertEqual(len(rule["support"]) + len(rule["tests"]), 6)

    def test_reused_holdout_roles_create_separate_rule_not_leaking_union(self):
        first = self.a.induce(episodes(), domain="cipher")[0]
        self.a.promote(first["id"])
        before = self.rules()[first["id"]]
        second = self.a.induce(list(reversed(episodes())), domain="cipher")[0]
        self.assertNotEqual(first["id"], second["id"])
        rules = self.rules()
        self.assertEqual(len(rules), 2)
        self.assertEqual(rules[first["id"]], before)
        self.assertEqual(rules[first["id"]]["status"], "APPROVED")
        self.assertEqual(rules[second["id"]]["status"], "VALIDATED")
        for rule in rules.values():
            self.assertFalse(set(rule["support"]) & set(rule["tests"]))
        self.assertFalse(set(rules[first["id"]]["support"]) & set(rules[second["id"]]["support"]) == set())


if __name__ == "__main__":
    unittest.main()
