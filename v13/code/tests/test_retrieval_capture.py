"""Synthetic collector guards only; these do not prove native model quality."""
import copy
import importlib.util
from pathlib import Path
import unittest

from v13.common import digest,dumps

spec=importlib.util.spec_from_file_location('retrieval_capture_fixture',Path(__file__).with_name('integration_retrieval.py'))
collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)

class RetrievalCaptureGuards(unittest.TestCase):
    def fixture(self):
        fixture={'input':'Projekt Kelmo16: Finanzrahmen?','key':'Projekt Kelmo16 Budget','value':'400 Euro','memory_id':'mem_fixture'}
        row={'topic':fixture['key'],'correction':fixture['value'],'matched_query':fixture['input']}
        messages=[{'role':'system','content':'Gespeicherte Nutzerkorrekturen (mit Thema): '+dumps([row])},
                  {'role':'user','content':fixture['input']}]
        capture={'role':'B1_DETAIL','messages':messages,'messages_sha256':digest(dumps(messages)),
                 'completed':True,'native_metrics':{'role':'B1_DETAIL','history_trimmed':False}}
        metadata={'memory_ids':['mem_fixture'],'context_source_refs':[{'id':'q'},{'id':'m'}]}
        sources={'q':fixture['input'],'m':fixture['value']}
        return capture,fixture,metadata,lambda ref:sources[ref['id']]

    def test_observer_preserves_message_identity_arguments_and_tokens(self):
        calls=[];records=[];saves=[]
        class Runner:
            role='B1_DETAIL';last_metrics={}
            def generate(self,messages,*args,**kwargs):
                calls.append((messages,args,kwargs));yield '400';yield ' Euro'
                self.last_metrics={'role':self.role,'history_trimmed':False}
        runner=Runner();messages=[{'role':'user','content':'raw query'}];original=copy.deepcopy(messages)
        cancel=object();collector.capture_generation(runner,records,lambda:'NATIVE_ANSWER',lambda:saves.append(True))
        self.assertEqual(list(runner.generate(messages,cancel,123,max_tokens=64)),['400',' Euro'])
        self.assertIs(calls[0][0],messages);self.assertIs(calls[0][1][0],cancel)
        self.assertEqual(calls[0][1][1],123);self.assertEqual(calls[0][2],{'max_tokens':64})
        self.assertEqual(messages,original);self.assertEqual(records[0]['messages'],original)
        self.assertEqual(records[0]['messages_sha256'],digest(dumps(original)))
        self.assertTrue(records[0]['completed']);self.assertEqual(len(saves),2)

    def test_observer_retains_native_failure_without_marking_completed(self):
        class Runner:
            role='B1_DETAIL';last_metrics={'history_trimmed':False}
            def generate(self,*args,**kwargs):
                yield 'partial';raise RuntimeError('native interruption')
        records=[];runner=Runner();collector.capture_generation(runner,records,lambda:'NATIVE_ANSWER',lambda:None)
        stream=runner.generate([{'role':'user','content':'query'}]);self.assertEqual(next(stream),'partial')
        with self.assertRaisesRegex(RuntimeError,'native interruption'):next(stream)
        self.assertFalse(records[0]['completed']);self.assertEqual(records[0]['error_type'],'RuntimeError')

    def test_exact_context_and_lineage_pass_but_not_output_quality_claim(self):
        capture,fixture,metadata,read=self.fixture()
        audit=collector.audit_source_context(capture,fixture,metadata,read,'B1_DETAIL')
        self.assertTrue(audit['pass']);self.assertEqual(audit['source_errors'],[])
        self.assertNotIn('native_answer_correct',audit['checks'])

    def test_missing_binding_tamper_trimming_wrong_role_or_erased_source_refuse(self):
        capture,fixture,metadata,read=self.fixture()
        mutations=[('binding',lambda c:c['messages'][0].update(content='Gespeicherte Nutzerkorrekturen (mit Thema): '+dumps([{'topic':fixture['key'],'correction':'400 Euro'}]))),
                   ('query',lambda c:c['messages'][-1].update(content='other query')),
                   ('tamper',lambda c:c.update(messages_sha256='0'*64)),
                   ('trimming',lambda c:c['native_metrics'].update(history_trimmed=True)),
                   ('role',lambda c:c['native_metrics'].update(role='C3_LANGUAGE')),
                   ('incomplete',lambda c:c.update(completed=False))]
        for name,mutate in mutations:
            with self.subTest(name=name):
                changed=copy.deepcopy(capture);mutate(changed)
                self.assertFalse(collector.audit_source_context(changed,fixture,metadata,read,'B1_DETAIL')['pass'])
        def erased(ref):
            if ref['id']=='m':raise ValueError('erased correction')
            return read(ref)
        audit=collector.audit_source_context(capture,fixture,metadata,erased,'B1_DETAIL')
        self.assertFalse(audit['pass']);self.assertEqual(audit['source_errors'],['ValueError'])

if __name__=='__main__':unittest.main()
