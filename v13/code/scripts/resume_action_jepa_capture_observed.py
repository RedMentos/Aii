#!/usr/bin/env python3
"""Transparent read-only observer around the unchanged native capture producer.

Only the producer's source-check APP root points at the verified immutable
completed STEP2 source archive. Native inputs, protocol and producer bytes do
not change. The wrapper records its own binding and actual subprocess returns.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capture_action_jepa_taps as producer


def memory_snapshot():
    result = {}
    for name in ('memory.events', 'memory.current', 'memory.max', 'memory.peak'):
        path = Path('/sys/fs/cgroup') / name
        result[name] = path.read_text().strip() if path.exists() else None
    return result


def verify_snapshot(archive, archive_sha, report_path, destination):
    if producer.sha(archive) != archive_sha:
        raise ValueError('Frozen source archive bytes differ from expected hash')
    report = json.loads(Path(report_path).read_text())
    if len(report.get('rows', [])) != 70 or report.get('status') in (None, 'RUNNING', 'DIAGNOSTIC_INCOMPLETE'):
        raise ValueError('Completed terminal 70-row report required')
    expected = report['source_hashes']
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, 'r:gz') as source:
        if {m.name for m in source.getmembers()} != set(expected):
            raise ValueError('Frozen archive source inventory differs from report')
        for member in source.getmembers():
            relative = Path(member.name)
            if not member.isfile() or relative.is_absolute() or '..' in relative.parts or member.size > 2_000_000:
                raise ValueError('Unsafe/unexpected frozen archive entry')
            raw = source.extractfile(member).read()
            if hashlib.sha256(raw).hexdigest() != expected[member.name]:
                raise ValueError('Frozen source archive member hash mismatch: ' + member.name)
            target = destination / relative
            if target.exists():
                if target.read_bytes() != raw:
                    raise ValueError('Existing immutable source snapshot changed')
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                target.chmod(0o444)
    # Execute the unchanged actual source checker on these verified bytes.
    previous = producer.APP
    producer.APP = destination
    try:
        checked = producer.check_frozen70(report_path)
    finally:
        producer.APP = previous
    return destination, checked


def observe(args):
    out = Path(args.out).resolve()
    registry = json.loads((out/'registration.json').read_text())
    if producer.sha(producer.__file__) != registry['artifacts']['capture_driver']['sha256']:
        raise ValueError('Original native producer bytes changed')
    archive = Path(args.frozen_source_archive).resolve()
    snapshot, checked = verify_snapshot(archive, args.frozen_source_archive_sha, args.check_frozen70,
                                       out/'recovery.checkpoint/frozen70-observer-source')
    current, texts = producer.registration(args)
    if producer.json_sha(current) != producer.json_sha(registry):
        raise ValueError('Original capture registration/parameters changed')
    x, records = producer.load_checkpoint(out, texts, producer.sha(out/'registration.json'))
    lineage_path = out/'resume-observer-registration.json'
    if lineage_path.exists():
        lineage = json.loads(lineage_path.read_text())
        if (lineage['wrapper']['sha256'] != producer.sha(__file__)
                or lineage['source_archive']['sha256'] != producer.sha(archive)
                or lineage['terminal_report']['sha256'] != producer.sha(args.check_frozen70)
                or lineage['original_registration_sha256'] != producer.sha(out/'registration.json')):
            raise ValueError('Observer registration changed')
        prefix = lineage['preserved_prefix_rows']
        if hashlib.sha256(x[:prefix].tobytes()).hexdigest() != lineage['preserved_prefix_array_sha256']:
            raise ValueError('Earlier actual native prefix changed')
        if records[:len(lineage['preserved_prefix_batch_records'])] != lineage['preserved_prefix_batch_records']:
            raise ValueError('Earlier actual native raw records changed')
    else:
        lineage = {'schema': 'v13-action-jepa-native-observer-lineage-v1',
                   'wrapper': producer.artifact(__file__), 'source_archive': producer.artifact(archive),
                   'terminal_report': producer.artifact(args.check_frozen70),
                   'original_producer': registry['artifacts']['capture_driver'],
                   'original_registration_sha256': producer.sha(out/'registration.json'),
                   'source_checker_snapshot_root': str(snapshot), 'verified_source_count': len(json.loads(Path(args.check_frozen70).read_text())['source_hashes']),
                   'preserved_prefix_rows': len(x), 'preserved_prefix_array_sha256': hashlib.sha256(x.tobytes()).hexdigest(),
                   'preserved_prefix_original_npz_sha256': producer.sha(out/'taps.npz'),
                   'preserved_prefix_batch_records': records, 'native_inputs_and_parameters_changed': False,
                   'source_checker_APP_override_only': True, 'working_tree_source_override': False,
                   'scope': 'Immutable completed STEP2 source-check snapshot; unchanged native producer; read-only exit/cgroup observer. Working tree after proof may differ.',
                   'receiver_authority': 0, 'semantic_quality_proven': False, 'canonical_architecture_complete': False}
        producer.atomic_json(lineage_path, lineage)
    if args.register_only:
        return {'status': 'OBSERVER_REGISTERED', 'preserved_rows': len(x), 'native_model_started': False,
                'source_snapshot_verified': checked}
    # Root coordination must authorize invocation with --run after competing
    # large native model jobs have been reaped. This script does not schedule it.
    attempt = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    observation_path = out/f'native-exit-observer-{attempt}.json'
    observed = {'schema': 'v13-action-native-exit-observation-v1', 'status': 'STARTING',
                'wrapper_sha256': producer.sha(__file__), 'lineage_sha256': producer.sha(lineage_path),
                'memory_start': memory_snapshot(), 'memory_samples': [], 'native_pid': None,
                'native_returncode': None, 'native_signal': None, 'cleanup_requests': [],
                'receiver_authority': 0, 'semantic_quality_proven': False}
    last_sample = 0.

    def persist():
        producer.atomic_json(observation_path, observed)

    def sample():
        nonlocal last_sample
        if time.monotonic() - last_sample < 2:
            return
        last_sample = time.monotonic()
        rss = None
        if observed['native_pid'] is not None:
            stat = Path('/proc') / str(observed['native_pid']) / 'status'
            if stat.exists():
                rss = next((s for s in stat.read_text().splitlines() if s.startswith('VmRSS:')), None)
        observed['memory_samples'].append({'utc': producer.now(), 'cgroup': memory_snapshot(), 'native_rss': rss})

    def profile(frame, event, value):
        if event not in ('call', 'return'):
            return
        obj = frame.f_locals.get('self')
        if not isinstance(obj, subprocess.Popen):
            return
        name = frame.f_code.co_name
        if name == '__init__' and event == 'return' and getattr(obj, 'pid', None):
            observed['native_pid'] = obj.pid
            observed['native_args'] = obj.args
            persist()
        if getattr(obj, 'pid', None) != observed['native_pid']:
            return
        if event == 'call' and name in ('terminate', 'kill'):
            observed['cleanup_requests'].append({'operation': name, 'utc': producer.now(),
                                                'returncode_before_request': obj.returncode})
        if name in ('poll', 'wait') and event == 'return':
            sample()
            if obj.returncode is not None:
                observed['native_returncode'] = obj.returncode
                observed['native_signal'] = signal.Signals(-obj.returncode).name if obj.returncode < 0 else None
                persist()

    persist()
    previous_app = producer.APP
    previous_profile = sys.getprofile()
    producer.APP = snapshot
    sys.setprofile(profile)
    try:
        result = producer.capture(args)
        observed['status'] = 'COMPLETE'
        observed['capture_result'] = result
        return result
    except BaseException as error:
        observed['status'] = 'FAILED'
        observed['error'] = {'type': type(error).__name__, 'reason': str(error)}
        raise
    finally:
        sys.setprofile(previous_profile)
        producer.APP = previous_app
        observed['memory_end'] = memory_snapshot()
        observed['completed_utc'] = producer.now()
        persist()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--register-only', action='store_true')
    mode.add_argument('--run', action='store_true')
    for name in ('plan', 'sentences', 'actions', 'model', 'server', 'out', 'check-frozen70', 'frozen-source-archive', 'frozen-source-archive-sha'):
        ap.add_argument('--' + name, required=True)
    ap.add_argument('--threads', type=int, default=2)
    ap.add_argument('--batch-size', type=int, default=16)
    args = ap.parse_args()
    try:
        print(json.dumps(observe(args)))
    except (OSError, ValueError, KeyError, RuntimeError, TimeoutError) as error:
        print(json.dumps({'status': 'UNAVAILABLE', 'reason': str(error), 'receiver_authority': 0}))
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
