import unittest
from model_registry_audit import audit

class AuditTests(unittest.TestCase):
    def setUp(self):
        self.valid = {'models': {'language': {'model_id':'test','revision':'abc','license_id':'test-license','license_url':'https://example.org/license','main_file':'x.gguf','files':[{'local_name':'x.gguf','sha256':'a'*64,'size':100,'url':'https://example.org/x'}]}}}
    def test_valid(self):
        self.assertEqual(audit(self.valid)['status'], 'PASS')
    def test_missing_license(self):
        self.valid['models']['language'].pop('license_id')
        self.assertIn('MISSING_LICENSE_ID', [i['code'] for i in audit(self.valid)['issues']])
    def test_bad_hash(self):
        self.valid['models']['language']['files'][0]['sha256']='bad'
        self.assertIn('INVALID_SHA256', [i['code'] for i in audit(self.valid)['issues']])
    def test_main_missing(self):
        self.valid['models']['language']['main_file']='wrong.gguf'
        self.assertIn('MAIN_FILE_NOT_LISTED', [i['code'] for i in audit(self.valid)['issues']])
    def test_invalid_file_list(self):
        self.valid['models']['language']['files']='bad'
        self.assertEqual(audit(self.valid)['status'], 'FAIL')

if __name__=='__main__': unittest.main()
