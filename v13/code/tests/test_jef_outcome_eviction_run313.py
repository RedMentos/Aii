"""Run313 RED/GREEN: durable JEF self-outcome identity after bounded retention.

Real production Runtime/Store SQLite; authored outcomes only, no native models.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
import tempfile
import unittest

from v13.runtime import Runtime
from v13 import fastpolicy as fp
from v13 import jefoutcome as jo


class JefOutcomeEvictionRun313(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def create_event(self, name, kind="B2_GIST"):
        e = self.r.store.event(self.r.session, name)
        fp.head(self.r, "wake", e, "both")
        result = self.emit(e, kind)
        self.assertEqual(result, {"wake": "gist" if kind == "B2_GIST" else "detail"})
        return e

    def emit(self, event, kind="B2_GIST"):
        return jo.after_turn(self.r, event,
                             {"wake_decision": {"action": "both"}}, "FINAL",
                             {"coalition": [{"source_kind": kind, "item_id": "offer"}]})

    def sources(self):
        return self.r.store.one(
            "SELECT COUNT(*) AS n FROM sources WHERE kind='OUTCOME_SELF_LABEL'")["n"]

    def labels(self):
        return (self.r.store.state(jo.KEY)[0] or {}).get("labels", [])

    def test_evicted_event_replay_after_restart_never_relabels_or_allocates_source(self):
        with patch.object(jo, "MAX", 2):
            first = self.create_event("run313 first")
            self.create_event("run313 second")
            self.create_event("run313 third")
            self.assertEqual(len(self.labels()), 2)
            self.assertEqual(self.sources(), 3)
            before = self.r.store.state(jo.KEY)
            self.r.close()
            self.r = Runtime(self.home)
            self.assertEqual(self.emit(first), {})
            self.assertEqual(self.r.store.state(jo.KEY), before)
            self.assertEqual(self.sources(), 3)
            self.assertNotIn(first["event_id"], [x["event_id"] for x in self.labels()])

    def test_changed_target_after_eviction_cannot_relabel_old_event(self):
        with patch.object(jo, "MAX", 2):
            first = self.create_event("run313 first changed")
            self.create_event("run313 second changed")
            self.create_event("run313 third changed")
            before = self.r.store.state(jo.KEY)
            count = self.sources()
            self.assertEqual(self.emit(first, "B1_DETAIL"), {})
            self.assertEqual(self.r.store.state(jo.KEY), before)
            self.assertEqual(self.sources(), count)

    def test_concurrent_callbacks_allocate_one_source_and_label(self):
        event = self.r.store.event(self.r.session, "run313 same event concurrency")
        fp.head(self.r, "wake", event, "both")
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.emit(event), range(8)))
        self.assertEqual(sum(bool(x) for x in results), 1)
        self.assertEqual(len(self.labels()), 1)
        self.assertEqual(self.sources(), 1)

    def test_receipt_failure_rolls_back_source_row_and_label_together(self):
        event = self.r.store.event(self.r.session, "run313 atomic source")
        fp.head(self.r, "wake", event, "both")
        before = self.r.store.state(jo.KEY)
        source_count = self.sources()
        original_dumps = jo.dumps
        def fail_receipt(value):
            if isinstance(value, dict) and all(k in value for k in
                    ("event_id", "component", "decision_packet_id", "source_id", "value")):
                raise RuntimeError("injected receipt serialization failure")
            return original_dumps(value)
        with patch.object(jo, "dumps", side_effect=fail_receipt):
            self.assertEqual(self.emit(event), {})
        self.assertEqual(self.r.store.state(jo.KEY), before)
        self.assertEqual(self.sources(), source_count)
        self.assertEqual(self.emit(event), {"wake": "gist"})
        self.assertEqual(self.sources(), source_count + 1)
        self.assertEqual(len(self.labels()), 1)
        self.assertEqual(self.r.store.integrity(True), [])

    def test_distinct_components_keep_separate_source_bound_labels(self):
        e = self.r.store.event(self.r.session, "run313 two heads")
        fp.head(self.r, "wake", e, "both")
        fp.head(self.r, "memory", e, "recall")
        meta = {"wake_decision": {"action": "both"}, "memory_ids": ["m1"]}
        result = jo.after_turn(self.r, e, meta, "FINAL",
            {"coalition": [{"source_kind": "B1_DETAIL", "item_id": "offer"}]})
        self.assertEqual(result, {"wake": "detail", "memory": "skip"})
        self.assertEqual(self.sources(), 2)
        self.assertEqual(jo.after_turn(self.r, e, meta, "FINAL",
            {"coalition": [{"source_kind": "B1_DETAIL", "item_id": "offer"}]}), {})
        self.assertEqual(self.sources(), 2)
        self.assertEqual(jo.training_rows(self.r.store, "wake",
            jo._decision(self.r.store, e["event_id"], "wake")["context_revision"], set()), [])


if __name__ == "__main__":
    unittest.main()
