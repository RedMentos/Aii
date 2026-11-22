"""Explicit verified exact F1/F5 source answer; no C3 generation or learned authority."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from v13.runtime import Runtime
from v13.operator import Operator
from scripts import ask_verified_budget as V


class VerifiedExactBudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.r=Runtime(Path(self.tmp.name))
        self.op=Operator(self.r)
    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()
    def add(self,key='Project Elyra budget',value='615 Euro'):
        e=self.r.store.event(self.r.session,key)
        mid=self.r.memory.feedback(e['event_id'],'fact',value,key=key,permission='record')
        return self.r.memory.candidate(mid,self.r.session)
    def test_exact_english_source_is_not_model_generated(self):
        self.add()
        with patch.object(self.r.pool,'get',side_effect=AssertionError('C3 native called')):
            got=json.loads(self.op.run(':verified exact What is the budget for Project Elyra?'))
        self.assertEqual(got['status'],'FINAL_SOURCE_EXACT')
        self.assertEqual(got['answer'],'Project Elyra: 615 Euro.')
        self.assertEqual(got['authority'],'EXACT_SOURCE')
        self.assertFalse(got['model_called'])
        self.assertFalse(got['learned'])
        self.assertEqual(got['native_calls'],0)
        self.assertEqual(self.r.cfg['learning_mode'],'RECORD_ONLY')
    def test_exact_german_source_and_question(self):
        self.add(key='Projekt Elyra budget',value='75 Euro')
        got=json.loads(self.op.run(':verified exact Wie hoch ist das Budget von Projekt Elyra?'))
        self.assertEqual(got['status'],'FINAL_SOURCE_EXACT')
        self.assertEqual(got['answer'],'Projekt Elyra: 75 Euro.')
        self.assertFalse(got['model_called'])
    def test_missing_conflicting_and_revoked_sources_never_answer(self):
        q=':verified exact What is the budget for Project Elyra?'
        self.assertEqual(json.loads(self.op.run(q))['status'],'CLARIFY')
        first=self.add()
        self.add(key='Project Elyra budgets',value='700 Euro')
        self.assertEqual(json.loads(self.op.run(q))['status'],'CLARIFY')
        self.r.memory.forget(first['id'])
        self.assertEqual(json.loads(self.op.run(q))['status'],'FINAL_SOURCE_EXACT')
    def test_revocation_between_checks_suppresses_exact_answer(self):
        row=self.add()
        original=V._preflight
        calls=[0]
        def changed(*args,**kwargs):
            calls[0]+=1
            if calls[0]==2:self.r.memory.forget(row['id'])
            return original(*args,**kwargs)
        with patch.object(V,'_preflight',side_effect=changed):
            got=V.exact_source(self.r,'What is the budget for Project Elyra?')
        self.assertEqual(got['status'],'CLARIFY')
        self.assertNotIn('answer',got)
    def test_default_verified_remains_preflight_only(self):
        self.add()
        got=json.loads(self.op.run(':verified What is the budget for Project Elyra?'))
        self.assertEqual(got['status'],'READY')
        self.assertNotIn('answer',got)
        with self.assertRaises(ValueError):self.op.run(':verified exact')


if __name__=='__main__':unittest.main()
