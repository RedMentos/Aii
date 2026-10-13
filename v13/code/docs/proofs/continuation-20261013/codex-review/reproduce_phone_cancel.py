#!/usr/bin/env python3
"""Actual original phone handler with a synthetic stalled install; no native/model work.

Run from any location. Original install/model/build are replaced by bound stubs
so the only work after PARITY is sleep. It demonstrates signal handling, not
native numerical behavior or a Redmi run. The original file is never edited.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

APP = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(APP / 'scripts'))
import tool_forecast_bounded_phone_candidate as bounded


def child(home, out):
    import test_tool_forecast_phone as original
    want = json.loads(original.tf.MANIFEST.read_text())['encoder']['model_sha256']
    original.ModelManager = lambda _: type('StubManager', (), {'path_for': lambda self, _: Path(home) / 'stub.gguf'})()
    original.file_hash = lambda _: want
    original.catalog = lambda: {'runner': {}}
    original.port.installed_identity = lambda *_: {'library_directory': str(home)}
    original.build_taps = lambda *_: (Path(home) / 'stub-tool', {'binary_sha256': 'SYNTHETIC_NOT_EXECUTED', 'identity_key': {}})
    def stalled_install(_):
        print('STALL_READY: installer replaced by sleep, no models loaded', flush=True)
        time.sleep(30)
        raise RuntimeError('synthetic stall finished')
    original.installer.install = stalled_install
    sys.argv = ['original-driver', '--installed-home', str(home), '--out-dir', str(out)]
    original.main()


def main():
    if len(sys.argv) == 4 and sys.argv[1] == 'child':
        child(Path(sys.argv[2]), Path(sys.argv[3]))
        return
    root = Path(sys.argv[1]).absolute()
    root.mkdir(parents=True, exist_ok=False)
    home = root / 'home'
    (home / 'data').mkdir(parents=True)
    cmd = [sys.executable, '-u', str(Path(__file__).resolve()), 'child', str(home)]
    original_out = root / 'original-driver'
    before_log = root / 'original.log'
    proc = None
    with before_log.open('wb') as log:
        try:
            proc = subprocess.Popen(cmd + [str(original_out)], stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            deadline = time.monotonic() + 10
            while 'STALL_READY' not in before_log.read_text() and proc.poll() is None and time.monotonic() < deadline:
                time.sleep(.02)
            if 'STALL_READY' not in before_log.read_text():
                raise RuntimeError('Original driver did not reach synthetic installer stall')
            os.kill(proc.pid, signal.SIGTERM)
            time.sleep(.25)
            still_running = proc.poll() is None
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
        finally:
            if proc and proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
    candidate_out = root / 'candidate'
    driver_report = candidate_out / 'device-check/report.json'
    after = bounded.run_driver(cmd + [str(driver_report.parent)], candidate_out,
                               timeout_s=1., grace_s=.1, driver_report=driver_report)
    report = {'schema': 'V13_PHONE_CANCEL_REPRO_V1',
              'original_phone_driver_sha256': bounded.sha_file(APP / 'scripts/test_tool_forecast_phone.py'),
              'bounded_candidate_sha256': bounded.sha_file(Path(bounded.__file__)),
              'reproducer_sha256': bounded.sha_file(Path(__file__)),
              'original_still_running_after_sigterm_250ms': still_running,
              'original_manually_killed_and_reaped': True,
              'candidate_status': after['status'], 'candidate_leader_reaped': after['leader_reaped'],
              'candidate_signals': after['signals'], 'candidate_elapsed_seconds': after['elapsed_seconds'],
              'partial_child_report_preserved': driver_report.is_file(),
              'native_models_launched': False, 'phone_measured': False,
              'claim_scope': 'Actual original signal handler with synthetic installer stall; software lifecycle only.'}
    bounded.save(root / 'repro.json', report)
    print(json.dumps(report, sort_keys=True))
    if not still_running or after['status'] != 'DEADLINE' or not after['leader_reaped']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
