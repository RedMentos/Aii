#!/usr/bin/env python3
"""Opt-in BP2b one-step CPU diagnostic, NOT a registered 30-step arm or utility proof.

Stops immediately AFTER the first hash-bound, fsynced optimizer/EMA checkpoint.
No model weights, optimizer state or personal prompts are uploaded to public CI.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import threading
import time
from unittest import mock

from scripts.bj1_body_jepa import ANCHORS, POOL
from scripts.bp2b_master_preflight import verify
from scripts.bp2b_native_runner import MASTER_SHA, PIN_PATH, plan
from v13.body_jepa import BodyJepaTrainer
from v13 import body_jepa_checkpoint as checkpoint

REVISION = 'bp2b-first-step-diagnostic-v1'
EXPECTED_SEED = 41
EXPECTED_ARM = 'legacy'


class FirstStepCommitted(Exception):
    def __init__(self, pointer):
        super().__init__('first optimizer step committed')
        self.pointer = pointer


def _sync_dir(path):
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_new(path, value):
    """Durable new-only receipt; never overwrite evidence from a failed attempt."""
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise ValueError('Refusing to replace attempt evidence')
    data = (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode('utf-8')
    tmp = path.with_name('.' + path.name + '.partial')
    fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(tmp, path)
        _sync_dir(path.parent)
    finally:
        if tmp.exists():
            tmp.unlink()


def diagnostic_plan():
    frozen = plan(EXPECTED_SEED, EXPECTED_ARM)
    if (frozen['master_expected_sha256'] != MASTER_SHA
            or frozen['config']['jepa_weight'] != 0
            or frozen['config']['max_steps'] != 30
            or frozen['config']['min_steps'] != 30
            or frozen['age_authority'] != 0):
        raise ValueError('Frozen BP2b reference plan changed')
    cfg = dict(frozen['config'])
    cfg.update(max_steps=1, min_steps=1, checkpoint_resume=True)
    return {'schema': REVISION, 'reference': frozen, 'diagnostic_config': cfg,
            'claim_limit': 'one CPU step only; no 30-step cohort or utility claim',
            'age_authority': 0, 'jepa_weight': 0}


def _rss_kib():
    with open('/proc/self/status', encoding='utf-8') as stream:
        for line in stream:
            if line.startswith('VmRSS:'):
                return int(line.split()[1])
    return None


class ResourceSamples:
    def __init__(self, path, interval=5.):
        self.path = Path(path)
        self.interval = interval
        self.stop_event = threading.Event()
        self.thread = None
        self.max_rss_kib = 0
        self.error = None

    def start(self):
        self.thread = threading.Thread(target=self._loop, name='bp2b-rss', daemon=True)
        self.thread.start()

    def _loop(self):
        try:
            with self.path.open('x', encoding='utf-8') as stream:
                while True:
                    rss = _rss_kib()
                    if rss is not None:
                        self.max_rss_kib = max(self.max_rss_kib, rss)
                    stream.write(json.dumps({'elapsed_monotonic_s': round(time.monotonic(), 3),
                                             'rss_kib': rss}, sort_keys=True) + '\n')
                    stream.flush()
                    os.fsync(stream.fileno())
                    if self.stop_event.wait(self.interval):
                        break
            _sync_dir(self.path.parent)
        except Exception as exc:
            self.error = type(exc).__name__

    def close(self):
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=10.)
        if self.error:
            raise RuntimeError('Resource sampling failed: ' + self.error)


def run_probe(master_dir, out, attempt, *, preflight=verify,
              trainer_factory=BodyJepaTrainer, save_fn=None):
    if type(attempt) is not str or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,31}', attempt):
        raise ValueError('Invalid diagnostic attempt ID')
    manifest = diagnostic_plan()
    root = Path(out)
    if root.is_symlink():
        raise ValueError('Diagnostic root symlink refused')
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        raise ValueError('Invalid diagnostic root')
    lock_path = root / '.bp2b-first-step-owner.lock'
    if lock_path.is_symlink():
        raise ValueError('Diagnostic owner lock symlink refused')
    with lock_path.open('a+b') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        source = preflight(master_dir, PIN_PATH, False)
        if (type(source) is not dict or source.get('status') != 'FULL_FILE_HASH_PASS'
                or source.get('master_sha256_verified_locally') is not True
                or source.get('master_expected_sha256') != MASTER_SHA):
            raise ValueError('Exact full master preflight required')
        dest = root / ('attempt-' + attempt)
        dest.mkdir(parents=True, exist_ok=False)
        native = (preflight is verify and trainer_factory is BodyJepaTrainer and save_fn is None)
        evidence_class = 'LINUX_NATIVE_DIAGNOSTIC' if native else 'SOFTWARE_FAKE_TEST'
        _write_new(dest / 'STARTED.json', {'plan': manifest, 'master_preflight': source,
                                         'evidence_class': evidence_class, 'status': 'STARTED'})
        sampler = ResourceSamples(dest / 'RSS.jsonl')
        started = time.monotonic()
        sampler.start()
        try:
            frozen = manifest['reference']
            items = [{'memory_id': 'bp2b_%02d' % i, 'prompt': POOL[i][0],
                      'target': POOL[i][1], 'answer_keys': POOL[i][2]}
                     for i in frozen['selected_indices']]
            tr = trainer_factory(master_dir, dest / 'trainer', master_sha256=MASTER_SHA,
                                 anchors=list(ANCHORS), cfg=manifest['diagnostic_config'], arch='lfm2')
            original_save = checkpoint.save if save_fn is None else save_fn

            def stop_after_commit(*args, **kwargs):
                receipt = original_save(*args, **kwargs)
                if (type(receipt) is not dict or type(receipt.get('step')) is not int
                        or receipt['step'] != 1 or not re.fullmatch(r'[0-9a-f]{64}', str(receipt.get('sha256')))):
                    raise ValueError('No verified first-step checkpoint receipt')
                raise FirstStepCommitted(receipt)

            with mock.patch.object(checkpoint, 'save', stop_after_commit):
                tr.fit(items, 'bp2b-first-step-diagnostic')
            raise ValueError('Trainer returned without a completed first-step checkpoint')
        except FirstStepCommitted as done:
            sampler.close()
            result = {'schema': REVISION, 'status': 'FIRST_STEP_COMMITTED',
                      'evidence_class': evidence_class, 'step': 1,
                      'checkpoint_sha256': done.pointer['sha256'],
                      'source_sha256': frozen['source_sha256'],
                      'master_sha256_verified_locally': True,
                      'seconds_to_first_committed_step_including_setup': round(time.monotonic() - started, 3),
                      'sampled_peak_rss_kib': sampler.max_rss_kib,
                      'jepa_weight': 0, 'age_authority': 0,
                      'claim_limit': 'diagnostic only; no heldout scoring, retention or native utility'}
            _write_new(dest / 'RESULT.json', result)
            return result
        except BaseException as exc:
            sampler.close()
            _write_new(dest / 'FAILED.json', {'schema': REVISION, 'status': 'FAILED',
                                             'error_class': type(exc).__name__,
                                             'elapsed_s': round(time.monotonic() - started, 3),
                                             'sampled_peak_rss_kib': sampler.max_rss_kib,
                                             'evidence_class': evidence_class,
                                             'age_authority': 0})
            raise


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--execute-native', action='store_true')
    parser.add_argument('--master-dir')
    parser.add_argument('--out')
    parser.add_argument('--attempt')
    args = parser.parse_args(argv)
    if args.dry_run == args.execute_native:
        raise ValueError('Select exactly one of --dry-run and --execute-native')
    if args.dry_run:
        print(json.dumps(diagnostic_plan(), sort_keys=True))
        return 0
    if not args.master_dir or not args.out or not args.attempt:
        raise ValueError('Native diagnostic requires master-dir, out and attempt')
    result = run_probe(args.master_dir, args.out, args.attempt)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
