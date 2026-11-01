import os
import platform
from pathlib import Path
import resource
import shutil
import time
import re
import threading
def prune_runner_logs(home,days,clock=None):
    """Expire only known diagnostic runner names; never traverse user data."""
    cutoff=(time.time() if clock is None else clock)-days*86400;removed=0
    for path in (Path(home)/'logs').iterdir():
        if not re.fullmatch(r'(?:B1_DETAIL|B2_GIST|C2_CONTROL|C3_LANGUAGE|TEACHER)(?:\.previous(?:\.previous)?)?\.log',path.name) or path.is_symlink():continue
        try:
            if path.is_file() and path.stat().st_mtime<cutoff:path.unlink();removed+=1
        except FileNotFoundError:pass
    return removed
def device():return {"platform":platform.platform(),"machine":platform.machine(),"python":platform.python_version(),"android":bool(os.environ.get("ANDROID_ROOT") or "com.termux" in os.environ.get("PREFIX","")),"cpu_count":os.cpu_count()}
class _ProcResolver:
    """Resolve inner PIDs without attributing unrelated outer-namespace memory.

    /proc may be mounted from an ancestor PID namespace. NSpid plus the PID
    namespace inode identifies our namespace's PID; starttime detects reuse.
    Scans and negative lookups are bounded. A reused PID stays unmeasurable for
    this resolver's lifetime because a numeric PID alone cannot identify its
    original process.
    """
    def __init__(self,root=Path('/proc'),own_pid=None,max_scan=4096,clock=time.monotonic,max_tracked=4096):
        self.root=Path(root);self.own_pid=os.getpid() if own_pid is None else own_pid
        self.max_scan=max_scan;self.max_tracked=max_tracked;self.clock=clock;self.cache={};self.missing={};self.reused=set();self.lock=threading.RLock()
    def identity(self,path):
        status=(path/'status').read_text();nspid=None;proc_pid=None
        for line in status.splitlines():
            if line.startswith('NSpid:'):nspid=tuple(int(x) for x in line.split()[1:])
            elif line.startswith('Pid:'):proc_pid=int(line.split()[1])
        stat=(path/'stat').read_text().rsplit(')',1)[1].split()
        # stat remainder starts at field 3; starttime is field 22.
        return (os.readlink(path/'ns/pid'),nspid,proc_pid,int(stat[19]))
    def _ours(self,identity,own,pid):
        ns,nspid,proc_pid,start=identity
        if ns!=own[0]:return False
        if nspid is not None:return bool(nspid) and nspid[-1]==pid
        # Kernels without NSpid are safe only when /proc/self exposes our PID.
        return own[2]==self.own_pid and proc_pid==pid
    def resolve(self,pid):
        own_path=self.root/'self';own=self.identity(own_path)
        if pid==self.own_pid:return own_path,own
        if pid in self.reused:return None,None
        if pid not in self.cache and pid not in self.missing and len(self.cache)+len(self.missing)+len(self.reused)>=self.max_tracked:return None,None
        old=self.cache.get(pid)
        if old:
            path,identity=old
            try:current=self.identity(path)
            except (OSError,ValueError,IndexError):current=None
            if current==identity and self._ours(current,own,pid):return old
            self.cache.pop(pid,None);self.reused.add(pid)
            return None,None
        if self.missing.get(pid,0)>self.clock():return None,None
        direct=self.root/str(pid)
        try:
            identity=self.identity(direct)
            if self._ours(identity,own,pid):
                self.missing.pop(pid,None);self.cache[pid]=(direct,identity);return direct,identity
        except (OSError,ValueError,IndexError):pass
        # Resolving descendants in another namespace is intentionally unsupported.
        # Walk at most max_scan entries, and require namespace identity, not only
        # a coincidentally matching NSpid suffix in an unrelated container.
        with os.scandir(self.root) as entries:
            for count,entry in enumerate(entries):
                if count>=self.max_scan:break
                if not entry.name.isdecimal():continue
                path=self.root/entry.name
                try:
                    identity=self.identity(path)
                    if self._ours(identity,own,pid):
                        self.missing.pop(pid,None);self.cache[pid]=(path,identity);return path,identity
                except (OSError,ValueError,IndexError):continue
        self.missing[pid]=self.clock()+2.;return None,None
    def memory(self,pid):
        result={'pid':pid,'rss_bytes':None,'pss_bytes':None,'mapped_file_bytes':None,'minor_faults':None,'major_faults':None,'measurement_status':'UNAVAILABLE','resolved_proc_pid':None}
        with self.lock:
            try:path,identity=self.resolve(pid)
            except (OSError,ValueError,IndexError):return result
            if path is None:return result
            measured={}
            try:
                for line in (path/'status').read_text().splitlines():
                    if line.startswith('VmRSS:'):measured['rss_bytes']=int(line.split()[1])*1024
            except (OSError,ValueError,IndexError):pass
            try:
                for line in (path/'smaps_rollup').read_text().splitlines():
                    if line.startswith('Pss:'):measured['pss_bytes']=int(line.split()[1])*1024
            except (OSError,ValueError,IndexError):pass
            try:
                stats=(path/'stat').read_text().rsplit(')',1)[1].split();measured['minor_faults']=int(stats[7]);measured['major_faults']=int(stats[9])
            except (OSError,ValueError,IndexError):pass
            try:
                mapped=0
                for line in (path/'maps').read_text().splitlines():
                    if '/' in line:a,b=line.split()[0].split('-');mapped+=int(b,16)-int(a,16)
                measured['mapped_file_bytes']=mapped
            except (OSError,ValueError,IndexError):pass
            try:after=self.identity(path)
            except (OSError,ValueError,IndexError):return result
            if after!=identity:
                self.cache.pop(pid,None);self.reused.add(pid);return result
            result.update(measured,resolved_proc_pid=identity[2])
            result['measurement_status']='MEASURED' if all(result[k] is not None for k in ('rss_bytes','pss_bytes','mapped_file_bytes','minor_faults','major_faults')) else 'PARTIAL'
            return result

_PROC_RESOLVER=_ProcResolver()
def process_memory(pid=None):
    """Current process uses /proc/self; children require verified PID identity."""
    global _PROC_RESOLVER
    own=os.getpid()
    if _PROC_RESOLVER.own_pid!=own:_PROC_RESOLVER=_ProcResolver(own_pid=own)
    return _PROC_RESOLVER.memory(own if pid is None else pid)
def snapshot(home,pids=()):
    available=total=temp=battery=charging=None
    try:
        vals={l.split(":")[0]:int(l.split()[1])*1024 for l in Path("/proc/meminfo").read_text().splitlines()};available=vals.get("MemAvailable");total=vals.get("MemTotal")
    except (OSError,ValueError):pass
    for base in [Path("/sys/class/power_supply/battery"),Path("/sys/class/power_supply/BAT0")]:
        try:temp=float((base/"temp").read_text())/10
        except (OSError,ValueError):pass
        try:battery=float((base/"capacity").read_text())
        except (OSError,ValueError):pass
        try:charging=(base/"status").read_text().strip() in {"Charging","Full"}
        except OSError:pass
    return {"wall_time":time.time(),"mem_available_bytes":available,"mem_total_bytes":total,"free_disk_bytes":shutil.disk_usage(home).free,"battery_temperature_c":temp,"battery_percent":battery,"charging":charging,"processes":[process_memory(p) for p in [os.getpid(),*pids]],"own_peak_rss_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
class ResourceGuard:
    def __init__(self,cfg):self.cfg=cfg;self.state="NORMAL"
    def update(self,s):
        mem=s["mem_available_bytes"];temp=s["battery_temperature_c"];floor=self.cfg["minimum_free_mb"]*1024*1024;limit=self.cfg["thermal_limit_c"]
        if (mem is not None and mem<floor) or (temp is not None and temp>=limit):new="CRITICAL"
        elif (mem is not None and mem<2*floor) or (temp is not None and temp>=limit-3):new="PRESSURE"
        elif self.state in {"CRITICAL","PRESSURE"}:new="RECOVERY"
        else:new="NORMAL"
        self.state=new;return new
