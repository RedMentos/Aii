"""Run84 real operator exact-rule proposal, rejection, approval and revocation."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.operator import Operator
from v13.output_policy import match
from v13.runtime import Runtime


class TestRun84OperatorRuleApproval(unittest.TestCase):
    def _open(self, home):
        r = Runtime(home)
        r.sleep.cycle.set_policy("enabled", "off")
        return r, Operator(r)

    def _request(self, op, command):
        reply = op.run(command)
        self.assertIn("; :requests", reply)
        rid = reply.split(";", 1)[0]
        self.assertTrue(rid)
        return rid

    def test_explicit_rule_approval_rejection_and_restart(self):
        with tempfile.TemporaryDirectory(prefix="v13-run84-rules-") as td:
            home = Path(td)
            query = "What is two plus two?"
            r, op = self._open(home)
            try:
                self.assertEqual(json.loads(op.run(":status"))["learning"], "RECORD_ONLY")
                before = json.loads(op.run(":rules"))
                version = r.store.generation()["rule_version"]
                with patch.object(r.pool, "get", side_effect=AssertionError("NATIVE_MODEL_CALLED")):
                    rejected = self._request(op, ":rules add Never invent dates")
                    self.assertEqual(r.store.one("SELECT status FROM requests WHERE id=?", (rejected,))["status"], "PENDING")
                    self.assertEqual(json.loads(op.run(":rules")), before)
                    self.assertEqual(r.store.generation()["rule_version"], version)
                    self.assertEqual(op.run(":reject " + rejected), "Abgelehnt")
                    self.assertEqual(r.store.one("SELECT status FROM requests WHERE id=?", (rejected,))["status"], "REJECTED")
                    self.assertEqual(json.loads(op.run(":rules")), before)
                    fixed = self._request(op, ':rules fixed "What is two plus two?" "4"')
                    self.assertIsNone(match(r.store, query))
                    with self.assertRaises(ValueError):
                        op.run(":approve not-a-real-request")
                    self.assertEqual(r.store.generation()["rule_version"], version)
                    op.run(":approve " + fixed)
                    self.assertNotEqual(r.store.generation()["rule_version"], version)
                    answer = match(r.store, query)
                    self.assertEqual(answer["answer"], "4")
                    self.assertFalse(answer["model_generated"])
                    self.assertEqual(answer["output_authority"], "APPROVED_FIXED_RULE")
                    self.assertIsNone(match(r.store, "What is two plus two"))
                    self.assertEqual(len(json.loads(op.run(":rules"))), len(before) + 1)
            finally:
                r.close()

            r, op = self._open(home)
            try:
                self.assertEqual(json.loads(op.run(":status"))["learning"], "RECORD_ONLY")
                self.assertEqual(match(r.store, query)["answer"], "4")
                rules = json.loads(op.run(":rules"))
                self.assertNotIn("Never invent dates", rules)
                fixed_index = next(i for i, x in enumerate(rules)
                                   if isinstance(x, dict) and x.get("kind") == "FIXED_EXACT")
                with patch.object(r.pool, "get", side_effect=AssertionError("NATIVE_MODEL_CALLED")):
                    removal = self._request(op, ":rules remove " + str(fixed_index))
                    self.assertEqual(match(r.store, query)["answer"], "4")
                    op.run(":approve " + removal)
                    self.assertIsNone(match(r.store, query))
                    self.assertEqual(json.loads(op.run(":rules")), before)
            finally:
                r.close()

            r, op = self._open(home)
            try:
                self.assertEqual(json.loads(op.run(":status"))["learning"], "RECORD_ONLY")
                self.assertIsNone(match(r.store, query))
                self.assertEqual(json.loads(op.run(":rules")), before)
            finally:
                r.close()


if __name__ == "__main__":
    unittest.main()
