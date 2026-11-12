"""Synthetic timed RAW EAR source contract; no native Android proof."""
import json
import unittest
from unittest.mock import Mock
from v13.a3_online_projector import A3Projector
from v13.a3_timed_audio import observe_timed_audio

class TimedAudioTests(unittest.TestCase):
    def setUp(self):
        self.data = dict(features=[.2,.4], final=True, start_ms=100,
                         end_ms=300, sample_rate_hz=16000,
                         acoustic=dict(rms=.25,pitch_hz=220.0,speech_probability=.6))
        self.store = Mock()
        self.runtime = Mock(store=self.store)
        self.ref = dict(source_id="ear_1",sha256="a"*64,char_start=0,
                        char_end=0,modality="text")
        self.projector = A3Projector(2,1)

    def run_fixture(self):
        raw=json.dumps(self.data)
        self.ref["char_end"]=len(raw)
        self.store.read_source.return_value=raw
        return observe_timed_audio(self.runtime,self.projector,self.ref)

    def test_timed_acoustic_no_transcript_or_action(self):
        result=self.run_fixture()
        self.assertEqual(result["a5"]["start_ms"],100)
        self.assertEqual(result["a5"]["acoustic"]["pitch_hz"],220.0)
        self.assertIsNone(result["a5"]["transcript"])
        self.assertFalse(result["jef"]["android_action_allowed"])
        self.assertGreaterEqual(self.store.read_source.call_count,2)

    def test_provisional_and_invalid_timing(self):
        self.data["final"]=False
        with self.assertRaises(PermissionError): self.run_fixture()
        self.data["final"]=True
        self.data["end_ms"]=99
        with self.assertRaises(ValueError): self.run_fixture()

    def test_nonfinite_acoustic_rejected(self):
        self.data["acoustic"]["rms"]=float("nan")
        with self.assertRaises(ValueError): self.run_fixture()

    def test_revocation_during_inference(self):
        raw=json.dumps(self.data)
        self.ref["char_end"]=len(raw)
        self.store.read_source.side_effect=[raw,ValueError("revoked")]
        with self.assertRaises(PermissionError):
            observe_timed_audio(self.runtime,self.projector,self.ref)

if __name__=="__main__": unittest.main()
