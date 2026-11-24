#!/usr/bin/env python3
"""Isolated C3 final-norm update/reference/reload experiment; no runtime authority.

Local authored fixtures are numerical test references, never human decisions or
approved learning sources. The original GGUF and installed runtime stay frozen.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import threading
import time

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from test_native_prefill_port import installed_identity, bounded_process, prepare_worker, save
from v13.common import file_hash
from v13.config import DEFAULTS, home_path
from v13.models import ModelManager, catalog
from v13.resources import device
from v13.runners import LlamaRunner

CPP = APP / 'docs/proofs/native_norm_shadow_port.cpp'
POLL_HEADER = APP / 'docs/proofs/native_norm_poll_policy.hpp'
SCOPE = ('Isolated authored numerical fixtures, actual FP32 final-norm scale update, '
         'full native quantized decode, independently dequantized FP64 reference, '
         'fresh-process reload and rollback. No human approval, runtime registration, '
         'retention/generalization, target-phone learning or full TrainRunnerProof.')
FIXTURES = [
    {'name': 'short_authored_greeting', 'messages': [
        {'role': 'system', 'content': 'Antworte kurz auf Deutsch.'},
        {'role': 'user', 'content': 'Begrüße Gast1 kurz.'}], 'reference': 'Hallo'},
    {'name': 'long_authored_greeting', 'messages': [
        {'role': 'system', 'content': 'Antworte kurz auf Deutsch. ' + ' '.join(
            f'Eintrag {i}: Dies sind ausdrücklich erfundene numerische Testdaten.' for i in range(12))},
        {'role': 'user', 'content': 'Begrüße Gast2 kurz.'}], 'reference': 'Hallo'}]
TOLERANCES = {'native_tail_logits_atol': 1e-5, 'reload_logits_atol': 0.,
              'rollback_logits_atol': 0., 'max_update_norm': .0010001,
              'reference_atol': 1e-6, 'reference_rtol': 1e-4,
              'surrogate_same_probability_atol': 1e-5,
              'surrogate_same_probability_rtol': 1e-3}


def prepare(home, identity, specs, cancel, out):
    # This shared existing read-only preparation pins every public header, source
    # archive, compiler and actual installed library; it performs no inference.
    _, dependency = prepare_worker(home, identity, specs['runner'], cancel, out / 'dependency')
    cache = home / 'tmp/native-norm-shadow'
    cache.mkdir(parents=True, exist_ok=True)
    source = home / 'tmp/native-prefill-port/source' / ('llama.cpp-' + specs['runner']['tag'])
    frozen = cache / 'norm-worker.cpp'
    frozen.write_bytes(CPP.read_bytes())
    frozen_header = cache / POLL_HEADER.name
    frozen_header.write_bytes(POLL_HEADER.read_bytes())
    header_sha = file_hash(frozen_header)
    frozen_sha = file_hash(frozen)
    (out / 'exact-worker.cpp').write_bytes(frozen.read_bytes())
    (out / POLL_HEADER.name).write_bytes(frozen_header.read_bytes())
    (out / 'exact-collector.py').write_bytes(Path(__file__).read_bytes())
    compiler = shutil.which('clang++') or shutil.which('g++')
    c_compiler = shutil.which('clang') or shutil.which('gcc')
    if not compiler or not c_compiler:
        raise RuntimeError('Native compilers unavailable; STARTEN.sh/setup.sh installs Termux clang')
    obj = cache / 'sha256.o'
    worker = cache / 'norm-worker'
    commands = [
        [c_compiler, '-std=c11', '-O2', '-I', str(source / 'vendor/hash'), '-c',
         str(source / 'vendor/hash/sha256/sha256.c'), '-o', str(obj)],
        [compiler, '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
         '-I', str(source / 'include'), '-I', str(source / 'ggml/include'),
         '-I', str(source / 'vendor'), '-I', str(source / 'vendor/hash/sha256'),
         str(frozen), str(obj), *identity['link_libraries'],
         '-Wl,-rpath,' + identity['library_directory'], '-ldl', '-pthread', '-o', str(worker)]]
    attempts = []
    for index, command in enumerate(commands):
        outcome = bounded_process(command, out / f'compile-{index}.log', cancel, 180)
        attempts.append({'command': command, 'outcome': outcome})
        save(out / 'build-attempt.json', {'source_sha256': frozen_sha, 'attempts': attempts})
        if outcome['exit_code'] or outcome['stop_reason']:
            raise RuntimeError('Strict native norm worker compilation failed; raw attempt retained')
    if file_hash(CPP) != frozen_sha or file_hash(frozen) != frozen_sha or file_hash(POLL_HEADER) != header_sha or file_hash(frozen_header) != header_sha:
        raise RuntimeError('Norm source changed during compilation; no run allowed')
    result = {'schema': 'V13_NATIVE_NORM_BUILD_V2', 'source_sha256': frozen_sha,
              'poll_policy_sha256': header_sha,
              'collector_sha256': file_hash(Path(__file__)), 'binary_sha256': file_hash(worker),
              'dependency_build': dependency, 'attempts': attempts, 'inference_performed': False}
    save(out / 'build.json', result)
    return worker, result


def bound_example(out, fixture, rendered, ids, target):
    files = {'context': out / 'context.json', 'reference': out / 'reference.json',
             'permission': out / 'experiment-scope.json'}
    save(files['context'], {'messages': fixture['messages'], 'actual_native_rendered_context': rendered,
                            'token_ids': ids, 'origin': 'AUTHORED_EXPERIMENT_FIXTURE'})
    save(files['reference'], {'first_reference_word': fixture['reference'], 'target_token_id': target,
                             'origin': 'AUTHORED_EXPERIMENT_REFERENCE', 'human_decision': False})
    save(files['permission'], {'scope': SCOPE, 'source_authority': 0, 'train_authority': 0,
                              'human_training_approval': False, 'production_import_authority': 0})
    example = {'experiment_fixture_only': True, 'reference_origin': 'AUTHORED_EXPERIMENT_REFERENCE',
               'source_bindings': {name + '_sha256': file_hash(path) for name, path in files.items()},
               'source_files': {name: str(path) for name, path in files.items()},
               'token_ids': ids, 'target_token_id': target}
    path = out / 'example.json'
    save(path, example)
    return path


def compare(train, reload):
    import numpy as np
    def same(left, right, tolerance):
        a = np.asarray(left, dtype=np.float64)
        b = np.asarray(right, dtype=np.float64)
        return bool(a.shape == b.shape == (65536,) and np.isfinite(a).all()
                    and np.isfinite(b).all() and np.max(np.abs(a - b)) <= tolerance)
    reference = train['independent_gradient_reference']
    original = np.asarray(train['original_master'], dtype=np.float64)
    candidate = np.asarray(train['candidate_master']['values'], dtype=np.float64)
    return {'native_tail_matches_actual_prefill': same(train['native_before']['logits'], train['native_tail_before']['logits'], TOLERANCES['native_tail_logits_atol']),
            'exact_gathered_last_norm_and_scale': train['native_before']['exact_selected_output_row']['all_1024_scale_products_exact'] is True,
            'all_loaded_libraries_verified_both_processes': train['all_loaded_libraries_verified'] is True and reload['all_loaded_libraries_verified'] is True,
            'reference_64_finite_differences': reference['reference_finite_difference_pass'] is True and len(reference['finite_differences']) == 64,
            'ggml_surrogate_matches_same_native_probability_reference': reference['ggml_surrogate_vs_same_native_probabilities_pass'] is True,
            'fresh_process_candidate_exact': same(train['native_after']['logits'], reload['native_candidate_reload']['logits'], 0.),
            'fresh_process_original_exact': same(train['native_before']['logits'], reload['native_before']['logits'], 0.),
            'both_rollbacks_exact': same(train['native_before']['logits'], train['native_rollback']['logits'], 0.) and same(train['native_before']['logits'], reload['native_rollback']['logits'], 0.),
            'bounded_nonzero_real_master_update': bool(original.shape == candidate.shape == (1024,) and 0 < np.linalg.norm(candidate - original) <= TOLERANCES['max_update_norm']),
            'candidate_master_hash_reload': train['candidate_master_sha256'] == reload['candidate_master_sha256'],
            'original_master_hash_rollback': train['original_master_sha256'] == train['restored_original_master_sha256'] == reload['original_master_sha256'],
            'frozen_output_both_processes_unchanged': train['frozen_native_output_before_sha256'] == train['frozen_native_output_after_sha256'] == reload['frozen_native_output_before_sha256'] == reload['frozen_native_output_after_sha256'],
            'original_gguf_both_processes_unchanged': train['original_gguf_unchanged'] is True and reload['original_gguf_unchanged'] is True,
            'fixture_hashes_both_processes_verified': train['source_bindings_independently_verified'] is True and reload['source_bindings_independently_verified'] is True,
            'zero_approval_source_train_receiver_authority': all(x['train_authority'] == x['source_authority'] == x['receiver_authority'] == 0 and x['human_training_approval_verified'] is False for x in [train, reload])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed-home')
    parser.add_argument('--out-dir')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--forward-poll', action='store_true', help='Separate bounded actual-forward search; exact gradient/approval gates stay false')
    parser.add_argument('--fixtures', type=int, choices=[1, 2], default=2)
    parser.add_argument('--seconds', type=int, default=120)
    parser.add_argument('--rss-limit-mb', type=int, default=768)
    args = parser.parse_args()
    if not 10 <= args.seconds <= 120 or not 128 <= args.rss_limit_mb <= 2048:
        parser.error('Bounded seconds 10..120 and RSS limit 128..2048 required')
    home = home_path(args.installed_home)
    out = Path(args.out_dir).resolve() if args.out_dir else home / 'exports' / ('norm-shadow-' + time.strftime('%Y%m%d-%H%M%S'))
    if out.exists() and any(out.iterdir()):
        parser.error('Use a fresh output directory; previous attempts remain immutable')
    (out / 'dependency').mkdir(parents=True, exist_ok=True)
    cancel = threading.Event()
    for sig in [signal.SIGINT, signal.SIGTERM]:
        signal.signal(sig, lambda *_: cancel.set())
    report = {'schema': 'V13_ISOLATED_NATIVE_NORM_PROOF_V2', 'status': 'PREPARING',
              'scope': SCOPE, 'device': device(), 'train_authority': 0, 'source_authority': 0,
              'production_registration': False, 'train_runner_proof': None, 'cases': [],
              'exact_quantized_gradient_gate': False, 'phone_learning_gate': False}
    path = out / 'report.json'
    save(path, report)
    lock = None
    runner = None
    try:
        specs = catalog()
        models = ModelManager(home)
        model = models.path_for('C3_LANGUAGE')
        if file_hash(model) != specs['models']['language']['files'][0]['sha256'] or models.revision('C3_LANGUAGE') != specs['models']['language']['revision']:
            raise RuntimeError('Exact pinned C3 model required')
        identity = installed_identity(home, model, specs['runner'])
        pins = out / 'loaded-library-pins.json'
        save(pins, {'libraries': identity['libraries']})
        worker, build = prepare(home, identity, specs, cancel, out)
        report['build'] = build
        report['installed_identity'] = identity
        prereg = {'scope': SCOPE, 'fixtures': FIXTURES[:args.fixtures], 'tolerances': TOLERANCES,
                  'reference_coordinates': [i * 33 for i in range(32)], 'reference_epsilons': [.001, .01],
                  'quantized_coordinates': [0, 341, 682, 1023], 'quantized_epsilons': [.001, .01],
                  'candidate_trial_step_factors': [1., .5, .25, .125],
                  'forward_poll_enabled': args.forward_poll,
                  'forward_poll': {'optimizer_kind': 'BOUNDED_ACTUAL_FORWARD_ONLY_POLL_NO_EXACT_DERIVATIVE',
                      'maximum_evaluations': 20, 'directions': ['surrogate_unit_direction_not_exact_gradient', 'coordinate_0', 'coordinate_341', 'coordinate_682', 'coordinate_1023'],
                      'radii': [.001, .0005], 'signs': [-1, 1], 'maximum_update_l2': .0010001,
                      'adaptive_radius_or_direction': False, 'full_native_prefill_validation_required': True,
                      'policy_source_sha256': file_hash(POLL_HEADER)},
                  'candidate_acceptance': 'STRICT_ACTUAL_QUANTIZED_FULL_VOCABULARY_CE_IMPROVEMENT_WITH_UNCHANGED_NORM_CAP',
                  'batch': 128, 'physical_batch': 128, 'threads': 2, 'max_context_tokens': 512,
                  'seconds_per_call': args.seconds, 'rss_limit_mb_boot_choice': args.rss_limit_mb,
                  'worker_binary_sha256': file_hash(worker), 'source_sha256': file_hash(CPP),
                  'collector_sha256': file_hash(Path(__file__)), 'installed_identity': identity}
        save(out / 'preregistration.json', prereg)
        report['preregistration_sha256'] = file_hash(out / 'preregistration.json')
        if args.prepare_only:
            report['status'] = 'PREPARED_NO_INFERENCE'
            return 0
        lock = (home / 'data/coordinator.lock').open('a+')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for fixture in FIXTURES[:args.fixtures]:
            case_dir = out / fixture['name']
            case_dir.mkdir()
            cfg = dict(DEFAULTS, context_tokens=1024, threads=2, answer_tokens=4)
            runner = LlamaRunner(home, 'C3_LANGUAGE', model, cfg)
            deadline = time.monotonic() + args.seconds
            runner.load(cancel, deadline)
            rendered, token_count, trimmed = runner._prompt(fixture['messages'], cancel, deadline, 4)
            ids = runner._json('POST', '/tokenize', {'content': rendered, 'add_special': True}, deadline)['tokens']
            if trimmed or token_count != len(ids) or not 0 < len(ids) <= 512 or (fixture['name'].startswith('long') and len(ids) <= 129):
                raise RuntimeError('Exact bounded short/long native context contract failed')
            reference_ids = runner._json('POST', '/tokenize', {'content': fixture['reference'], 'add_special': False}, deadline)['tokens']
            if not reference_ids:
                raise RuntimeError('Actual reference tokenization returned empty')
            unload = runner.unload()
            runner = None
            example = bound_example(case_dir, fixture, rendered, ids, reference_ids[0])
            row = {'name': fixture['name'], 'token_count': len(ids), 'template_unload': unload,
                   'example_sha256': file_hash(example), 'calls': []}
            report['cases'].append(row)
            report['status'] = 'RUNNING'
            save(path, report)
            args_base = [str(worker), '--model', str(model), '--example', str(example),
                         '--model-sha256', identity['model_sha256'], '--lib-sha256',
                         identity['libraries'][identity['llama_library']], '--backend-pins', str(pins)]
            if args.forward_poll:
                args_base += ['--forward-poll', '1']
            train_path = case_dir / 'train.json'
            for phase, target in [('TRAIN_OBSERVATION', train_path), ('FRESH_PROCESS_RELOAD', case_dir / 'reload.json')]:
                command = args_base + ['--output', str(target)]
                if phase == 'FRESH_PROCESS_RELOAD':
                    observations = json.loads(train_path.read_text())
                    command += ['--candidate', observations['candidate_checkpoint']['path']]
                outcome = bounded_process(command, case_dir / (phase.lower() + '.log'), cancel, args.seconds, args.rss_limit_mb)
                row['calls'].append({'phase': phase, **outcome})
                save(path, report)
                if outcome['exit_code'] or outcome['stop_reason'] or not target.is_file():
                    raise RuntimeError('Actual native norm ' + phase + ' failed; raw observations retained')
                row[phase.lower() + '_sha256'] = file_hash(target)
            train = json.loads(train_path.read_text())
            reload = json.loads((case_dir / 'reload.json').read_text())
            row['checks'] = compare(train, reload)
            row['numerical_update_reload_scope_pass'] = all(row['checks'].values())
            row['quantized_gradient_exactness'] = 'UNPROVEN_SURROGATE_ONLY'
            row['candidate_acceptance'] = train['candidate_acceptance']
            if args.forward_poll:
                row['surrogate_candidate_acceptance'] = train['surrogate_candidate_acceptance']
                row['forward_poll_candidate_found'] = train['forward_poll_candidate_found']
                row['forward_poll_accepted_observation_master'] = train['forward_poll_accepted_observation_master']
                row['optimizer_kind'] = train['optimizer_kind']
            row['training_eligible'] = False
            save(path, report)
        report['checks'] = {'all_processes_reaped': all(call['process_reaped'] for row in report['cases'] for call in row['calls']),
                            'scoped_numerical_checks': all(row['numerical_update_reload_scope_pass'] for row in report['cases']),
                            'source_unchanged': file_hash(CPP) == prereg['source_sha256'] and file_hash(Path(__file__)) == prereg['collector_sha256'] and file_hash(POLL_HEADER) == prereg['forward_poll']['policy_source_sha256'],
                            'original_model_unchanged': file_hash(model) == identity['model_sha256']}
        report['status'] = 'NUMERICAL_UPDATE_RELOAD_SCOPE_PASS' if all(report['checks'].values()) else 'NUMERICAL_UPDATE_RELOAD_SCOPE_FAIL'
        print(report['status'] + '; exact quantized gradient / approval / phone learning gates remain false')
        return 0 if all(report['checks'].values()) else 2
    except Exception as exc:
        report['status'] = 'ISOLATED_NATIVE_NORM_FAILED'
        report['error'] = type(exc).__name__ + ': ' + str(exc)
        print(report['error'], file=sys.stderr)
        return 1
    finally:
        if runner is not None:
            report['cleanup_unload'] = runner.unload()
        if lock is not None:
            lock.close()
        save(path, report)


if __name__ == '__main__':
    raise SystemExit(main())
