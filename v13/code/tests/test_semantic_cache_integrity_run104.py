"""Run104: cached semantic vectors cannot promote malformed persisted SQLite values.
Real Runtime/Store persistence; synthetic encoder; no native model/Redmi claim.
"""
import math
import tempfile
import time
import unittest
from pathlib import Path

from v13.common import Unavailable
from v13.runtime import Runtime
from v13.semantic_memory import SemanticKeys


class FixedEncoder:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail
        self.last_metrics = {}

    def installed(self):
        return True

    def revision(self):
        return "run104-fixed-synthetic-v1"

    def __call__(self, texts, cancel, deadline):
        self.calls.append(list(texts))
        if self.fail:
            raise Unavailable("synthetic encoder offline")
        # Query points along x; stored key along y. A poisoned x-cache
        # would falsely score 1.0 instead of the correct 0.0.
        return [[1., 0.]] + [[0., 1.] for _ in texts[1:]]


class SemanticCacheIntegrityRun104(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.cfg["memory_embed_dim"] = 2
        event = self.r.store.event(self.r.session, "Project Orion budget?")
        mid = self.r.memory.feedback(event["event_id"], "fact", "120 Euro", key="Project Orion budget?")
        self.row = self.r.store.one("SELECT id,source_id,key_text FROM memories WHERE id=?", (mid,))
        self.encoder = FixedEncoder()
        self.keys = SemanticKeys(self.r.store, self.r.cfg, self.encoder)
        self.key = self.keys.cache_key(self.row)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def inject(self, payload):
        self.r.store.set_state(self.key, [0., 1.])
        with self.r.store.tx() as c:
            c.execute("UPDATE states SET payload=? WHERE key=?", (payload, self.key))

    def score(self):
        return self.keys.similarities("Project Orion money?", [self.row], None, time.monotonic()+30)[self.row["id"]]

    def assert_reencoded(self):
        self.assertAlmostEqual(self.score(), 0., places=7)
        self.assertEqual([len(call) for call in self.encoder.calls], [2])
        saved, _ = self.r.store.state(self.key)
        self.assertEqual(saved, [0., 1.])
        self.assertTrue(all(math.isfinite(x) for x in saved))

    def test_sqlite_nan_cache_does_not_become_perfect_relevance(self):
        self.inject("[NaN, 0.0]")
        self.assert_reencoded()

    def test_sqlite_infinity_cache_does_not_become_perfect_relevance(self):
        self.inject("[Infinity, 0.0]")
        self.assert_reencoded()

    def test_unnormalized_cache_does_not_clip_to_perfect_relevance(self):
        self.inject("[100.0, 0.0]")
        self.assert_reencoded()

    def test_boolean_cache_is_not_a_real_embedding_coordinate(self):
        self.inject("[true, 0.0]")
        self.assert_reencoded()

    def test_non_numeric_cache_reencodes_instead_of_crashing(self):
        self.inject('["not-a-number", 0.0]')
        self.assert_reencoded()

    def test_valid_unit_cache_reused_without_key_reencoding(self):
        self.r.store.set_state(self.key, [0., 1.])
        self.assertAlmostEqual(self.score(), 0.)
        self.assertEqual([len(call) for call in self.encoder.calls], [1])

    def test_rounded_near_unit_cache_reused(self):
        self.r.store.set_state(self.key, [0.707107, 0.707107])
        self.assertAlmostEqual(self.score(), 0.707107, places=6)
        self.assertEqual([len(call) for call in self.encoder.calls], [1])

    def test_poisoned_cache_stays_untrusted_after_restart(self):
        self.inject("[NaN, 0.0]")
        self.r.close()
        self.r = Runtime(self.home)
        self.r.cfg["memory_embed_dim"] = 2
        self.encoder = FixedEncoder()
        self.keys = SemanticKeys(self.r.store, self.r.cfg, self.encoder)
        self.assert_reencoded()

    def test_poisoned_cache_cannot_bypass_encoder_failure(self):
        self.inject("[NaN, 0.0]")
        self.encoder.fail = True
        with self.assertRaises(Unavailable):
            self.score()


if __name__ == "__main__":
    unittest.main()
