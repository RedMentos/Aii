"""Synthetic RAW EAR PCM16 -> A5 -> B/C SHADOW path; not device evidence."""
import unittest
from v13.raw_ear_pcm import pcm16_audio_percept
from v13.audio_shadow_consumer import audio_shadow_observation

KW = dict(event_id="synthetic-event", generation_id="synthetic-generation",
          source_id="synthetic-source", source_sha256="a"*64,
          consent_receipt="synthetic-consent")

def frame(values):
    return b"".join(x.to_bytes(2, "little", signed=True) for x in values)

class RawEarPCMTests(unittest.TestCase):
    def test_end_to_end_shadow(self):
        pcm = frame([16384, -16384] * 80)
        packet = pcm16_audio_percept(pcm=pcm, sample_rate=8000, **KW)
        seen = []
        def read_source(source_id):
            seen.append(source_id)
            return {"sha256":"a"*64, "revoked":False, "modality":"audio"}
        observation = audio_shadow_observation(packet, read_source)
        self.assertEqual(seen, ["synthetic-source"])
        self.assertEqual(observation["windows"][0]["end_ms"], 20)
        self.assertAlmostEqual(observation["windows"][0]["rms"], .5)
        self.assertAlmostEqual(observation["windows"][0]["zcr"], 1.0)
        self.assertFalse(observation["learning_authority"])
        self.assertFalse(observation["action_authority"])
        self.assertNotIn("synthetic-consent", repr(observation))

    def test_provisional_retained(self):
        packet = pcm16_audio_percept(pcm=frame([0]*80), sample_rate=8000,
                                    finality="PROVISIONAL", **KW)
        result = audio_shadow_observation(
            packet, lambda _: {"sha256":"a"*64,"revoked":False,"modality":"audio"})
        self.assertEqual(result["finality"], "PROVISIONAL")

    def test_revoked_source_rejected(self):
        packet = pcm16_audio_percept(pcm=frame([0]*80), sample_rate=8000, **KW)
        with self.assertRaises(PermissionError):
            audio_shadow_observation(packet, lambda _: {
                "sha256":"a"*64,"revoked":True,"modality":"audio"})

    def test_oversize_rejected(self):
        with self.assertRaises(ValueError):
            pcm16_audio_percept(pcm=bytes(16002), sample_rate=8000, **KW)

    def test_misaligned_rejected(self):
        with self.assertRaises(ValueError):
            pcm16_audio_percept(pcm=bytes(3), sample_rate=8000, **KW)

    def test_fractional_ms_rejected(self):
        with self.assertRaises(ValueError):
            pcm16_audio_percept(pcm=bytes(6), sample_rate=8000, **KW)

    def test_no_consent_ref_rejected(self):
        with self.assertRaises(PermissionError):
            pcm16_audio_percept(pcm=bytes(160), sample_rate=8000,
                                **{**KW, "consent_receipt":None})

if __name__ == "__main__":
    unittest.main()
