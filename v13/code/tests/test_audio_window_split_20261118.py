import unittest
from v13.audio_percept import canonical_packets

REF = {"source_id":"synthetic-audio", "sha256":"a"*64}

class SplitRawEar(unittest.TestCase):
    def make(self, n, **kwargs):
        return canonical_packets([0.1]*n, 16000, REF, 100,
            consent_receipt="synthetic-opt-in",event_id="synthetic-event",
            generation_id="synthetic-generation",**kwargs)

    def test_two_seconds(self):
        packets=self.make(32000)
        self.assertEqual(len(packets),2)
        a,b=(p["segments"][0] for p in packets)
        self.assertEqual((a["start_ms"],a["end_ms"]), (100,1100))
        self.assertEqual((b["start_ms"],b["end_ms"]), (1100,2100))
        self.assertFalse(a["learning_authority"])
        self.assertFalse(b["action_authority"])
        self.assertEqual(packets[0]["source_ref"]["sha256"],REF["sha256"])

    def test_tail_coverage(self):
        packets=self.make(16080)
        self.assertEqual(len(packets),2)
        self.assertEqual(packets[1]["segments"][0]["end_ms"],1105)

    def test_single_sample_tail_preserved(self):
        packets=self.make(16001)
        self.assertEqual(len(packets),2)
        a,b=(p["segments"][0] for p in packets)
        self.assertEqual(a["end_ms"],b["start_ms"])
        self.assertEqual(b["end_ms"],1100)
        self.assertLessEqual(a["end_ms"]-a["start_ms"],1000)
        self.assertLessEqual(b["end_ms"]-b["start_ms"],1000)

    def test_invalid_rate_rejected_cleanly(self):
        for rate in (0, 16000.0, True, -1):
            with self.subTest(rate=rate):
                with self.assertRaises(ValueError):
                    canonical_packets([0.1]*160,rate,REF,0,
                        consent_receipt="ok",event_id="x",generation_id="y")

    def test_no_consent(self):
        with self.assertRaises(PermissionError):
            canonical_packets([0.1]*160,16000,REF,0,
                consent_receipt="",event_id="x",generation_id="y")

    def test_overflow_rejected(self):
        with self.assertRaises(ValueError):
            self.make(32001)

    def test_finality(self):
        self.assertEqual(self.make(160,provisional=False)[0]["segments"][0]["finality"],"FINAL")

if __name__=="__main__":unittest.main()
