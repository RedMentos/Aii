import hashlib
import tempfile
import unittest
from pathlib import Path
from model_probe import validate_model, probe

class ProbeTests(unittest.TestCase):
    def test_hash_and_role_guard(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'test.gguf'; p.write_bytes(b'abc')
            registry = {'models': {'language': {'model_id':'test', 'revision':'rev', 'license_id':'test', 'files':[{'local_name':'test.gguf','size':3,'sha256':hashlib.sha256(b'abc').hexdigest()}]}}}
            self.assertEqual(validate_model(registry,'language',p)['revision'],'rev')
            p.write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError,'sha256'): validate_model(registry,'language',p)
            with self.assertRaises(KeyError): validate_model(registry,'body',p)
    def test_process_and_timeout(self):
        self.assertEqual(probe('/bin/true','/tmp/none','x',2,1,1)['status'],'PASS')
        self.assertEqual(probe('/bin/false','/tmp/none','x',2,1,1)['status'],'FAIL')

if __name__ == '__main__': unittest.main()
