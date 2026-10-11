"""WP-V5 phone usability: pasted logs, ratings, :context, :pause, burn-out budget."""
import json
import tempfile
import unittest
from pathlib import Path
from v13 import inputs
from v13.runtime import Runtime
from v13.operator import Operator

LOG='''$ bash TESTEN.sh
[bench 13:11:47] Quelle /mnt/project-files/v13/code
Traceback (most recent call last):
  File "/x/y.py", line 3, in <module>
ValueError: kaputt
Ran 12 tests in 0.3s'''

class Detection(unittest.TestCase):
    def test_terminal_log_detection(self):
        self.assertTrue(inputs.looks_like_terminal_log(LOG))
        self.assertFalse(inputs.looks_like_terminal_log('Wie viel Budget bleibt?\nUnd welche Option ist lokal?\nDanke.'))
        self.assertFalse(inputs.looks_like_terminal_log('$ ls'))
    def test_implicit_feedback(self):
        self.assertEqual(inputs.implicit_feedback('Danke, genau so!'),'praise')
        self.assertEqual(inputs.implicit_feedback("That's wrong, you repeated my question."),'criticism')
        self.assertIsNone(inputs.implicit_feedback('Danke, aber das ist falsch.'))
        self.assertIsNone(inputs.implicit_feedback('Wie geht es weiter?'))
        self.assertIsNone(inputs.implicit_feedback(LOG))
    def test_read_block_joins_paste(self):
        from v13.ui import read_block
        feed=iter(['erste Zeile','zweite Zeile','dritte']);pending=[2]
        def ready():
            pending[0]-=1;return pending[0]>=0
        self.assertEqual(read_block('> ',ready,lambda p:next(feed)),'erste Zeile\nzweite Zeile\ndritte')

class OperatorCommands(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.op=Operator(self.r);s=self.r.store
        self.e=s.event(self.r.session,'Frage')
        with s.tx() as c:c.execute("INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) VALUES (?,?,?,?,?,?,?)",(self.r.session,self.e['event_id'],'assistant','Antwort','FINAL','{"model_generated": true}',0))
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def test_note_and_implicit_rating(self):
        row=json.loads(self.op.run(':note 9 sehr gut'));self.assertEqual((row['score'],row['origin']),(9,'EXPLICIT_NOTE'))
        with self.assertRaises(ValueError):self.op.run(':note 11')
        self.op._implicit_feedback('Falsch, das stimmt nicht.')
        summary=json.loads(self.op.run(':ratings'));self.assertEqual((summary['explicit'],summary['implicit']),(1,1))
        self.assertEqual(inputs.ratings(self.r.store)[-1]['score'],3)
    def test_context_and_pause_commands(self):
        self.assertIn('Noch kein',self.op.run(':context'))
        inputs.save_context(self.r.store,self.r.session,self.e['event_id'],'C3_LANGUAGE',[{'role':'user','content':'Frage'}])
        self.assertEqual(json.loads(self.op.run(':context'))['messages'][0]['content'],'Frage')
        self.assertEqual(json.loads(self.op.run(':pause traum'))['paused'],['traum'])
        self.assertEqual(inputs.background_blocked(self.r.store,'sleep_b',0),'PAUSED_TRAUM')
        self.assertIsNone(inputs.background_blocked(self.r.store,'sleep_c',0))
        self.op.run(':pause budget 2');self.assertEqual(inputs.background_blocked(self.r.store,'sleep_c',2),'BURNED_OUT_WAITING_FOR_INPUT')
        self.op.run(':resume traum');self.assertFalse(inputs.paused(self.r.store,'traum'))
        with self.assertRaises(ValueError):self.op.run(':pause alles')
    def test_logs_stay_out_of_native_history(self):
        from v13.history import native_history
        s=self.r.store;e=s.event(self.r.session,LOG)
        with s.tx() as c:c.execute("INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) VALUES (?,?,?,?,?,?,?)",(self.r.session,e['event_id'],'assistant','ok','FINAL',json.dumps({'context_source_refs':[e['source_ref']]}),0))
        now=s.event(self.r.session,'Neue Frage')
        rows,_=native_history(s,self.r.session,now['event_id'],8)
        self.assertNotIn(e['event_id'],{r['event_id'] for r in rows})

if __name__=='__main__':unittest.main()
