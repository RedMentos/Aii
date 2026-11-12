"""Synthetic regression: bounded A5 audio source gate. No Android hardware claim."""
import unittest
from v13.audio_source_gate import checked_audio_source_view

REF={'source_id':'synthetic','sha256':'a'*64,'modality':'audio','char_start':0,'char_end':0}
SEG={'start_ms':0,'end_ms':20,'consent_receipt_ref':'synthetic-consent','finality':'FINAL','action_authority':False,'learning_authority':False,'acoustic':{'rms':0.2,'zcr':0.1},'asr_transcript':None}
P={'modality':'audio','source_ref':REF,'provenance':[REF],'segments':[SEG],'event_id':'event','brain_generation_id':'gen'}
S={'sha256':'a'*64,'revoked':False,'modality':'audio'}
def run(p): return checked_audio_source_view(p,lambda _:S)
class GateHardeningTests(unittest.TestCase):
 def test_valid_and_copy(self):
  out=run(P);out['segments'][0]['acoustic']['rms']=0.8
  self.assertEqual(P['segments'][0]['acoustic']['rms'],0.2)
 def test_overlap(self):
  with self.assertRaises(ValueError):run({**P,'segments':[SEG,{**SEG,'start_ms':10,'end_ms':30}]})
 def test_bool_time(self):
  with self.assertRaises(ValueError):run({**P,'segments':[{**SEG,'start_ms':False}]})
 def test_nan(self):
  with self.assertRaises(ValueError):run({**P,'segments':[{**SEG,'acoustic':{'rms':float('nan'),'zcr':0.1}}]})
 def test_forged_asr(self):
  with self.assertRaises(ValueError):run({**P,'segments':[{**SEG,'asr_transcript':'hello'}]})
 def test_nonzero_text_span(self):
  ref={**REF,'char_end':10}
  with self.assertRaises(ValueError):run({**P,'source_ref':ref,'provenance':[ref]})
 def test_missing_identity(self):
  with self.assertRaises(ValueError):run({**P,'event_id':None})
 def test_many_segments(self):
  with self.assertRaises(ValueError):run({**P,'segments':[SEG]*65})
if __name__=='__main__':unittest.main()
