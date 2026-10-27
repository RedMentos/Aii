"""BP2b 12-arm serial native operator. No model loading on import or dry-run.

The registered cohort is defined exclusively by bp2b_native_runner.plan().
Partial batch execution is NOT a BP2b pass or an Age/learning promotion.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

from scripts.bp2b_native_runner import ARMS, SEEDS, plan, PIN_PATH, MASTER_SHA
from scripts.bp2b_master_preflight import verify as verify_master

REVISION = 'bp2b-native-batch-v1'
# The longest child suffix is "-s41-bp2b_minor" (15 chars); run_arm accepts
# at most 32 chars total and forbids dots. Validate before any native output.
PREFIX = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,16}\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')


def _verified_master_preflight(master_dir):
    # The pinned verifier requires a source-bound pin path and explicit full hash mode.
    return verify_master(master_dir, PIN_PATH, False)


def registered(prefix):
    if not isinstance(prefix, str) or not PREFIX.fullmatch(prefix) or '..' in prefix:
        raise ValueError('Invalid immutable attempt prefix')
    return [{'seed': seed, 'arm': arm, 'attempt': f'{prefix}-s{seed}-{arm}',
             'plan': plan(seed, arm)}
            for seed in SEEDS for arm in ARMS]


def _digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _write_atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.state-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, sort_keys=True, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _result_matches(path, job, expected_sha=None):
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError('Missing or symlinked native result')
    sha = _digest(path)
    if expected_sha is not None and sha != expected_sha:
        raise ValueError('Previously checkpointed native result changed')
    result = json.loads(path.read_text(encoding='utf-8'))
    if (result.get('status') != 'COMPLETED'
            or result.get('evidence_class') != 'LINUX_NATIVE_CANDIDATE'
            or result.get('seed') != job['seed']
            or result.get('arm') != job['arm']
            or result.get('plan') != job['plan']
            or result.get('age_authority') != 0
            or result.get('jepa_weight') != 0
            or result.get('master_sha256_verified_locally') is not True
            or not isinstance(result.get('adapter_sha256'), str)
            or not SHA.fullmatch(result['adapter_sha256'])):
        raise ValueError('Native result does not match frozen arm and negative gates')
    return sha


def _command(master_dir, out, job):
    return [sys.executable, str(Path(__file__).with_name('bp2b_native_runner.py')),
            '--seed', str(job['seed']), '--arm', job['arm'], '--out', str(out),
            '--master-dir', str(master_dir), '--attempt', job['attempt'], '--execute-native']


def execute(out, master_dir, prefix, max_jobs=12, timeout_seconds=2100,
            runner=subprocess.run, preflight=_verified_master_preflight):
    jobs = registered(prefix)
    if type(max_jobs) is not int or not 1 <= max_jobs <= len(jobs):
        raise ValueError('max_jobs must be 1..12; registered cohort remains 12')
    if type(timeout_seconds) is not int or timeout_seconds < 1:
        raise ValueError('Invalid positive timeout')
    # Hash the real pinned master before any batch state or attempt directory is created.
    master = preflight(master_dir)
    if (type(master) is not dict or master.get('status') != 'FULL_FILE_HASH_PASS'
            or master.get('master_sha256_verified_locally') is not True
            or master.get('master_expected_sha256') != MASTER_SHA):
        raise ValueError('Pinned public master preflight did not pass')
    out = Path(out).absolute()
    out.mkdir(parents=True, exist_ok=True)
    lock = out / '.bp2b-native-batch-owner.lock'
    with lock.open('a+b') as owner:
        try:
            fcntl.flock(owner.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('Another BP2b batch owns this output root') from exc
        state_dir = out / '.bp2b-batch' / prefix
        state_path = state_dir / 'STATE.json'
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding='utf-8'))
            if (state.get('revision') != REVISION or state.get('prefix') != prefix
                    or state.get('registered') != jobs
                    or state.get('master_pin_sha256') != master.get('pin_sha256')):
                raise ValueError('Existing batch checkpoint does not match immutable registration')
        else:
            if state_dir.exists() and any(state_dir.iterdir()):
                raise ValueError('Untracked batch directory; refusing overwrite')
            for job in jobs:
                attempt = out / f"seed-{job['seed']}" / job['arm'] / f"attempt-{job['attempt']}"
                if attempt.exists():
                    raise ValueError('Untracked native attempt exists: ' + str(attempt))
            state = {'revision': REVISION, 'prefix': prefix, 'registered': jobs,
                     'master_pin_sha256': master['pin_sha256'], 'evidence_class': 'PARTIAL_NATIVE_CANDIDATE',
                     'age_authority': 0, 'jepa_weight': 0, 'full_acceptance': False,
                     'attempts': {}, 'next_command': None}
            _write_atomic(state_path, state)
        for job in jobs[:max_jobs]:
            key = f"{job['seed']}:{job['arm']}"
            attempt = out / f"seed-{job['seed']}" / job['arm'] / f"attempt-{job['attempt']}"
            result = attempt / 'RESULT.json'
            old = state['attempts'].get(key)
            if old:
                if old.get('status') != 'COMPLETED':
                    raise ValueError('Existing failed/incomplete attempt must remain; use a new prefix')
                sha = _result_matches(result, job, old.get('result_sha256'))
                log = state_dir / f"log-s{job['seed']}-{job['arm']}.txt"
                if not log.is_file() or _digest(log) != old.get('log_sha256'):
                    raise ValueError('Previously checkpointed raw log changed')
                continue
            if attempt.exists():
                raise ValueError('Untracked native attempt exists; refusing overwrite')
            cmd = _command(master_dir, out, job)
            log = state_dir / f"log-s{job['seed']}-{job['arm']}.txt"
            if log.exists():
                raise ValueError('Untracked raw log exists; refusing overwrite')
            state['attempts'][key] = {'status': 'RUNNING', 'command': cmd,
                                      'started_unix': int(time.time())}
            state['next_command'] = ' '.join(cmd)
            _write_atomic(state_path, state)
            code = None
            with log.open('xb') as stream:
                try:
                    done = runner(cmd, stdout=stream, stderr=subprocess.STDOUT,
                                  timeout=timeout_seconds, check=False)
                    code = done.returncode
                except subprocess.TimeoutExpired:
                    code = 124
                except Exception as exc:
                    code = 125
                    stream.write(('RUNNER_EXCEPTION ' + type(exc).__name__ + '\n').encode())
                # Flush and fsync the raw log before publishing a durable state receipt.
                stream.flush()
                os.fsync(stream.fileno())
            record = {'status': 'FAILED', 'exit_code': code, 'command': cmd,
                      'log_sha256': _digest(log), 'completed_unix': int(time.time())}
            if code == 0:
                try:
                    record['result_sha256'] = _result_matches(result, job)
                    record['status'] = 'COMPLETED'
                except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
                    record['reason'] = 'RESULT_VALIDATION_' + type(exc).__name__
            state['attempts'][key] = record
            state['next_command'] = None if record['status'] == 'COMPLETED' else ' '.join(cmd)
            _write_atomic(state_path, state)
            if record['status'] != 'COMPLETED':
                raise RuntimeError(f"BP2b arm {key} failed (exit={code}); evidence retained")
        return {'state_path': str(state_path), 'completed': sum(
            a['status'] == 'COMPLETED' for a in state['attempts'].values()),
            'registered': len(jobs), 'full_acceptance': False,
            'evidence_class': 'PARTIAL_NATIVE_CANDIDATE'}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True)
    p.add_argument('--master-dir')
    p.add_argument('--attempt-prefix', default='preview')
    p.add_argument('--max-jobs', type=int, default=12)
    p.add_argument('--timeout-seconds', type=int, default=2100)
    p.add_argument('--execute-native', action='store_true')
    a = p.parse_args(argv)
    jobs = registered(a.attempt_prefix)
    if not 1 <= a.max_jobs <= len(jobs):
        p.error('max-jobs must be 1..12')
    if not a.execute_native:
        print(json.dumps({'revision': REVISION, 'execution': 'DRY_RUN',
                          'registered_count': len(jobs), 'selected_count': a.max_jobs,
                          'jobs': jobs, 'age_authority': 0, 'jepa_weight': 0,
                          'full_acceptance': False}, sort_keys=True))
        return 0
    if not a.master_dir or a.attempt_prefix == 'preview':
        p.error('--master-dir and unique --attempt-prefix required for --execute-native')
    print(json.dumps(execute(a.out, a.master_dir, a.attempt_prefix,
                             a.max_jobs, a.timeout_seconds), sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
