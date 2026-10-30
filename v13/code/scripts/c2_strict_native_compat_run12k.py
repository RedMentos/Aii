"""Run12K preregistered Linux-native C2 strict Runtime admission compatibility.

Four disjoint synthetic prompts, fixed seed, pinned Needle3, isolated Store.
No C3/Body output, route utility, Redmi, Age or learning promotion.
"""
import argparse
import hashlib
import json
from pathlib import Path
import traceback

from v13.cognition import scaffold_route
from v13.common import file_hash
from v13.config import initialize
from v13.control_calibration_worker import observation
from v13.models import ModelManager
from scripts import c2_native_route_provenance_20261030 as original

SCHEMA = 'v13.c2.strict_native_compat.run12k.v1'
SEED = 43  # Existing _turn implementation's fixed seed; prompts are disjoint.
PROMPTS = (
    'Hello from project Sable; greet me briefly.',
    'Project Kestrel: choose between route A and B and explain your choice.',
    'What is 13 + 29?',
    'Summarize project Ember in one sentence.',
)
PROMPT_SHA256 = 'cc45889077cae32fac4911ad91e7b2fa279a6bfd2d8d43ddac712e0ca1cc7014'
EXPECTED_SCAFFOLDS = ('simple', 'simple', 'detail', 'gist')
NEEDLE_SHA256 = 'c9d915eca282ed42d1a09b143b592adb4cc6744ffe2d294adf5cfc5548170c38'


def prompt_hash():
    return hashlib.sha256(json.dumps(PROMPTS, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def classify(row):
    """Read-only expected strict admission; never substitute a model result."""
    info = row.get('route_info')
    if not isinstance(info, dict):
        return {'valid_unique_tool': False, 'selected': False,
                'expected_selected': False, 'matches': False,
                'native_route': None, 'scaffold': None}
    control = info.get('native_control')
    valid = False
    route = None
    try:
        obs = observation(control)
        calls = control.get('function_calls')
        valid = (type(calls) is list and len(calls) == 1
                 and type(calls[0]) is dict
                 and calls[0].get('name') == 'select_processing'
                 and obs['proposal_count'] == 1
                 and obs['ambiguous'] is False)
        if valid:
            route = obs['route']
    except (ValueError, TypeError, KeyError, OverflowError):
        pass
    scaffold = info.get('scaffold')
    selected = info.get('source') == 'NATIVE_C2_ADVISORY'
    expected = valid and scaffold == 'simple'
    return {'valid_unique_tool': bool(valid), 'selected': selected,
            'expected_selected': bool(expected),
            'matches': bool(isinstance(control, dict) and scaffold in ('simple', 'detail', 'gist', 'both')
                            and selected == expected and (not selected or row.get('route') == route)),
            'native_route': route, 'scaffold': scaffold}


def run(base_home, out):
    base_home, out = Path(base_home).resolve(), Path(out).resolve()
    if out.exists():
        raise FileExistsError('FRESH_OUTPUT_DIRECTORY_REQUIRED')
    if (prompt_hash() != PROMPT_SHA256 or len(PROMPTS) != 4
            or tuple(map(scaffold_route, PROMPTS)) != EXPECTED_SCAFFOLDS
            or SEED != original.SEED
            or set(PROMPTS) & set(original.PROMPTS)):
        raise ValueError('PREREGISTRATION_CHANGED')
    out.mkdir(parents=True)
    (out / 'raw').mkdir()
    report = {
        'schema': SCHEMA, 'status': 'INCOMPLETE', 'seed': SEED,
        'prompt_sha256': PROMPT_SHA256, 'prompts': PROMPTS,
        'expected_scaffolds': EXPECTED_SCAFFOLDS,
        'rows': [], 'native_c2_proven': False,
        'strict_compatibility': False, 'native_route_utility_proven': False,
        'c3_called': False, 'body_called': False,
        'learning_mode': 'RECORD_ONLY', 'jepa_weight': 0,
        'step2_gate_promoted': False, 'b3_promoted': False,
        'body_jepa_available': False, 'redmi_measured': False,
        'whole_system_complete': False,
    }
    try:
        cfg = initialize(base_home)
        if (cfg['learning_mode'] != 'RECORD_ONLY' or cfg['system_stage'] != 0
                or cfg['latents_enabled'] or cfg.get('jepa_weight', 0) != 0):
            raise ValueError('BASE_NOT_AGE0')
        manager = ModelManager(base_home)
        verified = manager.verify(deep=True)
        if not verified.get('needle', {}).get('ok') or not verified['needle']['hash_checked']:
            raise ValueError('NEEDLE_NOT_VERIFIED')
        model_sha = file_hash(manager.path_for('C2_CONTROL'))
        if model_sha != NEEDLE_SHA256:
            raise ValueError('NEEDLE_SHA_MISMATCH')
        report['needle_model_sha256'] = model_sha
        report['needle_model_verified'] = {'ok': True, 'hash_checked': True}
        report['needle_worker_sha256'] = file_hash(base_home / 'bin/needle-worker')
        for i, prompt in enumerate(PROMPTS):
            try:
                row = original._turn(base_home, cfg, prompt, i, out)
                strict = classify(row)
                row['strict_admission'] = strict
                (out / 'raw' / f'{i:02d}_STRICT_ADMISSION.json').write_text(
                    json.dumps(strict, sort_keys=True, allow_nan=False) + '\n')
            except BaseException as exc:
                row = {'index': i, 'prompt': prompt,
                       'native_c2_invocation_valid_before_release': False,
                       'needle_process_reaped': False,
                       'error_type': type(exc).__name__,
                       'error': str(exc)[:200]}
                traceback.print_exc()
            report['rows'].append(row)
            (out / 'progress.json').write_text(
                json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + '\n')
        report['native_c2_proven'] = bool(len(report['rows']) == 4 and all(
            r.get('native_c2_invocation_valid_before_release') is True
            and r.get('needle_process_reaped') is True for r in report['rows']))
        safe = all(r.get('strict_admission', {}).get('matches') is True
                   for r in report['rows'])
        simple_admitted = sum(r.get('strict_admission', {}).get('selected') is True
                              for r in report['rows'][:2])
        report['strict_compatibility'] = bool(report['native_c2_proven']
                                              and safe and simple_admitted >= 1)
        report['simple_admitted'] = simple_admitted
        report['status'] = ('NATIVE_STRICT_COMPAT_PARTIAL_NO_UTILITY'
                            if report['strict_compatibility']
                            else 'NATIVE_STRICT_COMPAT_RED')
    except BaseException as exc:
        report.update(status='PILOT_ERROR', error_type=type(exc).__name__,
                      error=str(exc)[:200])
        traceback.print_exc()
    finally:
        (out / 'report.json').write_text(json.dumps(
            report, sort_keys=True, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'status': report['status'],
                      'native_c2_proven': report['native_c2_proven'],
                      'strict_compatibility': report['strict_compatibility']}))
    return report['strict_compatibility']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--home', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    return 0 if run(a.home, a.out) else 2


if __name__ == '__main__':
    raise SystemExit(main())

