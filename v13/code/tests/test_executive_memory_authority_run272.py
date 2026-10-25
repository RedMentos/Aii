"""Run272: persisted JEF memory/report must retain F5 human decision authority.

Actual Runtime + SQLite, synthetic text, no model/native/Redmi.
"""
import tempfile
from pathlib import Path
import unittest
from v13.runtime import Runtime


class ExecutiveMemoryAuthorityRun272(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.home=Path(self.tmp.name)
        self.r=Runtime(self.home)
        self.s=self.r.store
        self.session=self.r.session
        self.e=self.s.event(self.session,'Project Vega budget')
        self.r.executive.begin(self.e,self.session,self.r.cfg)
        self.mid=self.r.memory.feedback(self.e['event_id'],'fact','700 credits',key='Project Vega budget')
        self.sid=self.s.one('SELECT source_id FROM memories WHERE id=?',(self.mid,))['source_id']
        memories=self.r.memory.recall('Project Vega budget',self.session)
        self.assertEqual([m['id'] for m in memories],[self.mid])
        self.r.executive.update(self.e,self.session,memories=memories)
        self.r.executive.snapshot(self.e,self.session,memories)

    def tearDown(self):
        self.r.close();self.tmp.cleanup()

    def change(self,sql,args=()):
        with self.s.tx() as conn:conn.execute(sql,args)

    def assert_no_stale_correction(self):
        self.assertEqual(self.r.memory.recall('Project Vega budget',self.session),[])
        self.assertEqual(self.r.executive.view(self.session)['memory_refs'],[])
        self.assertNotIn('700 credits',self.r.executive.report(self.session,self.e))

    def test_valid_correction_is_available_after_restart(self):
        self.assertIn('700 credits',self.r.executive.report(self.session,self.e))
        self.r.close();self.r=Runtime(self.home);self.s=self.r.store
        self.assertEqual(self.r.executive.view(self.session)['memory_refs'][0]['memory_id'],self.mid)
        self.assertIn('700 credits',self.r.executive.report(self.session,self.e))

    def test_deleted_human_decision_cannot_survive_in_jef_snapshot(self):
        self.change("DELETE FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.source_ref.source_id')=?",(self.sid,))
        self.assert_no_stale_correction()

    def test_deleted_feedback_cannot_survive_in_jef_snapshot(self):
        self.change('DELETE FROM feedback WHERE source_id=?',(self.sid,))
        self.assert_no_stale_correction()

    def test_nonhuman_source_kind_cannot_survive_in_jef_snapshot(self):
        self.change('UPDATE sources SET kind=? WHERE id=?',('REPLAY_HYPOTHESIS',self.sid))
        self.assert_no_stale_correction()

    def test_duplicated_human_decision_cannot_survive_in_jef_snapshot(self):
        row=self.s.one("SELECT id FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.source_ref.source_id')=?",(self.sid,))
        self.change('INSERT INTO packets SELECT ?,kind,event_id,generation_id,payload,created FROM packets WHERE id=?',('pkt-run272-duplicate',row['id']))
        self.assert_no_stale_correction()

    def test_another_valid_memory_survives_invalid_first_memory(self):
        e2=self.s.event(self.session,'Project Vega funding')
        mid2=self.r.memory.feedback(e2['event_id'],'fact','42 credits',key='Project Vega funding')
        self.r.executive.update(self.e,self.session,memories=self.r.memory.recall('Project Vega funding',self.session))
        self.change("DELETE FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.source_ref.source_id')=?",(self.sid,))
        view=self.r.executive.view(self.session)
        self.assertEqual([m['memory_id'] for m in view['memory_refs']],[mid2])


if __name__=='__main__':unittest.main()
