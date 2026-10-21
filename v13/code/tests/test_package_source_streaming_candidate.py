import hashlib
import os
import tracemalloc
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from scripts import package_source_streaming_candidate as saver

class SourceStreamer(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.code=self.root/'code';self.code.mkdir()
        self.source=self.code/'v13'/'runtime.py';self.source.parent.mkdir()
        self.source.write_bytes(b'from v13 import api\n')
        self.proof=self.code/'docs'/'proofs'/'immutable'/'part-00000.bin';self.proof.parent.mkdir(parents=True)
        self.proof.write_bytes(bytes(range(256))*24000)
        self.out=self.root/'checkpoint.zip'

    def test_archive_manifest_exact_sources_and_roundtrip(self):
        report=saver.package(self.code,self.out)
        self.assertEqual(report['status'],'SOURCE_CHECKPOINT_LOCAL_ONLY')
        with zipfile.ZipFile(self.out) as z:
            doc=json.loads(z.read('V13-Phone/WORKSPACE_FILES.json'))
            self.assertEqual(doc['schema_version'],1)
            for rel,h in doc['files'].items():
                self.assertEqual(hashlib.sha256(z.read('V13-Phone/'+rel)).hexdigest(),h)
            self.assertEqual(z.read('V13-Phone/'+self.proof.relative_to(self.code).as_posix()),self.proof.read_bytes())

    def test_legacy_prefix_and_phone_filter(self):
        def mk(rel):
            p=self.code/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('x')
        for rel in saver.PHONE_REQUIRED_FIXTURES:mk(rel)
        mk('docs/canon/canon.md');mk('docs/proofs/unneeded/raw.json')
        saver.package(self.code,self.out,phone_install=True)
        with zipfile.ZipFile(self.out) as z:
            self.assertIn('V13-Phone/docs/canon/canon.md',z.namelist())
            self.assertNotIn('V13-Phone/docs/proofs/unneeded/raw.json',z.namelist())

    def test_refuses_existing_archive_instead_of_overwriting(self):
        self.out.write_bytes(b'previous saved checkpoint')
        with self.assertRaisesRegex(ValueError,'Refusing'):saver.package(self.code,self.out)
        self.assertEqual(self.out.read_bytes(),b'previous saved checkpoint')

    def test_requires_phone_fixtures(self):
        with self.assertRaisesRegex(ValueError,'fixtures'):saver.package(self.code,self.out,phone_install=True)
        self.assertFalse(self.out.exists())

    def test_refuses_output_inside_tree(self):
        with self.assertRaisesRegex(ValueError,'inside source'):saver.package(self.code,self.code/'output.zip')

    def test_excludes_model_weights_databases_and_user_cache(self):
        (self.code/'v13'/'stored_model.gguf').write_bytes(b'WEIGHTS')
        (self.code/'docs'/'proofs'/'history.sqlite').write_bytes(b'DATABASE')
        for relative in ['data/private.log','models/model.bin','.env']:
            p=self.code/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('private')
        saver.package(self.code,self.out)
        with zipfile.ZipFile(self.out) as z:
            names=' '.join(z.namelist())
            self.assertNotIn('stored_model.gguf',names)
            self.assertNotIn('history.sqlite',names)
            self.assertNotIn('private.log',names)
            self.assertNotIn('model.bin',names)
            self.assertNotIn('.env',names)

    def test_refuses_symlinked_runtime_files(self):
        target=self.root/'external.py';target.write_text('file outside tree')
        link=self.code/'v13'/'extra.py';link.symlink_to(target)
        with self.assertRaisesRegex(ValueError,'symlink'):saver.package(self.code,self.out)
        self.assertFalse(self.out.exists())

    def test_source_modified_mid_stream_does_not_publish(self):
        original=saver._fingerprint
        triggered=False
        def mutated(st):
            nonlocal triggered
            if not triggered and st.st_size==self.source.stat().st_size:
                triggered=True;self.source.write_bytes(b'MUTATED!!')
            return original(st)
        with patch.object(saver,'_fingerprint',side_effect=mutated):
            with self.assertRaises(ValueError):saver.package(self.code,self.out)
        self.assertFalse(self.out.exists())

    def test_source_deleted_during_pack_does_not_publish(self):
        original=saver._sha_stream
        def erase(stream):
            self.source.unlink(missing_ok=True)
            return original(stream)
        with patch.object(saver,'_sha_stream',side_effect=erase):
            with self.assertRaises(ValueError):saver.package(self.code,self.out)
        self.assertFalse(self.out.exists())

    def test_large_closed_evidence_package_memory_bounded(self):
        # Do not allocate the full proof in Python while measuring the packer.
        with self.proof.open('wb') as sink:
            for _ in range(24):sink.write(os.urandom(1 << 20))
        tracemalloc.start()
        try:
            saver.package(self.code,self.out)
            _,peak=tracemalloc.get_traced_memory()
        finally:tracemalloc.stop()
        self.assertLess(peak,12 << 20, f'Peak Python heap was {peak}')
        with zipfile.ZipFile(self.out) as z:
            self.assertEqual(len(z.read('V13-Phone/docs/proofs/immutable/part-00000.bin')),24 << 20)

    def test_verified_stream_uses_bounded_read_calls(self):
        actual=saver._sha_stream
        class Guarded:
            def __init__(self,f):self.f=f
            def read(self,size=-1):
                assert size==saver.CHUNK
                return self.f.read(size)
        with self.proof.open('rb') as source:
            self.assertEqual(actual(Guarded(source)),hashlib.sha256(self.proof.read_bytes()).hexdigest())

if __name__=='__main__':unittest.main()
