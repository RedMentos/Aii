"""Run295 frozen source-only tests; native proof is separate and serialized."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from scripts import run295_b1_source_placement as P
from v13.common import dumps


class FrozenB1Prompt(unittest.TestCase):
    def test_run288_exact_native_prompt_hash(self):
        self.assertEqual(hashlib.sha256(dumps(P.original_messages()).encode()).hexdigest(),
                         P.FROZEN_HASH)
        self.assertEqual(P.messages_for("baseline", P.MATCH), P.original_messages())

    def test_user_source_is_explicitly_sourced_and_does_not_change_system(self):
        m = P.messages_for("user_source", P.MATCH)
        self.assertEqual([x["role"] for x in m], ["system", "user", "user"])
        self.assertEqual(m[0], P.original_messages()[0])
        self.assertEqual(m[1]["content"], P.USER_SOURCE)
        self.assertEqual(m[-1]["content"], P.MATCH)

    def test_plain_system_arm_is_separate_and_unapproved(self):
        m = P.messages_for("system_plain", P.MATCH)
        self.assertEqual(len(m), 2)
        self.assertEqual(m[1], P.original_messages()[-1])
        self.assertTrue(m[0]["content"].endswith(P.SYSTEM_PLAIN))

    def test_negative_query_changes_task_request_not_saved_correction(self):
        for q in (P.WRONG_TOPIC, P.WRONG_ENTITY):
            m = P.messages_for("baseline", q)
            self.assertIn('"exact_request":"'+q+'"', m[0]["content"])
            self.assertIn('"matched_query":"'+P.MATCH+'"', m[0]["content"])
            self.assertEqual(m[-1]["content"], q)

    def test_unknown_arms_and_queries_fail_closed(self):
        with self.assertRaises(ValueError): P.messages_for("new_unregistered", P.MATCH)
        with self.assertRaises(ValueError): P.messages_for("baseline", "unregistered")

    def test_diagnostic_signal_requires_negative_controls_and_actual_native(self):
        rows = [{"arm": arm, "question": q, "status": "FINAL",
                 "native_completed": True, "output": "400 Euro" if q == P.MATCH else "Unknown"}
                for arm in P.ARMS for q in P.QUESTIONS]
        self.assertTrue(all(v["candidate_signal_only"] for v in P.evaluate(rows).values()))
        rows[1]["output"] = "400 Euro"
        self.assertFalse(P.evaluate(rows)["baseline"]["candidate_signal_only"])
        rows[1]["output"] = "Unknown"
        rows[0]["native_completed"] = False
        self.assertFalse(P.evaluate(rows)["baseline"]["native_complete"])

    def test_existing_output_refused_before_native_launch(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "exists.json"
            path.write_text("keep")
            with self.assertRaises(SystemExit):
                P.main(["--installed-home", td, "--out", str(path)])
            self.assertEqual(path.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
