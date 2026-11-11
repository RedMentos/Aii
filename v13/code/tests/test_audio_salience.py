import unittest
from v13.audio_salience import acoustic_salience

class AcousticSalienceTest(unittest.TestCase):
    def test_onset_and_order(self):
        frames=[{'start_ms':i*20,'end_ms':(i+1)*20,'rms':r} for i,r in enumerate([0,.7,.7,.1,.8,.1,.6])]
        result=acoustic_salience(frames,max_events=2,threshold=.3)
        self.assertEqual([x['start_ms'] for x in result],[20,80])
        self.assertEqual(result[0]['onset_delta'],.7)
    def test_silence_and_steady(self):
        frames=[{'start_ms':i*20,'end_ms':(i+1)*20,'rms':0} for i in range(10)]
        self.assertEqual(acoustic_salience(frames),[])
    def test_invalid(self):
        with self.assertRaises(ValueError): acoustic_salience([{'rms':float('nan')}])
        with self.assertRaises(ValueError): acoustic_salience([],max_events=True)
        with self.assertRaises(ValueError): acoustic_salience([],threshold=float('inf'))
if __name__=='__main__':unittest.main()
