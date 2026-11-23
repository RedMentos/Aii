#!/usr/bin/env python3
"""Isolated authored numeric receiver effect, with zero production authority."""
import argparse
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP / 'scripts'))
import test_native_prefill_port as port
import numpy as np
from v13.common import atomic_write, dumps, file_hash
from v13.config import DEFAULTS, home_path
from v13.models import ModelManager, catalog
from v13.resources import device
from v13.runners import LlamaRunner

MESSAGES = [{'role': 'system', 'content': 'Antworte kurz auf Deutsch.'},
            {'role': 'user', 'content': 'Hallo! Was kann ich als Erstes fragen?'}]
SCOPE = ('AUTHORED_NUMERIC_DIAGNOSTIC: bounded write to one ephemeral host F32 '
         'l_out-6 final-token row before verified next-layer norm-7 RMS, then remaining native layers. '
         'No learned projector, B3 utility, receiver authority, model training, '
         'production integration, latency improvement or phone claim.')
NUMERIC_DELTA_POLICY = ('AUTHORED_NUMERIC_DIAGNOSTIC alternating sign; '
                        'target L2=min(.0625, baseline_state_l2*.005); '
                        'coordinate=target L2/sqrt(1024), encoded F32. '
                        'Baseline norm only; no semantic or output-dependent tuning.')


def authored_numeric_delta(baseline_state):
    """Preregistered numeric fixture; this grants no receiver/runtime authority."""
    if not isinstance(baseline_state, list) or len(baseline_state) != 1024:
        raise ValueError('Exact baseline state with 1024 coordinates required')
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in baseline_state):
        raise ValueError('Finite numeric baseline coordinates required; no coercion')
    values = np.asarray(baseline_state, dtype=np.float64)
    if not np.isfinite(values).all() or np.max(np.abs(values)) > np.finfo(np.float32).max:
        raise ValueError('Finite F32 baseline coordinates required')
    baseline_l2 = float(np.linalg.norm(values))
    if not np.isfinite(baseline_l2) or baseline_l2 <= 0:
        raise ValueError('Actual nonzero baseline norm required')
    target_l2 = min(.0625, baseline_l2 * .005)
    coordinate = np.float32(target_l2 / np.sqrt(1024))
    if not np.isfinite(coordinate) or coordinate <= 0:
        raise ValueError('Nonzero representable F32 diagnostic update required')
    vector = [float(coordinate) * (1 if i % 2 == 0 else -1) for i in range(1024)]
    # The native port separately validates actual rounded tensor changes against
    # the unchanged .125 absolute/.01 relative caps before writing.
    return vector


def build_receiver(home, identity, runner, cancel, out):
    _, base = port.prepare_worker(home, identity, runner, cancel, out)
    key = {'base_identity': base['identity_key'], 'source_sha256': file_hash(APP / 'scripts/native_midlayer_effect.cpp'),
           'helper_sha256': file_hash(Path(__file__))}
    binary = home / 'bin/native-midlayer-effect'
    marker = home / 'config/native-midlayer-effect.json'
    prior = json.loads(marker.read_text()) if marker.exists() else {}
    if binary.is_file() and prior.get('identity_key') == key and prior.get('binary_sha256') == file_hash(binary):
        return binary, prior
    source = home / 'tmp/native-prefill-port/source' / ('llama.cpp-' + runner['tag'])
    sha_command = [base['identity_key']['c_compiler'], '-std=c11', '-O2', '-I', str(source / 'vendor/hash'),
                   '-c', str(source / 'vendor/hash/sha256/sha256.c'), '-o', str(home / 'tmp/native-prefill-port/sha256.o')]
    sha_build = port.bounded_process(sha_command, out / 'receiver-sha-build.log', cancel, 60)
    if sha_build['exit_code'] or sha_build['stop_reason']:
        raise RuntimeError('Pinned SHA build failed')
    temporary = binary.with_name(binary.name + '.new')
    command = [str(APP / 'scripts/native_midlayer_effect.cpp') if x == str(APP / 'scripts/native_prefill_worker.cpp') else str(temporary) if x == str(home / 'bin/native-prefill-worker.new') else x for x in base['command']]
    build = port.bounded_process(command, out / 'receiver-build.log', cancel, 180)
    port.save(out / 'receiver-build-attempt.json', {'command': command, 'identity_key': key, 'build': build})
    if build['exit_code'] or build['stop_reason'] or not temporary.is_file():
        raise RuntimeError('Receiver diagnostic compilation failed')
    temporary.chmod(0o700)
    os.replace(temporary, binary)
    result = {'schema': 'V13_MIDLAYER_DIAGNOSTIC_BUILD_V1', 'identity_key': key, 'command': command,
              'build': build, 'sha_build': sha_build, 'binary_sha256': file_hash(binary)}
    port.save(marker, result)
    return binary, result


def array_bytes(values, dtype, count):
    value = np.asarray(values, dtype=dtype)
    if value.shape != (count,) or not np.isfinite(value).all():
        raise ValueError('Actual finite complete native vector required')
    return value.tobytes()


def compare_effect(baseline, zero, nonzero):
    b = baseline['first_position']
    z = zero['first_position']
    n = nonzero['first_position']
    checks = {'baseline_zero_hidden_byte_identical': array_bytes(baseline['native_state_before'], '<f4', 1024) == array_bytes(zero['native_state_after'], '<f4', 1024),
              'baseline_zero_logits_byte_identical': array_bytes(b['logits'], '<f4', 65536) == array_bytes(z['logits'], '<f4', 65536),
              'baseline_zero_probability_byte_identical': array_bytes(b['probabilities'], '<f8', 65536) == array_bytes(z['probabilities'], '<f8', 65536),
              'baseline_zero_greedy_same': b['greedy_token_id'] == z['greedy_token_id'],
              'nonzero_actual_single_ephemeral_write': nonzero['ephemeral_tensor_writes'] == 1,
              'baseline_zero_no_write': baseline['ephemeral_tensor_writes'] == zero['ephemeral_tensor_writes'] == 0,
              'nonzero_cap_and_changed_state': 0 < nonzero['actual_update_l2'] <= .125 and nonzero['actual_relative_update'] <= .01 and nonzero['tensor_before_sha256'] != nonzero['tensor_after_sha256'],
              'same_original_native_state': baseline['tensor_before_sha256'] == zero['tensor_before_sha256'] == nonzero['tensor_before_sha256'],
              'all_current_nextlayer_paths_verified': all(x['verified_current_nextlayer_norm_consumes_source'] for x in [baseline, zero, nonzero]),
              'all_models_unchanged': all(x['model']['sha256'] == x['model_sha256_after'] for x in [baseline, zero, nonzero]),
              'all_native_vectors_bound': all(hashlib.sha256(array_bytes(x['native_state_before'], '<f4', 1024)).hexdigest() == x['tensor_before_sha256'] and hashlib.sha256(array_bytes(x['native_state_after'], '<f4', 1024)).hexdigest() == x['tensor_after_sha256'] for x in [baseline, zero, nonzero])}
    checks['only_final_row_changed'] = all(x['earlier_row_prefix_before_sha256'] == x['earlier_row_prefix_after_sha256'] for x in [baseline, zero, nonzero])
    checks['exact_architecture_layer_sequence_bound'] = all(x['actual_architecture'] == 'lfm2' and x['actual_layer_count'] == 14 and x['target_layer'] == 6 and x['next_consumer'] == 'norm-7' and x['sequence_id'] == 0 and x['selected_token_position'] == len(x['token_ids']) - 1 for x in [baseline, zero, nonzero])
    checks['finite_final_native_state_after_remaining_layers'] = all(len(x['final_native_state_after_remaining_layers']) == 1024 and np.isfinite(np.asarray(x['final_native_state_after_remaining_layers'])).all() for x in [baseline, zero, nonzero])
    left = np.asarray(b['logits'], dtype=np.float64)
    right = np.asarray(n['logits'], dtype=np.float64)
    lp = np.asarray(b['probabilities'], dtype=np.float64)
    rp = np.asarray(n['probabilities'], dtype=np.float64)
    array_bytes(n['logits'], '<f4', 65536)
    array_bytes(n['probabilities'], '<f8', 65536)
    error = float(np.abs(left - right).max())
    variation = float(np.abs(lp - rp).sum() / 2)
    checks['actual_full_vocabulary_effect_measured'] = error > 1e-8 and variation > 1e-9
    checks['actual_probability_mass_valid'] = bool(np.all(lp >= 0) and np.all(rp >= 0) and abs(lp.sum() - 1) <= 1e-9 and abs(rp.sum() - 1) <= 1e-9)
    return {'checks': checks, 'pass': all(checks.values()), 'logits_max_absolute_effect': error,
            'probability_total_variation': variation, 'baseline_greedy_token_id': b['greedy_token_id'],
            'nonzero_greedy_token_id': n['greedy_token_id'], 'greedy_changed': b['greedy_token_id'] != n['greedy_token_id']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed-home', default=None)
    parser.add_argument('--out-dir', default=None)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--rss-limit-mb', type=int, default=768)
    args = parser.parse_args()
    if not 128 <= args.rss_limit_mb <= 2048:
        parser.error('RSS128..2048MiB required')
    home = home_path(args.installed_home)
    out = Path(args.out_dir).resolve() if args.out_dir else home / 'exports' / ('midlayer-effect-' + time.strftime('%Y%m%d-%H%M%S'))
    if out.exists() and any(out.iterdir()):
        parser.error('Fresh attempt directory required')
    out.mkdir(parents=True, exist_ok=True)
    report = {'schema': 'V13_MIDLAYER_NUMERIC_EFFECT_PROOF_V1', 'status': 'PREPARING', 'scope': SCOPE,
              'device': device(), 'production_authority': 0, 'receiver_authority': 0,
              'training_authority': 0, 'variants': []}
    path = out / 'report.json'
    port.save(path, report)
    cancel = threading.Event()
    handlers = {sig: signal.signal(sig, lambda *_: cancel.set()) for sig in [signal.SIGINT, signal.SIGTERM]}
    lock = None
    template = None
    try:
        lock = (home / 'data/coordinator.lock').open('a+')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        specs = catalog()
        models = ModelManager(home)
        model = models.path_for('C3_LANGUAGE')
        if file_hash(model) != specs['models']['language']['files'][0]['sha256'] or models.revision('C3_LANGUAGE') != specs['models']['language']['revision']:
            raise RuntimeError('Exact pinned C3 required')
        identity = port.installed_identity(home, model, specs['runner'])
        pins = out / 'library-pins.json'
        port.save(pins, {'libraries': identity['libraries']})
        binary, build = build_receiver(home, identity, specs['runner'], cancel, out)
        report['build'] = build
        source_files = [APP / 'scripts/native_midlayer_effect.cpp', Path(__file__), APP / 'scripts/native_prefill_worker.cpp', APP / 'scripts/test_native_prefill_port.py']
        snapshots = out / 'source-snapshot'
        snapshots.mkdir()
        for file in source_files:
            shutil.copyfile(file, snapshots / file.name)
        frozen = {str(f.relative_to(APP)): file_hash(f) for f in source_files + [APP / 'specs/models.json', APP / 'v13/runners.py', APP / 'docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md']}
        prereg = {'messages': MESSAGES, 'source_hashes': frozen, 'variants': ['baseline', 'zero', 'nonzero'],
                  'nonzero_delta': NUMERIC_DELTA_POLICY, 'l2_cap_boot': .125,
                  'relative_update_cap_boot': .01, 'max_full_vocab_logit_effect_must_exceed': 1e-8,
                  'full_vocab_tv_must_exceed': 1e-9, 'greedy_change_required': False,
                  'exact_baseline_zero_byte_equality_required': True, 'scope': SCOPE,
                  'installed_identity': identity, 'binary_sha256': file_hash(binary)}
        port.save(out / 'preregistration.json', prereg)
        report['preregistration_sha256'] = file_hash(out / 'preregistration.json')
        report['source_hashes'] = frozen
        guards = subprocess.run([str(binary), '--guard-test'], capture_output=True, text=True, timeout=10)
        if guards.returncode:
            raise RuntimeError('Receiver typed guard failure')
        report['guard_checks'] = json.loads(guards.stdout)
        port.save(out / 'guard-checks.json', report['guard_checks'])
        if args.prepare_only:
            report['status'] = 'RECEIVER_PREPARED_GUARDS_PASS_NO_INFERENCE'
            return 0
        cfg = dict(DEFAULTS, context_tokens=2048, threads=2, answer_tokens=16)
        template = LlamaRunner(home, 'C3_LANGUAGE', model, cfg)
        deadline = time.monotonic() + 90
        template.load(cancel, deadline)
        prompt, count, trimmed = template._prompt(MESSAGES, cancel, deadline, 16)
        ids = template._json('POST', '/tokenize', {'content': prompt, 'add_special': True}, deadline)['tokens']
        if trimmed or count != len(ids) or not 1 <= count <= 128:
            raise RuntimeError('Actual exact receiver template binding failed')
        context = {'messages': MESSAGES, 'prompt': prompt, 'token_ids': ids, 'history_trimmed': trimmed}
        context_sha = hashlib.sha256(dumps(context).encode()).hexdigest()
        port.save(out / 'exact-context-source.json', context)
        token_file = out / 'exact-native-tokens.json'
        port.save(token_file, {'token_ids': ids, 'context_source_sha256': context_sha})
        report['template_release'] = template.unload()
        template = None
        report['status'] = 'RUNNING'
        port.save(path, report)
        observed = {}
        for mode in ['baseline', 'zero', 'nonzero']:
            port.require_uncancelled(cancel, time.monotonic() + 1)
            if any(file_hash(APP / k) != v for k, v in frozen.items()) or port.installed_identity(home, model, specs['runner']) != identity or file_hash(binary) != prereg['binary_sha256']:
                raise RuntimeError('Frozen source/library/model/binary changed')
            nonce = secrets.token_hex(16)
            raw = out / (mode + '-raw.json')
            command = [str(binary), '--model', str(model), '--tokens', str(token_file), '--output', str(raw),
                       '--model-sha256', identity['model_sha256'], '--lib-sha256', identity['libraries'][identity['llama_library']],
                       '--backend-pins', str(pins), '--context-source-sha256', context_sha,
                       '--nonce', nonce, '--mode', mode]
            if mode != 'baseline':
                if 'baseline' not in observed:
                    raise RuntimeError('Actual baseline required before any receiver vector; capability unavailable')
                payload = {'schema': 'V13_AUTHORED_MIDLAYER_EFFECT_VECTOR_V1', 'scope': 'AUTHORED_NUMERIC_DIAGNOSTIC',
                           'source_id': 'AUTHORED_NUMERIC_' + mode + '_' + nonce, 'nonce': nonce,
                           'model_sha256': identity['model_sha256'], 'runner_library_sha256': identity['libraries'][identity['llama_library']],
                           'backend_manifest_sha256': file_hash(pins), 'context_source_sha256': context_sha,
                           'token_file_sha256': file_hash(token_file), 'target_tensor': 'l_out-6',
                           'target_tensor_before_sha256': observed['baseline']['tensor_before_sha256'], 'dimension': 1024, 'architecture': 'lfm2', 'layer_count': 14,
                           'target_layer': 6, 'next_consumer': 'norm-7', 'sequence_id': 0,
                           'target_token_position': len(ids)-1, 'decode_epoch': 1,
                           'delta_vector': [0.] * 1024 if mode == 'zero' else authored_numeric_delta(observed['baseline']['native_state_before'])}
                delta = out / (mode + '-authored-delta.json')
                port.save(delta, payload)
                command.extend(['--delta', str(delta), '--delta-sha256', file_hash(delta)])
            metrics = port.bounded_process(command, out / (mode + '-native.log'), cancel, 93, args.rss_limit_mb)
            report['variants'].append({'mode': mode, 'command': command, 'metrics': metrics})
            if raw.exists():
                native = json.loads(raw.read_text())
                gz = raw.with_suffix('.json.gz')
                atomic_write(gz, gzip.compress(raw.read_bytes(), mtime=0))
                report['variants'][-1]['raw_artifact'] = {'path': gz.name, 'sha256': file_hash(gz)}
                report['variants'][-1]['native_status'] = native.get('status')
                report['variants'][-1]['native_error'] = native.get('error')
                if metrics['exit_code'] == 0 and metrics['stop_reason'] is None and native.get('status') == 'BOUNDED_MIDLAYER_DIAGNOSTIC_COMPLETE':
                    observed[mode] = native
            port.save(path, report)
            print(dumps({'mode': mode, 'exit_code': metrics['exit_code'], 'native_status': report['variants'][-1].get('native_status')}), flush=True)
        if set(observed) != {'baseline', 'zero', 'nonzero'}:
            raise RuntimeError('All three actual receiver variants required; no fabricated effect')
        report['comparison'] = compare_effect(observed['baseline'], observed['zero'], observed['nonzero'])
        report['checks'] = {'actual_receiver_comparison_pass': report['comparison']['pass'],
                            'all_processes_reaped': all(v['metrics']['process_reaped'] for v in report['variants']),
                            'source_model_library_binary_unchanged': all(file_hash(APP / k) == v for k, v in frozen.items()) and port.installed_identity(home, model, specs['runner']) == identity and file_hash(binary) == prereg['binary_sha256']}
        report['status'] = 'BOUNDED_MIDLAYER_NUMERIC_EFFECT_PASS' if all(report['checks'].values()) else 'BOUNDED_MIDLAYER_NUMERIC_EFFECT_FAIL'
        return 0 if report['status'].endswith('_PASS') else 1
    except BaseException as exc:
        report['status'] = 'BOUNDED_MIDLAYER_NUMERIC_EFFECT_FAIL'
        report['error'] = str(exc)
        report['error_type'] = type(exc).__name__
        report['traceback'] = traceback.format_exc()
        return 1
    finally:
        if template is not None:
            report['final_template_release'] = template.unload()
        if lock is not None:
            fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()
        for sig, handler in handlers.items():
            signal.signal(sig, handler)
        port.save(path, report)
        print(dumps({'status': report['status'], 'report': str(path), 'scope': SCOPE}), flush=True)


if __name__ == '__main__':
    raise SystemExit(main())
