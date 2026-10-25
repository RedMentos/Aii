"""Run391 RED-first: opt-in AG2 preaction evidence must reconcile after restart.

All effects are local fixture functions. No default Growth wiring or live learning.
"""
import tempfile
import time
import unittest
from pathlib import Path

from v13.common import dumps
from v13.runtime import Runtime
from v13.agi import hub
from v13.agi.tools import ToolRegistry, ToolSpec
from v13.agi.grounding_preaction import PreActionGrounding
from v13.transaction import Transactions


class PreActionRecoveryRun391(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.g = hub(self.r).grounding
        self.adapter = PreActionGrounding(self.g)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def registry(self, fn, after=None):
        t = ToolRegistry(
            self.r.store,
            on_pre_execute=self.adapter.before,
            on_outcome=self.adapter.after if after is None else after,
            on_abort=self.adapter.abort,
        )
        t.register(ToolSpec("measure", fn, schema={"value": "int"}))
        t.enable("measure")
        return t

    def manual(self, value=2, event_id=None, kind="tool:measure", ctx=None, action=None):
        t = Transactions(self.r.store)
        args = {"value": value}
        tx = t.prepare(event_id, "measure", args, "USER", "READ_LOCAL", True)
        t.commit_copy(tx["id"])
        aid, _ = self.g.expect(
            kind, dumps(args)[:120] if ctx is None else ctx,
            {"tool": "measure", "action_tx": tx["id"], "event_id": tx["event_id"], "origin": tx["origin"]} if action is None else action,
            modality="tool",
        )
        return t, tx["id"], aid

    def test_durable_transaction_id_is_present_before_effect(self):
        observed = []

        def effect(value):
            open_items = list(self.g.box.load()[0]["open"].values())
            self.assertEqual(len(open_items), 1)
            action_id = open_items[0]["action"]["action_tx"]
            durable = Transactions(self.r.store).get(action_id)
            observed.append((durable["tool"], durable["args"], durable["state"]))
            return value + 1

        tx = self.registry(effect).call("measure", {"value": 3})
        self.assertEqual(tx["status"], "EXECUTED")
        self.assertEqual(observed, [("measure", {"value": 3}, "EXECUTING")])

    def test_lost_success_callback_is_recovered_exactly_once(self):
        tx = self.registry(lambda value: value + 1, after=lambda _tx: None).call("measure", {"value": 3})
        self.assertEqual(tx["status"], "EXECUTED")
        self.assertEqual(self.g.report()["open"], 1)
        fresh = PreActionGrounding(hub(self.r).grounding)
        first = fresh.reconcile()
        second = fresh.reconcile()
        self.assertEqual(first["recovered"], 1)
        self.assertEqual(second["recovered"], 0)
        self.assertEqual(self.g.report()["open"], 0)
        self.assertEqual(self.g.report()["closed"], 1)
        self.assertEqual(self.g.samples()[-1]["actual"], "EXECUTED:4")
        self.assertEqual(sum(sum(h.values()) for h in self.g.box.load()[0]["table"].values()), 1)

    def test_lost_failed_callback_is_recovered_without_invented_result(self):
        def effect(value):
            raise RuntimeError("fixture")
        tx = self.registry(effect, after=lambda _tx: None).call("measure", {"value": 2})
        self.assertEqual(tx["status"], "FAILED")
        self.assertEqual(self.g.report()["open"], 1)
        out = self.adapter.reconcile()
        self.assertEqual(out["recovered"], 1)
        self.assertEqual(self.g.samples()[-1]["actual"], "FAILED:null")

    def test_crashed_executing_is_unknown_and_never_grounded(self):
        t, tid, aid = self.manual()
        t._write(lambda st: t._move(st, tid, "EXECUTING"))
        self.assertEqual(t.recover()["UNKNOWN"], 1)
        out = self.adapter.reconcile()
        self.assertEqual(out["discarded"], 1)
        self.assertEqual(self.g.report()["open"], 0)
        self.assertEqual(self.g.report()["closed"], 0)
        self.assertEqual(self.g.box.load()[0]["table"], {})

    def test_cancelled_is_discarded_without_training(self):
        t, tid, aid = self.manual()
        t.cancel(tid)
        out = self.adapter.reconcile()
        self.assertEqual(out["discarded"], 1)
        self.assertEqual(self.g.report()["open"], 0)
        self.assertEqual(self.g.report()["closed"], 0)

    def test_inflight_action_is_deferred_not_inferred(self):
        t, tid, aid = self.manual()
        first = self.adapter.reconcile()
        self.assertEqual(first["deferred"], 1)
        self.assertEqual(self.g.report()["open"], 1)
        self.assertEqual(self.g.report()["closed"], 0)
        t.execute(tid, lambda value: value + 1)
        second = self.adapter.reconcile()
        self.assertEqual(second["recovered"], 1)
        self.assertEqual(self.g.samples()[-1]["actual"], "EXECUTED:3")

    def test_mismatched_durable_source_is_discarded_not_trusted(self):
        for kind, ctx in (("tool:other", None), ("tool:measure", "wrong-args")):
            with self.subTest(kind=kind, ctx=ctx):
                t, tid, aid = self.manual(kind=kind, ctx=ctx)
                t.execute(tid, lambda value: value)
                out = self.adapter.reconcile()
                self.assertEqual(out["discarded"], 1)
                self.assertEqual(self.g.report()["open"], 0)
                self.assertEqual(self.g.report()["closed"], 0)
        self.assertEqual(self.g.box.load()[0]["table"], {})

    def test_unfinalized_turn_does_not_create_grounding(self):
        t, tid, aid = self.manual(event_id="unfinalized-turn")
        t.execute(tid, lambda value: value + 1)
        out = self.adapter.reconcile()
        self.assertEqual(out["recovered"], 0)
        self.assertEqual(out["deferred"], 1)
        self.assertEqual(self.g.report()["closed"], 0)
        self.g.clock = lambda: time.time() + 7200
        late = self.adapter.reconcile(stale_after_s=3600)
        self.assertEqual(late["discarded"], 1)
        self.assertEqual(self.g.report()["closed"], 0)

    def test_orphan_without_action_id_is_bounded_and_discarded_stale(self):
        aid, _ = self.g.expect("tool:measure", "{}", {"tool": "measure"}, modality="tool")
        self.assertEqual(self.adapter.reconcile()["deferred"], 1)
        self.g.clock = lambda: time.time() + 7200
        self.assertEqual(self.adapter.reconcile(stale_after_s=3600)["discarded"], 1)
        self.assertEqual(self.g.report()["closed"], 0)

    def test_real_final_turn_settles_only_after_final(self):
        sid = self.r.store.new_session("run391-final")
        event_id = self.r.store.event(sid, "Check result")["event_id"]
        t, tid, aid = self.manual(event_id=event_id)
        t.execute(tid, lambda value: value + 1)
        self.assertEqual(self.adapter.reconcile()["deferred"], 1)
        self.assertEqual(self.g.report()["closed"], 0)
        self.r.store.message(sid, event_id, "assistant", "Finished", "FINAL")
        self.assertEqual(self.adapter.reconcile()["recovered"], 1)
        self.assertEqual(self.g.samples()[-1]["actual"], "EXECUTED:3")

    def test_cancelled_turn_discards_completed_effect_without_learning(self):
        sid = self.r.store.new_session("run391-cancel")
        event_id = self.r.store.event(sid, "Check cancelled")["event_id"]
        t, tid, aid = self.manual(event_id=event_id)
        t.execute(tid, lambda value: value + 1)
        self.r.store.message(sid, event_id, "assistant", "", "CANCELLED")
        self.assertEqual(self.adapter.reconcile()["discarded"], 1)
        self.assertEqual(self.g.report()["closed"], 0)
        self.assertEqual(self.g.box.load()[0]["table"], {})

    def test_mismatched_event_and_origin_cannot_launder_durable_outcome(self):
        for field, forged in (("event_id", "another-turn"), ("origin", "SYSTEM")):
            with self.subTest(field=field):
                t, tid, aid = self.manual()
                t.execute(tid, lambda value: value)
                self.g.box.mutate(lambda st: st["open"][aid]["action"].__setitem__(field, forged))
                self.assertEqual(self.adapter.reconcile()["discarded"], 1)
                self.assertEqual(self.g.report()["closed"], 0)
        self.assertEqual(self.g.box.load()[0]["table"], {})

    def test_default_registry_still_uses_postaction_only(self):
        t = ToolRegistry(self.r.store, on_outcome=self.g.from_tool)
        t.register(ToolSpec("measure", lambda value: value + 1, schema={"value": "int"}))
        t.enable("measure")
        tx = t.call("measure", {"value": 2})
        self.assertEqual(tx["status"], "EXECUTED")
        self.assertEqual(self.g.report()["open"], 0)
        self.assertEqual(self.g.report()["closed"], 1)


if __name__ == "__main__":
    unittest.main()
