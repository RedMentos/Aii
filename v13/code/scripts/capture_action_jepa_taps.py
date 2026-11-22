#!/usr/bin/env python3
"""Resumable actual Qwen action-corpus mean-pool capture; registration is offline.

Native startup requires --run and a terminal source-intact 70-row STEP2 report.
Every successful batch has immutable raw request/response evidence and an
atomic NPZ checkpoint. Previously failed attempts are retained on resume.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_action_jepa_dataset import build_plan, corpus, json_sha, sha, CAPTURE_SCHEMA

APP = Path(__file__).resolve().parents[1]
REGISTRY_SCHEMA = 'v13-action-native-tap-registration-v1'


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, value):
    data = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
    atomic_bytes(path, data)


def atomic_bytes(path, data):
    path = Path(path)
    tmp = path.with_name(path.name + '.writing')
    with tmp.open('wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def artifact(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': sha(path)}


def library_bindings(server):
    parent = Path(server).resolve().parent
    return {p.name: artifact(p) for p in sorted(parent.glob('*.so*')) if p.is_file()}


def registration(args):
    plan = json.loads(Path(args.plan).read_text())
    if json_sha(plan) != json_sha(build_plan(args.sentences, args.actions, plan['legacy_split_seed'], plan['partition_seed'])):
        raise ValueError('Current preregistration differs from original corpus')
    _, _, texts = corpus(args.sentences, args.actions)
    if args.threads != 2 or args.batch_size != 16:
        raise ValueError('Preregistered capture uses exactly two threads and batches of sixteen')
    return {'schema': REGISTRY_SCHEMA, 'plan': artifact(args.plan), 'sentences': artifact(args.sentences),
            'actions': artifact(args.actions), 'texts_sha256': json_sha(texts), 'expected_rows': len(texts),
            'expected_dim': 1024, 'dtype': 'float64', 'batch_size': args.batch_size, 'threads': args.threads,
            'context': 2048, 'pooling': 'mean', 'embedding': True, 'native_template': 'raw_text_embedding',
            'artifacts': {'model_gguf': artifact(args.model), 'runner': artifact(args.server),
                          'extractor': artifact(Path(__file__).with_name('jepa_ablation_bench.py')),
                          'capture_driver': artifact(__file__)},
            'runtime_libraries': library_bindings(args.server),
            'model_role': 'B2_GIST_Qwen3.5-0.8B_Q4_0', 'receiver_authority': 0,
            'semantic_quality_proven': False, 'canonical_architecture_complete': False}, texts


def check_frozen70(report_path):
    path = Path(report_path).resolve()
    report = json.loads(path.read_text())
    if (report.get('status') in (None, 'RUNNING', 'DIAGNOSTIC_INCOMPLETE') or len(report.get('rows', [])) != 70
            or report.get('proof_version') != 3):
        raise ValueError('Frozen STEP2 report must be terminal with all 70 recorded rows')
    for name, expected in report['source_hashes'].items():
        target = APP / name
        if sha(target) != expected:
            raise ValueError('Frozen STEP2 source changed: ' + name)
    return {'path': str(path), 'sha256': sha(path), 'status': report['status'],
            'rows': 70, 'frozen_source_intact': True, 'utility_gate_inferred': False}


def validate_response(payload, requested, alias):
    if payload.get('model') != alias:
        raise ValueError('Embedding response is not from the owned unique model alias')
    data = payload['data']
    if not isinstance(data, list) or sorted(r['index'] for r in data) != list(range(requested)):
        raise ValueError('Embedding batch indices incomplete, duplicated or reordered')
    x = np.asarray([r['embedding'] for r in sorted(data, key=lambda r: r['index'])], dtype=np.float64)
    if x.shape != (requested, 1024) or not np.isfinite(x).all():
        raise ValueError('Expected finite actual 1024-dimensional native embeddings')
    return x


def write_checkpoint(out, x, texts, registry_sha, records):
    path = out / 'taps.npz'
    tmp = out / 'taps.npz.writing'
    metadata = {'registry_sha256': registry_sha, 'completed_rows': len(x), 'batch_records': records}
    with tmp.open('wb') as f:
        np.savez(f, x=x, texts=np.asarray(texts[:len(x)]), checkpoint=np.asarray(json.dumps(metadata, sort_keys=True)))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def load_checkpoint(out, texts, registry_sha):
    path = out / 'taps.npz'
    if not path.exists():
        return np.empty((0, 1024), dtype=np.float64), []
    with np.load(path, allow_pickle=False) as saved:
        x, observed = saved['x'], saved['texts']
        metadata = json.loads(str(saved['checkpoint']))
    if (metadata['registry_sha256'] != registry_sha or metadata['completed_rows'] != len(x)
            or x.ndim != 2 or x.shape[1] != 1024 or x.dtype != np.dtype('float64')
            or not np.isfinite(x).all() or observed.tolist() != texts[:len(x)] or len(x) > len(texts)):
        raise ValueError('Checkpoint source/shape/input order mismatch')
    offset = 0
    for record in metadata['batch_records']:
        raw = out / record['path']
        if sha(raw) != record['sha256']:
            raise ValueError('Recorded native batch bytes changed')
        batch = json.loads(raw.read_text())
        end = batch['end']
        if (batch['registry_sha256'] != registry_sha or batch['start'] != offset or not offset < end <= len(texts)
                or batch['inputs'] != texts[offset:end]):
            raise ValueError('Recorded native batch lineage mismatch')
        actual = validate_response(batch['response'], end - offset, batch['model_alias'])
        if not np.array_equal(actual, x[offset:end]):
            raise ValueError('Checkpoint floats differ from raw native response')
        offset = end
    if offset != len(x):
        raise ValueError('Checkpoint has unrecorded native rows')
    return x, metadata['batch_records']


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def request_json(url, payload=None, timeout=180):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    request = urllib.request.Request(url, data, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def progress(out, registry_sha, x, records, status, **extra):
    atomic_json(out / 'capture-state.json', {'schema': 'v13-action-native-tap-progress-v1',
                'status': status, 'updated_utc': now(), 'registry_sha256': registry_sha,
                'completed_rows': len(x), 'completed_batches': len(records),
                'taps_sha256': sha(out/'taps.npz') if (out/'taps.npz').exists() else None,
                'native_extraction_observed': False, 'receiver_authority': 0,
                'canonical_architecture_complete': False, **extra})


def capture(args):
    registered, texts = registration(args)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    registry_path = out / 'registration.json'
    if registry_path.exists():
        if json_sha(json.loads(registry_path.read_text())) != json_sha(registered):
            raise ValueError('Resume registration differs: source/model/runner/libraries/driver/config changed')
    else:
        if args.run:
            raise ValueError('Run requires a prior separate --register-only invocation')
        atomic_json(registry_path, registered)
    registry_sha = sha(registry_path)
    x, records = load_checkpoint(out, texts, registry_sha)
    if args.register_only:
        if not (out/'capture-state.json').exists():
            progress(out, registry_sha, x, records, 'REGISTERED', expected_rows=len(texts))
        return {'status': 'REGISTERED', 'completed_rows': len(x), 'expected_rows': len(texts), 'native_model_started': False}
    if not args.check_frozen70:
        raise ValueError('--check-frozen70 is required before actual native startup')
    freeze = check_frozen70(args.check_frozen70)
    if len(x) == len(texts) and (out/'capture-manifest.json').exists():
        manifest = json.loads((out/'capture-manifest.json').read_text())
        if manifest['taps_sha256'] != sha(out/'taps.npz'):
            raise ValueError('Completed native artifact changed')
        return {'status': 'ALREADY_CAPTURED', 'completed_rows': len(x), 'native_model_started': False}
    port = free_port()
    alias = 'v13-action-capture-' + uuid.uuid4().hex
    env = {k: v for k, v in os.environ.items() if not k.startswith('V13_') and k not in ('LD_PRELOAD', 'LD_LIBRARY_PATH')}
    env.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='2')
    attempt = uuid.uuid4().hex
    log_path = out / ('native-server-' + attempt + '.log')
    command = [str(Path(args.server).resolve()), '-m', str(Path(args.model).resolve()), '--embedding', '--pooling', 'mean',
               '--host', '127.0.0.1', '--port', str(port), '--alias', alias,
               '-c', '2048', '-t', '2', '-tb', '2', '--no-webui', '--log-disable']
    server = None
    reaped = False
    failed = None
    try:
        progress(out, registry_sha, x, records, 'STARTING', model_alias=alias, frozen70=freeze)
        with log_path.open('wb') as log:
            server = subprocess.Popen(command, stdout=log, stderr=log, env=env)
            deadline = time.monotonic() + 180
            while True:
                if server.poll() is not None:
                    raise RuntimeError('Owned native server exited before ready')
                try:
                    props = request_json(f'http://127.0.0.1:{port}/props', timeout=2)
                    if props.get('model_alias') == alias:
                        break
                except (OSError, ValueError):
                    pass
                if time.monotonic() > deadline:
                    raise TimeoutError('Owned native server not ready within 180 seconds')
                time.sleep(.25)
            (out/'batches').mkdir(exist_ok=True)
            while len(x) < len(texts):
                start, end = len(x), min(len(x) + args.batch_size, len(texts))
                batch_path = out/'batches'/f'batch-{start:05d}-{end:05d}.json'
                if batch_path.exists():
                    batch = json.loads(batch_path.read_text())
                    if batch['registry_sha256'] != registry_sha or batch['inputs'] != texts[start:end] or batch['start'] != start or batch['end'] != end:
                        raise ValueError('Pending batch source binding mismatch')
                    actual = validate_response(batch['response'], end-start, batch['model_alias'])
                else:
                    if server.poll() is not None:
                        raise RuntimeError('Owned native server died during capture')
                    began = time.monotonic()
                    payload = request_json(f'http://127.0.0.1:{port}/v1/embeddings',
                                           {'input': texts[start:end], 'model': alias}, timeout=300)
                    actual = validate_response(payload, end-start, alias)
                    batch = {'schema': 'v13-action-native-embedding-batch-v1', 'registry_sha256': registry_sha,
                             'start': start, 'end': end, 'inputs': texts[start:end], 'model_alias': alias,
                             'response': payload, 'native_http_duration_s': time.monotonic()-began,
                             'captured_utc': now(), 'server_pid': server.pid}
                    atomic_json(batch_path, batch)
                records.append({'path': batch_path.relative_to(out).as_posix(), 'sha256': sha(batch_path)})
                x = np.concatenate((x, actual))
                write_checkpoint(out, x, texts, registry_sha, records)
                progress(out, registry_sha, x, records, 'RUNNING', expected_rows=len(texts), frozen70=freeze)
                print(json.dumps({'status': 'BATCH_CAPTURED', 'rows': len(x), 'denominator': len(texts)}), flush=True)
    except BaseException as error:
        failed = error
        atomic_json(out/('failed-attempt-' + attempt + '.json'),
                    {'status': 'FAILED_ATTEMPT', 'reason': str(error), 'error_type': type(error).__name__,
                     'captured_utc': now(), 'completed_rows': len(x), 'registry_sha256': registry_sha,
                     'native_server_log': log_path.name})
    finally:
        if server is not None:
            if server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=10)
            else:
                server.wait()
            reaped = server.poll() is not None
    if failed is not None:
        progress(out, registry_sha, x, records, 'INCOMPLETE', worker_reaped=reaped,
                 expected_rows=len(texts), frozen70=freeze)
        raise failed
    current, _ = registration(args)
    if json_sha(current) != json_sha(registered):
        raise ValueError('Native/corpus artifacts changed during actual extraction')
    validated, _ = load_checkpoint(out, texts, registry_sha)
    if len(validated) != len(texts) or not reaped:
        raise ValueError('Native capture incomplete or worker not reaped')
    manifest = {'schema': CAPTURE_SCHEMA, 'native_extraction_observed': True,
                'tap_kind': 'llama.cpp-mean-last-layer-embedding', 'plan_sha256': registered['plan']['sha256'],
                'texts_sha256': registered['texts_sha256'], 'taps_sha256': sha(out/'taps.npz'),
                'shape': list(x.shape), 'dtype': str(x.dtype), 'artifacts': registered['artifacts'],
                'runtime_libraries': registered['runtime_libraries'], 'registration_sha256': registry_sha,
                'completed_batches': len(records), 'completed_rows': len(x), 'worker_reaped': True,
                'failed_attempts_preserved': sorted(p.name for p in out.glob('failed-attempt-*.json')),
                'frozen70': freeze, 'semantic_quality_proven': False, 'receiver_authority': 0,
                'canonical_architecture_complete': False}
    atomic_json(out/'capture-manifest.json', manifest)
    progress(out, registry_sha, x, records, 'CAPTURED', expected_rows=len(texts),
             worker_reaped=True, frozen70=freeze, native_extraction_observed=True)
    return {'status': 'CAPTURED', 'completed_rows': len(x), 'worker_reaped': True,
            'taps_sha256': manifest['taps_sha256'], 'receiver_authority': 0}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    choice = ap.add_mutually_exclusive_group(required=True)
    choice.add_argument('--register-only', action='store_true')
    choice.add_argument('--run', action='store_true')
    for name in ('plan', 'sentences', 'actions', 'model', 'server', 'out'):
        ap.add_argument('--' + name, required=True)
    ap.add_argument('--check-frozen70')
    ap.add_argument('--threads', type=int, default=2)
    ap.add_argument('--batch-size', type=int, default=16)
    args = ap.parse_args()
    try:
        print(json.dumps(capture(args)))
    except (OSError, ValueError, KeyError, RuntimeError, TimeoutError) as error:
        print(json.dumps({'status': 'UNAVAILABLE', 'reason': str(error), 'receiver_authority': 0}))
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
