"""Run117BO real SQLite USER SourceRef JEF/C3 budget formatter, zero authority."""
from pathlib import Path
import hashlib
import json
import sqlite3
import tempfile
import unittest

from v13.config import initialize
from v13.store import Store
from v13.agi import jef_c3_budget_formatter_shadow_run117bo as adapter

FIXTURE=Path(__file__).resolve().parents[1]/'docs/fixtures/run46b_jef_source_eligibility_seed401.json'
FIXTURE_SHA='8aa69cc86d2e2067e809d4f703ddbff3fc575ea111d7afd97a73012e0bda0e21'


class BudgetFormatter(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.home=Path(self.tmp.name)
        initialize(self.home)
        self.s=Store(self.home)
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),FIXTURE_SHA)
        self.rows=json.loads(FIXTURE.read_text())['fixtures']

    def tearDown(self):
        self.s.close()
        self.tmp.cleanup()

    def pair(self,index=0,session=None):
        session=session or self.s.new_session()
        row=self.rows[index]
        prior=self.s.event(session,row['prior'])['source_ref']
        current=self.s.event(session,row['current'])['source_ref']
        return session,prior,current,row['oracle']

    def call(self,pair,callback,**kw):
        session,prior,current,_=pair
        return adapter.format_shadow(self.s,session,prior,current,callback,
                                     operator_opt_in=True,callback_opt_in=True,**kw)

    def echo(self,messages,schema):
        self.assertEqual(schema,adapter.SCHEMA)
        self.assertEqual([x['role'] for x in messages],['system','user'])
        packet=json.loads(messages[1]['content'])
        self.assertEqual(packet['candidate_authority'],0)
        return json.dumps(packet['typed_jef_candidate'])

    def safe(self,result):
        self.assertEqual(result['delivery_authority'],0)
        self.assertFalse(result['output_committed'])
        self.assertEqual(result['tool_dispatches'],0)
        self.assertEqual(result['learning_authority'],0)
        self.assertFalse(result['native_proof'])
        self.assertEqual(result['jepa_weight'],0)
        self.assertEqual(result['age0'],'RECORD_ONLY')
        self.assertEqual(result['step2'],'UTILITY_FAIL')
        self.assertFalse(result['whole_system_complete'])
        self.assertNotIn('raw_output',result)
        self.assertNotIn('typed_jef_candidate',result)

    def test_off_requires_both_explicit_optins(self):
        calls=[]
        def fail(*_):calls.append(True);raise AssertionError('called')
        for kw in ({},{'operator_opt_in':True},{'callback_opt_in':True},
                   {'operator_opt_in':1,'callback_opt_in':True}):
            r=adapter.format_shadow(None,None,None,None,fail,**kw)
            self.assertEqual(r['status'],'OFF');self.safe(r)
        self.assertFalse(calls)

    def test_six_frozen_source_bound_candidates_match(self):
        for i in range(6):
            with self.subTest(i=i):
                p=self.pair(i)
                before=self.s.db.total_changes
                r=self.call(p,self.echo)
                self.assertEqual(r['status'],'FORMATTER_MATCH_SHADOW')
                self.assertTrue(r['formatter_match'])
                self.assertTrue(r['source_rechecked'])
                self.assertEqual(len(r['source_ref_sha256']),2)
                self.assertEqual(self.s.db.total_changes,before)
                self.safe(r)

    def test_none_unknown_semantics_and_wrong_remaining(self):
        none=next(i for i,x in enumerate(self.rows) if x['oracle']['choice']=='NONE')
        unknown=next(i for i,x in enumerate(self.rows) if x['oracle']['choice']=='UNKNOWN')
        for index in (none,unknown):
            p=self.pair(index)
            bad=lambda *_:json.dumps({'choice':p[3]['choice'],'remaining':1})
            r=self.call(p,bad)
            self.assertEqual(r['status'],'FORMATTER_SEMANTIC_RED')
            self.assertTrue(r['source_only_fallback']);self.safe(r)

    def test_wrong_candidate_is_mismatch_not_permission(self):
        p=self.pair()
        r=self.call(p,lambda *_:'{"choice":"B","remaining":3}')
        self.assertEqual(r['status'],'FORMATTER_MISMATCH_RED')
        self.assertTrue(r['source_only_fallback']);self.safe(r)

    def test_json_and_output_shape_fail_closed(self):
        p=self.pair()
        for raw in ('{"choice":"A","choice":"B","remaining":18}',
                    '{"choice":"A","remaining":NaN}',
                    '{"choice":"A","remaining":true}',
                    '{"choice":"A","remaining":18,"extra":0}',
                    'not JSON',None,b'bytes','x'*513,''):
            with self.subTest(raw=str(raw)[:30]):
                r=self.call(p,lambda *_:raw)
                self.assertIn(r['status'],('FORMATTER_JSON_RED','FORMATTER_OUTPUT_SHAPE_RED',
                                          'FORMATTER_SEMANTIC_RED'))
                self.assertTrue(r['source_only_fallback']);self.safe(r)

    def test_stale_reversed_foreign_and_partial_refs(self):
        p=self.pair()
        sess,prior,current,_=p
        self.s.event(sess,'Later user message')
        self.assertEqual(self.call(p,self.echo)['status'],'SOURCE_PREFLIGHT_RED')
        p=self.pair()
        sess,prior,current,_=p
        self.assertEqual(self.call((sess,current,prior,p[3]),self.echo)['status'],'SOURCE_PREFLIGHT_RED')
        self.assertEqual(self.call((self.s.new_session(),prior,current,p[3]),self.echo)['status'],'SOURCE_PREFLIGHT_RED')
        self.assertEqual(self.call((sess,dict(prior,char_start=1),current,p[3]),self.echo)['status'],'SOURCE_PREFLIGHT_RED')

    def test_deleted_source_fails_before_callback(self):
        p=self.pair()
        with self.s.tx() as c:c.execute('UPDATE sources SET deleted=1 WHERE id=?',(p[1]['source_id'],))
        self.assertEqual(self.call(p,self.echo)['status'],'SOURCE_PREFLIGHT_RED')

    def test_callback_store_mutation_denied(self):
        p=self.pair()
        def mutate(*_):
            self.s.event(p[0],'newer user message')
            return json.dumps(p[3])
        r=self.call(p,mutate)
        self.assertEqual(r['status'],'CALLBACK_STORE_MUTATION_RED');self.safe(r)

    def test_callback_update_then_restore_denied(self):
        p=self.pair()
        title=self.s.one('SELECT title FROM sessions WHERE id=?',(p[0],))['title']
        def mutate(*_):
            self.s.db.execute('UPDATE sessions SET title=? WHERE id=?',('temporary',p[0]))
            self.s.db.execute('UPDATE sessions SET title=? WHERE id=?',(title,p[0]))
            return json.dumps(p[3])
        r=self.call(p,mutate)
        self.assertEqual(r['status'],'CALLBACK_STORE_MUTATION_RED');self.safe(r)

    def test_external_commit_denied(self):
        p=self.pair()
        path=self.home/'data/db/brain.sqlite3'
        def mutate(*_):
            with sqlite3.connect(path,timeout=5) as db:
                db.execute('UPDATE sessions SET title=? WHERE id=?',('external',p[0]))
            return json.dumps(p[3])
        r=self.call(p,mutate)
        self.assertEqual(r['status'],'CALLBACK_STORE_MUTATION_RED');self.safe(r)

    def test_blob_tamper_during_callback_denied(self):
        p=self.pair()
        def mutate(*_):
            (self.home/'data/blobs'/p[1]['sha256']).write_bytes(b'corrupt')
            return json.dumps(p[3])
        r=self.call(p,mutate)
        self.assertEqual(r['status'],'POST_CALLBACK_SOURCE_RED');self.safe(r)

    def test_mutated_prompt_schema_and_exception_denied(self):
        p=self.pair()
        def mutate(messages,schema):
            messages[1]['content']='forged'
            schema['required'].append('forged')
            return json.dumps(p[3])
        self.assertEqual(self.call(p,mutate)['status'],'CALLBACK_INPUT_MUTATED_RED')
        def boom(*_):raise RuntimeError('sensitive value not logged')
        r=self.call(p,boom)
        self.assertEqual(r['status'],'CALLBACK_RED')
        self.assertNotIn('sensitive value',json.dumps(r));self.safe(r)

    def test_unserializable_callback_mutation_is_red_not_exception(self):
        p=self.pair()
        def mutate(messages,schema):
            messages.append(object())
            return json.dumps(p[3])
        r=self.call(p,mutate)
        self.assertEqual(r['status'],'CALLBACK_INPUT_MUTATED_RED');self.safe(r)

    def test_approval_receipt_never_supported(self):
        p=self.pair()
        self.assertEqual(self.call(p,self.echo,approval_receipt={'ok':True})['status'],
                         'REAL_TTY_APPROVAL_UNSUPPORTED')


if __name__=='__main__':unittest.main()
