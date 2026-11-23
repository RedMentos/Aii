"""Preregistered World-JEPA fixture schema recovery with frozen synthetic values."""
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from v13 import world_model as wm
from tests.test_run50_world_jepa_action_outcome_adapter import FakeReadOnlyView
from tests.test_world_jepa_readonly_store import fixture
from scripts.world_jepa_readonly_store import ReadOnlyStore

FAKE128_SHA = "04285e5717551ecf00ef4bd18267b7dba07a0fe34a49d428df5f1093b985cb92"
SQL64_SHA = "b3cc29df39e21415f7fc835e6eb383e78b4df5804be04c54c453bffcc1f51fca"
ORIGINAL_KEYS = ("id", "event_id", "status", "expected", "outcome", "created")


def digest(rows):
    projection = [{k: row[k] for k in ORIGINAL_KEYS} for row in rows]
    return hashlib.sha256(json.dumps(projection, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


class WorldJepaFixtureProvenanceTests(unittest.TestCase):
    def test_fake128_original_values_and_committed_routes(self):
        view = FakeReadOnlyView(128)
        self.assertEqual(digest(view._rows), FAKE128_SHA)
        got = wm.transitions(view)
        self.assertEqual(len(got), 128)
        self.assertEqual({a: sum(x["a"] == a for x in got) for a in wm.ACTIONS},
                         {a: 32 for a in wm.ACTIONS})

    def test_closed_sqlite64_original_values_and_committed_routes(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "synthetic.sqlite"
            fixture(path, n=64)
            with sqlite3.connect(path) as conn:
                conn.row_factory = sqlite3.Row
                rows = [dict(r) for r in conn.execute(
                    "SELECT id,event_id,status,expected,outcome,created "
                    "FROM actions ORDER BY created ASC")]
            self.assertEqual(digest(rows), SQL64_SHA)
            store = ReadOnlyStore(path)
            try:
                got = wm.transitions(store)
                self.assertEqual(len(got), 64)
                self.assertEqual({a: sum(x["a"] == a for x in got) for a in wm.ACTIONS},
                                 {a: 16 for a in wm.ACTIONS})
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
