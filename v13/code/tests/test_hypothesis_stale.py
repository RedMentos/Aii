"""WP-BP10 / FS10: stale open questions are marked; only mode active hides them; nothing is written."""
from pathlib import Path
import tempfile
import unittest
from v13.runtime import Runtime
from v13.hypothesis_stale import classify,filter_questions,mode

class Stale(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.s=self.r.store
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def q(self,text):
        e=self.s.event(self.r.session,text);return {'source_ref':e['source_ref'],'event_id':e['event_id']}

    def test_fresh_topic_and_topic_shift(self):
        a=self.q('Wie hoch ist das Budget von Projekt Aurora genau?')
        self.assertEqual(classify(self.s,self.r.session,a,'Und das Budget von Projekt Aurora?'),[])
        self.assertIn('TOPIC_SHIFT',classify(self.s,self.r.session,a,'Erzähl mir etwas über Wetter und Pilze'))
    def test_too_old_and_corrected_since(self):
        a=self.q('Wie hoch ist das Budget von Projekt Aurora genau?')
        for i in range(8):self.q(f'Völlig anderes Thema Nummer {i} Garten Kochen')
        self.assertIn('TOO_OLD',classify(self.s,self.r.session,a,'Budget Aurora'))
        e=self.s.event(self.r.session,'Projekt Aurora Budget?');self.r.memory.feedback(e['event_id'],'fact','90 Euro')
        self.assertIn('CORRECTED_SINCE',classify(self.s,self.r.session,a,'Budget Aurora'))
    def test_modes_shadow_keeps_active_hides_and_nothing_written(self):
        old=self.q('Wie hoch ist das Budget von Projekt Aurora genau?');self.q('Wetter Pilze Garten heute');cur='Wetter Pilze Garten morgen'
        qs=[old]
        before=self.s.rows('SELECT id FROM memories')
        shown,rep=filter_questions(self.s,{'hypothesis_stale':'shadow'},self.r.session,qs,cur)
        self.assertEqual((shown,rep['stale']),(qs,1))
        shown,rep=filter_questions(self.s,{'hypothesis_stale':'active'},self.r.session,qs,cur)
        self.assertEqual((shown,rep['stale'],rep['reasons']),([],1,['TOPIC_SHIFT']))
        shown,rep=filter_questions(self.s,{'hypothesis_stale':'off'},self.r.session,qs,cur);self.assertEqual((shown,rep['checked']),(qs,0))
        self.assertEqual(before,self.s.rows('SELECT id FROM memories'))
        with self.assertRaises(ValueError):mode({'hypothesis_stale':'x'})
    def test_answered_later(self):
        a=self.q('Wie hoch ist das Budget von Projekt Aurora genau?');b=self.q('Wie hoch ist das Budget von Projekt Aurora genau, nochmal?')
        import time
        with self.s.tx() as c:c.execute("INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) VALUES (?,?,?,?,?,?,?)",(self.r.session,b['event_id'],'assistant','120 Euro','FINAL','{}',time.time()))
        self.assertIn('ANSWERED_LATER',classify(self.s,self.r.session,a,'Budget Aurora'))
    def test_source_gone(self):
        a=self.q('Frage zu Aurora');a['source_ref']=dict(a['source_ref'],source_id='nope')
        self.assertEqual(classify(self.s,self.r.session,a,'Aurora'),['SOURCE_GONE'])
    def test_executive_report_context_uses_cfg(self):
        # report_context without cfg keeps old behaviour; with cfg and shadow mode it returns the same list
        rc=self.r.executive.report_context(self.r.session);self.assertEqual(rc['unresolved_observer_hypotheses'],[])
        rc=self.r.executive.report_context(self.r.session,'x',self.r.cfg);self.assertEqual(rc['unresolved_observer_hypotheses'],[])
if __name__=='__main__':unittest.main()
