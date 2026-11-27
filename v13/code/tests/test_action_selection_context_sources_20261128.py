"""C5 ActionSelection must retain the source-bound organ context it actually receives."""
import json
import tempfile
import unittest
from pathlib import Path

from v13.focal import ActionGate
from v13.runtime import Runtime


class ActionSelectionContextSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.tmp.name))
        self.runtime.sleep.cycle.set_policy("enabled", "off")
        self.gate = ActionGate(self.runtime.store)

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def event(self, text="user query"):
        envelope = self.runtime.store.event(self.runtime.session, text)
        return {
            "event_id": envelope["event_id"],
            "brain_generation_id": envelope["brain_generation_id"],
            "source_ref": envelope["source_ref"],
        }

    def source(self, text):
        return self.runtime.store.source(text)

    def select(self, event, coalition):
        return self.gate.select(
            event,
            route="both",
            direct=False,
            resource_state="NORMAL",
            coalition=coalition,
            view={"uncertainty": 0.1, "conflict": 0.2},
            age={"tools": False},
        )

    def last_packet(self, event):
        row = self.runtime.store.one(
            "SELECT payload FROM packets WHERE kind='ActionSelection' AND event_id=? "
            "ORDER BY rowid DESC LIMIT 1",
            (event["event_id"],),
        )
        return json.loads(row["payload"])

    def test_action_selection_binds_current_query_and_all_active_organs(self):
        event = self.event()
        refs = {
            "B1_DETAIL": self.source("precise body evidence"),
            "B2_GIST": self.source("broad body evidence"),
            "MEMORY": self.source("retrieved memory evidence"),
            "WORLD": self.source("world transition evidence"),
            "SELF": self.source("self-model evidence"),
            "B3_CALLOSUM": self.source("callosum control context"),
        }
        coalition = [
            {"item_id": "b1-1", "source_kind": "B1_DETAIL", "priority": 0.8,
             "source_refs": [refs["B1_DETAIL"]]},
            {"item_id": "b2-1", "source_kind": "B2_GIST", "priority": 0.7,
             "source_refs": [refs["B2_GIST"], refs["B1_DETAIL"]]},
            {"item_id": "mem-1", "source_kind": "MEMORY", "priority": 0.5,
             "source_refs": [refs["MEMORY"]]},
            {"item_id": "world-1", "source_kind": "WORLD", "priority": 0.4,
             "source_refs": [refs["WORLD"]]},
            {"item_id": "self-1", "source_kind": "SELF", "priority": 0.3,
             "source_refs": [refs["SELF"]]},
            {"item_id": "b3-1", "source_kind": "B3_CALLOSUM", "priority": 0.2,
             "source_refs": [refs["B3_CALLOSUM"]]},
        ]
        result = self.select(event, coalition)
        packet = self.last_packet(event)
        expected = [event["source_ref"], *refs.values()]

        self.assertEqual(packet["source_refs"], expected)
        self.assertEqual(packet["provenance"], expected)
        self.assertEqual(packet["source_ref_count"], len(expected))
        self.assertFalse(packet["source_refs_truncated"])
        self.assertEqual(
            packet["context_input_organs"],
            ["A_SOURCE", "B1_DETAIL", "B2_GIST", "MEMORY", "WORLD", "SELF", "B3_CALLOSUM"],
        )
        self.assertEqual(
            [item["item_id"] for item in packet["context_sources"]],
            ["b1-1", "b2-1", "mem-1", "world-1", "self-1", "b3-1"],
        )
        self.assertTrue(all(item["source_bound"] for item in packet["context_sources"]))
        self.assertEqual(result["source_refs"], expected)
        self.assertEqual(result["context_input_organs"], packet["context_input_organs"])

    def test_invalid_coalition_source_ref_fails_before_action_selection_is_persisted(self):
        event = self.event("query with invalid context")
        valid = self.source("valid source")
        invalid = dict(valid, sha256="0" * 64)
        before = self.runtime.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind='ActionSelection'"
        )["n"]
        coalition = [{
            "item_id": "bad-memory",
            "source_kind": "MEMORY",
            "priority": 1.0,
            "source_refs": [invalid],
        }]

        with self.assertRaises(ValueError):
            self.select(event, coalition)

        after = self.runtime.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind='ActionSelection'"
        )["n"]
        self.assertEqual(after, before)

    def test_context_item_cap_is_explicit_and_all_source_refs_remain_bound(self):
        event = self.event("many context sources")
        coalition = []
        refs = []
        for index in range(18):
            ref = self.source(f"source {index}")
            refs.append(ref)
            coalition.append({
                "item_id": f"memory-{index}",
                "source_kind": "MEMORY",
                "priority": 1.0 / (index + 1),
                "source_refs": [ref],
            })

        self.select(event, coalition)
        packet = self.last_packet(event)

        self.assertEqual(packet["source_refs"], [event["source_ref"], *refs])
        self.assertEqual(packet["source_ref_count"], 19)
        self.assertFalse(packet["source_refs_truncated"])
        self.assertEqual(len(packet["context_sources"]), 16)
        self.assertTrue(packet["context_sources_truncated"])
        self.assertEqual(packet["context_input_organs"], ["A_SOURCE", "MEMORY"])


if __name__ == "__main__":
    unittest.main()
