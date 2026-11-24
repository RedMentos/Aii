"""Run349 RED-first: a digital-error modulator and its own action outcome
must be one SQLite crash boundary. Synthetic local SOURCE_COPY only; no model.
"""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13.common import digest


class WorldModulatorAtomicityRun349(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.e = self.r.store.event(self.r.session, "A synthetic local copy action")
        forecast = self.r.world.forecast(self.e, "SOURCE_COPY", native_prediction=False)
        forecast["learned_latent_prediction"] = {"synthetic_probe": True}
        self.aid = self.r.store.start_action(
            self.e["event_id"], self.e["brain_generation_id"], forecast=forecast
        )
        output = "Exact synthetic self candidate"
        self.r.store.message(
            self.r.session, self.e["event_id"], "assistant",
            text=output, status="FINAL"
        )
        self.r.store.finish_action(
            self.aid, "FINAL",
            {"role": "SOURCE_COPY", "action_duration_s": 1.5,
             "characters": len(output), "self_candidate_hash": digest(output)}
        )

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def packets(self, kind):
        return self.r.store.rows(
            "SELECT id,payload FROM packets WHERE kind=? AND event_id=?",
            (kind, self.e["event_id"])
        )

    def observe(self, score=.25):
        with patch.object(self.r.learner, "world_score", return_value=score):
            return self.r.world.observe(self.aid)

    def test_abort_prediction_insert_rolls_back_modulator_as_a_pair(self):
        with self.r.store.tx() as c:
            c.execute("""
                CREATE TRIGGER run349_abort_prediction
                BEFORE INSERT ON packets
                WHEN NEW.kind='PredictionOutcome'
                BEGIN SELECT RAISE(ABORT, 'injected outcome crash'); END
            """)
        with self.assertRaises(sqlite3.DatabaseError):
            self.observe()
        # Old code has an orphan digital-error modulator here.
        self.assertEqual(self.packets("ModulatorPacket"), [])
        self.assertEqual(self.packets("PredictionOutcome"), [])
        self.assertIsNotNone(self.r.store.one(
            "SELECT outcome FROM actions WHERE id=?", (self.aid,)
        )["outcome"])
        with self.r.store.tx() as c:
            c.execute("DROP TRIGGER run349_abort_prediction")
        outcome = self.observe()
        self.assertEqual(outcome["status"], "FINAL")
        self.assertEqual(len(self.packets("ModulatorPacket")), 1)
        self.assertEqual(len(self.packets("PredictionOutcome")), 1)
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 1)

    def test_completed_pair_is_idempotent_across_restart(self):
        first = self.observe()
        self.assertEqual(self.observe(), first)
        self.assertEqual(len(self.packets("ModulatorPacket")), 1)
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.assertEqual(self.observe(), first)
        self.assertEqual(len(self.packets("ModulatorPacket")), 1)
        self.assertEqual(len(self.packets("PredictionOutcome")), 1)
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 1)

    def test_nonfinite_latent_score_keeps_own_outcome_without_modulator(self):
        observed = self.observe(score=float("nan"))
        self.assertEqual(observed["status"], "FINAL")
        self.assertNotIn("digital_latent_error", observed)
        self.assertIsNone(observed["semantic_success"])
        self.assertFalse(observed["external_world_observation"])
        self.assertEqual(self.packets("ModulatorPacket"), [])
        self.assertEqual(len(self.packets("PredictionOutcome")), 1)


    def test_abort_modulator_insert_never_publishes_orphan_outcome(self):
        with self.r.store.tx() as c:
            c.execute("""
                CREATE TRIGGER run349_abort_modulator
                BEFORE INSERT ON packets
                WHEN NEW.kind='ModulatorPacket'
                BEGIN SELECT RAISE(ABORT, 'injected modulator failure'); END
            """)
        with self.assertRaises(sqlite3.DatabaseError):
            self.observe()
        self.assertEqual(self.packets("ModulatorPacket"), [])
        self.assertEqual(self.packets("PredictionOutcome"), [])
        with self.r.store.tx() as c:
            c.execute("DROP TRIGGER run349_abort_modulator")
        self.assertEqual(self.observe()["status"], "FINAL")
        self.assertEqual(len(self.packets("ModulatorPacket")), 1)
        self.assertEqual(len(self.packets("PredictionOutcome")), 1)

    def test_crash_after_pair_commit_recovers_materialized_view_once(self):
        with patch.object(self.r.world, "_refresh", side_effect=RuntimeError("injected view crash")):
            with self.assertRaisesRegex(RuntimeError, "injected view crash"):
                self.observe()
        self.assertEqual(len(self.packets("ModulatorPacket")), 1)
        self.assertEqual(len(self.packets("PredictionOutcome")), 1)
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 1)
        self.observe()
        self.assertEqual(len(self.packets("ModulatorPacket")), 1)
        self.assertEqual(len(self.packets("PredictionOutcome")), 1)


if __name__ == "__main__":
    unittest.main()
