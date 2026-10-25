"""Run388 RED-first: AG2 prediction must precede an actual tool effect."""
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from v13.runtime import Runtime
from v13.agi import hub
from v13.agi.tools import ToolRegistry, ToolSpec
from v13.agi.grounding_preaction import PreActionGrounding
from v13.transaction import Transactions


class PreActionToolRun388(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.tmp.name))
        self.runtime.sleep.cycle.set_policy("enabled", "off")
        self.g = hub(self.runtime).grounding
        self.adapter = PreActionGrounding(self.g)

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def registry(self, fn):
        t = ToolRegistry(
            self.runtime.store,
            on_pre_execute=self.adapter.before,
            on_outcome=self.adapter.after,
            on_abort=self.adapter.abort,
        )
        t.register(ToolSpec("measure", fn, schema={"value": "int"}))
        t.enable("measure")
        return t

    def test_preaction_exists_during_real_effect_then_closes_once(self):
        observed = []

        def effect(value):
            st = self.g.box.load()[0]
            observed.append((len(st["open"]), len(st["closed"])))
            time.sleep(0.002)
            return value + 1

        tx = self.registry(effect).call("measure", {"value": 3})
        self.assertEqual(tx["status"], "EXECUTED")
        self.assertEqual(tx["result"], 4)
        self.assertEqual(observed, [(1, 0)])
        self.assertEqual(self.g.report()["open"], 0)
        self.assertEqual(self.g.report()["closed"], 1)
        rec = self.g.samples()[-1]
        self.assertEqual(rec["actual"], "EXECUTED:4")
        self.assertGreaterEqual(rec["latency_s"], 0)
        self.assertIsNotNone(tx.get("preaction_id"))

    def test_failed_effect_is_grounded_once(self):
        def fail(value):
            self.assertEqual(self.g.report()["open"], 1)
            raise RuntimeError("failure fixture")

        tx = self.registry(fail).call("measure", {"value": 2})
        self.assertEqual(tx["status"], "FAILED")
        self.assertEqual(self.g.report()["open"], 0)
        self.assertEqual(self.g.report()["closed"], 1)
        self.assertEqual(self.g.samples()[-1]["actual"], "FAILED:null")

    def test_postcopy_hard_block_discards_not_learns(self):
        t = self.registry(lambda value: value)
        with mock.patch.object(Transactions, "execute", new=lambda _self, tid, _fn: {"id": tid, "state": "CANCELLED", "error": "HARD_BLOCK:fixture"}):
            tx = t.call("measure", {"value": 3})
        self.assertEqual(tx["status"], "DENIED")
        self.assertEqual(self.g.report()["open"], 0)
        self.assertEqual(self.g.report()["closed"], 0)
        self.assertEqual(self.g.box.load()[0]["table"], {})

    def test_idempotency_does_not_duplicate_preaction(self):
        t = self.registry(lambda value: value + 1)
        first = t.call("measure", {"value": 1}, idempotency_key="run388-once")
        second = t.call("measure", {"value": 1}, idempotency_key="run388-once")
        self.assertEqual(first["status"], "EXECUTED")
        self.assertEqual(second["status"], "DEDUPLICATED")
        self.assertEqual(self.g.report()["open"], 0)
        self.assertEqual(self.g.report()["closed"], 1)

    def test_forecast_payload_is_not_misread_as_baseline_outcome(self):
        t = self.registry(lambda value: value)
        tx = t.call("measure", {"value": 1}, predicted={"forecast_kind": "shadow", "confidence": 0.9})
        self.assertEqual(tx["status"], "EXECUTED")
        self.assertIsNone(self.g.samples()[-1]["predicted"])

    def test_nonhard_cancel_discards_without_false_failure_evidence(self):
        t = self.registry(lambda value: value)
        with mock.patch.object(Transactions, "execute", new=lambda _self, tid, _fn: {"id": tid, "state": "CANCELLED", "error": "CANCELLED_BY_USER"}):
            tx = t.call("measure", {"value": 3})
        self.assertEqual(tx["status"], "CANCELLED")
        self.assertEqual(self.g.report()["open"], 0)
        self.assertEqual(self.g.report()["closed"], 0)
        self.assertEqual(self.g.box.load()[0]["table"], {})

    def test_predictor_failure_does_not_block_tool_or_fabricate_grounding(self):
        def broken(_tx):
            raise RuntimeError("predictor unavailable")
        t = ToolRegistry(
            self.runtime.store,
            on_pre_execute=broken,
            on_outcome=self.adapter.after,
            on_abort=self.adapter.abort,
        )
        t.register(ToolSpec("measure", lambda value: value + 1, schema={"value": "int"}))
        t.enable("measure")
        tx = t.call("measure", {"value": 4})
        self.assertEqual((tx["status"], tx["result"]), ("EXECUTED", 5))
        self.assertEqual(tx["preaction_error"], "RuntimeError")
        self.assertEqual(self.g.report()["open"], 0)
        self.assertEqual(self.g.report()["closed"], 0)

    def test_legacy_registry_without_hooks_remains_postaction(self):
        during = []

        def effect(value):
            during.append(self.g.report()["open"])
            return value + 1

        t = ToolRegistry(self.runtime.store, on_outcome=self.g.from_tool)
        t.register(ToolSpec("measure", effect, schema={"value": "int"}))
        t.enable("measure")
        tx = t.call("measure", {"value": 1})
        self.assertEqual(tx["status"], "EXECUTED")
        self.assertEqual(during, [0])
        self.assertEqual(self.g.report()["closed"], 1)


if __name__ == "__main__":
    unittest.main()
