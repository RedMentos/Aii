"""Run273: B4 persisted MEMORY slots must retain F5 human authority.

Actual Runtime/SQLite and synthetic text only; no native model or Redmi.
"""
import tempfile
from pathlib import Path
import unittest
from v13.runtime import Runtime
from v13.focal import Workspace,item,boundary


class FocalMemoryAuthorityRun273(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name)
        self.r=Runtime(self.home);self.s=self.r.store;self.session=self.r.session
        self.e=self.s.event(self.session,'Project Focal budget')
        self.mid=self.r.memory.feedback(self.e['event_id'],'fact','123 credits',key='Project Focal budget')
        self.sid=self.s.one('SELECT source_id FROM memories WHERE id=?',(self.mid,))['source_id']
        self.w=Workspace(self.s,self.session)
        m=self.r.memory.recall('Project Focal budget',self.session)[0]
        self.x=self.slot(m,self.e)
        self.w.save(self.e,[self.x],[],4)
        self.next=self.s.event(self.session,'Focal continuation')

    def tearDown(self):self.r.close();self.tmp.cleanup()

    def slot(self,m,e):
        return item('MEMORY',m['id'],[m['source_ref']],m['value'],e['event_id'],uncertainty=.2,
                    salience=0.,goal=.7,utility=.4,sq=1.,status='MEMORY_SOURCE',self_generated=False,
                    bounds=boundary(self.s,[m['source_ref']]))

    def change(self,sql,args=()):
        with self.s.tx() as conn:conn.execute(sql,args)

    def load(self):return self.w.load(self.next)

    def test_valid_focal_memory_survives_restart(self):
        self.assertEqual([(x['payload_ref'],x['text']) for x in self.load()],[(self.mid,'123 credits')])
        self.r.close();self.r=Runtime(self.home);self.s=self.r.store;self.w=Workspace(self.s,self.session)
        self.assertEqual([x['payload_ref'] for x in self.load()],[self.mid])

    def test_deleted_human_decision_cannot_reenter_focal(self):
        self.change("DELETE FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.source_ref.source_id')=?",(self.sid,))
        self.assertEqual(self.load(),[])

    def test_deleted_feedback_cannot_reenter_focal(self):
        self.change('DELETE FROM feedback WHERE source_id=?',(self.sid,))
        self.assertEqual(self.load(),[])

    def test_nonhuman_source_kind_cannot_reenter_focal(self):
        self.change('UPDATE sources SET kind=? WHERE id=?',('REPLAY_HYPOTHESIS',self.sid))
        self.assertEqual(self.load(),[])

    def test_duplicate_human_decision_cannot_reenter_focal(self):
        row=self.s.one("SELECT id FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.source_ref.source_id')=?",(self.sid,))
        self.change('INSERT INTO packets SELECT ?,kind,event_id,generation_id,payload,created FROM packets WHERE id=?',('pkt-run273-duplicate',row['id']))
        self.assertEqual(self.load(),[])

    def test_slot_source_ref_retargeting_to_readable_foreign_source_is_refused(self):
        foreign=self.s.source('123 credits','HUMAN_DECISION')
        st,version=self.s.state(self.w.key)
        st['slots'][0]['source_refs']=[foreign]
        self.s.set_state(self.w.key,st,expected=version)
        self.assertEqual(self.load(),[])

    def test_independent_valid_focal_slot_survives_first_revocation(self):
        e2=self.s.event(self.session,'Project Focal funding')
        mid2=self.r.memory.feedback(e2['event_id'],'fact','42 credits',key='Project Focal funding')
        m2=self.r.memory.recall('Project Focal funding',self.session)[0]
        self.w.save(e2,[self.x,self.slot(m2,e2)],[],4)
        self.next=self.s.event(self.session,'next again')
        self.change("DELETE FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.source_ref.source_id')=?",(self.sid,))
        self.assertEqual([x['payload_ref'] for x in self.load()],[mid2])


if __name__=='__main__':unittest.main()
