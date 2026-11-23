#!/usr/bin/env python3
"""Two actual same-context pause/resume diagnostics; no old-head integration."""
import argparse
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import secrets
import selectors
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
from v13.common import atomic_write, dumps, file_hash, safe_text
from v13.config import DEFAULTS, home_path
from v13.models import ModelManager, catalog
from v13.resources import device, process_memory
from v13.runners import LlamaRunner

MESSAGES = [{'role': 'system', 'content': 'Antworte kurz auf Deutsch.'},
            {'role': 'user', 'content': 'Hallo! Was kann ich als Erstes fragen?'}]
SCOPE = ('Authored numeric zero/nonzero first-position bias on one paused real causal C3 '
         'context, followed by unbiased native continuation. No production/approval authority, '
         'old embedding-head compatibility, learning, receiver injection, latency or phone claim.')


def build_session(home, identity, runner, cancel, out):
    _, base = port.prepare_worker(home, identity, runner, cancel, out)
    key = {'base_build_identity': base['identity_key'],
           'source_sha256': file_hash(APP / 'scripts/native_prefill_session.cpp'),
           'helper_sha256': file_hash(Path(__file__))}
    binary = home / 'bin/native-prefill-session'
    marker = home / 'config/native-prefill-session.json'
    prior = json.loads(marker.read_text()) if marker.exists() else {}
    if binary.is_file() and prior.get('identity_key') == key and prior.get('binary_sha256') == file_hash(binary):
        return binary, prior
    original = base['command']
    sha_attempt = base['sha_build']
    sha_command = json.loads((out / 'worker-sha-build-attempt.json').read_text())['command'] if (out / 'worker-sha-build-attempt.json').exists() else [key['base_build_identity']['c_compiler'], '-std=c11', '-O2', '-I', str(home / 'tmp/native-prefill-port/source' / ('llama.cpp-' + runner['tag']) / 'vendor/hash'), '-c', str(home / 'tmp/native-prefill-port/source' / ('llama.cpp-' + runner['tag']) / 'vendor/hash/sha256/sha256.c'), '-o', str(home / 'tmp/native-prefill-port/sha256.o')]
    # Never trust a transient SHA object merely because a previous worker was valid.
    sha_attempt = port.bounded_process(sha_command, out / 'session-sha-build.log', cancel, 60)
    if sha_attempt['exit_code'] or sha_attempt['stop_reason']:
        raise RuntimeError('Pinned SHA compilation failed')
    temp = binary.with_name(binary.name + '.new')
    command = [str(APP / 'scripts/native_prefill_session.cpp') if x == str(APP / 'scripts/native_prefill_worker.cpp') else str(temp) if x == str(home / 'bin/native-prefill-worker.new') else x for x in original]
    build = port.bounded_process(command, out / 'session-build.log', cancel, 180)
    port.save(out / 'session-build-attempt.json', {'identity_key': key, 'command': command, 'build': build})
    if build['exit_code'] or build['stop_reason'] or not temp.exists():
        raise RuntimeError('Session worker compilation failed')
    temp.chmod(0o700)
    os.replace(temp, binary)
    result = {'schema': 'V13_PREFILL_SESSION_BUILD_V1', 'identity_key': key,
              'command': command, 'build': build, 'sha_build': sha_attempt,
              'binary_sha256': file_hash(binary)}
    port.save(marker, result)
    return binary, result


def identity_of_handle(handle):
    value = dict(handle)
    value.pop('handle_id', None)
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(encoded).hexdigest()


def command_for(handle, features, mode):
    rows = []
    fixture = {'policy': 'ZERO_NUMERIC_DELTA' if mode == 'zero' else 'SECOND_BEST_NATIVE_ROW_PLUS_GAP_PLUS_ONE',
               'numeric_fixture_authority': 'DIAGNOSTIC_ONLY', 'approval_authority': 0}
    if mode == 'nonzero':
        logits = features['first_position']['logits']
        order = sorted(range(len(logits)), key=lambda i: (-logits[i], i))
        top, second = order[:2]
        bias = float(logits[top]) - float(logits[second]) + 1.
        if not 0 < bias <= 12:
            raise RuntimeError('Second-best numeric diagnostic needs >12 bias; retained failure, no repaired fixture')
        rows = [[second, bias]]
        fixture.update(baseline_top_token_id=top, diagnostic_target_token_id=second, actual_numeric_bias=bias)
    return {'command': 'resume', 'handle_id': handle['handle_id'], 'nonce': handle['nonce'],
            'context_source_sha256': handle['context_source_sha256'], 'bias': rows}, fixture


def run_paused(binary, identity, home, out, token_file, context_sha, mode, cancel, seconds, rss_mb):
    raw_path = out / (mode + '-result.json')
    features_path = out / (mode + '-features.json')
    pin_file = out / 'library-pins.json'
    nonce = secrets.token_hex(16)
    command = [str(binary), '--model', identity['model_path'], '--tokens', str(token_file),
               '--output', str(raw_path), '--features', str(features_path),
               '--model-sha256', identity['model_sha256'], '--lib-sha256', identity['libraries'][identity['llama_library']],
               '--backend-pins', str(pin_file), '--context-source-sha256', context_sha,
               '--nonce', nonce, '--wait-seconds', '15', '--seconds', str(seconds)]
    started = time.monotonic()
    samples = []
    peaks = {'rss_bytes': None, 'pss_bytes': None}
    metrics = {'mode': mode, 'command': command, 'resource_samples': samples, 'resource_peak': peaks,
               'resource_sample_count': 0, 'stop_reason': None, 'protocol': [], 'resume_commands_sent': 0}
    log = out / (mode + '-native.log')
    process = None
    selector = selectors.DefaultSelector()
    pending = b''
    try:
        with log.open('wb') as stderr:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr, start_new_session=True)
            selector.register(process.stdout, selectors.EVENT_READ)
            while process.poll() is None:
                memory = process_memory(process.pid)
                metrics['resource_sample_count'] += 1
                for key in peaks:
                    if memory.get(key) is not None:
                        peaks[key] = max(peaks[key] or 0, memory[key])
                samples.append({'elapsed_s': time.monotonic() - started, **memory})
                if len(samples) > 64:
                    del samples[1]
                if cancel.is_set():
                    metrics['stop_reason'] = 'CANCELLED'
                    break
                if time.monotonic() - started >= seconds + 3:
                    metrics['stop_reason'] = 'DEADLINE'
                    break
                if (memory.get('rss_bytes') or 0) > rss_mb * 1024 * 1024:
                    metrics['stop_reason'] = 'RSS_LIMIT'
                    break
                for key, _ in selector.select(.05):
                    data = os.read(key.fileobj.fileno(), 8192)
                    if not data:
                        selector.unregister(key.fileobj)
                        continue
                    pending += data
                    if len(pending) > 65536:
                        raise RuntimeError('Bounded worker protocol exceeded64KiB')
                    while b'\n' in pending:
                        line, pending = pending.split(b'\n', 1)
                        msg = json.loads(line)
                        metrics['protocol'].append(msg)
                        if msg.get('status') == 'PREFILLED_READY':
                            if metrics['resume_commands_sent']:
                                raise RuntimeError('Duplicate READY handle refused')
                            handle = msg['handle']
                            if handle['nonce'] != nonce or handle['pid'] != process.pid or handle['context_source_sha256'] != context_sha or handle['model_sha256'] != identity['model_sha256'] or handle['lib_sha256'] != identity['libraries'][identity['llama_library']] or handle['features_sha256'] != file_hash(features_path) or handle['token_file_sha256'] != file_hash(token_file) or identity_of_handle(handle) != handle['handle_id']:
                                raise RuntimeError('Actual paused handle identity mismatch')
                            features = json.loads(features_path.read_text())
                            if features['pid'] != process.pid or features['token_ids'] != json.loads(token_file.read_text())['token_ids']:
                                raise RuntimeError('Actual paused features/token/process binding mismatch')
                            resume, fixture = command_for(handle, features, mode)
                            metrics['numeric_fixture'] = fixture
                            metrics['paused_pid'] = process.pid
                            metrics['paused_feature_sha256'] = file_hash(features_path)
                            port.save(out / (mode + '-resume-command.json'), resume)
                            port.save(out / (mode + '-controller.json'), metrics)
                            process.stdin.write((dumps(resume) + '\n').encode())
                            process.stdin.flush()
                            process.stdin.close()
                            metrics['resume_commands_sent'] = 1
            if process.poll() is not None and process.stdout is not None:
                tail = process.stdout.read()
                for line in (pending + tail).splitlines():
                    if line:
                        metrics['protocol'].append(json.loads(line))
    except BaseException as exc:
        metrics['error'] = str(exc)
        metrics['error_type'] = type(exc).__name__
    finally:
        selector.close()
        if process is not None:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=3)
            metrics['exit_code'] = process.wait()
            metrics['process_reaped'] = process.poll() is not None
            if process.stdout:
                process.stdout.close()
            if process.stdin and not process.stdin.closed:
                process.stdin.close()
        metrics['wall_elapsed_s'] = time.monotonic() - started
        if log.exists():
            metrics['log_sha256'] = file_hash(log)
        for artifact in [raw_path, features_path]:
            if artifact.exists():
                gz = artifact.with_suffix('.json.gz')
                atomic_write(gz, gzip.compress(artifact.read_bytes(), mtime=0))
                metrics[artifact.stem + '_artifact'] = {'path': gz.name, 'sha256': file_hash(gz)}
        port.save(out / (mode + '-controller.json'), metrics)
    if raw_path.exists() and features_path.exists():
        raw = json.loads(raw_path.read_text())
        features = json.loads(features_path.read_text())
        command = json.loads((out / (mode + '-resume-command.json')).read_text()) if (out / (mode + '-resume-command.json')).exists() else None
        checks = {'actual_completed': raw.get('status') == 'PAUSE_RESUME_DIAGNOSTIC_COMPLETE' and metrics.get('exit_code') == 0 and metrics['stop_reason'] is None and 'error' not in metrics,
                  'one_bound_command': metrics['resume_commands_sent'] == 1 and raw.get('handle_consumed') is True and raw.get('accepted_command') == command,
                  'same_native_process': raw.get('pid') == features.get('pid') == metrics.get('paused_pid'),
                  'same_context_without_prefill': raw.get('same_context_lifetime') is True and raw.get('resume_prefill_calls') == 0,
                  'three_unbiased_continuations': raw.get('resume_decode_calls') == raw.get('unbiased_continuation_steps') == 3 and len(raw.get('continuation', [])) == 3 and all(x.get('bias_applied') is False for x in raw.get('continuation', [])),
                  'actual_full_prefill_features': len(features.get('live_last_state', [])) == 1024 and len(features.get('first_position', {}).get('logits', [])) == len(features.get('first_position', {}).get('probabilities', [])) == 65536,
                  'no_additional_commands_accepted': raw.get('additional_commands_accepted') == 0,
                  'all_loaded_libraries_verified': raw.get('all_loaded_libraries_verified') is True,
                  'reaped': metrics.get('process_reaped') is True}
        if mode == 'zero':
            checks['zero_bias_preserves_first_token'] = raw.get('first_biased_token_id') == raw.get('first_native_greedy_token_id') and raw.get('bias_applied_positions') == 0
        else:
            checks['bounded_numeric_bias_changes_first_token'] = raw.get('first_biased_token_id') == metrics.get('numeric_fixture', {}).get('diagnostic_target_token_id') and raw.get('first_biased_token_id') != raw.get('first_native_greedy_token_id') and raw.get('bias_applied_positions') == 1
        metrics['checks'] = checks
        metrics['pass'] = all(checks.values())
        metrics['native_preview'] = raw.get('decoded_native_preview')
    else:
        metrics['pass'] = False
    port.save(out / (mode + '-controller.json'), metrics)
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed-home', default=None)
    parser.add_argument('--out-dir', default=None)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--seconds', type=int, default=90)
    parser.add_argument('--rss-limit-mb', type=int, default=768)
    args = parser.parse_args()
    if not 5 <= args.seconds <= 120 or not 128 <= args.rss_limit_mb <= 2048:
        parser.error('seconds5..120 and RSS128..2048MiB required')
    home = home_path(args.installed_home)
    out = Path(args.out_dir).resolve() if args.out_dir else home / 'exports' / ('prefill-session-' + time.strftime('%Y%m%d-%H%M%S'))
    if out.exists() and any(out.iterdir()):
        parser.error('Use a fresh attempt directory')
    out.mkdir(parents=True, exist_ok=True)
    report = {'schema': 'V13_PREFILL_SESSION_PAIR_PROOF_V1', 'status': 'PREPARING', 'scope': SCOPE,
              'device': device(), 'production_integration': False, 'old_feature_compatibility': 'UNPROVED', 'variants': []}
    report_path = out / 'report.json'
    port.save(report_path, report)
    cancel = threading.Event()
    handlers = {sig: signal.signal(sig, lambda *_: cancel.set()) for sig in [signal.SIGINT, signal.SIGTERM]}
    lock = None
    template = None
    try:
        lock = (home / 'data/coordinator.lock').open('a+')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        models = ModelManager(home)
        specs = catalog()
        model = models.path_for('C3_LANGUAGE')
        if file_hash(model) != specs['models']['language']['files'][0]['sha256'] or models.revision('C3_LANGUAGE') != specs['models']['language']['revision']:
            raise RuntimeError('Exact pinned C3 required')
        identity = port.installed_identity(home, model, specs['runner'])
        port.save(out / 'library-pins.json', {'libraries': identity['libraries']})
        binary, build = build_session(home, identity, specs['runner'], cancel, out)
        report['build'] = build
        snapshot = out / 'source-snapshot'
        snapshot.mkdir()
        sources = [APP / 'scripts/native_prefill_session.cpp', APP / 'scripts/test_native_prefill_session.py',
                   APP / 'scripts/native_prefill_worker.cpp', APP / 'scripts/test_native_prefill_port.py']
        for source in sources:
            shutil.copyfile(source, snapshot / source.name)
        frozen = {str(p.relative_to(APP)): file_hash(p) for p in sources + [APP / 'v13/runners.py', APP / 'specs/models.json', APP / 'docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md']}
        report['source_hashes'] = frozen
        prereg = {'messages': MESSAGES, 'variants': ['zero', 'nonzero'], 'source_hashes': frozen,
                  'nonzero_policy': 'Second-best actual native row receives (top-minus-second+1), only when0<bias<=12; elseFAIL',
                  'bias_position_limit': 1, 'rows_limit': 16, 'wait_seconds': 15, 'continuations': 3,
                  'deadline_seconds': args.seconds, 'rss_limit_mib_boot': args.rss_limit_mb, 'scope': SCOPE,
                  'installed_identity': identity, 'binary_sha256': file_hash(binary)}
        port.save(out / 'preregistration.json', prereg)
        report['preregistration_sha256'] = file_hash(out / 'preregistration.json')
        guards = subprocess.run([str(binary), '--guard-test'], capture_output=True, text=True, timeout=10)
        if guards.returncode:
            raise RuntimeError('Native command-validation guard checks failed: ' + guards.stderr)
        report['guard_checks'] = json.loads(guards.stdout)
        port.save(out / 'guard-checks.json', report['guard_checks'])
        if args.prepare_only:
            report['status'] = 'PREPARED_GUARDS_PASS_NO_INFERENCE'
            return 0
        cfg = dict(DEFAULTS, context_tokens=2048, threads=2, answer_tokens=16)
        template = LlamaRunner(home, 'C3_LANGUAGE', model, cfg)
        deadline = time.monotonic() + args.seconds
        template.load(cancel, deadline)
        prompt, count, trimmed = template._prompt(MESSAGES, cancel, deadline, 16)
        ids = template._json('POST', '/tokenize', {'content': prompt, 'add_special': True}, deadline)['tokens']
        if trimmed or count != len(ids) or not 1 <= count <= 512:
            raise RuntimeError('Actual exact native template binding failed')
        context = {'messages': MESSAGES, 'prompt': prompt, 'token_ids': ids, 'history_trimmed': trimmed}
        context_sha = hashlib.sha256(dumps(context).encode()).hexdigest()
        token_file = out / 'exact-native-tokens.json'
        port.save(token_file, {'token_ids': ids, 'context_source_sha256': context_sha})
        port.save(out / 'exact-context-source.json', context)
        report['template_release'] = template.unload()
        template = None
        report['status'] = 'RUNNING'
        port.save(report_path, report)
        for mode in ['zero', 'nonzero']:
            port.require_uncancelled(cancel, time.monotonic() + 1)
            if any(file_hash(APP / k) != v for k, v in frozen.items()) or port.installed_identity(home, model, specs['runner']) != identity or file_hash(binary) != prereg['binary_sha256']:
                raise RuntimeError('Frozen source/model/library/binary changed')
            row = run_paused(binary, identity, home, out, token_file, context_sha, mode, cancel, args.seconds, args.rss_limit_mb)
            report['variants'].append(row)
            port.save(report_path, report)
            print(dumps({'mode': mode, 'pass': row['pass'], 'process_reaped': row.get('process_reaped')}), flush=True)
            print('Native Vorschau: ' + safe_text(row.get('native_preview', '')), flush=True)
        z = json.loads((out / 'zero-features.json').read_text())
        n = json.loads((out / 'nonzero-features.json').read_text())
        report['checks'] = {'two_actual_variants_pass': len(report['variants']) == 2 and all(x['pass'] for x in report['variants']),
                            'same_original_native_prefill_logits': z['first_position']['logits'] == n['first_position']['logits'],
                            'same_original_live_state': z['live_last_state'] == n['live_last_state'],
                            'all_source_model_library_binary_unchanged': all(file_hash(APP / k) == v for k, v in frozen.items()) and port.installed_identity(home, model, specs['runner']) == identity and file_hash(binary) == prereg['binary_sha256']}
        report['status'] = 'PAUSE_RESUME_NUMERIC_PAIR_PASS' if all(report['checks'].values()) else 'PAUSE_RESUME_NUMERIC_PAIR_FAIL'
        return 0 if report['status'].endswith('_PASS') else 1
    except BaseException as exc:
        report['status'] = 'PAUSE_RESUME_NUMERIC_PAIR_FAIL'
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
        port.save(report_path, report)
        print(dumps({'status': report['status'], 'report': str(report_path), 'scope': SCOPE}), flush=True)


if __name__ == '__main__':
    raise SystemExit(main())
