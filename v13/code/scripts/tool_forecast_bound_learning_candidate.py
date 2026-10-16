#!/usr/bin/env python3
"""Preregister and run a fresh, source-bound native SHADOW learning cohort.

The original parity, learner and numerical gates are unchanged. A separate
integrity gate requires every planned call, and each completed call is fsynced
before continuing. No resume, changed-source continuation, or phone claim.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import sys
import threading
import time
import traceback
import numpy as np

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
sys.path.insert(0, str(APP / 'scripts'))
from scripts.tool_forecast_bounded_phone_candidate import save, sha_file, run_driver
from scripts.tool_forecast_learning_integrity_candidate import analyze_checked, expected_grid
from scripts import tool_forecast_learning_check as original
from scripts import install_tool_forecast as installer
from scripts import test_native_prefill_port as port
from v13.models import ModelManager, catalog
from v13 import toolforecast as F
from v13.agi import hub
from v13.runtime import Runtime

SCHEMA = 'V13_BOUND_NATIVE_LEARNING_CANDIDATE_V1'
CONFIRMED = 'CONTINUAL_LEARNING_CONFIRMED'
LIMIT = ('Linux native Qwen taps and closed-form residual adaptation in two fixed tool worlds; '
         'SHADOW only, no decision authority, no Redmi measurement, no general learning or Canon pass.')


def source_binding(root=APP):
    root = Path(root)
    paths = [p for directory in ('v13', 'scripts', 'specs') for p in (root / directory).rglob('*')
             if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py', '.cpp', '.h', '.json', '.npz')]
    return {str(p.relative_to(root)): sha_file(p) for p in sorted(paths)}


def native_binding(home):
    home = Path(home)
    identity = port.installed_identity(home, ModelManager(home).path_for('B2_GIST'), catalog()['runner'])
    tool = home / 'bin/native-layer-taps'
    if not tool.is_file():
        raise ValueError('Build the pinned native-layer-taps before preregistration')
    return identity | {'tool_path': str(tool), 'tool_sha256': sha_file(tool),
                       'build_marker_sha256': sha_file(home / 'config/native-layer-taps.json')}


def numerical_runtime_binding():
    numpy_root = Path(np.__file__).resolve().parent
    extensions = sorted(numpy_root.rglob('*.so'))
    bundled = numpy_root.parent / 'numpy.libs'
    if bundled.is_dir():
        extensions += sorted(p for p in bundled.iterdir() if p.is_file())
    return {'python': sys.version, 'executable': str(Path(sys.executable).resolve()),
            'executable_sha256': sha_file(sys.executable), 'numpy': np.__version__,
            'numpy_init_sha256': sha_file(np.__file__),
            'numpy_native_libraries': {str(p): sha_file(p) for p in extensions},
            'platform': platform.platform(), 'machine': platform.machine(),
            'thread_environment': {k: os.environ.get(k) for k in
                                   ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')}}


def verify_sources(prereg, root=APP):
    got = source_binding(root)
    if got != prereg['sources']:
        changed = sorted(k for k in set(got) | set(prereg['sources']) if got.get(k) != prereg['sources'].get(k))
        raise ValueError('SOURCE_BINDING_CHANGED: ' + ', '.join(changed[:12]))


def claim_cohort(home, prereg_sha256, out):
    """One attempt per preregistration, including failed or interrupted attempts.

    The caller holds the installed-home coordinator lock. This durable claim
    prevents accidental sequential retries under the same preregistration.
    It is an audit control, not protection against an operator deleting files.
    """
    directory = Path(home) / 'data/tool_forecast/cohort-claims'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (prereg_sha256 + '.json')
    try:
        with path.open('x') as stream:
            json.dump({'preregistration_sha256': prereg_sha256, 'original_output': str(Path(out).resolve()),
                       'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                       'consumed_even_if_interrupted': True}, stream, sort_keys=True)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        fd = os.open(directory, os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)
    except FileExistsError as exc:
        raise ValueError('PREREGISTRATION_ALREADY_CONSUMED: ' + str(path)) from exc
    return path


def preregister(home, plan, output):
    plan = Path(plan).resolve()
    doc = json.loads(plan.read_text())
    grid = expected_grid(doc)
    if len(grid) != 610 or doc.get('mode') != 'region':
        raise ValueError('This cohort requires the declared 610-call region plan')
    record = {'schema': SCHEMA, 'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'sources': source_binding(), 'native': native_binding(home),
              'numerical_runtime': numerical_runtime_binding(),
              'plan_path': str(plan), 'plan_sha256': sha_file(plan), 'plan': doc,
              'plan_scope': doc.get('claim_limit'), 'retention_controls': doc.get('retention_controls'),
              'gates': dict(original.GATES), 'expected_calls': len(grid), 'threads': 4,
              'experience_calls': 250, 'held_out_calls': 360, 'maximum_seconds': 7200,
              'rule': F.LEARN_RULE, 'scope': LIMIT,
              'failure_policy': 'No retuning, dropped calls, resume, or replacement after inspecting outcomes. Preserve negative and partial evidence.'}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(record, stream, indent=1, sort_keys=True, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    return record


class Journal(list):
    def __init__(self, path, prereg_sha256, progress):
        super().__init__()
        self.path, self.binding, self.progress = Path(path), prereg_sha256, progress

    def append(self, row):
        value = row | {'ordinal': len(self), 'preregistration_sha256': self.binding}
        with self.path.open('a') as stream:
            stream.write(json.dumps(value, sort_keys=True, allow_nan=False) + '\n')
            stream.flush(); os.fsync(stream.fileno())
        super().append(value)
        self.progress(len(self), row)


def worker(home, prereg_path, out):
    home, out, prereg_path = Path(home).resolve(), Path(out).resolve(), Path(prereg_path).resolve()
    prereg = json.loads(prereg_path.read_text())
    out.mkdir(parents=True, exist_ok=False)
    report = {'schema': SCHEMA, 'status': 'VERIFYING', 'verdict': 'CONTINUAL_LEARNING_NOT_CONFIRMED',
              'preregistration_sha256': sha_file(prereg_path), 'scope': LIMIT,
              'plan_scope': prereg.get('plan_scope'), 'retention_controls': prereg.get('retention_controls'),
              'canonical_gate_pass': False, 'phone_measured': False, 'receiver_authority': 0}
    start = time.monotonic(); runtime = None; rows = None
    path = out / 'report.json'
    save(path, report)
    try:
        with (home / 'data/coordinator.lock').open('a+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if prereg.get('schema') != SCHEMA or prereg['gates'] != original.GATES or prereg['rule'] != F.LEARN_RULE:
                raise ValueError('Invalid or stale preregistration')
            verify_sources(prereg)
            if numerical_runtime_binding() != prereg['numerical_runtime']:
                raise ValueError('NUMERICAL_RUNTIME_CHANGED')
            if native_binding(home) != prereg['native']:
                raise ValueError('NATIVE_BINDING_CHANGED')
            plan_doc = prereg['plan']
            if sha_file(prereg['plan_path']) != prereg['plan_sha256']:
                raise ValueError('PLAN_FILE_CHANGED')
            claim = claim_cohort(home, report['preregistration_sha256'], out)
            report['cohort_claim_path'] = str(claim)
            shutil.copyfile(prereg_path, out / 'preregistration.json')
            report['status'] = 'PARITY'; save(path, report)
            n = prereg['native']
            rc = installer.install(argparse.Namespace(home=str(home), tool=n['tool_path'], model=n['model_path'],
                                     threads=prereg['threads'], backend_dir=n['library_directory']))
            encfile = home / 'data/tool_forecast' / ('encoder.json' if rc == 0 else 'encoder-parity-failed.json')
            enc = json.loads(encfile.read_text())
            save(out / 'encoder.json', enc)
            report['parity'] = enc['parity']
            if rc:
                report['status'] = 'PARITY_FAIL'
                return 1
            verify_sources(prereg)
            test_home = out / 'home'
            (test_home / 'data/tool_forecast').mkdir(parents=True)
            shutil.copyfile(encfile, test_home / 'data/tool_forecast/encoder.json')
            runtime = Runtime(test_home)
            runtime.sleep.cycle.set_policy('enabled', 'off')
            g, tf = hub(runtime), F.for_runtime(runtime)
            tf.set_mode('SHADOW'); g.tools.enable('calc'); g.tools.enable('sandbox_note')
            def progress(count, row):
                report.update(completed_calls=count, last_arm=row['arm'], elapsed_seconds=round(time.monotonic()-start, 2))
                save(path, report)
                if count % 10 == 0:
                    print(json.dumps({k: report[k] for k in ('status', 'completed_calls', 'elapsed_seconds')}), flush=True)
            rows = Journal(out / 'rows.jsonl', report['preregistration_sha256'], progress)
            report['status'] = 'EXPERIENCE'; save(path, report)
            original.live.run_arms(runtime, g, tf, plan_doc['plan'], original.EXP_ARMS, rows)
            snapshot = original.snapshot_experience(test_home, out, rows, plan_doc)
            report['phase_a_experience'] = snapshot
            verify_sources(prereg)
            report['status'] = 'LEARNING'; save(path, report)
            learned = tf.learn(mode='region')
            save(out / 'learn.json', learned)
            original.verify_experience_snapshot(out, snapshot, learned)
            report['status'] = 'HELD_OUT'; save(path, report)
            original.live.run_arms(runtime, g, tf, plan_doc['plan'],
                          ('calc_shift_test', 'calc_in_test', 'note_shift_test', 'note_in_test'), rows)
            save(out / 'rows.json', rows)
            verify_sources(prereg)
            if native_binding(home) != prereg['native']:
                raise ValueError('NATIVE_BINDING_CHANGED_AFTER_RUN')
            if numerical_runtime_binding() != prereg['numerical_runtime']:
                raise ValueError('NUMERICAL_RUNTIME_CHANGED_AFTER_RUN')
            if sha_file(test_home / 'data/tool_forecast/encoder.json') != sha_file(encfile):
                raise ValueError('ENCODER_BINDING_CHANGED_AFTER_RUN')
            original.verify_experience_snapshot(out, snapshot, learned)
            report['phase_a_snapshot_verified_after'] = True
            analysis = analyze_checked(rows, learned, plan_doc)
            save(out / 'analysis.json', analysis)
            report |= {'status': analysis['verdict'], 'verdict': analysis['verdict'], 'analysis': analysis,
                       'runtime_report': tf.report(), 'source_binding_verified_after': True,
                       'native_binding_verified_after': True, 'rows_sha256': sha_file(out / 'rows.jsonl')}
            return 0 if analysis['verdict'] == CONFIRMED else 1
    except BaseException as exc:
        report |= {'status': 'ERROR', 'error': type(exc).__name__ + ': ' + str(exc)[:600]}
        (out / 'error.txt').write_text(traceback.format_exc())
        return 1
    finally:
        try:
            if runtime:
                runtime.close()
        except BaseException as exc:
            report |= {'status': 'ERROR', 'verdict': 'CONTINUAL_LEARNING_NOT_CONFIRMED',
                       'shutdown_error': type(exc).__name__ + ': ' + str(exc)[:600]}
            raise
        finally:
            if rows is not None:
                save(out / 'rows.json', rows)
            report['elapsed_seconds'] = round(time.monotonic() - start, 2)
            save(path, report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('preregister', 'run', 'worker'))
    parser.add_argument('--home', required=True)
    parser.add_argument('--preregistration', required=True)
    parser.add_argument('--plan')
    parser.add_argument('--out')
    a = parser.parse_args()
    if a.command == 'preregister':
        if not a.plan: parser.error('--plan required')
        preregister(a.home, a.plan, a.preregistration)
        return 0
    if not a.out: parser.error('--out required')
    if a.command == 'worker':
        return worker(a.home, a.preregistration, a.out)
    prereg = json.loads(Path(a.preregistration).read_text())
    out = Path(a.out).resolve()
    cancel = threading.Event()
    handlers = {s: signal.signal(s, lambda *_: cancel.set()) for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        receipt = run_driver([sys.executable, str(Path(__file__).resolve()), 'worker', '--home', str(Path(a.home).resolve()),
                              '--preregistration', str(Path(a.preregistration).resolve()), '--out', str(out/'cohort')],
                             out, timeout_s=prereg['maximum_seconds'], cancel=cancel,
                             binding={'preregistration_sha256': sha_file(a.preregistration)})
        result_path = out/'cohort/report.json'
        result = json.loads(result_path.read_text()) if result_path.is_file() else {}
        return 0 if receipt['status'] == 'DRIVER_EXITED' and result.get('status') == CONFIRMED else 1
    finally:
        for sig, handler in handlers.items(): signal.signal(sig, handler)


if __name__ == '__main__':
    sys.exit(main())
