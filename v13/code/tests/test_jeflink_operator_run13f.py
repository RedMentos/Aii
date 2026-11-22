"""Run13F actual local Operator.run :jeflink, Age0 SHADOW only."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tests.test_context_source_link_budget_run13e import prepare
from v13.operator import Operator
from v13.runtime import Runtime


class Run13FJeflinkOperator(unittest.TestCase):
    def test_tty_command_produces_exact_source_answer_without_chat_or_native(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                runtime.sleep.cycle.set_policy("enabled", "off")
                source, query, plan, _ = prepare(runtime)
                op = Operator(runtime)
                cmd = f":jeflink {plan['packet_id']} {query} {source}"
                self.assertIn(":jeflink", op.run(":help"))
                before = runtime.store.one(
                    "SELECT count(*) AS n FROM sources")["n"]
                messages = runtime.store.one(
                    "SELECT count(*) AS n FROM messages WHERE role='assistant'")["n"]
                with patch.object(runtime.pool, "get",
                                  side_effect=AssertionError("NATIVE_MODEL_CALLED")):
                    result = json.loads(op.run(cmd))
                self.assertEqual(before, runtime.store.one(
                    "SELECT count(*) AS n FROM sources")["n"])
                self.assertEqual(messages, runtime.store.one(
                    "SELECT count(*) AS n FROM messages WHERE role='assistant'")["n"])
                self.assertIn("Cedar leaves 169 Euro remaining.", result["answer"])
                self.assertIn("Quartz leaves 58 Euro remaining.", result["answer"])
                self.assertIn("Quartz finishes sooner.", result["answer"])
                for key, value in {
                    "status": "SHADOW_NO_AUTHORITY",
                    "operator_diagnostic": True, "not_chat_turn": True,
                    "no_autonomous_egress": True, "age0_record_only": True,
                    "native_calls": 0, "model_called": False,
                    "weight_updates": False, "jepa_weight": 0,
                    "delivery_authority": 0, "whole_system_complete": False,
                }.items():
                    self.assertEqual(result[key], value, key)
            finally:
                runtime.close()

    def test_wrong_packet_and_malformed_args_do_not_dispatch(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                source, query, plan, _ = prepare(runtime)
                op = Operator(runtime)
                with self.assertRaises(ValueError):
                    op.run(":jeflink")
                with self.assertRaises(ValueError):
                    op.run(":jeflink invalid " + query + " " + source)
                with patch.object(runtime.pool, "get",
                                  side_effect=AssertionError("NATIVE_MODEL_CALLED")):
                    got = json.loads(op.run(
                        ":jeflink pkt_" + "0" * 32 + " " + query + " " + source))
                self.assertIsNone(got["answer"])
                self.assertEqual(got["delivery_authority"], 0)
            finally:
                runtime.close()

    def test_only_local_tty_idle_age0_current_session(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                source, query, plan, _ = prepare(runtime)
                op = Operator(runtime)
                cmd = f":jeflink {plan['packet_id']} {query} {source}"
                with self.assertRaises(ValueError):
                    op.run(cmd, origin="REMOTE")
                with patch.object(runtime, "require_idle",
                                  side_effect=RuntimeError("BUSY")):
                    with self.assertRaisesRegex(RuntimeError, "BUSY"):
                        op.run(cmd)
                old = runtime.cfg["learning_mode"]
                runtime.cfg["learning_mode"] = "SHADOW"
                try:
                    with self.assertRaisesRegex(ValueError, "AGE0"):
                        op.run(cmd)
                finally:
                    runtime.cfg["learning_mode"] = old
                other = runtime.store.new_session("foreign")
                alien = runtime.store.event(other, "Unrelated query")["event_id"]
                with self.assertRaisesRegex(ValueError, "CURRENT_SESSION"):
                    op.run(f":jeflink {plan['packet_id']} {alien} {source}")
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
