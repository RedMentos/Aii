"""A5 RAW EAR persistence checks; synthetic host only."""
import json
import unittest
from v13.pcm_features import build_pcm_raw_ear
from v13.audio_a5 import audio_source_descriptor, persist_audio_percept

class FakeStore:
    def __init__(self, text):
        self.text = text
        self.saved = None
    def read_source(self, ref):
        return self.text
    def add_packet(self, kind, packet):
        self.saved = (kind, json.loads(json.dumps(packet)))
        return packet

class AudioA5Test(unittest.TestCase):
    def setUp(self):
        self.raw = build_pcm_raw_ear("source:synthetic", bytes(32000), 16000, provisional=False)
        self.ref = {"source_id":"src_test","sha256":"0"*64,
                    "char_start":0,"char_end":len(audio_source_descriptor(self.raw)),
                    "modality":"text"}
        self.event = {"source_ref":self.ref, "event_id":"evt_test",
                      "brain_generation_id":"gen_test"}

    def test_a5_timed_packet_and_zero_authority(self):
        s = FakeStore(audio_source_descriptor(self.raw))
        p = persist_audio_percept(s, self.event, self.raw)
        self.assertEqual(p["modality"], "audio_acoustic")
        self.assertEqual(len(p["segments"]), 50)
        self.assertEqual(p["segments"][-1]["end_ms"], 1000)
        self.assertEqual(p["raw_ear"]["source_sha256"], self.raw.source_sha256)
        self.assertEqual(p["native_receiver_authority"], 0)
        self.assertFalse(p["android_capture_verified"])
        self.assertEqual(s.saved[0], "PerceptPacket")

    def test_provisional_audio_cannot_be_authoritative(self):
        provisional = build_pcm_raw_ear("source:synthetic", bytes(32000), 16000, provisional=True)
        store = FakeStore(audio_source_descriptor(provisional))
        with self.assertRaisesRegex(ValueError, "provisional"):
            persist_audio_percept(store, self.event, provisional)
        self.assertIsNone(store.saved)

    def test_source_mismatch_no_persistence(self):
        s = FakeStore("v13.audio_pcm_sha256:" + "f"*64 + "\\n")
        with self.assertRaises(ValueError):
            persist_audio_percept(s, self.event, self.raw)
        self.assertIsNone(s.saved)

    def test_asr_cannot_be_promoted_as_acoustic_truth(self):
        from v13.raw_ear_contract import build_raw_ear
        from v13.pcm_features import extract_pcm_frames
        pcm = bytes(32000)
        raw = build_raw_ear("source:synthetic", pcm, 16000,
                            extract_pcm_frames(pcm,16000),
                            asr_text="hello", asr_teacher_id="teacher:test")
        s = FakeStore(audio_source_descriptor(raw))
        with self.assertRaises(ValueError):
            persist_audio_percept(s,self.event,raw)
        self.assertIsNone(s.saved)
