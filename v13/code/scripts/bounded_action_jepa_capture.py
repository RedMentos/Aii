#!/usr/bin/env python3
"""Preregistered bounded worker lifetimes around the byte-unchanged tap driver.

Eight successfully persisted new batches per owned native worker, then an
explicit checkpoint-boundary exception invokes the driver's existing cleanup.
No native call is made during registration. Rebuilt binaries create a separate
cohort when their byte binding differs; historical rows are never relabelled.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import shutil
import zipfile

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capture_action_jepa_taps as producer
from resume_action_jepa_capture_observed import memory_snapshot, verify_snapshot

MAX_BATCHES = 8
SCHEMA = 'v13-bounded-native-tap-lifecycle-v1'


class CheckpointBoundary(BaseException):
    """Expected lifecycle interruption, never an inference failure."""


def array_sha(x):
    return hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()


def process_identity(pid, command, proc=Path('/proc')):
    """Read-only namespace-aware lookup; never signal a discovered /proc PID.

    Popen owns its namespace PID. /proc can expose the host namespace, so require
    its NSpid mapping AND exact full command, including the fresh unique alias.
    Ambiguous or unavailable observations are returned as missing, not guessed.
    """
    expected = [str(v) for v in command]
    matches = []
    for directory in proc.iterdir():
        if not directory.name.isdecimal():
            continue
        try:
            status = (directory/'status').read_text()
            mapping = next((line.split()[1:] for line in status.splitlines() if line.startswith('NSpid:')), [])
            actual = (directory/'cmdline').read_bytes().rstrip(b'\0').decode().split('\0')
            if str(pid) not in mapping or actual != expected:
                continue
            stat = (directory/'stat').read_text()
            # comm may itself contain spaces or parentheses; fields start after
            # the final ')'. starttime is field 22, remainder index 19.
            starttime = stat.rsplit(')', 1)[1].split()[19]
            rss = next((int(s.split()[1])*1024 for s in status.splitlines() if s.startswith('VmRSS:')), None)
            matches.append({'proc_pid': int(directory.name), 'nspid': [int(n) for n in mapping],
                            'starttime_ticks': starttime, 'rss_bytes': rss})
        except (OSError, UnicodeError, ValueError, IndexError):
            continue
    return matches[0] if len(matches) == 1 else None


def original_prefix(args):
    old = Path(args.original_capture).resolve()
    registry = json.loads((old/'registration.json').read_text())
    _, _, texts = producer.corpus(args.sentences, args.actions)
    x, records = producer.load_checkpoint(old, texts, producer.sha(old/'registration.json'))
    with zipfile.ZipFile(args.prefix_archive) as saved:
        for name in ('registration.json', 'taps.npz'):
            if saved.read(name) != (old/name).read_bytes():
                raise ValueError('Historical recovered prefix differs from durable closed archive')
        for record in records:
            if hashlib.sha256(saved.read(record['path'])).hexdigest() != record['sha256']:
                raise ValueError('Historical batch differs from durable closed archive')
    if len(x) != 736 or len(records) != 46:
        raise ValueError('Only the verified durable 736-row / 46-batch prefix is recoverable')
    return old, registry, x, records


def preregister(args):
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    old, old_registry, old_x, old_records = original_prefix(args)
    current, texts = producer.registration(args)
    if producer.sha(producer.__file__) != old_registry['artifacts']['capture_driver']['sha256']:
        raise ValueError('Original capture driver bytes changed')
    exact = producer.json_sha(current) == producer.json_sha(old_registry)
    snapshot, checked = verify_snapshot(args.frozen_source_archive, args.frozen_source_archive_sha,
                                        args.check_frozen70, out/'snapshot.checkpoint/frozen70')
    capture_out = out/'exact-resume' if exact else out/'new-cohort'
    if exact and not (capture_out/'registration.json').exists():
        capture_out.mkdir(parents=True, exist_ok=True)
        for name in ('registration.json', 'taps.npz'):
            shutil.copyfile(old/name, capture_out/name)
        (capture_out/'batches').mkdir(exist_ok=True)
        for record in old_records:
            shutil.copyfile(old/record['path'], capture_out/record['path'])
    # Separate controls always start at row zero, independent of main prefix.
    cohorts = [capture_out, out/'control-worker-1', out/'control-worker-2']
    for destination in cohorts:
        local = copy.copy(args)
        local.out, local.register_only, local.run = str(destination), True, False
        producer.capture(local)
    binding = {'schema': SCHEMA, 'wrapper': producer.artifact(__file__),
               'inherited_native_environment': {k: v for k, v in sorted(os.environ.items()) if k.startswith(('LLAMA_', 'GGML_'))},
               'driver_environment_overrides': {'OPENBLAS_NUM_THREADS':'1', 'OMP_NUM_THREADS':'2', 'V13_variables':'removed', 'LD_PRELOAD':'removed', 'LD_LIBRARY_PATH':'removed'},
               'source_checker': producer.artifact(Path(__file__).with_name('resume_action_jepa_capture_observed.py')),
               'exporter': producer.artifact(Path(__file__).with_name('export_action_jepa_dataset.py')),
               'python_version': sys.version, 'numpy_version': np.__version__,
               'source_archive': producer.artifact(args.frozen_source_archive),
               'terminal_report': producer.artifact(args.check_frozen70),
               'original_prefix_archive': producer.artifact(args.prefix_archive),
               'original_registration': producer.artifact(old/'registration.json'),
               'original_prefix_rows': len(old_x), 'original_prefix_array_sha256': array_sha(old_x),
               'original_prefix_records': old_records, 'current_registration': current,
               'exact_original_binding': exact, 'main_capture_out': str(capture_out),
               'source_checker_snapshot_root': str(snapshot), 'frozen70': checked,
               'maximum_successful_new_batches_per_worker': MAX_BATCHES,
               'control_workers': 2, 'control_batches_per_worker': 1,
               'control_gate': 'np.array_equal across two actual fresh-worker first-batch arrays; fail closed',
               'historical_drift_control': 'first 16 historical rows vs fresh worker; report exact equality and max_abs_difference, no mixing when native binding differs',
               'checkpoint_stop': 'after raw batch + NPZ + RUNNING progress atomically persisted; unchanged driver owned Popen termination and wait',
               'native_parameters_changed': False, 'native_model_started': False,
               'receiver_authority': 0, 'semantic_quality_proven': False,
               'canonical_architecture_complete': False}
    path = out/'bounded-lifecycle-registration.json'
    if path.exists() and json.loads(path.read_text()) != binding:
        raise ValueError('Published lifecycle registration differs; use a separately named cohort')
    if not path.exists():
        producer.atomic_json(path, binding)
    return binding


def one_worker(args, snapshot, limit, observation_path):
    out = Path(args.out).resolve()
    registry, texts = producer.registration(args)
    registry_sha = producer.sha(out/'registration.json')
    x, records = producer.load_checkpoint(out, texts, registry_sha)
    initial_count = len(records)
    observed = {'schema': 'v13-bounded-native-worker-observation-v1', 'status': 'STARTING',
                'started_utc': producer.now(), 'initial_rows': len(x), 'maximum_new_batches': limit,
                'registry_sha256': registry_sha, 'memory_start': memory_snapshot(),
                'samples': [], 'owned_popen_pid': None, 'native_returncode': None,
                'cleanup_requests': [], 'native_started': False, 'receiver_authority': 0}
    original_popen, original_progress, original_app = subprocess.Popen, producer.progress, producer.APP
    stop = threading.Event()
    owned = []
    lock = threading.Lock()

    def sample():
        if owned:
            obj = owned[0]
            identity = process_identity(obj.pid, obj.args)
            with lock:
                observed['samples'].append({'utc': producer.now(), 'memory': memory_snapshot(), 'native_identity': identity})
                producer.atomic_json(observation_path, observed)

    def sampler():
        while not stop.wait(2):
            sample()

    class ObservedPopen(original_popen):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            if owned:
                raise ValueError('Driver started more than one native process in a lifecycle')
            owned.append(self)
            observed.update(owned_popen_pid=self.pid, native_command=self.args, native_started=True)
            sample()

        def terminate(self):
            observed['cleanup_requests'].append({'operation': 'owned_Popen_terminate', 'utc': producer.now(), 'returncode_before': self.poll()})
            return super().terminate()

        def kill(self):
            observed['cleanup_requests'].append({'operation': 'owned_Popen_kill', 'utc': producer.now(), 'returncode_before': self.poll()})
            return super().kill()

    def progress(*a, **kw):
        original_progress(*a, **kw)
        # This position is after both the raw batch and NPZ have been fsynced.
        if a[4] == 'RUNNING':
            sample()
            if len(a[3]) - initial_count >= limit and len(a[2]) < len(texts):
                raise CheckpointBoundary('Preregistered owned-worker boundary after %d successful new batches' % limit)

    producer.atomic_json(observation_path, observed)
    thread = threading.Thread(target=sampler, daemon=True)
    producer.APP = snapshot
    producer.progress = progress
    subprocess.Popen = ObservedPopen
    thread.start()
    result = None
    try:
        result = producer.capture(args)
        observed['status'] = 'CAPTURED'
    except CheckpointBoundary as error:
        observed.update(status='CONTROLLED_CHECKPOINT_BOUNDARY', controlled_reason=str(error))
    except BaseException as error:
        observed.update(status='FAILED', error={'type': type(error).__name__, 'reason': str(error)})
        raise
    finally:
        stop.set()
        thread.join(timeout=5)
        subprocess.Popen, producer.progress, producer.APP = original_popen, original_progress, original_app
        if owned:
            observed['native_returncode'] = owned[0].poll()
            observed['native_signal_number'] = -owned[0].returncode if owned[0].returncode is not None and owned[0].returncode < 0 else None
            observed['worker_reaped'] = owned[0].returncode is not None
        else:
            observed['worker_reaped'] = True
        observed.update(completed_utc=producer.now(), memory_end=memory_snapshot())
        current_x, current_records = producer.load_checkpoint(out, texts, registry_sha)
        observed.update(completed_rows=len(current_x), completed_new_batches=len(current_records)-initial_count,
                        taps_sha256=producer.sha(out/'taps.npz') if (out/'taps.npz').exists() else None)
        start_events = dict(line.split() for line in (observed['memory_start'].get('memory.events') or '').splitlines())
        end_events = dict(line.split() for line in (observed['memory_end'].get('memory.events') or '').splitlines())
        observed['cgroup_event_deltas'] = {k: int(end_events[k])-int(v) for k,v in start_events.items() if k in end_events}
        observed['rss_observed'] = any(row.get('native_identity') is not None for row in observed['samples'])
        producer.atomic_json(observation_path, observed)
    if observed['native_started'] and not observed['rss_observed']:
        raise ValueError('Namespace-aware owned native identity/RSS unavailable; no automatic restart')
    if not observed['worker_reaped']:
        raise ValueError('Owned native worker was not reaped; automatic continuation forbidden')
    if observed['status'] == 'CONTROLLED_CHECKPOINT_BOUNDARY' and observed['completed_new_batches'] != limit:
        raise ValueError('Controlled interruption did not occur at the preregistered batch boundary')
    return observed, result


def execute(args):
    out = Path(args.out).resolve()
    path = out/'bounded-lifecycle-registration.json'
    if not path.exists():
        raise ValueError('Run requires a separate published preregistration')
    registered = json.loads(path.read_text())
    if preregister(args) != registered:
        raise ValueError('Lifecycle bytes changed before startup')
    snapshot = Path(registered['source_checker_snapshot_root'])
    control_arrays = []
    for number in (1, 2):
        local = copy.copy(args)
        local.out, local.run, local.register_only = str(out/f'control-worker-{number}'), True, False
        registry_sha = producer.sha(Path(local.out)/'registration.json')
        _, _, texts = producer.corpus(args.sentences, args.actions)
        x, _ = producer.load_checkpoint(Path(local.out), texts, registry_sha)
        if not len(x):
            one_worker(local, snapshot, 1, out/f'control-worker-{number}-observation.json')
            x, _ = producer.load_checkpoint(Path(local.out), texts, registry_sha)
        observation = json.loads((out/f'control-worker-{number}-observation.json').read_text())
        if (observation.get('status') != 'CONTROLLED_CHECKPOINT_BOUNDARY'
                or not observation.get('native_started') or not observation.get('worker_reaped')
                or not observation.get('rss_observed') or observation.get('completed_new_batches') != 1):
            raise ValueError('Fresh control lacks its reaped actual native observation')
        if len(x) != 16:
            raise ValueError('Fresh control must contain exactly one actual 16-input batch')
        control_arrays.append(x)
    _, _, historical_x, _ = original_prefix(args)
    invariance = {'schema': 'v13-native-restart-invariance-v1',
                  'control_worker_1_array_sha256': array_sha(control_arrays[0]),
                  'control_worker_2_array_sha256': array_sha(control_arrays[1]),
                  'fresh_workers_exact_equal': bool(np.array_equal(*control_arrays)),
                  'fresh_workers_max_abs_difference': float(np.max(np.abs(control_arrays[0]-control_arrays[1]))),
                  'historical_first16_exact_equal': bool(np.array_equal(historical_x[:16], control_arrays[0])),
                  'historical_first16_max_abs_difference': float(np.max(np.abs(historical_x[:16]-control_arrays[0]))),
                  'original_native_binding_equal': registered['exact_original_binding'],
                  'mixed_cohort_rows': False, 'receiver_authority': 0}
    producer.atomic_json(out/'fresh-worker-invariance.json', invariance)
    if not invariance['fresh_workers_exact_equal']:
        raise ValueError('Actual fresh-worker numerical invariance failed; no main capture allowed')
    if registered['exact_original_binding'] and not invariance['historical_first16_exact_equal']:
        raise ValueError('Historical numerical drift despite matching artifact bytes; no exact resume allowed')
    local = copy.copy(args)
    local.out, local.run, local.register_only = registered['main_capture_out'], True, False
    main = Path(local.out)
    index = len(list(out.glob('main-worker-*.json')))
    while True:
        # Existing numbered observations are immutable, including failures.
        index += 1
        observed, result = one_worker(local, snapshot, MAX_BATCHES, out/f'main-worker-{index:03d}.json')
        print(json.dumps({'lifecycle_worker': index, 'status': observed['status'], 'rows': observed['completed_rows']}), flush=True)
        if observed['status'] == 'CAPTURED':
            return result
        if observed['status'] != 'CONTROLLED_CHECKPOINT_BOUNDARY':
            raise ValueError('Uncontrolled failure forbids automatic restart')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--register-only', action='store_true')
    mode.add_argument('--run', action='store_true')
    for name in ('plan', 'sentences', 'actions', 'model', 'server', 'out', 'original-capture', 'prefix-archive',
                 'check-frozen70', 'frozen-source-archive', 'frozen-source-archive-sha'):
        ap.add_argument('--'+name, required=True)
    ap.add_argument('--threads', type=int, default=2)
    ap.add_argument('--batch-size', type=int, default=16)
    args = ap.parse_args()
    if args.register_only:
        binding = preregister(args)
        print(json.dumps({'status':'REGISTERED', 'exact_original_binding':binding['exact_original_binding'], 'native_model_started':False}))
    else:
        try:
            print(json.dumps(execute(args)))
        except (OSError, ValueError, KeyError, RuntimeError, TimeoutError) as error:
            print(json.dumps({'status':'FAILED_CLOSED', 'reason':str(error), 'receiver_authority':0}))
            return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
