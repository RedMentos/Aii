"""Bounded resource observation for the existing F7 state machine.

The monitor never kills a process or writes Store state. Critical measurements
signal the existing cancellation Event; the owner preserves output and unloads
native runners through its normal cancellation path.
"""
from collections import deque
import threading
import time
from .resources import ResourceGuard,snapshot

class NativePressureMonitor:
    def __init__(self,home,cfg,pids=(),cancel=None,guard=None,interval=.25,phase=None,snapshot_fn=snapshot,request_cancel=None):
        self.home=home;self.cfg=cfg;self.pids=pids;self.cancel=cancel or threading.Event()
        self.guard=guard or ResourceGuard(cfg);self.interval=max(.1,min(1.,float(interval)))
        self.phase=phase;self.snapshot_fn=snapshot_fn;self.done=threading.Event();self.lock=threading.RLock()
        self.samples=deque(maxlen=64);self.transitions=deque(maxlen=32);self.sample_count=0;self.failures=0
        self.reason=None;self.critical_snapshot=None;self.started=None;self.finished=None;self.thread=None
        self.request_cancel=request_cancel;self.resource_cancel_signalled=False
        self.peaks={'rss_bytes':None,'pss_bytes':None};self.last_state=self.guard.state
    def _sample(self):
        if self.done.is_set():return
        try:
            ids=self.pids() if callable(self.pids) else self.pids
            # Native pool size is small; bound both enumeration and report size.
            import itertools
            ids=list(dict.fromkeys(itertools.islice(ids,32)))
            row=self.snapshot_fn(self.home,ids)
            phase=self.phase() if callable(self.phase) else self.phase
            with self.lock:
                if self.done.is_set():return
                state=self.guard.update(row);elapsed=time.monotonic()-self.started
                entry={'elapsed_s':elapsed,'phase':phase,'resource_state':state,'snapshot':row}
                self.samples.append(entry);self.sample_count+=1
                if state!=self.last_state:
                    self.transitions.append({'elapsed_s':elapsed,'from':self.last_state,'to':state});self.last_state=state
                for process in row.get('processes',[]):
                    for key in self.peaks:
                        value=process.get(key)
                        if value is not None:self.peaks[key]=max(self.peaks[key] or 0,value)
                if state=='CRITICAL' and self.reason is None:
                    low=row.get('mem_available_bytes') is not None and row['mem_available_bytes']<self.cfg['minimum_free_mb']*1024*1024
                    hot=row.get('battery_temperature_c') is not None and row['battery_temperature_c']>=self.cfg['thermal_limit_c']
                    self.reason='MEMORY_AND_THERMAL_CRITICAL' if low and hot else ('MEMORY_CRITICAL' if low else 'THERMAL_CRITICAL')
                    self.critical_snapshot=entry
                    if self.request_cancel:self.resource_cancel_signalled=bool(self.request_cancel())
                    elif not self.cancel.is_set():self.cancel.set();self.resource_cancel_signalled=True
        except Exception:
            # Missing proc/sysfs fields are null in snapshot; unexpected observer
            # failure is diagnosed without fabricating a normal/critical sample.
            with self.lock:self.failures+=1
    def _watch(self):
        while not self.done.wait(self.interval):self._sample()
    def start(self):
        if self.started is not None:raise RuntimeError('Pressure monitor is single-use')
        self.started=time.monotonic();self._sample()
        self.thread=threading.Thread(target=self._watch,name='v13-native-pressure',daemon=True);self.thread.start();return self
    def stop(self):
        self.done.set()
        if self.thread:self.thread.join(timeout=1.25)
        self.finished=time.monotonic();return self.report()
    def report(self):
        with self.lock:
            return {'resource_state':self.last_state,'critical_reason':self.reason,'resource_cancel_signalled':self.resource_cancel_signalled,'sample_count':self.sample_count,'observer_failures':self.failures,'sample_interval_s':self.interval,'samples':list(self.samples),'transitions':list(self.transitions),'critical_snapshot':self.critical_snapshot,'sampled_peak_rss_bytes':self.peaks['rss_bytes'],'sampled_peak_pss_bytes':self.peaks['pss_bytes'],'monitor_stopped':self.done.is_set() and (self.thread is None or not self.thread.is_alive()),'duration_s':None if self.started is None else (self.finished or time.monotonic())-self.started,'native_kv_bytes':None}
    def __enter__(self):return self.start()
    def __exit__(self,*exc):self.stop()
