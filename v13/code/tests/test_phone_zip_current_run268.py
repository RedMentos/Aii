"""Run268 independent phone source ZIP verifier negative controls."""
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

from scripts import verify_phone_zip_current_run268 as V


class CurrentPhoneZipVerifier(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)/'src'
        self.root.mkdir()
        self.archive=Path(self.tmp.name)/'phone.zip'
        self.files={k:(k+' source bytes').encode() for k in V.REQUIRED}
        self.files['tests/example.txt']=b'fixture'

    def tearDown(self):self.tmp.cleanup()

    def build(self,files=None,duplicate=None):
        files=self.files if files is None else files
        for rel,content in files.items():
            p=self.root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content)
        manifest={'schema_version':1,'files':{k:hashlib.sha256(v).hexdigest() for k,v in files.items()}}
        with zipfile.ZipFile(self.archive,'w',zipfile.ZIP_DEFLATED) as z:
            for rel,content in files.items():
                info=zipfile.ZipInfo(V.ROOT+rel)
                info.external_attr=((0o100755 if rel.endswith('.sh') else 0o100644)<<16)
                z.writestr(info,content)
            if duplicate:
                z.writestr(V.ROOT+duplicate,files[duplicate])
            z.writestr(V.ROOT+'WORKSPACE_FILES.json',json.dumps(manifest))

    def test_valid_archive_exact_checkout(self):
        self.build()
        r=V.verify(self.archive,self.root,min_files=0)
        self.assertEqual(r['file_count'],len(self.files))
        self.assertEqual(r['checkout_byte_parity'],'PASS')
        self.assertFalse(r['redmi_measured'])

    def test_changed_checkout_refused(self):
        self.build()
        (self.root/'v13/runtime.py').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'checkout source SHA256 mismatch'):
            V.verify(self.archive,self.root,min_files=0)

    def test_member_sha_mismatch_refused(self):
        self.build()
        with zipfile.ZipFile(self.archive,'a') as z:
            z.writestr(V.ROOT+'extra.txt',b'unregistered')
        with self.assertRaisesRegex(ValueError,'manifest member set mismatch'):
            V.verify(self.archive,self.root,min_files=0)

    def test_forbidden_model_payload_refused(self):
        files=dict(self.files,**{'models/private.gguf':b'weights'})
        self.build(files)
        with self.assertRaisesRegex(ValueError,'forbidden private/model payload'):
            V.verify(self.archive,self.root,min_files=0)

    def test_duplicate_member_refused(self):
        self.build(duplicate='tests/example.txt')
        with self.assertRaisesRegex(ValueError,'duplicate ZIP member'):
            V.verify(self.archive,self.root,min_files=0)

    def test_path_traversal_refused(self):
        self.build()
        with zipfile.ZipFile(self.archive,'a') as z:
            z.writestr('V13-Phone/../escape.txt',b'no')
        with self.assertRaisesRegex(ValueError,'unsafe ZIP path'):
            V.verify(self.archive,self.root,min_files=0)

    def test_symlink_member_refused(self):
        self.build()
        with zipfile.ZipFile(self.archive,'a') as z:
            info=zipfile.ZipInfo(V.ROOT+'links/evil')
            info.external_attr=((stat.S_IFLNK|0o777)<<16)
            z.writestr(info,b'../elsewhere')
        with self.assertRaisesRegex(ValueError,'symlink ZIP member'):
            V.verify(self.archive,self.root,min_files=0)


if __name__=='__main__':
    unittest.main()
