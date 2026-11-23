"""WP-U4: cold sources are archived losslessly; SourceRefs, :doctor, restore and :forget keep working; hot sources stay plain."""
from pathlib import Path
import tempfile
import time
import unittest
from v13.runtime import Runtime
from v13 import archive as A

TEXT='Projekt Aurora: Das Budget im Mai beträgt 120 Euro, verteilt auf Material und Reisen. '*20

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off')
        self.blobs=self.r.home/'data/blobs';self.later=lambda:time.time()+(A.ARCHIVE_DAYS+1)*86400
    def tearDown(self):self.r.close();self.tmp.cleanup()

class Archive(Base):
    def test_cold_user_source_is_archived_and_still_readable(self):
        e=self.r.store.event(self.r.session,TEXT);ref=e['source_ref']
        self.assertEqual(A.run(self.r.store)['counts'],{})  # too young
        out=A.run(self.r.store,self.later)
        self.assertEqual(out['counts'],{'ARCHIVED':1});self.assertGreater(out['saved_bytes'],0)
        self.assertFalse((self.blobs/ref['sha256']).exists());self.assertTrue((self.blobs/(ref['sha256']+'.z')).exists())
        self.assertEqual(self.r.store.read_source(ref),TEXT)
        self.assertEqual([x for x in self.r.store.integrity(full=True) if 'Source' in x],[])
        self.assertEqual(A.report(self.r.store)['archived_blobs'],1)
        self.assertEqual(A.restore(self.r.store,ref['sha256']),'RESTORED');self.assertTrue((self.blobs/ref['sha256']).exists())
        self.assertEqual(self.r.store.read_source(ref),TEXT)
    def test_active_memory_keeps_its_sources_hot_superseded_value_goes_cold(self):
        e=self.r.store.event(self.r.session,TEXT);old='Alter Wert '*80;new='Neuer Wert '*80
        self.r.memory.feedback(e['event_id'],'fact',old)
        self.assertNotIn(e['source_ref']['sha256'],A.candidates(self.r.store,self.later))  # event of an active memory
        self.r.memory.feedback(e['event_id'],'fact',new)
        hashes=A.candidates(self.r.store,self.later)
        oldh=self.r.store.one("SELECT s.hash FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.active=0")['hash']
        newh=self.r.store.one("SELECT s.hash FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.active=1")['hash']
        self.assertIn(oldh,hashes);self.assertNotIn(newh,hashes);self.assertNotIn(e['source_ref']['sha256'],hashes)
    def test_corrupt_archive_is_detected_and_small_blobs_stay(self):
        e=self.r.store.event(self.r.session,TEXT);small=self.r.store.event(self.r.session,'kurz')
        A.run(self.r.store,self.later);h=e['source_ref']['sha256']
        self.assertTrue((self.blobs/small['source_ref']['sha256']).exists())
        (self.blobs/(h+'.z')).write_bytes(b'kaputt')
        with self.assertRaises(ValueError):self.r.store.read_source(e['source_ref'])
        self.assertTrue(any('Source beschädigt' in x for x in self.r.store.integrity(full=True)))
    def test_sleep_c_runs_archive_and_operator(self):
        c=self.r.sleep.cycle.run('c',origin='USER')['phases'][0];self.assertIn('archive',c)
        from v13.archive import operator_command
        self.assertIn('archived_blobs',operator_command(self.r,['status']))

if __name__=='__main__':unittest.main()
