"""Synthetic tests for read-only A5 source gate; not native device evidence."""
import unittest
from v13.audio_source_gate import checked_audio_source_view

REF = {'source_id':'synthetic','sha256':'a'*64,'modality':'audio','char_start':0,'char_end':0}
PACKET = {'modality':'audio','source_ref':REF,'provenance':[REF],
          'segments':[{'start_ms':0,'end_ms':20,'consent_receipt_ref':'synthetic-consent','finality':'FINAL','acoustic':{'rms':0.2,'zcr':0.1},'action_authority':False,'learning_authority':False}],
          'event_id':'synthetic','brain_generation_id':'synthetic'}
STORE = {'sha256':'a'*64,'revoked':False,'modality':'audio'}

class GateTests(unittest.TestCase):
    def test_valid(self):
        result=checked_audio_source_view(PACKET, lambda sid: STORE)
        self.assertEqual(result['authority'],'SHADOW_ONLY')
    def test_revoked(self):
        with self.assertRaises(PermissionError):
            checked_audio_source_view(PACKET,lambda sid:{**STORE,'revoked':True})
    def test_hash_mismatch(self):
        with self.assertRaises(PermissionError):
            checked_audio_source_view(PACKET,lambda sid:{**STORE,'sha256':'b'*64})
    def test_no_source(self):
        with self.assertRaises(PermissionError):
            checked_audio_source_view(PACKET,lambda sid:None)
    def test_forged_authority(self):
        with self.assertRaises(PermissionError):
            checked_audio_source_view({**PACKET,'segments':[{**PACKET['segments'][0],'action_authority':True}]},lambda sid:STORE)
    def test_bad_provenance(self):
        with self.assertRaises(ValueError):
            checked_audio_source_view({**PACKET,'provenance':[]},lambda sid:STORE)
    def test_missing_revocation_flag(self):
        with self.assertRaises(PermissionError):
            checked_audio_source_view(PACKET,lambda sid:{'sha256':'a'*64,'modality':'audio'})

if __name__=='__main__':unittest.main()
