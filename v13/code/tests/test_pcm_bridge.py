"""Synthetic PCM bridge tests; host-only."""
import json
import struct
import unittest
from v13.pcm_bridge import pcm_to_timed_source

class PcmBridgeTests(unittest.TestCase):
    def test_silence(self):
        x=json.loads(pcm_to_timed_source(bytes(640),16000,start_ms=100))
        self.assertEqual((x['start_ms'],x['end_ms']), (100,120))
        self.assertEqual(x['features'],[0.0,0.0])
        self.assertEqual(x['acoustic']['speech_probability'],0.0)

    def test_signal(self):
        raw=struct.pack('<320h', *([10000,-10000]*160))
        x=json.loads(pcm_to_timed_source(raw,16000))
        self.assertGreater(x['features'][0],0.3)
        self.assertGreater(x['features'][1],0.99)
        self.assertEqual(x['end_ms'],20)

    def test_reject_invalid(self):
        for kwargs in ({'start_ms':True},{'start_ms':86400000},{'final':1}):
            with self.assertRaises(ValueError):
                pcm_to_timed_source(bytes(640),16000,**kwargs)
        with self.assertRaises(ValueError):
            pcm_to_timed_source(b'',16000)
        with self.assertRaises(ValueError):
            pcm_to_timed_source(bytes(640),16000,start_ms=86399990)

    def test_provisional_preserved(self):
        x=json.loads(pcm_to_timed_source(bytes(640),16000,final=False))
        self.assertIs(x['final'],False)

if __name__=='__main__':
    unittest.main()
