"""Actual SQLite checkpoint corruption regressions, no model-quality assertions."""
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
import zipfile
from v13.common import digest,dumps,file_hash
from v13.config import initialize
from v13.store import Store

spec=importlib.util.spec_from_file_location('step2_checkpoint_collector',Path(__file__).with_name('integration_step2_utility.py'))
collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)

class ClosedCheckpoint(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.base=self.root/'base';initialize(self.base)
        self.installed=self.root/'installed';initialize(self.installed)
        (self.installed/'config/models.json').write_text('{}')
        store=Store(self.base)
        try:
            self.session=store.new_session('Checkpoint regression')
            self.ref=store.source('Authoritative closed source')
            for role in ('B1_DETAIL','B2_GIST'):
                store.set_state(role+':'+self.session,{'step':1,'source_ref':self.ref})
                store.set_state(role+':'+self.session,{'step':2,'source_ref':self.ref})
            self.states={role:store.state(role+':'+self.session) for role in ('B1_DETAIL','B2_GIST')}
        finally:store.close()
        self.expected=collector.checkpoint_hashes(self.base)
        self.sealed=collector.seal_checkpoint(self.base,self.expected)
    def tearDown(self):self.temp.cleanup()
    def clone(self,name='clone'):
        home=self.root/name
        return home,collector.clone_base(self.base,home,self.installed,self.expected,self.sealed)
    def assert_closed_state(self,home):
        store=Store(home)
        try:
            actual={role:store.state(role+':'+self.session) for role in self.states}
            self.assertTrue(collector.same_persisted_state(actual,self.states))
            self.assertEqual(store.read_source(self.ref),'Authoritative closed source')
            self.assertFalse(store.integrity(True))
        finally:store.close()
    def test_real_stale_wal_breaks_directory_copy_but_not_closed_clone(self):
        stale=self.root/'stale';shutil.copytree(self.base,stale)
        db=sqlite3.connect(stale/'data/db/brain.sqlite3',isolation_level=None)
        try:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('UPDATE states SET version=1,payload=?',(dumps({'step':1,'source_ref':self.ref}),))
            for suffix in ('-wal','-shm'):
                shutil.copyfile(stale/('data/db/brain.sqlite3'+suffix),self.base/('data/db/brain.sqlite3'+suffix))
            self.assertEqual(file_hash(self.base/'data/db/brain.sqlite3'),self.expected['data/db/brain.sqlite3'])
            unsafe=self.root/'unsafe';shutil.copytree(self.base,unsafe)
            store=Store(unsafe)
            try:self.assertEqual(store.state('B2_GIST:'+self.session)[1],1)
            finally:store.close()
            home,metadata=self.clone()
            self.assertEqual(len(metadata['excluded_unregistered_sidecars']),2)
            self.assert_closed_state(home)
        finally:db.close()
    def test_each_variant_has_independent_real_database_state(self):
        home,_=self.clone('first');self.assert_closed_state(home)
        store=Store(home)
        try:store.set_state('B2_GIST:'+self.session,{'changed_in_first_variant':True})
        finally:store.close()
        home,_=self.clone('second');self.assert_closed_state(home)
        self.assertEqual(file_hash(self.base/'data/db/brain.sqlite3'),self.expected['data/db/brain.sqlite3'])
    def test_changed_closed_database_or_source_fails_before_destination(self):
        for relative in ('data/db/brain.sqlite3','data/blobs/'+self.ref['sha256']):
            path=self.base/relative;original=path.read_bytes();path.write_bytes(original+b'tamper')
            with self.assertRaisesRegex(ValueError,'Checkpoint bytes changed'):self.clone()
            self.assertFalse((self.root/'clone').exists());path.write_bytes(original)
    def test_changed_seal_fails_before_destination(self):
        path=Path(self.sealed['path']);path.write_bytes(path.read_bytes()+b'tamper')
        with self.assertRaisesRegex(ValueError,'Sealed checkpoint bytes changed'):self.clone()
        self.assertFalse((self.root/'clone').exists())
    def test_seal_refuses_live_store(self):
        store=Store(self.base)
        try:
            with self.assertRaises(BlockingIOError):collector.seal_checkpoint(self.base,self.expected)
        finally:store.close()
    def test_manifest_rejects_escape_alias_transient_and_symlink(self):
        for relative in ('../outside','/outside','config//settings.json','data/db/brain.sqlite3-wal','data/coordinator.lock'):
            with self.assertRaises(ValueError):collector.checkpoint_bytes(self.base,dict(self.expected,**{relative:digest(b'x')}))
        blob=self.base/'data/blobs'/self.ref['sha256'];original=blob.read_bytes();blob.unlink()
        outside=self.root/'outside';outside.write_bytes(original);blob.symlink_to(outside)
        with self.assertRaisesRegex(ValueError,'symlink'):self.clone()
        self.assertFalse((self.root/'clone').exists())
    def test_duplicate_or_extra_sealed_member_is_refused(self):
        path=Path(self.sealed['path'])
        with zipfile.ZipFile(path,'a') as archive:archive.writestr('extra',b'unregistered')
        changed=dict(self.sealed,sha256=file_hash(path))
        with self.assertRaisesRegex(ValueError,'member set'):
            collector.clone_base(self.base,self.root/'clone',self.installed,self.expected,changed)
        self.assertFalse((self.root/'clone').exists())

if __name__=='__main__':unittest.main()
