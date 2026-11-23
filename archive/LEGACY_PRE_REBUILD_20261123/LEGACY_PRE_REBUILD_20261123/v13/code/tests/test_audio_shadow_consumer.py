"""Synthetic A5 -> B/C shadow consumer contract tests; not Redmi proof."""
import copy
import unittest
from v13.audio_percept_contract import audio_percept_packet
from v13.audio_shadow_consumer import audio_shadow_observation

ARGS = dict(event_id="synthetic-event", generation_id="synthetic-generation",
            source_id="synthetic-source", source_sha256="a"*64,
            start_ms=0, end_ms=20, rms=0.2, zcr=0.1,
            consent_receipt="synthetic-local-receipt")
STORE = {"sha256":"a"*64, "revoked":False, "modality":"audio"}

class AudioShadowConsumerTests(unittest.TestCase):
    def packet(self, **changes):
        return audio_percept_packet(**(ARGS | changes))

    def test_final_bounded_observation(self):
        out = audio_shadow_observation(self.packet(), lambda sid: STORE)
        self.assertEqual(out["kind"], "A5_AUDIO_OBSERVATION")
        self.assertEqual(out["finality"], "FINAL")
        self.assertEqual(out["windows"][0]["rms"], 0.2)
        self.assertFalse(out["action_authority"])
        self.assertFalse(out["learning_authority"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertNotIn("synthetic-local-receipt", repr(out))
        self.assertNotIn("asr_transcript", repr(out))

    def test_provisional_not_promoted(self):
        out = audio_shadow_observation(self.packet(finality="PROVISIONAL"), lambda sid: STORE)
        self.assertEqual(out["finality"], "PROVISIONAL")

    def test_revoked_rejected(self):
        with self.assertRaises(PermissionError):
            audio_shadow_observation(self.packet(), lambda sid: {**STORE, "revoked":True})

    def test_hash_mismatch_rejected(self):
        with self.assertRaises(PermissionError):
            audio_shadow_observation(self.packet(), lambda sid: {**STORE, "sha256":"b"*64})

    def test_no_source_rejected(self):
        with self.assertRaises(PermissionError):
            audio_shadow_observation(self.packet(), lambda sid: None)

    def test_mutation_does_not_change_packet(self):
        p = self.packet()
        before = copy.deepcopy(p)
        out = audio_shadow_observation(p, lambda sid: STORE)
        out["windows"][0]["rms"] = 0.9
        out["source_ref"]["source_id"] = "modified"
        self.assertEqual(p, before)

    def test_forged_action_authority_rejected(self):
        p = self.packet()
        p["segments"][0]["action_authority"] = True
        with self.assertRaises(PermissionError):
            audio_shadow_observation(p, lambda sid: STORE)

if __name__ == "__main__":
    unittest.main()
