#!/usr/bin/env python3
"""Run the existing phone check with a deadline, owned-process cleanup and durable partial output.

Independent candidate: it does not change Thread M's native driver, plans,
forecasts, thresholds, encoder installation or authority. The wrapper receipt
describes execution only; read device-check/report.json for actual checks.
Linux/Termux POSIX process groups are required. No other process is signalled.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

APP = Path(__file__).resolve().parents[1]
DRIVER = APP / 'scripts/test_tool_forecast_phone.py'
SCHEMA = 'V13_BOUNDED_TOOL_FORECAST_DEVICE_DRIVER_CANDIDATE_V1'


def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(1 << 20):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.new')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def read_report(path):
    try:
        value = json.loads(Path(path).read_text())
        if not isinstance(value, dict) or not isinstance(value.get('status'), str):
            return None
        return value
    except (OSError, ValueError):
        return None


def run_driver(command, output, *, timeout_s, grace_s=3., cancel=None,
               driver_report=None, binding=None, progress=None):
    """Spawn a new owned session. On cancellation/deadline TERM then KILL the entire group.

    A killed child can leave its report incomplete. Preserve all bytes and use
    an independent receipt; never rewrite its model report as PASS/FAIL.
    command is an argv list, never a shell command. No externally supplied PIDs.
    """
    if not math.isfinite(timeout_s) or timeout_s <= 0 or not math.isfinite(grace_s) or grace_s < 0:
        raise ValueError('Finite positive timeout and nonnegative grace required')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    cancel = cancel or threading.Event()
    report_path = output / 'wrapper-report.json'
    report = {'schema': SCHEMA, 'status': 'PREPARING', 'command': list(command),
              'timeout_seconds': timeout_s, 'grace_seconds': grace_s,
              'binding': binding or {}, 'native_quality_claimed': False,
              'phone_measured_by_wrapper': False, 'canonical_gate_pass': False,
              'partial_outputs_preserved': True, 'signals': []}
    save(report_path, report)
    start = time.monotonic()
    proc = None
    stop = None
    try:
        if cancel.is_set():
            report['status'] = 'CANCELLED_BEFORE_START'
            return report
        with (output / 'driver.log').open('wb') as log:
            proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, start_new_session=True)
            report |= {'status': 'RUNNING', 'owned_pid': proc.pid, 'owned_pgid': proc.pid}
            save(report_path, report)
            last_update = 0.
            while proc.poll() is None:
                elapsed = time.monotonic() - start
                if cancel.is_set():
                    stop = 'CANCELLED'
                    break
                if elapsed >= timeout_s:
                    stop = 'DEADLINE'
                    break
                if elapsed - last_update >= 5.:
                    child = read_report(driver_report) if driver_report else None
                    report['elapsed_seconds'] = round(elapsed, 3)
                    report['child_status_observed'] = (child or {}).get('status')
                    save(report_path, report)
                    if progress:
                        progress(report)
                    last_update = elapsed
                cancel.wait(min(.05, max(.001, timeout_s - elapsed)))
            if stop:
                def send(sig):
                    try:
                        os.killpg(proc.pid, sig)
                        report['signals'].append(signal.Signals(sig).name)
                    except ProcessLookupError:
                        pass
                send(signal.SIGTERM)
                report['status'] = stop + '_CLEANING_UP'
                save(report_path, report)
                # The leader may exit while a native descendant ignores TERM.
                # Keep the group cleanup deadline, then kill surviving descendants.
                end = time.monotonic() + grace_s
                while time.monotonic() < end:
                    proc.poll()
                    try:
                        os.killpg(proc.pid, 0)
                    except ProcessLookupError:
                        break
                    time.sleep(min(.05, max(0., end - time.monotonic())))
                send(signal.SIGKILL)
            rc = proc.wait()
            log.flush()
            os.fsync(log.fileno())
        child = read_report(driver_report) if driver_report else None
        report |= {'status': stop or ('DRIVER_EXITED' if rc == 0 else 'DRIVER_ERROR'),
                   'driver_exit_code': rc, 'leader_reaped': True,
                   'child_status_observed': (child or {}).get('status'),
                   'driver_log_sha256': sha_file(output / 'driver.log')}
        if driver_report and Path(driver_report).is_file():
            report['child_report_sha256'] = sha_file(driver_report)
            report['child_report_path'] = str(Path(driver_report).absolute())
        if stop is None and rc == 0 and driver_report and child is None:
            report['status'] = 'DRIVER_REPORT_MISSING_OR_INVALID'
        elif stop is None and rc == 0 and driver_report and child['status'] not in (
                'PARITY_PASS_NO_LIVE', 'LIVE_PATH_CONFIRMED', 'LIVE_PATH_CONFIRMED+CONTINUAL_LEARNING_CONFIRMED'):
            report['status'] = 'DRIVER_CHECKS_NOT_CONFIRMED'
        return report
    except BaseException as exc:
        report |= {'status': 'WRAPPER_ERROR', 'error': type(exc).__name__ + ': ' + str(exc)[:400]}
        if proc and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
                report['signals'].append('SIGKILL')
            except ProcessLookupError:
                pass
            proc.wait()
            report['leader_reaped'] = True
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        return report
    finally:
        report['elapsed_seconds'] = round(time.monotonic() - start, 3)
        save(report_path, report)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--installed-home', required=True)
    ap.add_argument('--out-dir')
    ap.add_argument('--timeout-seconds', type=float, default=7200.)
    ap.add_argument('--grace-seconds', type=float, default=3.)
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--skip-live', action='store_true')
    ap.add_argument('--with-learning', action='store_true')
    args = ap.parse_args(argv)
    if (not math.isfinite(args.timeout_seconds) or not 1 <= args.timeout_seconds <= 86400
            or not math.isfinite(args.grace_seconds) or not 0 <= args.grace_seconds <= 30
            or not 1 <= args.threads <= 32):
        ap.error('timeout 1..86400 seconds; grace 0..30 seconds; threads 1..32')
    home = Path(args.installed_home).expanduser().absolute()
    out = Path(args.out_dir).absolute() if args.out_dir else home / 'exports' / (
        'tool-forecast-bounded-' + time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid()))
    if out.exists():
        ap.error('Fresh output folder required; previous outputs are preserved')
    cancel = threading.Event()
    handlers = {s: signal.signal(s, lambda *_: cancel.set()) for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        child_report = out / 'device-check/report.json'
        command = [sys.executable, str(DRIVER), '--installed-home', str(home),
                   '--out-dir', str(child_report.parent), '--threads', str(args.threads)]
        if args.skip_live:
            command.append('--skip-live')
        if args.with_learning:
            command.append('--with-learning')
        paths = [DRIVER, Path(__file__), APP / 'v13/toolforecast.py', APP / 'specs/tool-forecast.json',
                 APP / 'scripts/install_tool_forecast.py', APP / 'scripts/native_layer_taps.cpp',
                 APP / 'scripts/test_native_prefill_port.py', APP / 'scripts/tool_forecast_live_check.py',
                 APP / 'scripts/tool_forecast_learning_check.py', APP / 'specs/tool_forecast/live-plan.json',
                 APP / 'specs/tool_forecast/learning-plan.json']
        binding = {str(p.relative_to(APP)): sha_file(p) for p in paths}
        report = run_driver(command, out, timeout_s=args.timeout_seconds, grace_s=args.grace_seconds,
                            cancel=cancel, driver_report=child_report, binding=binding,
                            progress=lambda r: print('Prüfung läuft: %s (%.0f s)' % (
                                r.get('child_status_observed') or r['status'], r['elapsed_seconds']), flush=True))
        print('Bericht: %s (%s)' % (out / 'wrapper-report.json', report['status']), flush=True)
        return {'DRIVER_EXITED': 0, 'CANCELLED': 130, 'CANCELLED_BEFORE_START': 130,
                'DEADLINE': 124}.get(report['status'], 1)
    finally:
        for s, handler in handlers.items():
            signal.signal(s, handler)


if __name__ == '__main__':
    sys.exit(main())
