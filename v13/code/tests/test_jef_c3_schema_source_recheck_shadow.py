"""Real Store, default-OFF JEF/C3 schema adapter tests; no native model."""
import json
import sqlite3
from pathlib import Path
import tempfile
import unittest

from scripts import jef_c3_schema_fixture_727 as f
from scripts import jef_c3_c5_c6_operator_cli as cli
from v13 import jef_c3_schema_source_recheck_shadow as adapter
from v13.common import dumps

class Adapter(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.r=cli.Runtime(Path(self.tmp.name))
        self.row=f.fixtures()[0]

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def record(self,key,value):
        e=self.r.store.event(self.r.session,'Record: '+key)
        mid=self.r.memory.feedback(e['event_id'],'fact',value,
                                   permission='record',key=key,scope='session')
        self.r.memory.candidate(mid,self.r.session)
        return mid

    def source(self,row=None):
        row=row or self.row
        project,domain=row['project'],row['domain']
        ids=[self.record(f'Project {project} archived {domain} policy',row['policy_source']),
             self.record(f'Project {project} latest {domain} option sheet',row['sheet_source'])]
        event=self.r.store.event(self.r.session,row['current'])
        return event,ids

    def invoke(self,event,ids,callback,**kw):
        return adapter.format_schema_shadow(self.r.memory,self.r.session,
            event['event_id'],event['source_ref'],ids,callback,
            operator_opt_in=True,callback_opt_in=True,**kw)

    def assert_safe(self,r):
        self.assertEqual(r['delivery_authority'],0)
        self.assertFalse(r['output_committed'])
        self.assertEqual(r['tool_dispatches'],0)
        self.assertEqual(r['learning_authority'],0)
        self.assertFalse(r['real_tty_approved'])
        self.assertFalse(r['native_proof'])
        self.assertEqual(r['age0'],'RECORD_ONLY')
        self.assertEqual(r['step2'],'UTILITY_FAIL')
        self.assertEqual(r['jepa_weight'],0)
        self.assertNotIn('raw_output',r)
        self.assertNotIn('policy_source',r)
        self.assertNotIn('sheet_source',r)

    def test_schema_matches_native_frozen_run68(self):
        self.assertEqual(adapter.SCHEMA,f.SCHEMA)
        self.assertEqual(adapter.SCHEMA_SHA256,
                         adapter._sha(dumps(f.SCHEMA).encode()))

    def test_off_requires_exact_two_optins_no_callback(self):
        calls=[]
        def callback(*a):calls.append(a);raise AssertionError('CALLED')
        for kwargs in ({},{'operator_opt_in':1,'callback_opt_in':True},
                       {'operator_opt_in':True,'callback_opt_in':1}):
            r=adapter.format_schema_shadow(None,None,None,None,None,callback,**kwargs)
            self.assertEqual(r['status'],'OFF');self.assert_safe(r)
        self.assertEqual(calls,[])

    def test_valid_real_store_source_recheck_six_cases(self):
        for row in f.fixtures():
            event,ids=self.source(row)
            before=self.r.store.one('SELECT COUNT(*) AS n FROM messages')['n']
            def callback(messages,schema):
                self.assertEqual(schema,f.SCHEMA)
                self.assertEqual(len(messages),2)
                self.assertEqual(json.loads(messages[1]['content'])['typed_jef_action'],row['expected'])
                return json.dumps({'action':row['expected']})
            result=self.invoke(event,ids,callback)
            self.assertEqual(result['status'],'FORMATTER_MATCH_SHADOW')
            self.assertTrue(result['formatter_match'])
            self.assertTrue(result['source_rechecked'])
            self.assertEqual(result['typed_jef_action'],row['expected'])
            self.assertFalse(result['source_only_fallback'])
            self.assertEqual(self.r.store.one('SELECT COUNT(*) AS n FROM messages')['n'],before)
            self.assertEqual(self.r.store.one('SELECT COUNT(*) AS n FROM actions')['n'],0)
            self.assert_safe(result)

    def test_wrong_and_malformed_json_fallback_without_authority(self):
        event,ids=self.source()
        for output,status in ((json.dumps({'action':'B'}),'FORMATTER_ACTION_MISMATCH_RED'),
                              ('Option A','FORMATTER_JSON_RED'),
                              ('{"action":"A","action":"B"}','FORMATTER_JSON_RED'),
                              ('{"action":"A","extra":1}','FORMATTER_JSON_RED'),
                              ('{"action":NaN}','FORMATTER_JSON_RED'),
                              ('{"action":1}','FORMATTER_JSON_RED')):
            with self.subTest(output=output):
                r=self.invoke(event,ids,lambda m,s:output)
                self.assertEqual(r['status'],status)
                self.assertTrue(r['source_only_fallback'])
                self.assertTrue(r['source_rechecked'])
                self.assert_safe(r)

    def test_nonstring_and_oversize_fail(self):
        event,ids=self.source()
        for value in (None,b'{"action":"A"}','x'*1025,''):
            r=self.invoke(event,ids,lambda m,s:value)
            self.assertEqual(r['status'],'FORMATTER_OUTPUT_SHAPE_RED')
            self.assert_safe(r)

    def test_callback_exception_red(self):
        event,ids=self.source()
        def boom(*a):raise RuntimeError('private details not echoed')
        r=self.invoke(event,ids,boom)
        self.assertEqual(r['status'],'CALLBACK_RED')
        self.assertEqual(r['error_type'],'RuntimeError')
        self.assertNotIn('private details',dumps(r))
        self.assert_safe(r)

    def test_schema_and_message_mutation_cannot_change_bound_original(self):
        event,ids=self.source()
        def mutate(messages,schema):
            messages[0]['content']='forged'
            schema['properties']['action']['enum'].append('UNKNOWN')
            return '{"action":"A"}'
        r=self.invoke(event,ids,mutate)
        self.assertEqual(r['status'],'FORMATTER_MATCH_SHADOW')
        self.assertEqual(adapter.SCHEMA,f.SCHEMA)
        self.assert_safe(r)

    def test_source_forget_during_callback_denies(self):
        event,ids=self.source()
        def forget(*a):
            self.r.memory.forget(ids[1]);return '{"action":"A"}'
        r=self.invoke(event,ids,forget)
        # Forget changes Store inventory; the earlier mutation guard fails shut.
        self.assertEqual(r['status'],'CALLBACK_STORE_MUTATION_RED')
        self.assertFalse(r['source_rechecked'])
        self.assert_safe(r)

    def test_unrelated_same_connection_update_denied_without_count_change(self):
        event,ids=self.source()
        before=adapter._footprint(self.r.memory)
        def mutate(*_):
            self.r.store.db.execute(
                "UPDATE sessions SET title=? WHERE id=?",
                ("unrelated changed title",self.r.session))
            self.assertEqual(adapter._footprint(self.r.memory),before)
            return '{"action":"A"}'
        result=self.invoke(event,ids,mutate)
        self.assertEqual(result['status'],'CALLBACK_STORE_MUTATION_RED')
        self.assertFalse(result['source_rechecked'])
        self.assert_safe(result)

    def test_same_connection_update_then_restore_denied(self):
        event,ids=self.source()
        before=adapter._footprint(self.r.memory)
        original=self.r.store.one(
            "SELECT title FROM sessions WHERE id=?",(self.r.session,))['title']
        def mutate(*_):
            self.r.store.db.execute(
                "UPDATE sessions SET title=? WHERE id=?",
                ("temporary mutation",self.r.session))
            self.r.store.db.execute(
                "UPDATE sessions SET title=? WHERE id=?",
                (original,self.r.session))
            self.assertEqual(adapter._footprint(self.r.memory),before)
            return '{"action":"A"}'
        result=self.invoke(event,ids,mutate)
        self.assertEqual(result['status'],'CALLBACK_STORE_MUTATION_RED')
        self.assert_safe(result)

    def test_other_connection_commit_denied_without_count_change(self):
        event,ids=self.source()
        before=adapter._footprint(self.r.memory)
        path=self.r.store.home/'data/db/brain.sqlite3'
        def mutate(*_):
            with sqlite3.connect(path,timeout=5) as other:
                other.execute("UPDATE sessions SET title=? WHERE id=?",
                              ("external mutation",self.r.session))
            self.assertEqual(adapter._footprint(self.r.memory),before)
            return '{"action":"A"}'
        result=self.invoke(event,ids,mutate)
        self.assertEqual(result['status'],'CALLBACK_STORE_MUTATION_RED')
        self.assert_safe(result)

    def test_new_user_event_during_callback_denies(self):
        event,ids=self.source()
        def new_user(*a):
            self.r.store.event(self.r.session,'Later user request')
            return '{"action":"A"}'
        r=self.invoke(event,ids,new_user)
        self.assertEqual(r['status'],'CALLBACK_STORE_MUTATION_RED')
        self.assert_safe(r)

    def test_swapped_foreign_and_approval_denied_before_callback(self):
        event,ids=self.source()
        def never(*a):raise AssertionError('callback should not run')
        self.assertEqual(self.invoke(event,ids[::-1],never)['status'],'SOURCE_ADMISSION_RED')
        self.assertEqual(self.invoke(event,[ids[0],ids[0]],never)['status'],'SOURCE_ADMISSION_RED')
        self.assertEqual(self.invoke(event,ids,never,approval_receipt={'approved':True})['status'],
                         'REAL_TTY_APPROVAL_UNSUPPORTED')

    def test_missing_callback_rejected(self):
        event,ids=self.source()
        r=self.invoke(event,ids,None)
        self.assertEqual(r['status'],'INVALID_CALLBACK')
        self.assert_safe(r)

if __name__=='__main__':unittest.main()
