import unittest
from model_registry_probe import audit

class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.m = {'models': {r: {'model_id': r, 'revision': 'a'*40,
            'license_id': 'Apache-2.0', 'license_url': 'https://example.org/license',
            'quant_format': 'Q4', 'files': [{'size': 100, 'sha256': 'b'*64}],
            'platforms': {'android-arm64': []}} for r in ('language','body','gist','needle')}}
    def test_read_only_no_measurement_claim(self):
        rows = audit(self.m)
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r['native_ttft_ms'] is None and not r['redmi_verified'] for r in rows))
    def test_revision_mismatch(self):
        self.assertEqual(audit(self.m, {'body': {'exact_revision':'old','download_complete':True}})[1]['slot_status'], 'REVISION_MISMATCH')
    def test_missing_android_artifact(self):
        del self.m['models']['needle']['platforms']
        self.assertIn('ANDROID_ARM64_ARTIFACT_MISSING', audit(self.m)[3]['warnings'])
    def test_missing_license(self):
        del self.m['models']['gist']['license_id']
        self.assertIn('MISSING_PROVENANCE', audit(self.m)[2]['warnings'])

if __name__ == '__main__': unittest.main()
