import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from model_probe import validate_model, probe, evaluate_output

class ProbeTests(unittest.TestCase):
    def test_hash_and_role_guard(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'test.gguf'; p.write_bytes(b'abc')
            registry = {'models': {'language': {'model_id':'test', 'revision':'rev', 'license_id':'test', 'files':[{'local_name':'test.gguf','size':3,'sha256':hashlib.sha256(b'abc').hexdigest()}]}}}
            self.assertEqual(validate_model(registry,'language',p)['revision'],'rev')
            p.write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError,'sha256'): validate_model(registry,'language',p)
            with self.assertRaises(KeyError): validate_model(registry,'body',p)
            p.unlink(); p.symlink_to(Path(d)/'other.gguf')
            with self.assertRaisesRegex(ValueError,'symlink'): validate_model(registry,'language',p)
            p.unlink(); p.write_bytes(b'abc')
            registry['models']['language']['license_id'] = ''
            with self.assertRaisesRegex(ValueError,'provenance'): validate_model(registry,'language',p)

    def test_process_and_timeout(self):
        self.assertEqual(probe('/bin/true','/tmp/none','x',2,1,1,'4')['status'],'NO_VISIBLE_OUTPUT')
        self.assertEqual(probe('/bin/false','/tmp/none','x',2,1,1)['status'],'PROCESS_FAIL')
        with tempfile.TemporaryDirectory() as d:
            script = Path(d)/'slow.sh'
            script.write_text('#!/bin/sh\nsleep 2\n')
            script.chmod(0o700)
            self.assertEqual(probe(script,'/tmp/none','x',0.01,1,1)['status'],'TIMEOUT')
            good = Path(d)/'good.sh'
            good.write_text('#!/bin/sh\nprintf "2+2=4"\n')
            good.chmod(0o700)
            self.assertEqual(probe(good,'/tmp/none','2+2=',2,1,1,'4')['status'],'ANSWER_CORRECT')

    def test_grade_negative_controls(self):
        self.assertEqual(evaluate_output('2+2=4','2+2=','4')['status'],'ANSWER_CORRECT')
        for output in ('2+2=2','2+2=24','2+2=The answer is 4','2+2='):
            self.assertNotEqual(evaluate_output(output,'2+2=','4')['status'],'ANSWER_CORRECT')
        self.assertEqual(evaluate_output('2+2=4','2+2=',None)['status'],'OUTPUT_UNGRADED')

    def test_resource_and_prompt_guards(self):
        for timeout, threads, predict in [(0,1,1),(301,1,1),(1,0,1),(1,17,1),(1,1,0),(1,1,513)]:
            with self.assertRaisesRegex(ValueError,'resource'): probe('/bin/true','x','x',timeout,threads,predict)
        with self.assertRaisesRegex(ValueError,'prompt'): probe('/bin/true','x','a'*2049,1,1,1)

if __name__ == '__main__': unittest.main()
