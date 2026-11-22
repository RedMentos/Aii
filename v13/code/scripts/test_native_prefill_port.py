#!/usr/bin/env python3
"""Portable, read-only C3 same-prefill BodyPort proof (llama.cpp b10964).

Uses actual installed C3 template/token IDs, then runs baseline and callback
workers separately under the existing coordinator lock. No production switch,
feature-compatibility, semantic quality, phone speedup or training claim.
"""
import argparse
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
import numpy as np
from v13.bootstrap import extract
from v13.common import atomic_write, dumps, file_hash, safe_text
from v13.config import DEFAULTS, home_path
from v13.models import ModelManager, catalog, download_file
from v13.resources import device, process_memory
from v13.runners import LlamaRunner

TOLERANCES = {'logits_atol': 1e-5, 'logits_rtol': 1e-6,
              'max_probability_total_variation': 1e-6,
              'probability_mass_atol': 1e-9, 'nonzero_hidden_squared_norm': 1e-20}
MESSAGES = [
    {'name': 'short_native_greeting', 'messages': [
        {'role': 'system', 'content': 'Antworte kurz auf Deutsch.'},
        {'role': 'user', 'content': 'Hallo! Was kann ich als Erstes fragen?'}]},
    {'name': 'long_exact_context', 'messages': [
        {'role': 'system', 'content': 'Antworte kurz auf Deutsch. Die folgenden Einträge sind ausdrücklich bereitgestellte Testdaten: ' +
         ' '.join(f'Eintrag {i}: Projekt Morgen hat ein Budget von 120 Euro und eine Frist von 3 Tagen.' for i in range(8))},
        {'role': 'user', 'content': 'Wie hoch ist das Budget von Projekt Morgen?'}]}]
SCOPE = ('Read-only observer invariance of a same causal C3 prefill and continuation. '
         'No production integration, old embedding-feature compatibility, speedup, '
         'semantic quality, receiver injection, model training or full-Canon proof.')


def save(path, value):
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2))


def require_uncancelled(cancel, deadline):
    if cancel.is_set():
        raise RuntimeError('Native port test cancelled; completed raw artifacts retained')
    if time.monotonic() >= deadline:
        raise RuntimeError('Native port test exceeded bounded deadline')


def installed_identity(home, model, runner):
    server = (home / 'bin/llama-server').resolve(strict=True)
    marker = json.loads((home / 'config/runner.json').read_text())
    if marker.get('tag') != runner['tag'] or marker.get('binary_sha256') != file_hash(server):
        raise RuntimeError('Installed server identity differs from setup manifest; run setup.sh')
    directory = server.parent
    libraries = {}
    for p in directory.glob('lib*.so*'):
        if p.is_file():
            resolved = p.resolve(strict=True)
            libraries[str(resolved)] = file_hash(resolved)
    for stem in ['libllama.so', 'libggml.so', 'libggml-base.so', 'libggml-cpu']:
        if not any(Path(p).name.startswith(stem) for p in libraries):
            raise RuntimeError('Installed shared library missing: ' + stem)
    # Link the exact installed shared objects rather than a system-wide -l search.
    def library(stem):
        found = [Path(p) for p in libraries if Path(p).name.startswith(stem)]
        if len(found) != 1:
            raise RuntimeError('Ambiguous installed shared library: ' + stem)
        return found[0]
    return {'server_path': str(server), 'server_sha256': file_hash(server),
            'model_path': str(model), 'model_sha256': file_hash(model),
            'library_directory': str(directory), 'libraries': libraries,
            'llama_library': str(library('libllama.so')),
            'link_libraries': [str(library(x)) for x in ['libllama.so', 'libggml.so', 'libggml-base.so']],
            'runner_manifest_sha256': file_hash(home / 'config/runner.json')}


def bounded_process(command, log, cancel, seconds, rss_limit_mb=None, env=None):
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.monotonic()
    deadline = started + seconds
    peak = {'rss_bytes': None, 'pss_bytes': None}
    samples = []
    count = 0
    reason = None
    with log.open('wb') as handle:
        proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=handle,
                                stderr=subprocess.STDOUT, env=env, start_new_session=True)
        try:
            while proc.poll() is None:
                memory = process_memory(proc.pid)
                count += 1
                for key in peak:
                    if memory.get(key) is not None:
                        peak[key] = max(peak[key] or 0, memory[key])
                samples.append({'elapsed_s': time.monotonic() - started, **memory})
                if len(samples) > 64:
                    del samples[1]
                if cancel.is_set():
                    reason = 'CANCELLED'
                elif time.monotonic() >= deadline:
                    reason = 'DEADLINE'
                elif rss_limit_mb and (memory.get('rss_bytes') or 0) > rss_limit_mb * 1024 * 1024:
                    reason = 'RSS_LIMIT'
                if reason:
                    break
                cancel.wait(.05)
        finally:
            if proc.poll() is None:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    proc.wait(timeout=3)
            rc = proc.wait()
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {'exit_code': rc, 'stop_reason': reason, 'process_reaped': proc.poll() is not None,
            'wall_elapsed_s': time.monotonic() - started,
            'user_cpu_s': after.ru_utime - before.ru_utime,
            'system_cpu_s': after.ru_stime - before.ru_stime,
            'sample_interval_s': .05, 'resource_sample_count': count,
            'resource_peak': peak, 'resource_samples': samples,
            'log_path': str(log), 'log_sha256': file_hash(log)}


def prepare_worker(home, identity, runner, cancel, out):
    cache = home / 'tmp/native-prefill-port'
    cache.mkdir(parents=True, exist_ok=True)
    compiler = shutil.which('clang++') or shutil.which('g++')
    if not compiler:
        raise RuntimeError('C++ compiler missing; Termux setup.sh installs clang')
    c_compiler = shutil.which('clang') or shutil.which('gcc')
    if not c_compiler:
        raise RuntimeError('C compiler missing for pinned SHA implementation')
    archive_spec = {'url': runner['source_url'], 'size': runner['source_size'], 'sha256': runner['source_sha256']}
    archive = download_file(archive_spec, cache / 'llama-source.tar.gz', cancel=cancel)
    src = cache / 'source' / ('llama.cpp-' + runner['tag'])
    if not src.exists():
        extract(archive, cache / 'source')
    # Extraction marker is not sufficient: exact required build input hashes are
    # compared with fresh pinned archive members before any compilation/reuse.
    import tarfile
    needed = ['include/llama.h', 'ggml/include/ggml.h', 'ggml/include/ggml-backend.h',
              'ggml/include/ggml-cpu.h', 'ggml/include/ggml-alloc.h',
              'common/json.hpp', 'vendor/nlohmann/json.hpp',
              'vendor/hash/sha256/sha256.h', 'vendor/hash/sha256/sha256.c', 'vendor/hash/rotate-bits/rotate-bits.h']
    source_hashes = {}
    with tarfile.open(archive) as tar:
        # Include all public ggml headers: their transitive includes are pinned too.
        names = [m.name for m in tar.getmembers() if m.isfile() and
                 (m.name.startswith('llama.cpp-' + runner['tag'] + '/ggml/include/') or
                  m.name.split('/', 1)[-1] in needed)]
        for name in names:
            relative = name.split('/', 1)[1]
            data = tar.extractfile(name).read()
            expected = hashlib.sha256(data).hexdigest()
            if file_hash(src / relative) != expected:
                raise RuntimeError('Pinned source extraction changed: ' + relative)
            source_hashes[relative] = expected
    for required in ['include/llama.h', 'vendor/nlohmann/json.hpp', 'vendor/hash/sha256/sha256.h', 'vendor/hash/sha256/sha256.c', 'vendor/hash/rotate-bits/rotate-bits.h']:
        if required not in source_hashes:
            raise RuntimeError('Pinned source missing required build input: ' + required)
    worker = home / 'bin/native-prefill-worker'
    marker = home / 'config/native-prefill-worker.json'
    identity_key = {'worker_source_sha256': file_hash(APP / 'scripts/native_prefill_worker.cpp'),
                    'collector_source_sha256': file_hash(Path(__file__)),
                    'source_archive': archive_spec, 'headers_and_sha_source': source_hashes,
                    'installed': identity, 'compiler': str(Path(compiler).resolve()), 'compiler_sha256': file_hash(Path(compiler).resolve()),
                    'c_compiler': str(Path(c_compiler).resolve()), 'c_compiler_sha256': file_hash(Path(c_compiler).resolve()),
                    'machine': platform.machine(), 'build_flags': ['-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror']}
    old = json.loads(marker.read_text()) if marker.exists() else {}
    if worker.is_file() and old.get('identity_key') == identity_key and old.get('binary_sha256') == file_hash(worker):
        return worker, old
    temporary = worker.with_name(worker.name + '.new')
    sha_object = cache / 'sha256.o'
    sha_command = [c_compiler, '-std=c11', '-O2', '-I', str(src / 'vendor/hash'), '-c', str(src / 'vendor/hash/sha256/sha256.c'), '-o', str(sha_object)]
    sha_build = bounded_process(sha_command, out / 'worker-sha-build.log', cancel, 60)
    save(out / 'worker-sha-build-attempt.json', {'command': sha_command, 'build': sha_build})
    if sha_build['exit_code'] or sha_build['stop_reason']:
        raise RuntimeError('Pinned SHA compilation failed; see worker-sha-build.log')
    command = [compiler, *identity_key['build_flags'], '-I', str(src / 'include'),
               '-I', str(src / 'ggml/include'), '-I', str(src / 'vendor'),
               '-I', str(src / 'vendor/hash/sha256'), str(APP / 'scripts/native_prefill_worker.cpp'),
               str(sha_object), *identity['link_libraries'],
               '-Wl,-rpath,' + identity['library_directory'], '-ldl', '-pthread', '-o', str(temporary)]
    log = out / 'worker-build.log'
    build = bounded_process(command, log, cancel, 180)
    save(out / 'worker-build-attempt.json', {'identity_key': identity_key, 'command': command, 'build': build})
    if build['exit_code'] or build['stop_reason'] or not temporary.is_file():
        raise RuntimeError('Native worker compilation failed; see ' + str(log))
    temporary.chmod(0o700)
    os.replace(temporary, worker)
    result = {'schema': 'V13_PORTABLE_NATIVE_PREFILL_BUILD_V1', 'identity_key': identity_key,
              'binary_sha256': file_hash(worker), 'command': command, 'build': build, 'sha_build': sha_build}
    save(marker, result)
    return worker, result


def compare_pair(baseline, live, ids):
    checks = {'actual_native_status': baseline.get('status') == live.get('status') == 'READONLY_NATIVE_PORT_OBSERVED',
              'exact_input_tokens': baseline.get('token_ids') == live.get('token_ids') == ids,
              'actual_loaded_libraries_verified': baseline.get('all_loaded_libraries_verified') is True and live.get('all_loaded_libraries_verified') is True,
              'same_greedy_continuation': baseline.get('first_position', {}).get('greedy_token_id') == live.get('first_position', {}).get('greedy_token_id') and baseline.get('continuation') == live.get('continuation'),
              'same_actual_preview': baseline.get('decoded_native_token_ids') == live.get('decoded_native_token_ids') and baseline.get('decoded_native_preview') == live.get('decoded_native_preview'),
              'same_decode_norm_and_output': live.get('decode_calls', [{}])[-1].get('result_norm_count') == 1 and live.get('decode_calls', [{}])[-1].get('result_output_count') == 1}
    h = np.asarray(live.get('live_last_state', []), dtype=np.float64)
    checks['finite_nonzero_1024_hidden'] = bool(h.shape == (1024,) and np.isfinite(h).all() and h @ h > TOLERANCES['nonzero_hidden_squared_norm'])
    left = np.asarray(live.get('first_position', {}).get('logits', []), dtype=np.float64)
    right = np.asarray(baseline.get('first_position', {}).get('logits', []), dtype=np.float64)
    logits_valid = left.shape == right.shape == (65536,) and np.isfinite(left).all() and np.isfinite(right).all()
    checks['complete_finite_actual_logits'] = bool(logits_valid)
    checks['observer_invariant_logits'] = bool(logits_valid and np.allclose(left, right, atol=TOLERANCES['logits_atol'], rtol=TOLERANCES['logits_rtol']))
    lp = np.asarray(live.get('first_position', {}).get('probabilities', []), dtype=np.float64)
    rp = np.asarray(baseline.get('first_position', {}).get('probabilities', []), dtype=np.float64)
    prob_valid = lp.shape == rp.shape == (65536,) and np.isfinite(lp).all() and np.isfinite(rp).all() and np.all(lp >= 0) and np.all(rp >= 0)
    checks['complete_actual_probability_distribution'] = bool(prob_valid and abs(lp.sum() - 1) <= TOLERANCES['probability_mass_atol'] and abs(rp.sum() - 1) <= TOLERANCES['probability_mass_atol'])
    variation = float(np.abs(lp - rp).sum() / 2) if prob_valid else None
    checks['observer_invariant_distribution'] = bool(prob_valid and variation <= TOLERANCES['max_probability_total_variation'])
    checks['computed_output_present'] = baseline.get('logits_computed') is True and live.get('logits_computed') is True
    return {'checks': checks, 'pass': all(checks.values()), 'probability_total_variation': variation,
            'logits_max_absolute_error': float(np.abs(left - right).max()) if logits_valid else None,
            'hidden_squared_norm': float(h @ h) if checks['finite_nonzero_1024_hidden'] else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed-home', default=None)
    parser.add_argument('--out-dir', default=None)
    parser.add_argument('--prepare-only', action='store_true', help='Build and verify identity; no inference')
    parser.add_argument('--seconds', type=int, default=90)
    parser.add_argument('--rss-limit-mb', type=int, default=768)
    args = parser.parse_args()
    if not 5 <= args.seconds <= 120 or not 128 <= args.rss_limit_mb <= 2048:
        parser.error('seconds must be 5..120; rss limit must be 128..2048 MB')
    home = home_path(args.installed_home)
    if not (home / 'config/runner.json').is_file():
        parser.error('Run STARTEN.sh/setup.sh first; installed native runner required')
    out = Path(args.out_dir).resolve() if args.out_dir else home / 'exports' / ('native-prefill-' + time.strftime('%Y%m%d-%H%M%S'))
    if out.exists() and any(out.iterdir()):
        parser.error('Use a new output directory; completed/failed attempts are immutable')
    out.mkdir(parents=True, exist_ok=True)
    cancel = threading.Event()
    old_handlers = {}
    for sig in [signal.SIGINT, signal.SIGTERM]:
        old_handlers[sig] = signal.signal(sig, lambda *_: cancel.set())
    report = {'schema': 'V13_PORTABLE_NATIVE_PREFILL_PROOF_V1', 'status': 'PREPARING',
              'device': device(), 'scope': SCOPE, 'production_integration': False,
              'training_authority': 0, 'receiver_authority': 0, 'native_kv_bytes': None,
              'cases': [], 'contexts': [], 'checks': {}, 'created_wall_time': time.time()}
    path = out / 'report.json'
    save(path, report)
    lock = None
    runner_instance = None
    try:
        lock = (home / 'data/coordinator.lock').open('a+')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError('V13 is running: close :chat before this isolated test') from exc
        specs = catalog()
        models = ModelManager(home)
        model = models.path_for('C3_LANGUAGE')
        expected = specs['models']['language']['files'][0]['sha256']
        if file_hash(model) != expected or models.revision('C3_LANGUAGE') != specs['models']['language']['revision']:
            raise RuntimeError('Read-only proof requires the exact pinned C3 model, not an imported replacement')
        identity = installed_identity(home, model, specs['runner'])
        pins_path = out / 'loaded-library-pins.json'
        save(pins_path, {'libraries': identity['libraries']})
        worker, build = prepare_worker(home, identity, specs['runner'], cancel, out)
        report['build'] = build
        report['installed_identity'] = identity
        frozen = {str(p.relative_to(APP)): file_hash(p) for p in [
            Path(__file__), APP / 'scripts/native_prefill_worker.cpp', APP / 'specs/models.json',
            APP / 'v13/runners.py', APP / 'docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md']}
        prereg = {'schema': 'V13_PORTABLE_NATIVE_PREFILL_PREREGISTRATION_V1', 'messages': MESSAGES,
                  'prefix_token_lengths': [127, 128, 129], 'tolerances': TOLERANCES,
                  'batch': 128, 'physical_batch': 128, 'context': 2048, 'threads': 2,
                  'continuations': 3, 'deadline_seconds_per_native_call': args.seconds,
                  'rss_limit_mb_boot_choice': args.rss_limit_mb, 'source_hashes': frozen,
                  'installed_identity': identity, 'worker_binary_sha256': file_hash(worker), 'scope': SCOPE}
        save(out / 'preregistration.json', prereg)
        report['preregistration_sha256'] = file_hash(out / 'preregistration.json')
        report['source_hashes'] = frozen
        if args.prepare_only:
            report['status'] = 'PREPARED_NO_INFERENCE'
            return 0
        cfg = dict(DEFAULTS, context_tokens=2048, threads=2, answer_tokens=16)
        report['status'] = 'RUNNING'
        save(path, report)
        cases = []
        for fixture in MESSAGES:
            deadline = time.monotonic() + args.seconds
            require_uncancelled(cancel, deadline)
            runner_instance = LlamaRunner(home, 'C3_LANGUAGE', model, cfg)
            monitor_done = threading.Event()
            template_metrics = {'rss_bytes': None, 'pss_bytes': None, 'resource_sample_count': 0, 'rss_limit_exceeded': False}
            def monitor_template():
                while not monitor_done.is_set():
                    proc = runner_instance.proc if runner_instance is not None else None
                    if proc is not None and proc.poll() is None:
                        mem = process_memory(proc.pid)
                        template_metrics['resource_sample_count'] += 1
                        for key in ['rss_bytes', 'pss_bytes']:
                            if mem.get(key) is not None:
                                template_metrics[key] = max(template_metrics[key] or 0, mem[key])
                        if (mem.get('rss_bytes') or 0) > args.rss_limit_mb * 1024 * 1024:
                            template_metrics['rss_limit_exceeded'] = True
                            cancel.set()
                    monitor_done.wait(.05)
            monitor = threading.Thread(target=monitor_template, daemon=True)
            monitor.start()
            try:
                runner_instance.load(cancel, deadline)
                prompt, n, trimmed = runner_instance._prompt(fixture['messages'], cancel, deadline, 16)
                ids = runner_instance._json('POST', '/tokenize', {'content': prompt, 'add_special': True}, deadline)['tokens']
                if trimmed or n != len(ids) or not 1 <= n <= 512:
                    raise RuntimeError('Native exact template token/context binding failed')
                context = {'name': fixture['name'], 'messages': fixture['messages'], 'prompt': prompt,
                           'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                           'token_ids': ids, 'token_count': n, 'history_trimmed': trimmed}
                report['contexts'].append(context)
            finally:
                monitor_done.set()
                monitor.join(timeout=1)
                release = runner_instance.unload()
                runner_instance = None
            require_uncancelled(cancel, deadline)
            context['template_server_resource_peak'] = template_metrics
            context['template_server_release'] = release
            save(path, report)
            cases.append((fixture['name'], ids, 'EXACT_NATIVE_TEMPLATE'))
            if fixture['name'] == 'long_exact_context':
                if n <= 129:
                    raise RuntimeError('Long preregistered context must cross physical batch boundary')
                cases.extend((fixture['name'] + '-prefix-' + str(k), ids[:k], 'NATIVE_TOKEN_PREFIX_DIAGNOSTIC') for k in [127, 128, 129])
        for name, ids, binding in cases:
            if any(file_hash(APP / k) != v for k, v in frozen.items()) or installed_identity(home, model, specs['runner']) != identity or file_hash(worker) != prereg['worker_binary_sha256']:
                raise RuntimeError('Source/library/model identity changed during proof')
            case = {'name': name, 'binding': binding, 'token_count': len(ids), 'variants': {}}
            report['cases'].append(case)
            token_path = out / (name + '-tokens.json')
            save(token_path, {'token_ids': ids, 'binding': binding})
            observed = {}
            for mode in ['baseline', 'live']:
                raw_path = out / (name + '-' + mode + '.raw.json')
                log = out / (name + '-' + mode + '.log')
                command = [str(worker), '--model', str(model), '--tokens', str(token_path), '--output', str(raw_path),
                           '--mode', mode, '--model-sha256', identity['model_sha256'],
                           '--lib-sha256', identity['libraries'][identity['llama_library']],
                           '--backend-pins', str(pins_path), '--n-batch', '128', '--n-ubatch', '128',
                           '--ctx', '2048', '--threads', '2', '--continue', '3', '--seconds', str(args.seconds)]
                metrics = bounded_process(command, log, cancel, args.seconds + 3, args.rss_limit_mb)
                case['variants'][mode] = metrics
                if raw_path.exists():
                    raw = json.loads(raw_path.read_text())
                    compressed = out / (name + '-' + mode + '.json.gz')
                    atomic_write(compressed, gzip.compress(raw_path.read_bytes(), mtime=0))
                    metrics['raw_artifact'] = {'path': compressed.name, 'sha256': file_hash(compressed), 'bytes': compressed.stat().st_size}
                    # Preserve the raw failed response as well as its compressed copy.
                    if metrics['exit_code'] == 0 and metrics['stop_reason'] is None:
                        observed[mode] = raw
                save(path, report)
                print(dumps({'case': name, 'mode': mode, 'exit_code': metrics['exit_code'], 'stop_reason': metrics['stop_reason']}), flush=True)
                require_uncancelled(cancel, time.monotonic() + 1)
            if set(observed) == {'baseline', 'live'}:
                case['comparison'] = compare_pair(observed['baseline'], observed['live'], ids)
                case['status'] = 'PAIR_PASS' if case['comparison']['pass'] else 'PAIR_FAIL'
                print('Native Vorschau: ' + safe_text(observed['live'].get('decoded_native_preview', '')), flush=True)
            else:
                case['status'] = 'PAIR_FAIL'
                case['error'] = 'Both actual native variants required; no synthetic replacement'
            save(path, report)
        report['checks'] = {'five_preregistered_cases': len(report['cases']) == 5,
                            'all_actual_native_pairs_pass': all(c.get('status') == 'PAIR_PASS' for c in report['cases']),
                            'all_processes_reaped': all(v['process_reaped'] for c in report['cases'] for v in c['variants'].values()),
                            'exact_model_libraries_unchanged': installed_identity(home, model, specs['runner']) == identity,
                            'worker_binary_unchanged': file_hash(worker) == prereg['worker_binary_sha256'],
                            'all_source_hashes_unchanged': all(file_hash(APP / k) == v for k, v in frozen.items())}
        report['status'] = 'LIVE_PREFILL_OBSERVER_INVARIANCE_PASS' if all(report['checks'].values()) else 'LIVE_PREFILL_OBSERVER_INVARIANCE_FAIL'
        return 0 if report['status'].endswith('_PASS') else 1
    except BaseException as exc:
        report['status'] = 'LIVE_PREFILL_OBSERVER_INVARIANCE_FAIL'
        report['error_type'] = type(exc).__name__
        report['error'] = str(exc)
        report['traceback'] = traceback.format_exc()
        return 1
    finally:
        if runner_instance is not None:
            report['last_template_server_release'] = runner_instance.unload()
        if lock is not None:
            fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()
        for sig, old in old_handlers.items():
            signal.signal(sig, old)
        save(path, report)
        print(dumps({'status': report['status'], 'report': str(path), 'scope': SCOPE}), flush=True)


if __name__ == '__main__':
    raise SystemExit(main())
