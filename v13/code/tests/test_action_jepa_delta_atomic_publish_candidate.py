"""Only atomic publication tests: no native training or JEPA utility is implied."""
import errno
import json
import subprocess
import sys
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from scripts import action_jepa_delta_atomic_publish_candidate as atomic

class DeltaAtomicPublish(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.dst=self.root/'restored'

    @staticmethod
    def implementation(base,archives,path):
        path.mkdir()
        (path/'registration.json').write_bytes(b'signed registration')
        (path/'taps.npz').write_bytes(b'NPZ original exact bytes')
        return {'completed_rows':1875,'exact_original_npz_bytes_restored':True,'receiver_authority':0}

    def test_noreplace_same_filesystem_capability_probe(self):
        result=atomic.probe_noreplace_directory(self.root)
        self.assertEqual(result['status'],'ATOMIC_NOREPLACE_FILESYSTEM_PROBE_PASS')
        self.assertFalse(result['phone_measured'])
        self.assertEqual(list(self.root.iterdir()),[])

    def test_probe_requires_existing_non_symlink_parent(self):
        with self.assertRaisesRegex(ValueError,'ordinary'):
            atomic.probe_noreplace_directory(self.root/'missing')
        link=self.root/'linked';link.symlink_to(self.root)
        with self.assertRaisesRegex(ValueError,'ordinary'):
            atomic.probe_noreplace_directory(link)

    def test_probe_cli_does_not_emit_native_pass(self):
        cp=subprocess.run([sys.executable,str(Path(atomic.__file__)),'--probe-directory',str(self.root)],capture_output=True,text=True)
        self.assertEqual(cp.returncode,0,cp.stderr)
        value=json.loads(cp.stdout)
        self.assertEqual(value['status'],'ATOMIC_NOREPLACE_FILESYSTEM_PROBE_PASS')
        self.assertIs(value['canonical_gate_pass'],False)
        self.assertEqual(list(self.root.iterdir()),[])

    def test_atomic_directory_published_after_verified_restore(self):
        r=atomic.restore_atomic('base',['delta'],self.dst,restore_impl=self.implementation)
        self.assertTrue(self.dst.is_dir());self.assertTrue((self.dst/'taps.npz').exists())
        self.assertEqual(r['publication'],'ATOMIC_DIRECTORY_NOREPLACE')
        self.assertFalse(r['semantic_quality_proven'])
        self.assertEqual(len(list(self.root.glob('.v13-delta-restore-*'))),0)

    def test_mid_restore_exception_leaves_no_partial_final_evidence(self):
        def broken(base,archives,path):
            path.mkdir();(path/'taps.npz').write_bytes(b'PARTIAL');raise RuntimeError('simulated disk failure')
        with self.assertRaises(RuntimeError):atomic.restore_atomic('base',['delta'],self.dst,restore_impl=broken)
        self.assertFalse(self.dst.exists())
        self.assertEqual(len(list(self.root.glob('.v13-delta-restore-*'))),0)

    def test_false_success_flags_or_missing_files_refused(self):
        for change in ({'exact_original_npz_bytes_restored':False},{'receiver_authority':1},{'completed_rows':0}):
            with self.subTest(change=change):
                def forged(base,archives,path):
                    result=self.implementation(base,archives,path)
                    result.update(change);return result
                with self.assertRaises(ValueError):atomic.restore_atomic('base',['delta'],self.dst,restore_impl=forged)
                self.assertFalse(self.dst.exists())

    def test_existing_empty_destination_never_replaced(self):
        self.dst.mkdir();marker=self.dst/'sentinel';marker.write_bytes(b'ORIGINAL')
        with self.assertRaisesRegex(ValueError,'existing'):
            atomic.restore_atomic('base',['delta'],self.dst,restore_impl=self.implementation)
        self.assertEqual(marker.read_bytes(),b'ORIGINAL')

    def test_existing_empty_directory_not_replaced_by_atomic_rename(self):
        staging=self.root/'staging';staging.mkdir();self.dst.mkdir()
        with self.assertRaises(OSError) as caught:atomic.rename_noreplace(staging,self.dst)
        self.assertIn(caught.exception.errno,(errno.EEXIST,errno.ENOSYS))
        self.assertTrue(self.dst.is_dir());self.assertTrue(staging.is_dir())

    def test_no_delta_archive_refused(self):
        with self.assertRaisesRegex(ValueError,'At least one'):atomic.restore_atomic('base',[],self.dst,restore_impl=self.implementation)
        self.assertFalse(self.dst.exists())

    def test_restoration_with_symlink_refused_before_publication(self):
        def forged(base,archives,path):
            result=self.implementation(base,archives,path)
            (path/'linked').symlink_to('/tmp/fake-output')
            return result
        with self.assertRaisesRegex(ValueError,'Symlink'):
            atomic.restore_atomic('base',['delta'],self.dst,restore_impl=forged)
        self.assertFalse(self.dst.exists())

    def test_concurrent_competing_writers_cannot_replace(self):
        barrier=threading.Barrier(2)
        errors=[]
        def writer(identity):
            def producer(base,archives,path):
                result=self.implementation(base,archives,path)
                (path/'identity').write_text(identity)
                barrier.wait(timeout=5)
                return result
            try:atomic.restore_atomic('base',['delta'],self.dst,restore_impl=producer)
            except (ValueError,OSError) as exc:errors.append(type(exc).__name__)
        t1=threading.Thread(target=writer,args=('A',));t2=threading.Thread(target=writer,args=('B',));t1.start();t2.start();t1.join(8);t2.join(8)
        self.assertFalse(t1.is_alive() or t2.is_alive())
        self.assertEqual(len(errors),1)
        self.assertIn((self.dst/'identity').read_text(),('A','B'))

    def test_rename_failure_retains_previous_and_cleans_stage(self):
        with patch.object(atomic,'rename_noreplace',side_effect=OSError(errno.EIO,'disk unavailable')):
            with self.assertRaises(OSError):atomic.restore_atomic('base',['delta'],self.dst,restore_impl=self.implementation)
        self.assertFalse(self.dst.exists())
        self.assertEqual(len(list(self.root.glob('.v13-delta-restore-*'))),0)


if __name__=='__main__':unittest.main()
