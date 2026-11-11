"""Synthetic A5 -> B1/B2/JEF acoustic shadow route; no device proof."""
import unittest
from v13.audio_views import acoustic_views
from v13.pcm_features import build_pcm_raw_ear
from v13.audio_a5 import persist_audio_percept, audio_source_descriptor

class Store:
    def __init__(self, descriptor):
        self.descriptor=descriptor
        self.saved=None
    def read_source(self, ref):
        return self.descriptor
    def add_packet(self, kind, value):
        self.saved=value
        return value

class AudioViewsTest(unittest.TestCase):
    def setUp(self):
        raw=build_pcm_raw_ear("synthetic:pcm",bytes(32000),16000,provisional=False)
        descriptor=audio_source_descriptor(raw)
        ref={"source_id":"src_synthetic","sha256":"0"*64,
             "char_start":0,"char_end":len(descriptor),"modality":"text"}
        store=Store(descriptor)
        self.packet=persist_audio_percept(store,{"source_ref":ref,"event_id":"evt_test",
            "brain_generation_id":"gen_test"},raw)

    def test_both_hemispheres_and_jef_preserve_source(self):
        views=acoustic_views(self.packet)
        self.assertEqual(views["source_ref"],self.packet["source_ref"])
        self.assertEqual(len(views["b2_gist"]),8)
        self.assertEqual(views["jef_control"]["frame_count"],50)
        self.assertEqual(views["jef_control"]["duration_ms"],1000)
        self.assertFalse(views["jef_control"]["semantic_truth_authority"])
        self.assertEqual(views["jef_control"]["action_authority"],0)
        self.assertTrue(all(x["rms"]==0 for x in views["b1_detail"]))
        self.assertTrue(all(x["rms"]==0 for x in views["b2_gist"]))

    def test_rejects_provisional_and_tampered_source(self):
        p=dict(self.packet)
        p["raw_ear"]=dict(p["raw_ear"],provenance="provisional")
        with self.assertRaises(ValueError):
            acoustic_views(p)
        p=dict(self.packet)
        p["segments"]=[dict(x) for x in p["segments"]]
        p["segments"][0]["source_ref"]={"source_id":"other"}
        with self.assertRaises(ValueError):
            acoustic_views(p)

    def test_rejects_divergent_a5_vs_raw_ear(self):
        # A5 must not silently overwrite acoustic evidence from RAW EAR.
        p=dict(self.packet,segments=[dict(x) for x in self.packet["segments"]])
        p["segments"][0]["rms"]=0.75
        with self.assertRaisesRegex(ValueError,"acoustic value mismatch"):
            acoustic_views(p)
        p=dict(self.packet,raw_ear=dict(self.packet["raw_ear"]))
        p["raw_ear"]["frames"]=p["raw_ear"]["frames"][:-1]
        with self.assertRaisesRegex(ValueError,"frame count mismatch"):
            acoustic_views(p)
        p=dict(self.packet,raw_ear=dict(self.packet["raw_ear"],android_capture_verified=True))
        with self.assertRaises(ValueError):
            acoustic_views(p)

    def test_rejects_forged_native_authority_and_invalid_rms(self):
        p=dict(self.packet,android_capture_verified=True)
        with self.assertRaises(ValueError):
            acoustic_views(p)
        p=dict(self.packet,segments=[dict(x) for x in self.packet["segments"]])
        p["segments"][0]["rms"]=float("nan")
        with self.assertRaises(ValueError):
            acoustic_views(p)

if __name__=="__main__":
    unittest.main()
