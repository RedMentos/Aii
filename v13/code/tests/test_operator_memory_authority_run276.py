"""Run276: :memory must not show corrections without live F5 human authority.

Actual Runtime+Operator+SQLite, synthetic text; no native model or Redmi.
"""
import json
import tempfile
from pathlib import Path
import unittest
from v13.runtime import Runtime
from v13.operator import Operator


class OperatorMemoryAuthorityRun276(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name)
        self.r=Runtime(self.home);self.s=self.r.store;self.op=Operator(self.r)
        self.session=self.r.session
        self.e=self.s.event(self.session,'Project Gamma budget')
        self.mid=self.r.memory.feedback(self.e['event_id'],'fact','777 credits',key='Project Gamma budget')
        self.sid=self.s.one('SELECT source_id FROM memories WHERE id=?',(self.mid,))['source_id']

    def tearDown(self):self.r.close();self.tmp.cleanup()

    def change(self,sql,args=()):
        with self.s.tx() as conn:conn.execute(sql,args)

    def listed(self):return json.loads(self.op.run(':memory'))

    def test_valid_memory_is_listed_with_existing_schema_after_restart(self):
        self.assertEqual(self.listed(),[{'id':self.mid,'kind':'fact','scope':'session','key_text':'Project Gamma budget','value':'777 credits'}])
        self.r.close();self.r=Runtime(self.home);self.s=self.r.store;self.op=Operator(self.r)
        self.assertEqual([x['id'] for x in self.listed()],[self.mid])
        self.assertEqual(self.s.rows('SELECT * FROM updates'),[])

    def test_deleted_human_decision_is_not_listed(self):
        self.change("DELETE FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.source_ref.source_id')=?",(self.sid,))
        self.assertEqual(self.listed(),[])

    def test_deleted_feedback_is_not_listed(self):
        self.change('DELETE FROM feedback WHERE source_id=?',(self.sid,))
        self.assertEqual(self.listed(),[])

    def test_deleted_source_or_changed_kind_is_not_listed(self):
        self.change('UPDATE sources SET kind=? WHERE id=?',('REPLAY_HYPOTHESIS',self.sid))
        self.assertEqual(self.listed(),[])
        self.change('UPDATE sources SET kind=? WHERE id=?',('HUMAN_DECISION',self.sid))
        self.change('UPDATE sources SET deleted=1 WHERE id=?',(self.sid,))
        self.assertEqual(self.listed(),[])

    def test_mutated_memory_value_is_not_displayed(self):
        self.change('UPDATE memories SET value=? WHERE id=?',('999 credits',self.mid))
        self.assertEqual(self.listed(),[])

    def test_valid_independent_memory_survives_revocation(self):
        e2=self.s.event(self.session,'Project Delta budget')
        mid2=self.r.memory.feedback(e2['event_id'],'fact','42 credits',key='Project Delta budget')
        self.change("DELETE FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.source_ref.source_id')=?",(self.sid,))
        self.assertEqual([x['id'] for x in self.listed()],[mid2])

    def test_session_and_global_scope_are_respected(self):
        e2=self.s.event(self.session,'Global Project Budget')
        global_mid=self.r.memory.feedback(e2['event_id'],'fact','20 credits',key='Global Project Budget',scope='global')
        other=self.op.run(':new')
        self.assertNotEqual(other,self.session)
        self.assertEqual([x['id'] for x in self.listed()],[global_mid])
        self.assertEqual(self.op.run(':open '+self.session),self.session)
        self.assertEqual({x['id'] for x in self.listed()},{self.mid,global_mid})


if __name__=='__main__':unittest.main()
