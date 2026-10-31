"""Synthetic fail-closed tests; no native model or actual V13 runtime invoked."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'jef_fullsuite_parent_compare.py'
spec = importlib.util.spec_from_file_location('jef_fullsuite_parent_compare', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture(path, head, n=20, failure='test_case', *, bad_manifest=False,
            duplicate=False, missing_stage=None, zip_symlink=False):
    report = ('.'*n + '\n' + '='*70 + '\nERROR: '+failure+' (suite.Case)\n'
              + '-'*70 + '\nTraceback (most recent call last):\n'
              + 'ValueError: frozen-source-mismatch\n\n'
              + '-'*70 + '\nRan '+str(n)+' tests in 1.0s\n\n'
              + 'FAILED (failures=0, errors=1, skipped=0)\n')
    members = {'HEAD.txt': head+'\n', 'FULL_EXIT.txt': '1\n', 'FULL_RAW.log': report}
    members.update({s+'_EXIT.txt': ('1\n' if s == missing_stage else '0\n') for s in mod.STAGES})
    manifest = ''.join(hashlib.sha256(v.encode()).hexdigest()+'  ./'+k+'\n'
                       for k,v in sorted(members.items()))
    if bad_manifest:
        manifest = '0'+manifest[1:]
    members['SHA256SUMS'] = manifest
    with zipfile.ZipFile(path,'w') as z:
        for k,v in members.items():
            if zip_symlink and k == 'HEAD.txt':
                info = zipfile.ZipInfo(k)
                info.create_system = 3
                info.external_attr = (0o120777 << 16)
                z.writestr(info, v)
            else:
                z.writestr(k,v)
        if duplicate:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                z.writestr('HEAD.txt',head+'\n')
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Audit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.a = Path(self.tmp.name)/'a.zip'
        self.b = Path(self.tmp.name)/'b.zip'
        self.ah = 'a'*40
        self.bh = 'b'*40

    def build(self, **kw):
        sha = fixture(self.a,self.ah,**kw)
        return mod.read_bundle(self.a,sha,self.ah)

    def test_identical_fingerprint_extra_tests_still_red(self):
        a=self.build()
        bsha=fixture(self.b,self.bh,n=24)
        b=mod.read_bundle(self.b,bsha,self.bh)
        result=mod.compare(a,b,4)
        self.assertEqual(result['status'],'MATCHING_RETAINED_FAILURE_HEADERS_NOT_A_GREEN_SUITE')
        self.assertEqual(result['errors'],1)
        self.assertIn('no proof',result['claim_limit'])

    def test_changed_error_rejected(self):
        a=self.build()
        bsha=fixture(self.b,self.bh,n=24,failure='different_test')
        b=mod.read_bundle(self.b,bsha,self.bh)
        with self.assertRaisesRegex(ValueError,'fingerprint'):
            mod.compare(a,b,4)

    def test_test_count_mismatch_rejected(self):
        a=self.build()
        bsha=fixture(self.b,self.bh,n=23)
        with self.assertRaisesRegex(ValueError,'test-count'):
            mod.compare(a,mod.read_bundle(self.b,bsha,self.bh),4)

    def test_sha_and_head_binding(self):
        sha=fixture(self.a,self.ah)
        with self.assertRaisesRegex(ValueError,'ZIP SHA256'):
            mod.read_bundle(self.a,'0'*64,self.ah)
        with self.assertRaisesRegex(ValueError,'tested HEAD'):
            mod.read_bundle(self.a,sha,self.bh)

    def test_manifest_tamper_rejected(self):
        sha=fixture(self.a,self.ah,bad_manifest=True)
        with self.assertRaisesRegex(ValueError,'member hash'):
            mod.read_bundle(self.a,sha,self.ah)

    def test_duplicate_member_rejected(self):
        sha=fixture(self.a,self.ah,duplicate=True)
        with self.assertRaisesRegex(ValueError,'duplicate'):
            mod.read_bundle(self.a,sha,self.ah)

    def test_symlink_rejected(self):
        sha=fixture(self.a,self.ah,zip_symlink=True)
        with self.assertRaisesRegex(ValueError,'unsafe ZIP'):
            mod.read_bundle(self.a,sha,self.ah)

    def test_failed_prerequisite_rejected(self):
        sha=fixture(self.a,self.ah,missing_stage='PRIVACY')
        with self.assertRaisesRegex(ValueError,'PRIVACY prerequisite'):
            mod.read_bundle(self.a,sha,self.ah)

    def test_corrupted_zip_rejected(self):
        self.a.write_bytes(b'not a zip')
        with self.assertRaises(zipfile.BadZipFile):
            mod.read_bundle(self.a,hashlib.sha256(self.a.read_bytes()).hexdigest(),self.ah)

    def test_missing_manifest_rejected(self):
        with zipfile.ZipFile(self.a,'w') as z:
            z.writestr('HEAD.txt',self.ah)
        with self.assertRaisesRegex(ValueError,'missing SHA256SUMS'):
            mod.read_bundle(self.a,hashlib.sha256(self.a.read_bytes()).hexdigest(),self.ah)


if __name__=='__main__':
    unittest.main()
