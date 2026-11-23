"""Synthetic no-weight negative tests for exact frozen Python source inventory."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from scripts import source_handoff_binding_audit_candidate as audit


class FrozenSourceBinding(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.code=self.root/'code';self.code.mkdir()
        self.py=self.code/'v13'/'runtime.py';self.py.parent.mkdir();self.py.write_text('frozen runtime')
        self.nested=self.code/'v13'/'agi'/'weights.py';self.nested.parent.mkdir();self.nested.write_text('nested frozen runtime')
        self.harness=self.code/'scripts'/'source_handoff_ablation.py';self.harness.parent.mkdir();self.harness.write_text('frozen harness')
        self.registration=self.root/'prereg.json'
        self.base={'schema':'SOURCE_HANDOFF_ABLATION_PREREGISTRATION_V1',
                   'binding':{'source_scope':audit.SCOPE,'source_sha256':{}}}
        for name in ('v13/runtime.py','v13/agi/weights.py','scripts/source_handoff_ablation.py'):
            self.base['binding']['source_sha256'][name]=hashlib.sha256((self.code/name).read_bytes()).hexdigest()
        self.save()

    def save(self):self.registration.write_text(json.dumps(self.base,sort_keys=True))

    def test_full_recursively_registered_tree_passes(self):
        out=audit.audit(self.registration,self.code)
        self.assertEqual(out['verified_source_count'],3)
        self.assertEqual(out['verified_runtime_source_count'],2)
        self.assertFalse(out['native_model_and_library_bindings_verified'])
        cp=subprocess.run([sys.executable,str(Path(audit.__file__)),'--preregistration',str(self.registration),'--code-root',str(self.code)],capture_output=True,text=True)
        self.assertEqual(cp.returncode,0,cp.stderr)
        self.assertEqual(json.loads(cp.stdout)['status'],'SOURCE_BINDING_PASS_MODELS_UNVERIFIED')

    def test_nested_runtime_source_byte_drift_rejected(self):
        self.nested.write_text('changed later')
        with self.assertRaisesRegex(ValueError,'SHA256 drift'):audit.audit(self.registration,self.code)

    def test_new_unlisted_runtime_source_rejected(self):
        (self.code/'v13'/'unregistered.py').write_text('new')
        with self.assertRaisesRegex(ValueError,'inventory drift'):audit.audit(self.registration,self.code)

    def test_removed_runtime_source_rejected(self):
        self.nested.unlink()
        with self.assertRaisesRegex(ValueError,'inventory drift'):audit.audit(self.registration,self.code)

    def test_symlinked_bound_source_rejected(self):
        old=self.harness.read_text();self.harness.unlink()
        outside=self.root/'outside.py';outside.write_text(old)
        self.harness.symlink_to(outside)
        with self.assertRaisesRegex(ValueError,'escapes|symbolic|linked'):audit.audit(self.registration,self.code)

    def test_malicious_path_traversal_and_absolute_path_rejected(self):
        for name in ('../outside.py','/tmp/outside.py','v13//runtime.py','v13/../runtime.py','v13\\runtime.py'):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError,'Noncanonical|escapes'):
                    audit._safe_member(name,self.code.resolve())

    def test_source_inventory_scope_not_weakened(self):
        self.base['binding']['source_scope']='PARTIAL';self.save()
        with self.assertRaisesRegex(ValueError,'scope'):audit.audit(self.registration,self.code)

    def test_malformed_hash_rejected(self):
        self.base['binding']['source_sha256']['v13/runtime.py']='fake';self.save()
        with self.assertRaisesRegex(ValueError,'SHA256 binding'):audit.audit(self.registration,self.code)

    def test_no_registration_symlink(self):
        copied=self.root/'other.json';copied.write_bytes(self.registration.read_bytes())
        self.registration.unlink();self.registration.symlink_to(copied)
        with self.assertRaisesRegex(ValueError,'unsafe'):audit.audit(self.registration,self.code)

    def test_cli_failure_no_raw_source_text(self):
        self.py.write_text('private source secret')
        cp=subprocess.run([sys.executable,str(Path(audit.__file__)),'--preregistration',str(self.registration),'--code-root',str(self.code)],capture_output=True,text=True)
        self.assertEqual(cp.returncode,2)
        self.assertNotIn('private source secret',cp.stderr)
        self.assertEqual(json.loads(cp.stderr)['status'],'SOURCE_BINDING_REJECTED')


if __name__=='__main__':unittest.main()
