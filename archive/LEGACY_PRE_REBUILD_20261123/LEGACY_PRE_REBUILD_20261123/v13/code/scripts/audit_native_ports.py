#!/usr/bin/env python3
"""Read installed artifacts and optionally measure the existing native ports.

No downloads, credentials, training, approval, or model mutation. A dynamic
optimizer symbol is evidence of a library export, never a TrainRunnerProof.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v13.common import APP, atomic_write, dumps, file_hash
from v13.config import DEFAULTS, home_path
from v13.models import ModelManager, ROLES, catalog
from v13.runners import LlamaRunner, NeedleRunner

SCHEMA = 'V13_NATIVE_PORT_AUDIT_V1'
SYMBOLS = ('llama_get_embeddings_ith', 'llama_get_logits_ith',
           'llama_sampler_init_logit_bias', 'llama_opt_init', 'llama_opt_epoch',
           'llama_model_quantize', 'needle_embed', 'needle_complete')


def inspect_gguf(path):
    """Read bounded metadata/tensor headers without loading tensor weights."""
    path = Path(path)
    with path.open('rb') as stream:
        def read(n):
            if n < 0 or stream.tell() + n > min(path.stat().st_size, 64 * 1024 * 1024):
                raise ValueError('GGUF header exceeds bounded 64 MiB audit budget')
            data = stream.read(n)
            if len(data) != n:
                raise ValueError('Truncated GGUF header')
            return data
        def unpack(fmt):
            return struct.unpack('<' + fmt, read(struct.calcsize('<' + fmt)))[0]
        def string(keep=True):
            n = unpack('Q')
            if n > 8 * 1024 * 1024:
                raise ValueError('GGUF string exceeds audit budget')
            raw = read(n)
            return raw.decode('utf-8', errors='replace') if keep else None
        formats = {0:'B', 1:'b', 2:'H', 3:'h', 4:'I', 5:'i', 6:'f', 7:'?', 10:'Q', 11:'q', 12:'d'}
        def value(kind, keep=True, depth=0):
            if kind in formats:
                result = unpack(formats[kind])
                return result if keep else None
            if kind == 8:
                return string(keep)
            if kind != 9 or depth:
                raise ValueError('Unsupported GGUF metadata type')
            item_kind, count = unpack('I'), unpack('Q')
            if count > 1000000 or item_kind == 9:
                raise ValueError('GGUF array exceeds bounded audit policy')
            for _ in range(count):
                value(item_kind, False, depth + 1)
            return {'item_type':item_kind, 'length':count} if keep else None
        if read(4) != b'GGUF':
            raise ValueError('Not a GGUF artifact')
        version, tensors, entries = unpack('I'), unpack('Q'), unpack('Q')
        if version not in {2, 3} or tensors > 100000 or entries > 100000:
            raise ValueError('Unsupported/bounded GGUF header')
        metadata = {}
        for _ in range(entries):
            key = string()
            if key in metadata:
                raise ValueError('Duplicate GGUF metadata key')
            metadata[key] = value(unpack('I'))
        types = Counter(); parameters = 0; selected = []
        for _ in range(tensors):
            name, rank = string(), unpack('I')
            if rank > 4:
                raise ValueError('GGUF tensor rank exceeds supported audit format')
            dimensions = [unpack('Q') for _ in range(rank)]
            if any(n == 0 or n > 2**32 for n in dimensions):
                raise ValueError('Invalid GGUF tensor dimensions')
            tensor_type, offset = unpack('I'), unpack('Q')
            types[tensor_type] += 1
            parameters += math.prod(dimensions)
            if name in {'token_embd.weight', 'output.weight', 'output_norm.weight'} or 'expert' in name:
                if len(selected) < 64:
                    selected.append({'name':name, 'dimensions':dimensions, 'ggml_type':tensor_type, 'data_offset':offset})
        return {'version':version, 'metadata':metadata, 'tensor_count':tensors,
                'stored_parameter_elements':parameters, 'tensor_types':dict(types),
                'selected_tensor_headers':selected, 'header_bytes':stream.tell(),
                'train_master_proven':False, 'weight_payload_loaded':False}


def inspect_symbols(path):
    executable = shutil.which('nm') or shutil.which('llvm-nm')
    result = {'artifact':str(path), 'sha256':file_hash(path), 'symbols':None}
    if executable is None:
        return result | {'status':'UNAVAILABLE', 'reason':'nm/llvm-nm is not installed'}
    completed = subprocess.run([executable, '-D', '--defined-only', str(path)],
                               capture_output=True, text=True, timeout=15)
    if completed.returncode:
        return result | {'status':'UNAVAILABLE', 'reason':completed.stderr[:300]}
    exports = {line.split()[-1].split('@')[0] for line in completed.stdout.splitlines() if line.split()}
    return result | {'status':'INSPECTED', 'symbols':{name:name in exports for name in SYMBOLS},
                     'export_count':len(exports), 'train_runner_proven':False}


def artifact(path, expected=None):
    path = Path(path)
    if not path.is_file():
        return {'path':str(path), 'present':False, 'sha256':None, 'matches_manifest':False}
    result = {'path':str(path), 'present':True, 'size':path.stat().st_size, 'sha256':file_hash(path)}
    result['matches_manifest'] = None if expected is None else result['sha256'] == expected['sha256'] and result['size'] == expected['size']
    return result


def absent_ports():
    return {
        'native_body_training':{'available':False, 'proof':None, 'trainable_parameter_count':0,
            'reason':'No integrated native body gradient/optimizer/checkpoint/restart/retention TrainRunnerProof'},
        'active_expert':{'available':False, 'proof':None, 'authority':0,
            'reason':'Installed LFM fallback is dense; no V13 sparse expert training port'},
        'train_master':{'available':False, 'proof':None,
            'reason':'Packed inference artifact does not establish FP32/BF16 optimizer masters'},
        'quantizer_training_roundtrip':{'available':False, 'proof':None,
            'reason':'No integrated post-update re-quantization/reload parity proof'},
        'receiver_latent_injection':{'available':False, 'proof':None, 'authority':0,
            'reason':'No trained receiver port, receiver revision calibration or utility/OOD ablation'},
        'MobileMoE_runner':{'available':False, 'proof':None, 'authority':0,
            'reason':'No installed authorized weights and no packed Android/native training runner proof'}
    }


def probe_role(home, models, role, seconds):
    cancel = threading.Event(); deadline = time.monotonic() + seconds
    cfg = DEFAULTS | {'threads':2, 'context_tokens':1024, 'temperature':0.}
    output = {}; runner = None
    try:
        if role == 'C2_CONTROL':
            runner = NeedleRunner(home, models)
            values = runner.embed('Native capability audit: Budget 120 Euro.', cancel, deadline)
            output['embedding'] = {'available':len(values) == 3072 and all(math.isfinite(v) for v in values),
                'dimension':len(values), 'sha256':hashlib.sha256(dumps(values).encode()).hexdigest(),
                'metrics':dict(runner.last_metrics)}
            output['structured_control'] = {'actual':runner.control('Berechne die Hälfte von 120 Euro.', cancel, deadline),
                                             'metrics':dict(runner.last_metrics)}
        else:
            runner = LlamaRunner(home, role, models.path_for(role), cfg, purpose='tap')
            result = runner.tap('Native capability audit: Budget 120 Euro.', cancel, deadline, max_tokens=64)
            output['read_only_tap'] = {'available':True, 'token_ids':result['token_ids'],
                'vector_sha256':hashlib.sha256(dumps(result['vectors']).encode()).hexdigest(),
                'metrics':result['metrics'], 'separate_prefill':True, 'live_generation_kv_tap':False}
            output['server_props'] = runner._json('GET', '/props', None, deadline)
            runner.unload(); runner = None
            if role == 'C3_LANGUAGE':
                runner = LlamaRunner(home, role, models.path_for(role), cfg)
                runner.load(cancel, deadline)
                prompt, _, _ = runner._prompt([{'role':'user','content':'Sag kurz Hallo.'}], cancel, deadline, 4)
                payload = {'prompt':prompt, 'temperature':0., 'seed':13, 'cache_prompt':False}
                baseline = runner.completion_one(payload, cancel, deadline)
                choices = runner._json('POST', '/tokenize', {'content':' Ja Nein Hallo Test Budget', 'add_special':False}, deadline)['tokens']
                first = baseline.get('tokens', [])
                alternate = next((token for token in choices if not first or token != first[0]), None)
                if first and alternate is not None:
                    bias = [[first[0], -12.], [alternate, 12.]]
                    changed = runner.completion_one(payload | {'logit_bias':bias}, cancel, deadline)
                    output['first_token_bias'] = {'available':bool(changed.get('tokens')) and changed['tokens'] != first,
                        'baseline':baseline, 'biased':changed, 'bias':bias,
                        'scope':'one native decoder position; external delta; no base weight update'}
                else:
                    output['first_token_bias'] = {'available':False, 'reason':'No native first token or alternate token'}
    except Exception as exc:
        output['error'] = {'type':type(exc).__name__, 'message':str(exc)[:500]}
    finally:
        if runner is not None:
            unloaded = runner.unload()
            output['process_reaped'] = True if role == 'C2_CONTROL' else unloaded.get('process_reaped', False)
    return output


def audit(home, probe_native=False, seconds=60., progress=None):
    home = Path(home).resolve(); models = ModelManager(home); specs = catalog()
    result = {'schema':SCHEMA, 'created_at':datetime.now(timezone.utc).isoformat(),
        'device':{'platform':platform.platform(), 'machine':platform.machine(),
                  'android':bool(os.environ.get('ANDROID_ROOT') or 'com.termux' in str(home))},
        'audit_source_sha256':file_hash(Path(__file__)),
        'runner_source_sha256':file_hash(APP / 'v13/runners.py'),
        'catalog_sha256':file_hash(APP / 'specs/models.json'),
        'native_probes_requested':probe_native, 'roles':{}, 'absent_ports':absent_ports(),
        'train_runner_proof':None, 'native_body_update_authority':0,
        'claim_limit':'Local installed inference ports only; Linux does not prove Redmi; no body learning claim'}
    model_cache = {}; binary_cache = {}
    for role in ('C3_LANGUAGE','B1_DETAIL','B2_GIST','C2_CONTROL','TEACHER'):
        key = ROLES[role]; installed = models.installed.get(key)
        entry = {'model_revision':models.revision(role), 'model_id':installed.get('model_id') if installed else None,
                 'native_body_update_authority':0, 'ports':None}
        result['roles'][role] = entry
        if not installed:
            entry['status'] = 'UNAVAILABLE'; entry['reason'] = 'Model not installed'; continue
        if key not in model_cache:
            observed = {name:artifact(home / details['path'], details) for name, details in installed['files'].items()}
            main = home / installed['files'][installed['main_file']]['path']
            metadata = None
            if main.is_file() and main.suffix == '.gguf':
                try: metadata = inspect_gguf(main)
                except Exception as exc: metadata = {'error':type(exc).__name__, 'message':str(exc)}
            model_cache[key] = {'artifacts':observed, 'gguf':metadata,
                'catalog_revision_matches':key in specs['models'] and installed['exact_revision'] == specs['models'][key]['revision'],
                'catalog_main_artifact_matches':key in specs['models'] and any(
                    row['sha256'] == observed.get(installed['main_file'], {}).get('sha256') and
                    row['size'] == observed.get(installed['main_file'], {}).get('size')
                    for row in specs['models'][key]['files'])}
        entry.update(model_cache[key])
        binary = home / 'bin/needle-worker' if role == 'C2_CONTROL' else Path(os.environ.get('V13_LLAMA_SERVER', home / 'bin/llama-server'))
        if str(binary) not in binary_cache:
            observed = artifact(binary)
            manifest_path = home / ('config/needle-worker.json' if role == 'C2_CONTROL' else 'config/runner.json')
            marker = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
            observed['manifest'] = marker
            observed['matches_install_manifest'] = bool(marker.get('binary_sha256')) and marker['binary_sha256'] == observed['sha256']
            if role == 'C2_CONTROL':
                observed['source_matches_install_manifest'] = marker.get('source_sha256') == file_hash(APP / 'scripts/needle_worker.cpp')
            libraries = list(binary.resolve().parent.glob('libllama.so*')) if role != 'C2_CONTROL' else [home / 'bin/libneedle.so']
            observed['library_exports'] = [inspect_symbols(p) for p in libraries if p.is_file()]
            binary_cache[str(binary)] = observed
        entry['runner'] = binary_cache[str(binary)]
        verified = all(row['matches_manifest'] for row in entry['artifacts'].values()) and entry['runner']['present'] and entry['runner']['matches_install_manifest']
        entry['status'] = 'ARTIFACTS_VERIFIED' if verified else 'ARTIFACTS_UNVERIFIED'
        pinned = entry['catalog_revision_matches'] and entry['catalog_main_artifact_matches']
        if role == 'C2_CONTROL': pinned = pinned and entry['runner'].get('source_matches_install_manifest', False)
        if probe_native and verified and pinned and role != 'TEACHER':
            if progress: progress('Probing ' + role)
            entry['ports'] = probe_role(home, models, role, seconds)
        elif probe_native and role == 'TEACHER':
            entry['probe_limit'] = 'Imported teacher has no pinned native tap contract in this audit'
        elif probe_native and not pinned:
            entry['probe_limit'] = 'Changed/imported model or worker has no pinned native port contract'
    result['status'] = 'AUDIT_COMPLETE'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home'); parser.add_argument('--out', required=True)
    parser.add_argument('--probe-native', action='store_true')
    parser.add_argument('--seconds-per-role', type=float, default=60.)
    args = parser.parse_args()
    if not 5 <= args.seconds_per_role <= 600: parser.error('--seconds-per-role must be 5..600')
    result = audit(home_path(args.home), args.probe_native, args.seconds_per_role,
                   progress=lambda message:print(message, file=sys.stderr, flush=True))
    atomic_write(Path(args.out), dumps(result))
    print(json.dumps({'status':result['status'], 'report':args.out,
                      'native_body_update_authority':0, 'train_runner_proof':None}))


if __name__ == '__main__':
    main()
