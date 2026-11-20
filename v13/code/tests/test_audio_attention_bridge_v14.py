"""Linux synthetic A5 acoustic -> A4 modulation contract checks."""
import unittest
from v13.audio_attention_bridge import modulate_audio_attention

class Sink:
    def modulate(self, event_id, sal=None):
        self.received = (event_id, sal)
        return self.received

class AudioAttentionTests(unittest.TestCase):
    def packet(self):
        return {'schema': 'v13.a5.audio-acoustic/1', 'modality': 'audio_raw_ear',
                'source_ref': {'source_id': 'fixture'}, 'features': {'rms': .4, 'peak': .8}}

    def test_consumer(self):
        s = Sink()
        modulate_audio_attention(s, 'e', self.packet())
        self.assertEqual(s.received[0], 'e')
        self.assertAlmostEqual(s.received[1]['external_interrupt'], .4)

    def test_change(self):
        s = Sink()
        modulate_audio_attention(s, 'e', self.packet(), {'features': {'rms': .1}})
        self.assertAlmostEqual(s.received[1]['novelty'], .9)

    def test_bad_schema(self):
        p = self.packet(); p['schema'] = 'bad'
        with self.assertRaises(ValueError):
            modulate_audio_attention(Sink(), 'e', p)

    def test_bad_features(self):
        p = self.packet(); p['features']['peak'] = float('nan')
        with self.assertRaises(ValueError):
            modulate_audio_attention(Sink(), 'e', p)

if __name__ == '__main__':
    unittest.main()
