import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from v13.resources import _ProcResolver,process_memory

class ProcessMemoryChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.task('self',2165,16,100,'ours');self.r=_ProcResolver(self.root,own_pid=16)
    def tearDown(self):self.tmp.cleanup()
    def task(self,name,outer,inner,start,ns,rss=100):
        p=self.root/str(name);p.mkdir(exist_ok=True);(p/'ns').mkdir(exist_ok=True)
        link=p/'ns/pid'
        if link.is_symlink():link.unlink()
        link.symlink_to('pid:['+ns+']');(p/'status').write_text(f'Pid:\t{outer}\nNSpid:\t{outer}\t{inner}\nVmRSS:\t{rss} kB\n')
        fields=['S']+['0']*22;fields[7]='7';fields[9]='9';fields[19]=str(start)
        (p/'stat').write_text(str(outer)+' (name with ) parens) '+' '.join(fields));(p/'smaps_rollup').write_text('Pss: 80 kB\n');(p/'maps').write_text('1000-3000 r--p 00000000 00:00 0 /model\n');return p
    def test_self_uses_self_not_outer_coincident_numeric_pid(self):
        self.task(16,16,16,888,'other',rss=999)
        m=self.r.memory(16);self.assertEqual(m['rss_bytes'],102400);self.assertEqual(m['resolved_proc_pid'],2165);self.assertEqual(m['measurement_status'],'MEASURED')
    def test_child_requires_same_namespace_and_inner_pid_mapping(self):
        self.task(22,22,22,123,'other',rss=999);self.task(2010,2010,22,125,'other',rss=888);self.task(2170,2170,22,150,'ours',rss=321)
        m=self.r.memory(22);self.assertEqual(m['rss_bytes'],321*1024);self.assertEqual(m['pss_bytes'],80*1024);self.assertEqual(m['mapped_file_bytes'],8192);self.assertEqual((m['minor_faults'],m['major_faults']),(7,9));self.assertEqual(m['resolved_proc_pid'],2170)
    def test_missing_permission_and_scan_cap_return_null_without_guessing(self):
        self.task(2170,2170,22,150,'ours');r=_ProcResolver(self.root,own_pid=16,max_scan=0)
        m=r.memory(22);self.assertEqual(m['measurement_status'],'UNAVAILABLE');self.assertIsNone(m['rss_bytes'])
        (self.root/'self/ns/pid').unlink();self.assertIsNone(self.r.memory(22)['rss_bytes'])
    def test_missing_smaps_does_not_hide_verified_rss(self):
        p=self.task(2170,2170,22,150,'ours');(p/'smaps_rollup').unlink()
        m=self.r.memory(22);self.assertEqual(m['rss_bytes'],102400);self.assertIsNone(m['pss_bytes']);self.assertEqual(m['measurement_status'],'PARTIAL')
    def test_cached_pid_reuse_is_never_attributed_to_previous_child(self):
        self.task(2170,2170,22,150,'ours');self.assertIsNotNone(self.r.memory(22)['rss_bytes'])
        self.task(2170,2170,22,200,'ours',rss=999)
        for _ in range(2):self.assertIsNone(self.r.memory(22)['rss_bytes'])
    def test_exited_cached_child_cannot_be_replaced_by_different_outer_pid(self):
        import shutil
        self.task(2170,2170,22,150,'ours');self.r.memory(22);shutil.rmtree(self.root/'2170')
        self.task(2200,2200,22,200,'ours',rss=999)
        self.assertIsNone(self.r.memory(22)['rss_bytes']);self.assertIsNone(self.r.memory(22)['pss_bytes'])
    def test_pid_tracking_is_bounded_for_arbitrary_requests(self):
        self.r.max_scan=0;self.r.max_tracked=32
        for pid in range(1000,1100):self.r.memory(pid)
        self.assertLessEqual(len(self.r.cache)+len(self.r.missing)+len(self.r.reused),32)
    def test_reuse_during_sample_discards_every_field(self):
        p=self.task(2170,2170,22,150,'ours');self.r.memory(22);original=self.r.identity;calls=0
        def identity(path):
            nonlocal calls
            if path==p:
                calls+=1
                if calls==2:self.task(2170,2170,22,200,'ours')
            return original(path)
        with patch.object(self.r,'identity',side_effect=identity):m=self.r.memory(22)
        self.assertEqual(m['measurement_status'],'UNAVAILABLE');self.assertIsNone(m['minor_faults']);self.assertIsNone(m['rss_bytes'])
    def test_kernel_without_nspid_accepts_only_matching_mount_namespace(self):
        self.task(22,22,22,150,'ours');(self.root/'22/status').write_text('Pid: 22\nVmRSS: 100 kB\n')
        self.assertIsNone(self.r.memory(22)['rss_bytes'])
        (self.root/'self/status').write_text('Pid: 16\nVmRSS: 100 kB\n')
        self.assertEqual(_ProcResolver(self.root,own_pid=16).memory(22)['rss_bytes'],102400)
    def test_actual_self_signature_keeps_original_fields(self):
        m=process_memory();self.assertEqual(m['pid'],os.getpid())
        self.assertTrue({'pid','rss_bytes','pss_bytes','mapped_file_bytes','minor_faults','major_faults'}<=set(m))
        if m['measurement_status']=='MEASURED':self.assertGreater(m['rss_bytes'],0)

if __name__=='__main__':unittest.main()
