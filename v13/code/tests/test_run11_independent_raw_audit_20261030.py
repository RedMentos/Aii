"""Adversarial read-only ZIP closure tests for Run11 independent audit."""
import hashlib
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile

from scripts import run11_independent_raw_audit_20261030 as m


class Run11IndependentAuditTests(unittest.TestCase):
    def archive(self, root, *, inner_tamper=False, missing=False, duplicate=False,
                traversal=False):
        p=Path(root)/'artifact.zip'
        contents={'TEST_RAW.log':'Ran 2 tests in 0.01s\n\nOK\n',
                  'TEST_EXIT.txt':'0\n', 'PINS_EXIT.txt':'0\n'}
        manifest=''.join(hashlib.sha256(v.encode()).hexdigest()+'  ./'+k+'\n'
                         for k,v in sorted(contents.items()))
        with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
            for name,value in contents.items():
                if missing and name=='TEST_EXIT.txt':
                    continue
                if inner_tamper and name=='TEST_RAW.log':
                    value+='FORGED'
                z.writestr(name,value)
            z.writestr('SHA256SUMS',manifest)
            if duplicate:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore',UserWarning)
                    z.writestr('TEST_RAW.log','FORGED')
            if traversal:
                z.writestr('../escape.txt','FORGED')
        return p,hashlib.sha256(p.read_bytes()).hexdigest()

    def test_closed_zip_and_test_count(self):
        with tempfile.TemporaryDirectory() as td:
            p,h=self.archive(td)
            r=m.audit(p,h,'preflight')
            self.assertEqual(r['integrity'],'CLEAN')
            self.assertEqual(r['tests'],2)
            self.assertEqual(r['inner_sha256'],'3/3')
            self.assertFalse(r['native_or_gate_promotion'])

    def test_outer_digest_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p,h=self.archive(td)
            with self.assertRaisesRegex(ValueError,'OUTER_SHA256_MISMATCH'):
                m.audit(p,'0'*64,'preflight')

    def test_inner_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p,h=self.archive(td,inner_tamper=True)
            with self.assertRaisesRegex(ValueError,'INNER_SHA256_MISMATCH'):
                m.audit(p,h,'preflight')

    def test_missing_inner_member_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p,h=self.archive(td,missing=True)
            with self.assertRaisesRegex(ValueError,'INNER_MANIFEST_NOT_CLOSED'):
                m.audit(p,h,'preflight')

    def test_duplicate_member_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p,h=self.archive(td,duplicate=True)
            with self.assertRaisesRegex(ValueError,'DUPLICATE_ZIP_MEMBER'):
                m.audit(p,h,'preflight')

    def test_traversal_member_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p,h=self.archive(td,traversal=True)
            with self.assertRaisesRegex(ValueError,'ZIP_PATH_TRAVERSAL'):
                m.audit(p,h,'preflight')


if __name__=='__main__':
    unittest.main()
