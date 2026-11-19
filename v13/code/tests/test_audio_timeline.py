import unittest
from v13.audio_timeline import AudioTimeline

def p(start,end,status='PROVISIONAL',source='fixture',consent='fixture'):
    return {'schema':'v13.a5.raw_ear/1','source_ref':{'source_id':source,'consent_id':consent,'sha256':'abc','start_ms':start,'end_ms':end},'status':status,'learning_eligible':False,'acoustic_features':{'rms':0.0}}

class TimelineTests(unittest.TestCase):
    def test_progress_and_final(self):
        t=AudioTimeline();self.assertEqual(t.accept(p(0,20))['frame_count'],1)
        self.assertEqual(t.accept(p(20,40,'FINAL'))['status'],'FINAL')
        with self.assertRaises(ValueError):t.accept(p(40,60))
    def test_overlap(self):
        t=AudioTimeline();t.accept(p(0,20))
        with self.assertRaises(ValueError):t.accept(p(19,30))
    def test_consent_switch(self):
        t=AudioTimeline();t.accept(p(0,20))
        with self.assertRaises(ValueError):t.accept(p(20,40,consent='other'))
    def test_budget(self):
        t=AudioTimeline(max_frames=1);t.accept(p(0,20))
        with self.assertRaises(ValueError):t.accept(p(20,40))
    def test_invalid_rights(self):
        t=AudioTimeline();q=p(0,20);q['learning_eligible']=True
        with self.assertRaises(ValueError):t.accept(q)
    def test_boolean_timestamp(self):
        t=AudioTimeline();q=p(True,20)
        with self.assertRaises(ValueError):t.accept(q)
    def test_external_mutation_cannot_change_committed_provenance(self):
        t=AudioTimeline();q=p(0,20);t.accept(q)
        q['source_ref']['start_ms']=999999
        q['source_ref']['source_id']='forged'
        q['acoustic_features']['rms']=float('nan')
        self.assertEqual(t.frames[0]['source_ref']['start_ms'],0)
        self.assertEqual(t.frames[0]['source_ref']['source_id'],'fixture')
        self.assertEqual(t.frames[0]['acoustic_features']['rms'],0.0)
        self.assertEqual(t.accept(p(20,40,'FINAL'))['start_ms'],0)
    def test_failed_frame_no_mutation(self):
        t=AudioTimeline();t.accept(p(0,20));before=(len(t.frames),t.last_end_ms)
        with self.assertRaises(ValueError):t.accept(p(10,40))
        self.assertEqual((len(t.frames),t.last_end_ms),before)
if __name__=='__main__':unittest.main()
