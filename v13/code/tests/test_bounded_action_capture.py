"""Lifecycle and namespace guards; no model or native inference in these tests."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import bounded_action_jepa_capture as bounded
import capture_action_jepa_taps as producer


class LifecycleTests(unittest.TestCase):
    def proc(self, root, host, namespace, command, rss=100):
        path = root/str(host)
        path.mkdir()
        (path/'status').write_text(f'NSpid:\t{host}\t{namespace}\nVmRSS:\t{rss} kB\n')
        (path/'cmdline').write_bytes(b'\0'.join(s.encode() for s in command)+b'\0')
        (path/'stat').write_text(f'{host} (server with spaces) S '+' '.join(str(i) for i in range(1,30)))

    def test_namespace_pid_requires_exact_unique_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            command=['/server','--alias','unique']
            self.proc(root,1000,7,command)
            self.proc(root,1001,8,command)
            observed=bounded.process_identity(7,command,root)
            self.assertEqual(observed['proc_pid'],1000)
            self.assertEqual(observed['rss_bytes'],102400)
            self.assertIsNone(bounded.process_identity(7,['/server','--alias','other'],root))
            self.proc(root,1002,7,command)
            self.assertIsNone(bounded.process_identity(7,command,root))

    def fixture(self, root):
        out=root/'capture';out.mkdir()
        (out/'registration.json').write_text('{}')
        args=argparse.Namespace(out=str(out))
        texts=['t'+str(i) for i in range(200)]
        state={'rows':0,'batches':0}
        def load(*a):
            return np.zeros((state['rows'],1024)),[{}]*state['batches']
        def capture(*a):
            # A model-free fake of driver checkpoint ordering and owned cleanup.
            worker=producer.subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])
            try:
                for i in range(1,14):
                    state.update(rows=i*16,batches=i)
                    producer.progress(out,'registry',np.zeros((i*16,1024)),[{}]*i,'RUNNING')
            finally:
                worker.terminate();worker.wait(timeout=10)
        return args,out,texts,state,load,capture

    def test_eight_batch_checkpoint_boundary_reaps_owned_worker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);args,out,texts,state,load,capture=self.fixture(root)
            with patch.object(producer,'registration',return_value=({},texts)), patch.object(producer,'load_checkpoint',side_effect=load), patch.object(producer,'progress'), patch.object(producer,'capture',side_effect=capture):
                observed,result=bounded.one_worker(args,root,8,root/'observation.json')
            self.assertEqual(state,{'rows':128,'batches':8})
            self.assertEqual(observed['status'],'CONTROLLED_CHECKPOINT_BOUNDARY')
            self.assertTrue(observed['worker_reaped'])
            self.assertEqual(observed['cleanup_requests'][0]['operation'],'owned_Popen_terminate')
            self.assertEqual(observed['native_returncode'],-15)
            self.assertIsNone(result)

    def test_uncontrolled_exception_is_retained_and_propagated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);args,out,texts,state,load,capture=self.fixture(root)
            def failure(*a):
                raise RuntimeError('native response disconnected')
            with patch.object(producer,'registration',return_value=({},texts)), patch.object(producer,'load_checkpoint',side_effect=load), patch.object(producer,'capture',side_effect=failure):
                with self.assertRaisesRegex(RuntimeError,'disconnected'):
                    bounded.one_worker(args,root,8,root/'observation.json')
            result=json.loads((root/'observation.json').read_text())
            self.assertEqual(result['status'],'FAILED')
            self.assertFalse(result['native_started'])
            self.assertIn('memory_start',result)
            self.assertIn('memory_end',result)

    def test_restart_invariance_failure_prevents_main_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            binding={'source_checker_snapshot_root':str(root),'exact_original_binding':False,'main_capture_out':str(root/'main')}
            (root/'bounded-lifecycle-registration.json').write_text(json.dumps(binding))
            for number in (1,2):
                child=root/f'control-worker-{number}'
                child.mkdir();(child/'registration.json').write_text('{}')
                (root/f'control-worker-{number}-observation.json').write_text(json.dumps({'status':'CONTROLLED_CHECKPOINT_BOUNDARY','native_started':True,'worker_reaped':True,'rss_observed':True,'completed_new_batches':1}))
            args=argparse.Namespace(out=str(root),sentences='unused',actions='unused')
            arrays=[np.zeros((16,1024)),np.ones((16,1024))]
            with patch.object(bounded,'preregister',return_value=binding), patch.object(producer,'corpus',return_value=(None,None,['x']*1875)), patch.object(producer,'load_checkpoint',side_effect=[(arrays[0],[{}]),(arrays[1],[{}])]), patch.object(bounded,'original_prefix',return_value=(None,None,np.zeros((736,1024)),None)), patch.object(bounded,'one_worker') as worker:
                with self.assertRaisesRegex(ValueError,'invariance failed'):
                    bounded.execute(args)
                worker.assert_not_called()
            report=json.loads((root/'fresh-worker-invariance.json').read_text())
            self.assertFalse(report['fresh_workers_exact_equal'])
            self.assertFalse(report['mixed_cohort_rows'])

    def test_matching_bytes_with_historical_drift_prevents_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            binding={'source_checker_snapshot_root':str(root),'exact_original_binding':True,'main_capture_out':str(root/'main')}
            (root/'bounded-lifecycle-registration.json').write_text(json.dumps(binding))
            for number in (1,2):
                child=root/f'control-worker-{number}'
                child.mkdir();(child/'registration.json').write_text('{}')
                (root/f'control-worker-{number}-observation.json').write_text(json.dumps({'status':'CONTROLLED_CHECKPOINT_BOUNDARY','native_started':True,'worker_reaped':True,'rss_observed':True,'completed_new_batches':1}))
            args=argparse.Namespace(out=str(root),sentences='unused',actions='unused')
            x=np.ones((16,1024))
            with patch.object(bounded,'preregister',return_value=binding), patch.object(producer,'corpus',return_value=(None,None,['x']*1875)), patch.object(producer,'load_checkpoint',return_value=(x,[{}])), patch.object(bounded,'original_prefix',return_value=(None,None,np.zeros((736,1024)),None)), patch.object(bounded,'one_worker') as worker:
                with self.assertRaisesRegex(ValueError,'Historical numerical drift'):
                    bounded.execute(args)
                worker.assert_not_called()

    def test_saved_control_without_rss_or_controlled_status_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            binding={'source_checker_snapshot_root':str(root),'exact_original_binding':True,'main_capture_out':str(root/'main')}
            (root/'bounded-lifecycle-registration.json').write_text(json.dumps(binding))
            child=root/'control-worker-1';child.mkdir();(child/'registration.json').write_text('{}')
            (root/'control-worker-1-observation.json').write_text(json.dumps({'status':'FAILED','native_started':True,'worker_reaped':True,'completed_new_batches':1}))
            args=argparse.Namespace(out=str(root),sentences='unused',actions='unused')
            with patch.object(bounded,'preregister',return_value=binding), patch.object(producer,'corpus',return_value=(None,None,['x']*1875)), patch.object(producer,'load_checkpoint',return_value=(np.zeros((16,1024)),[{}])), patch.object(bounded,'one_worker') as worker:
                with self.assertRaisesRegex(ValueError,'reaped actual native observation'):
                    bounded.execute(args)
                worker.assert_not_called()

    def test_driver_bytes_are_unchanged(self):
        self.assertEqual(producer.sha(producer.__file__),'42b38b8d0f3f96a811f330895de62e35ec81bfea89383edd3ba00da52d06defd')


if __name__ == '__main__':
    unittest.main()
