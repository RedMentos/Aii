"""Run80 real SQLite post-render source envelope race counterexamples (SHADOW)."""
import json
from pathlib import Path
import tempfile
import time
import unittest

from scripts.run52_b1b2_cross_turn_native import load_fixture, OVERRIDES
from tests.test_run52_b1b2_cross_turn import FakeRuntime
from v13.common import dumps
from v13.b1b2_c3_source_envelope_candidate import build_c3_source_envelope
from v13.b1b2_topic_partition_candidate import (
    TopicPartitionOfferConsumer, _TopicStateView)
from v13.b1b2_causal_context_candidate import _project_scope

FIXTURE = (Path(__file__).resolve().parents[1]
           / "docs/fixtures/run52_b1b2_cross_turn_seed479.json")
ROLES = ("B1_DETAIL", "B2_GIST")


class PostRenderBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = FakeRuntime(Path(self.temp.name))
        self.r.cfg.update(OVERRIDES)
        self.f = {x["id"]: x for x in load_fixture(FIXTURE)["fixtures"]}
        self.event = self.r.store.event(
            self.r.session, self.f["Harbor"]["prior"])
        consumer = TopicPartitionOfferConsumer(self.r)
        self.ids = {}
        for role in ROLES:
            result = consumer.guarded_offer(
                role, self.event, 0, time.monotonic() + 30,
                operator_opt_in=True)
            self.assertEqual(result["status"], "SHADOW_OFFER_PRODUCED")
            self.ids[role] = result["offer_packet_id"]

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def build(self):
        return build_c3_source_envelope(
            self.r, self.event, self.ids, operator_opt_in=True)

    def query_id(self, role):
        row = self.r.store.one(
            "SELECT payload FROM packets WHERE id=?", (self.ids[role],))
        return json.loads(row["payload"])["query_packet_id"]

    def mutate_after_render(self, change):
        original = self.r.cognition.analyst_context

        def injected(*args, **kwargs):
            rendered = original(*args, **kwargs)
            change()
            return rendered

        self.r.cognition.analyst_context = injected

    def counts(self):
        return tuple(self.r.store.one(
            "SELECT COUNT(*) AS n FROM " + table)["n"]
            for table in ("actions", "messages"))

    def test_unchanged_query_and_state_pass_prompt_only(self):
        before = self.counts()
        result = self.build()
        self.assertEqual(result["status"],
                         "C3_SOURCE_ENVELOPE_SHADOW_NO_MODEL_CALL")
        self.assertTrue(result["prompt_only"])
        self.assertEqual(result["delivery_authority"], 0)
        self.assertEqual(result["learning_authority"], 0)
        self.assertEqual(self.counts(), before)

    def test_query_mutated_after_successful_analyst_render_refused(self):
        qid = self.query_id("B2_GIST")

        def change():
            row = self.r.store.one(
                "SELECT payload FROM packets WHERE id=?", (qid,))
            query = json.loads(row["payload"])
            query["source_refs"] = []
            with self.r.store.tx() as db:
                db.execute("UPDATE packets SET payload=? WHERE id=?",
                           (dumps(query), qid))

        before = self.counts()
        self.mutate_after_render(change)
        result = self.build()
        self.assertEqual(result["status"], "QUERY_CHANGED_DURING_ENVELOPE")
        self.assertEqual(self.counts(), before)
        self.assertEqual(result["delivery_authority"], 0)

    def test_query_deleted_after_successful_analyst_render_refused(self):
        qid = self.query_id("B1_DETAIL")

        def change():
            with self.r.store.tx() as db:
                db.execute("DELETE FROM packets WHERE id=?", (qid,))

        self.mutate_after_render(change)
        self.assertEqual(self.build()["status"],
                         "QUERY_CHANGED_DURING_ENVELOPE")

    def test_retained_state_same_payload_new_version_refused(self):
        scope = _project_scope(self.f["Harbor"]["prior"])
        self.assertEqual(len(scope), 1)
        topic = next(iter(scope))
        view = _TopicStateView(
            self.r.store, "B2_GIST", self.r.session,
            self.event["brain_generation_id"],
            self.r.models.revision("B2_GIST"), topic)
        key = view.partition_key

        def change():
            payload, version = self.r.store.state(key, {})
            self.r.store.set_state(key, payload, expected=version)

        before = self.counts()
        self.mutate_after_render(change)
        result = self.build()
        self.assertEqual(
            result["status"], "RETAINED_STATE_CHANGED_DURING_ENVELOPE")
        self.assertEqual(self.counts(), before)
        self.assertEqual(result["delivery_authority"], 0)

    def test_missing_query_before_render_fails_closed(self):
        qid = self.query_id("B1_DETAIL")
        with self.r.store.tx() as db:
            db.execute("DELETE FROM packets WHERE id=?", (qid,))
        self.assertEqual(self.build()["status"], "QUERY_PACKET_MISSING")


if __name__ == "__main__":
    unittest.main()
