import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import control_budget as C

class Store:
    def __init__(self,gen=None,rows=None):self.gen=gen or {};self._rows=rows or []
    def generation(self):return self.gen
    def rows(self,sql,args=None):return self._rows if 'FROM messages' in sql else []

class FabricReview(unittest.TestCase):
    def test_reject_outside_checkpoint_path(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'checkpoints').mkdir()
            outside=root/'secret.npz';outside.write_bytes(b'secret')
            self.assertEqual(C.checkpoints(Store({'weights':str(outside)}),root),[])
    def test_reject_checkpoint_symlink_escape(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'checkpoints').mkdir()
            outside=root/'secret.npz';outside.write_bytes(b'secret')
            (root/'checkpoints'/'leak.npz').symlink_to(outside)
            self.assertEqual(C.checkpoints(Store({'weights':'checkpoints/leak.npz'}),root),[])
    def test_accept_inside_regular_checkpoint(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'checkpoints').mkdir()
            (root/'checkpoints'/'head.npz').write_bytes(b'1234')
            r=C.checkpoints(Store({'weights':'checkpoints/head.npz'}),root)
            self.assertEqual(r[0]['bytes'],4)
            self.assertEqual(r[0]['path'],'checkpoints/head.npz')
    def test_nonfinite_stage_marks_ignored(self):
        d=C.durations({'ingress':float('nan'),'routing':.2,'finished':.3})
        self.assertTrue(all(math.isfinite(v) for v in d.values()))
        self.assertNotIn('ingress',d)
    def test_nonmonotonic_stage_marks_rejected(self):
        d=C.durations({'ingress':.3,'routing':.2,'finished':.5})
        self.assertEqual(d,{})
    def test_malformed_metadata_skipped(self):
        rows=[{'metadata':'[]','created':1.},{'metadata':'{"stage_marks_s":{"ingress":0.1,"finished":0.3}}','created':2.}]
        self.assertEqual(C.latency(Store(rows=rows))['turns'],1)
    def test_nonfinite_limit_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):C.report(Store(),td,{'control_budget_params_mb':float('nan')})
    def test_no_limits_remains_report_only(self):
        with tempfile.TemporaryDirectory() as td:
            r=C.report(Store(),td,{})
            self.assertEqual(r['verdict'],'NO_LIMITS')
            self.assertIn('UNMEASURED',r['energy_thermal'])

if __name__=='__main__':unittest.main()
