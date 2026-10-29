"""Context OS exact SourceRef restoration × Sleep S7 paged digest cross-organ regression.

Synthetic Store-only evidence. No model calls, no learning, no gate promotion.
"""
import json
import tempfile
import unittest
from pathlib import Path

from v13 import sleep_offline as S
from v13.operator import Operator
from v13.runtime import Runtime


class ContextSleepSourceIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.tmp.name))
        self.runtime.sleep.cycle.set_policy("enabled", "off")

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def turn(self, n, session=None, final=True):
        session = session or self.runtime.session
        original = "Source %03d: Äpfel, 42.75 EUR, `x=%d` 😀." % (n, n)
        event = self.runtime.store.event(session, original)
        if final:
            self.runtime.store.message(
                session, event["event_id"], "assistant",
                "Exact source acknowledged %03d." % n,
                status="FINAL", metadata={"direct_source_copy": True},
            )
        return event, original

    def test_130_turn_catchup_keeps_old_exact_source_retrievable(self):
        events = [self.turn(i) for i in range(130)]
        store = self.runtime.store
        session = self.runtime.session
        self.assertEqual(S.digest(store)["turns"], 64)
        before, version = store.state(S.KEY)
        self.assertEqual(before["sessions"][session]["entries"][0]["event_id"],
                         events[0][0]["event_id"])
        reply = json.loads(Operator(self.runtime).run(
            ":ctxos source " + events[0][0]["event_id"]))
        self.assertEqual(reply["text"], events[0][1])
        self.assertEqual(reply["authority"], "SOURCE_EXACT_READ_ONLY")
        self.assertFalse(reply["context_applied"])
        self.assertEqual(store.state(S.KEY)[1], version)
        self.assertEqual(S.digest(store)["turns"], 64)
        self.assertEqual(S.digest(store)["turns"], 2)
        self.assertEqual(S.digest(store)["turns"], 0)
        self.assertEqual(S.view(store, session, cap=100000)["entries"], 96)
        # Even an entry outside the retained digest is still exact in SourceRef.
        self.assertEqual(json.loads(Operator(self.runtime).run(
            ":ctxos source " + events[0][0]["event_id"]))["text"], events[0][1])
        self.assertEqual(self.runtime.context_os.report()["mode"], "SHADOW")

    def test_revocation_filters_digest_and_blocks_explicit_restore(self):
        events = [self.turn(i) for i in range(70)]
        store = self.runtime.store
        self.assertEqual(S.digest(store)["turns"], 64)
        self.assertEqual(S.digest(store)["turns"], 6)
        self.assertEqual(S.view(store, self.runtime.session, cap=100000)["entries"], 70)
        target = events[50][0]
        with store.tx() as cur:
            cur.execute("UPDATE sources SET deleted=1 WHERE id=?",
                        (target["source_ref"]["source_id"],))
        self.assertEqual(S.view(store, self.runtime.session, cap=100000)["entries"], 69)
        with self.assertRaisesRegex(ValueError, "CTXOS_SOURCE"):
            self.runtime.context_os.source(target["event_id"], self.runtime.session)
        self.assertEqual(json.loads(Operator(self.runtime).run(
            ":ctxos source " + events[51][0]["event_id"]))["text"], events[51][1])

    def test_incomplete_turn_does_not_advance_digest_or_expose_foreign_source(self):
        for i in range(64):
            self.turn(i)
        pending, text = self.turn(64, final=False)
        self.assertEqual(S.digest(self.runtime.store)["turns"], 64)
        self.assertEqual(S.digest(self.runtime.store)["turns"], 0)
        self.assertEqual(self.runtime.context_os.source(
            pending["event_id"], self.runtime.session)["text"], text)
        other = self.runtime.store.new_session("other")
        foreign, _ = self.turn(999, session=other)
        with self.assertRaisesRegex(ValueError, "CTXOS_SOURCE"):
            self.runtime.context_os.source(foreign["event_id"], self.runtime.session)
        self.runtime.store.message(
            self.runtime.session, pending["event_id"], "assistant",
            "Exact source acknowledged 064.",
            status="FINAL", metadata={"direct_source_copy": True},
        )
        self.assertEqual(S.digest(self.runtime.store)["turns"], 1)


if __name__ == "__main__":
    unittest.main()
