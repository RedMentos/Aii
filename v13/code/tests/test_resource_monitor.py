import threading
import time
import unittest
from v13.pressure import NativePressureMonitor
from v13.resources import ResourceGuard

CFG={'minimum_free_mb':100,'thermal_limit_c':45.}
def snap(mb=1000,temp=None,rss=None,pss=None):
    return {'mem_available_bytes':None if mb is None else mb*1024*1024,'battery_temperature_c':temp,'processes':[{'pid':12,'rss_bytes':rss,'pss_bytes':pss}]}

class ResourceMonitorChecks(unittest.TestCase):
    def test_existing_operator_cancel_cannot_be_relabelled_as_resource_first_cause(self):
        cancel=threading.Event();cancel.set();m=self.monitor([snap(90)],cancel)
        m._sample();self.assertEqual(m.reason,'MEMORY_CRITICAL')
        self.assertFalse(m.resource_cancel_signalled)
    def test_owner_arbitrates_cancel_without_losing_measured_pressure(self):
        calls=[];m=self.monitor([snap(90)],request_cancel=lambda:calls.append(True) or False)
        m._sample();self.assertEqual(calls,[True]);self.assertFalse(m.resource_cancel_signalled)
        self.assertEqual(m.report()['critical_reason'],'MEMORY_CRITICAL')
    def monitor(self,rows,cancel=None,**kwargs):
        stream=iter(rows);last=[None]
        def read(home,pids):
            try:last[0]=next(stream)
            except StopIteration:pass
            return last[0]
        m=NativePressureMonitor('/unused',CFG,cancel=cancel,interval=1,snapshot_fn=read,**kwargs)
        # Deterministic manual samples exercise the real state/cancel mechanism.
        m.started=time.monotonic();return m
    def test_growth_critical_signal_preserves_raw_snapshot_without_kill(self):
        cancel=threading.Event();m=self.monitor([snap(rss=100),snap(150,rss=200),snap(90,rss=300)],cancel)
        m._sample();self.assertEqual(m.last_state,'NORMAL');m._sample();self.assertEqual(m.last_state,'PRESSURE');self.assertFalse(cancel.is_set())
        m._sample();self.assertTrue(cancel.is_set());r=m.report();self.assertEqual(r['critical_reason'],'MEMORY_CRITICAL');self.assertEqual(r['critical_snapshot']['snapshot']['mem_available_bytes'],90*1024*1024);self.assertEqual(r['sampled_peak_rss_bytes'],300)
    def test_thermal_missing_fields_and_existing_recovery_policy(self):
        m=self.monitor([snap(None,None),snap(1000,45),snap(1000,30),snap(1000,30)])
        m._sample();self.assertEqual(m.last_state,'NORMAL');self.assertIsNone(m.report()['sampled_peak_pss_bytes'])
        m._sample();self.assertEqual(m.reason,'THERMAL_CRITICAL');m._sample();self.assertEqual(m.last_state,'RECOVERY');m._sample();self.assertEqual(m.last_state,'NORMAL');self.assertEqual(m.reason,'THERMAL_CRITICAL');self.assertTrue(m.cancel.is_set())
    def test_both_critical_boundaries_keep_guard_thresholds(self):
        m=self.monitor([snap(100,42),snap(99,45)])
        m._sample();self.assertEqual(m.last_state,'PRESSURE');m._sample();self.assertEqual(m.reason,'MEMORY_AND_THERMAL_CRITICAL')
    def test_missing_snapshot_or_failure_never_fabricates_measurements(self):
        def missing(home,pids):raise OSError('unavailable')
        m=NativePressureMonitor('/unused',CFG,snapshot_fn=missing);m.start();r=m.stop()
        self.assertEqual(r['sample_count'],0);self.assertEqual(r['observer_failures'],1);self.assertIsNone(r['sampled_peak_rss_bytes']);self.assertIsNone(r['native_kv_bytes']);self.assertFalse(m.cancel.is_set())
    def test_history_and_pid_enumeration_are_bounded(self):
        sizes=[]
        def read(home,pids):sizes.append(len(pids));return snap(150,rss=1)
        m=NativePressureMonitor('/unused',CFG,pids=lambda:iter(range(10000000)),snapshot_fn=read);m.started=time.monotonic()
        for _ in range(100):m._sample()
        r=m.report();self.assertEqual(r['sample_count'],100);self.assertEqual(len(r['samples']),64);self.assertEqual(max(sizes),32);self.assertLessEqual(len(r['transitions']),32)
    def test_context_stop_is_preemptible_and_cannot_cancel_after_exit(self):
        reads=[];cancel=threading.Event()
        def read(home,pids):reads.append(time.monotonic());return snap(1000)
        started=time.monotonic()
        with NativePressureMonitor('/unused',CFG,cancel=cancel,interval=1,snapshot_fn=read) as m:
            self.assertEqual(m.sample_count,1)
        self.assertLess(time.monotonic()-started,.5);self.assertTrue(m.report()['monitor_stopped']);m._sample();self.assertEqual(len(reads),1);self.assertFalse(cancel.is_set())
        with self.assertRaises(RuntimeError):m.start()
    def test_user_cancel_survives_observation_and_guard_is_shared(self):
        cancel=threading.Event();cancel.set();guard=ResourceGuard(CFG)
        m=self.monitor([snap(150)],cancel,guard=guard);m._sample();self.assertTrue(cancel.is_set());self.assertEqual(guard.state,'PRESSURE');self.assertIsNone(m.reason)

if __name__=='__main__':unittest.main()
