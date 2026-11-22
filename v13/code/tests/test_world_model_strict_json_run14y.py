"""Run14Y test-first: T8 World fit and counterfactual must reject ambiguous source JSON."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from v13.runtime import Runtime
from v13 import world_model as WM


class WorldModelStrictJSONRun14Y(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    @staticmethod
    def row(name, expected=None, outcome=None):
        return {
            "id": name, "event_id": "event-" + name, "generation_id": "gen-test",
            "status": "FINAL", "created": 3600,
            "expected": expected or '{"forecast":{"input_chars":100,"resource_state":"NORMAL"}}',
            "outcome": outcome or '{"action_duration_s":1.5,"characters":30}',
        }

    def test_duplicate_source_fields_never_become_world_training_transitions(self):
        rows = [
            self.row("good"),
            self.row("nested-forecast", expected='{"forecast":{"input_chars":100,"input_chars":200,"resource_state":"NORMAL"}}'),
            self.row("escaped-forecast", expected=r'{"forecast":{"input_chars":100,"\u0069nput_chars":200,"resource_state":"NORMAL"}}'),
            self.row("top-forecast", expected='{"forecast":{"input_chars":100},"forecast":{"input_chars":200}}'),
            self.row("outcome", outcome='{"action_duration_s":1.5,"characters":30,"characters":31}'),
            self.row("selection"),
            self.row("escaped-selection"),
        ]
        valid = json.dumps({
            "event_id": "placeholder", "brain_generation_id": "gen-test",
            "stage": "COMMIT", "route_hint": "detail",
        })

        def select(sql, params=()):
            if "FROM actions a" in sql:
                return rows
            if "FROM packets WHERE kind='ActionSelection'" in sql:
                eid, gen, _ = params
                base = valid.replace("placeholder", eid)
                if eid == "event-selection":
                    base = base.replace('"route_hint": "detail"', '"route_hint":"detail","route_hint":"gist"')
                elif eid == "event-escaped-selection":
                    base = base.replace('"route_hint": "detail"', r'"route_hint":"detail","\u0072oute_hint":"gist"')
                return [{"payload": base}]
            raise AssertionError(sql)

        with mock.patch.object(self.r.store, "rows", side_effect=select):
            actual = WM.transitions(self.r.store)
        self.assertEqual([x["action_id"] for x in actual], ["good"])
        self.assertEqual(actual[0]["a"], "detail")

    def test_for_event_rejects_duplicate_forecast_without_fabricating_state(self):
        cases = [
            '{"forecast":{"input_chars":100,"input_chars":200}}',
            r'{"forecast":{"input_chars":100,"\u0069nput_chars":200}}',
            '{"forecast":{"input_chars":100},"forecast":{"input_chars":200}}',
        ]
        for raw in cases:
            with self.subTest(raw=raw):
                row = {"expected": raw, "created": 3600}
                with mock.patch.object(self.r.store, "one", return_value=row), \
                     mock.patch.object(WM, "load", return_value=None):
                    result = WM.for_event(self.r.store, "event", "detail")
                self.assertEqual(
                    (result["label"], result["confidence"], result["reason"], result["authority"]),
                    ("SIMULATION_UNCERTAIN", 0., "INVALID_OBSERVED_STATE", "HYPOTHESIS"),
                )

    def test_unique_valid_source_remains_eligible(self):
        with mock.patch.object(self.r.store, "one", return_value={
            "expected": '{"forecast":{"input_chars":100,"resource_state":"NORMAL"}}',
            "created": 3600,
        }), mock.patch.object(WM, "load", return_value=None):
            self.assertEqual(WM.for_event(self.r.store, "event", "detail")["reason"], "NO_WORLD_MODEL")


if __name__ == "__main__":
    unittest.main()
