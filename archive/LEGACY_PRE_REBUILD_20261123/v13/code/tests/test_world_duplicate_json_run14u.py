"""Run14U test-first: ambiguous duplicate JSON keys cannot become F4 World evidence."""
import json
import re
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.world import _strict_json_object


class WorldDuplicateJsonRun14U(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def action(self):
        event = self.r.store.event(self.r.session, "Run14U own action source")
        forecast = self.r.world.forecast(event, "SOURCE_COPY", native_prediction=False)
        aid = self.r.store.start_action(event["event_id"], self.r.store.generation_id, forecast=forecast)
        self.r.store.finish_action(aid, "FINAL", {"role": "SOURCE_COPY", "action_duration_s": 2.0})
        return event, aid

    def test_strict_parser_rejects_duplicate_keys_at_every_depth(self):
        for raw in (
            '{"role":"SOURCE_COPY","role":"C3_LANGUAGE"}',
            '{"observation":{"scored":true,"scored":false}}',
            '{"arr":[{"x":1,"x":2}]}',
        ):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    _strict_json_object(raw)
        self.assertEqual(_strict_json_object('{"role":"SOURCE_COPY","nested":{"x":1}}')["nested"], {"x": 1})

    def test_duplicate_action_outcome_never_creates_observation(self):
        event, aid = self.action()
        raw = '{"role":"SOURCE_COPY","role":"C3_LANGUAGE","action_duration_s":2.0}'
        with self.r.store.tx() as c:
            c.execute("UPDATE actions SET outcome=? WHERE id=?", (raw, aid))
        self.assertIsNone(self.r.world.observe(aid))
        self.assertEqual(self.r.store.one("SELECT outcome FROM actions WHERE id=?", (aid,))["outcome"], raw)
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE event_id=? AND kind='PredictionOutcome'",
            (event["event_id"],))["n"], 0)
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 0)

    def test_duplicate_receipt_not_counted_then_valid_action_recovered(self):
        event, aid = self.action()
        self.assertIsNotNone(self.r.world.observe(aid))
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 1)
        row = self.r.store.one(
            "SELECT id,payload FROM packets WHERE event_id=? AND kind='PredictionOutcome'",
            (event["event_id"],))
        raw = row["payload"]
        altered, n = re.subn(r'("scored":(?:true|false))', r'\1,"scored":true', raw, count=1)
        self.assertEqual(n, 1)
        self.assertNotEqual(altered, raw)
        self.assertIsNotNone(json.loads(altered))  # syntactically valid, semantically ambiguous
        with self.r.store.tx() as c:
            c.execute("UPDATE packets SET payload=? WHERE id=?", (altered, row["id"]))
        self.r.world._refresh(self.r.session)
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 0)
        self.assertEqual(self.r.world.world_state()["recent"], [])
        self.r.world.recover()
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 1)
        self.assertEqual(self.r.store.one("SELECT payload FROM packets WHERE id=?", (row["id"],))["payload"], altered)
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE event_id=? AND kind='PredictionOutcome'",
            (event["event_id"],))["n"], 2)


if __name__ == "__main__":
    unittest.main()
