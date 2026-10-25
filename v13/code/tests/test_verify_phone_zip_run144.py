"""Run144 synthetic adversarial archive tests, not Redmi evidence."""
import hashlib
import io
import json
import unittest
import zipfile
from scripts.verify_phone_zip_run144 import verify, sha, check_zip, git_blob


def pack(files):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
        for k,v in files:z.writestr(k,v)
    return b.getvalue()


class ArchiveIntegrity(unittest.TestCase):
    def test_git_blob(self):
        self.assertEqual(git_blob(b'hello\n'),'ce013625030ba8dba906f756967f9e9ca394464a')
    def test_wrapper_and_inner_hash_must_match(self):
        inner=pack([('V13-Phone/WORKSPACE_FILES.json','{}')])
        wrapper=pack([('V13-Phone-Run141.zip',inner)])
        with self.assertRaisesRegex(ValueError,'wrapper SHA'):verify(wrapper)
        with self.assertRaisesRegex(ValueError,'inner SHA'):verify(wrapper,sha(wrapper))
    def test_zip_slip_and_symlink_refused(self):
        for name in ('V13-Phone/../escape','/V13-Phone/escape','V13-Phone\\escape'):
            with self.subTest(name=name):
                with zipfile.ZipFile(io.BytesIO(pack([(name,'x')]))) as z:
                    with self.assertRaises(ValueError):check_zip(z)
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:
            i=zipfile.ZipInfo('V13-Phone/link');i.create_system=3;i.external_attr=(0o120777<<16)
            z.writestr(i,'target')
        with zipfile.ZipFile(io.BytesIO(b.getvalue())) as z:
            with self.assertRaisesRegex(ValueError,'symlink'):check_zip(z)
    def test_duplicate_zip_entries_refused(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',UserWarning)
                z.writestr('V13-Phone/a','x');z.writestr('V13-Phone/a','y')
        with zipfile.ZipFile(io.BytesIO(b.getvalue())) as z:
            with self.assertRaisesRegex(ValueError,'duplicate'):check_zip(z)
    def test_wrong_wrapper_member_refused(self):
        inner=pack([('V13-Phone/WORKSPACE_FILES.json','{}')]);outer=pack([('wrong.zip',inner)])
        with self.assertRaisesRegex(ValueError,'wrapper members'):verify(outer,sha(outer))

if __name__=='__main__':unittest.main()
