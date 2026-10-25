"""Run203: lexical Memory.recall must not retarget human corrections via mutable keys.

Actual Runtime/SQLite and source packets, synthetic text only; no model inference.
"""
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime


ALPHA='Projekt Alpha Budget'
BETA='Projekt Beta Budget'


class MemoryRecallKeyLineageRun203(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.home=Path(self.tmp.name)
        self.r=Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled','off')
        self.s=self.r.store
        self.e=self.s.event(self.r.session,ALPHA)
        self.mid=self.r.memory.feedback(self.e['event_id'],'fact','120 Euro',key=ALPHA)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def mutate(self,sql,args):
        with self.s.tx() as c:c.execute(sql,args)

    def recall(self,query,session=None):
        return self.r.memory.recall(query,session or self.r.session)

    def test_original_correction_recalled_without_read_side_effect(self):
        before=self.s.one("SELECT COUNT(*) AS n FROM sources WHERE kind='MEMORY_KEY'")['n']
        got=self.recall(ALPHA)
        self.assertEqual([m['id'] for m in got],[self.mid])
        self.assertEqual(got[0]['value'],'120 Euro')
        after=self.s.one("SELECT COUNT(*) AS n FROM sources WHERE kind='MEMORY_KEY'")['n']
        self.assertEqual(before,after)

    def test_mutated_key_cannot_redirect_alpha_value_to_beta_question(self):
        self.mutate('UPDATE memories SET key_text=? WHERE id=?',(BETA,self.mid))
        self.assertEqual(self.recall(BETA),[])

    def test_mutated_scope_cannot_leak_to_another_session(self):
        second=self.s.new_session()
        self.mutate('UPDATE memories SET scope=? WHERE id=?',('global',self.mid))
        self.assertEqual(self.recall(ALPHA,second),[])

    def test_mutated_kind_cannot_relabel_a_human_correction(self):
        self.mutate('UPDATE memories SET kind=? WHERE id=?',('preference',self.mid))
        self.assertEqual(self.recall(ALPHA),[])

    def test_mutated_memory_record_key_cannot_authorize_retargeting(self):
        self.mutate("UPDATE packets SET payload=json_set(payload,'$.key',?) WHERE kind='MemoryRecord' AND json_extract(payload,'$.memory_id')=?",(BETA,self.mid))
        self.assertEqual(self.recall(ALPHA),[])

    def test_missing_memory_record_does_not_leave_unbound_value_live(self):
        self.mutate("DELETE FROM packets WHERE kind='MemoryRecord' AND json_extract(payload,'$.memory_id')=?",(self.mid,))
        self.assertEqual(self.recall(ALPHA),[])


if __name__=='__main__':
    unittest.main()
