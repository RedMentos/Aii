"""Run175 isolated Linux subreaper/pidfd candidate (NOT cgroup replacement).

Controller process must be dedicated to exactly one owned experiment. No PID
signals or post-reap killpg; pidfd is required for every descendant signal.
"""
import ctypes
import errno
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

PR_SET_CHILD_SUBREAPER=36

def enable_subreaper():
    libc=ctypes.CDLL(None,use_errno=True)
    if libc.prctl(PR_SET_CHILD_SUBREAPER,1,0,0,0)!=0:
        raise OSError(ctypes.get_errno(),'prctl subreaper refused')

def adopted_children():
    """Read /proc PPid, never infer ownership from recycled process groups."""
    found=[];own=os.getpid()
    for item in Path('/proc').iterdir():
        if not item.name.isdecimal():continue
        try:
            s=(item/'status').read_text()
            fields=dict(x.split(':',1) for x in s.splitlines() if ':' in x)
            if int(fields['PPid'].strip())==own:found.append(int(item.name))
        except (OSError,KeyError,ValueError):continue
    return found

def reap_adopted(deadline):
    """Only direct children of dedicated subreaper; all kills by stable pidfd."""
    found=set();killed=set();reaped=set()
    while time.monotonic()<deadline:
        for pid in adopted_children():
            found.add(pid)
            try:fd=os.pidfd_open(pid,0)
            except ProcessLookupError:continue
            try:
                try:signal.pidfd_send_signal(fd,signal.SIGKILL,None,0);killed.add(pid)
                except ProcessLookupError:pass
            finally:os.close(fd)
        while True:
            try:pid,_=os.waitpid(-1,os.WNOHANG)
            except ChildProcessError:break
            if not pid:break
            reaped.add(pid)
        if not adopted_children():
            return {'adopted':len(found),'killed_by_pidfd':len(killed),
                    'reaped':len(reaped),'remaining':0,'closed':True}
        time.sleep(.02)
    return {'adopted':len(found),'killed_by_pidfd':len(killed),
            'reaped':len(reaped),'remaining':len(adopted_children()),'closed':False}

def run_case(double_fork=False):
    if not (sys.platform.startswith('linux') and hasattr(os,'pidfd_open') and
            hasattr(signal,'pidfd_send_signal') and Path('/proc').is_dir()):
        raise RuntimeError('run175_requires_linux_pidfd_and_proc')
    if adopted_children():
        raise RuntimeError('run175_requires_dedicated_childless_controller')
    enable_subreaper()
    with tempfile.TemporaryDirectory(prefix='v13-run175-') as d:
        mark=Path(d)/'spawned.pid'
        code=(
            'import os,subprocess,sys,time\n'
            + ('p=os.fork()\nif p:\n sys.exit(0)\nos.setsid()\n' if double_fork else '')
            + 'p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"],start_new_session=True)\n'
            + 'open(sys.argv[1],"w").write(str(p.pid))\n'
        )
        proc=subprocess.Popen([sys.executable,'-c',code,str(mark)],stdin=subprocess.DEVNULL,
                              stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,start_new_session=True)
        try:
            proc.wait(timeout=5)
            until=time.monotonic()+3
            while not mark.is_file() and time.monotonic()<until:time.sleep(.01)
            if not mark.is_file():raise RuntimeError('run175_child_marker_missing')
            spawned=int(mark.read_text())
            # Parent may have exited but a double-forked intermediate is still running.
            until=time.monotonic()+2
            while spawned not in adopted_children() and time.monotonic()<until:time.sleep(.01)
            cleanup=reap_adopted(time.monotonic()+4)
            if not cleanup['closed'] or cleanup['adopted']<1:
                raise RuntimeError('run175_orphan_cleanup_unverified')
            return {'schema':'V13_RUN175_SUBREAPER_PIDFD_V1','double_fork':double_fork,
                    'leader_returncode':proc.returncode,'orphan_adopted':True,
                    'cleanup':cleanup,'evidence_class':'LINUX_NATIVE_SYNTHETIC_PROCESS_ONLY',
                    'cgroup_isolation_proven':False,'body_model_executed':False,
                    'full_v13_proven':False}
        finally:
            if proc.poll() is None:proc.kill();proc.wait()
            # Exception path must also try to reap only this dedicated controller's
            # adopted descendants. No unsafe numeric-PID fallback is permitted.
            if adopted_children():
                reap_adopted(time.monotonic()+4)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--double-fork',action='store_true');args=p.parse_args()
    print(json.dumps(run_case(args.double_fork),sort_keys=True,indent=2))
