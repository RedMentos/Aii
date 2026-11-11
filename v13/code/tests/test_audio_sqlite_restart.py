"""Real V13 SQLite Store restart regression for synthetic acoustic replay.

Host Python test only. No Redmi, Android microphone, or model claims.
Run: cd v13/code && python -m unittest tests.test_audio_sqlite_restart -v
"""
import math
import struct
import tempfile
import unittest
from pathlib import Path

from v13.store import Store
from v13.pcm_features import build_pcm_raw_ear
from v13.audio_a5 import audio_source_descriptor, persist_audio_percept
from v13.audio_store_bridge import replay_acoustic_packet


class RealSQLiteAudioReplay(unittest.TestCase):
    def test_restart_replay_and_revocation(self):
        rate = 16000
        samples = [round(10000 * math.sin(2 * math.pi * 440 * i / rate))
                   for i in range(3200)]
        pcm = struct.pack("<" + "h" * len(samples), *samples)
        raw = build_pcm_raw_ear("synthetic:sqlite:440", pcm, rate,
                                provisional=False)
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            for name in ("data", "data/db", "data/blobs"):
                (home / name).mkdir(parents=True, exist_ok=True)
            store = Store(home)
            try:
                session = store.new_session("audio sqlite fixture")
                event = store.event(session, audio_source_descriptor(raw))
                packet = persist_audio_percept(store, event, raw)
                packet_id = packet["packet_id"]
                source_id = event["source_ref"]["source_id"]
                self.assertEqual(
                    replay_acoustic_packet(store, packet_id)["authority"], "SHADOW")
            finally:
                store.close()

            # Reopen a NEW real SQLite connection after releasing the lock.
            reopened = Store(home)
            try:
                views = replay_acoustic_packet(reopened, packet_id)
                self.assertEqual(views["jef_control"]["frame_count"], 10)
                self.assertTrue(views["b1_detail"][0]["rms"] > 0)
                self.assertEqual(views["jef_control"]["action_authority"], 0)
                self.assertIsNone(views["b1_detail"][0]["voiced_probability"])
                # Source revocation must invalidate already persisted A5 replay.
                with reopened.tx() as db:
                    db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                               (source_id,))
                with self.assertRaises(ValueError):
                    replay_acoustic_packet(reopened, packet_id)
            finally:
                reopened.close()

    def test_provisional_not_written_to_real_store(self):
        raw = build_pcm_raw_ear("synthetic:sqlite:provisional",
                                bytes(3200), 16000, provisional=True)
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            for name in ("data", "data/db", "data/blobs"):
                (home / name).mkdir(parents=True, exist_ok=True)
            store = Store(home)
            try:
                event = store.event(store.new_session("provisional"),
                                    audio_source_descriptor(raw))
                before = store.one("SELECT count(*) AS n FROM packets")["n"]
                with self.assertRaisesRegex(ValueError, "provisional"):
                    persist_audio_percept(store, event, raw)
                after = store.one("SELECT count(*) AS n FROM packets")["n"]
                self.assertEqual(before, after)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
