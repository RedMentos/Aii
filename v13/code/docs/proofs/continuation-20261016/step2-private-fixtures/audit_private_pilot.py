#!/usr/bin/env python3
"""Read-only consistency audit of the frozen V13 STEP2 private pilot.

Does not execute models, rescore utility, mutate a cohort or promote gates.
Install/source verification is opt-in; absent inputs remain explicit evidence gaps.
This candidate lives OUTSIDE runtime_adapter.source_bindings() and must not
change a preregistered runtime or its 18-row/42-call experiment.
"""
import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = 'V13_STEP2_PRIVATE_PILOT_READONLY_AUDIT_V1'
REG_SCHEMA = 'V13_STEP2_PRIVATE_RUNTIME_ADAPTER_V1_REGISTRATION'
REPORT_SCHEMA = 'V13_STEP2_PRIVATE_RUNTIME_ADAPTER_V1_REPORT'
SCOPE = 'THREE_COMPLEMENTARY_CASE_DIAGNOSTIC_NOT_FULL_STEP2'
IDS = ('private_bfzwzwww', 'private_eztsxxpt', 'private_amvcghct')
ACTIONS = ('A', 'B', 'NONE')
ARMS = {
    'b1_model_quotes': ['B1_DETAIL'],
    'b2_model_quotes': ['B2_GIST'],
    'paired_model_quotes': ['B1_DETAIL', 'B2_GIST'],
    'same_policy_dual': ['B1_DETAIL', 'B1_DETAIL'],
    'no_message': ['B1_DETAIL', 'B2_GIST'],
    'exact_source_control': [],
}
DELIVERY = {
    'b1_model_quotes': 'MODEL_VALIDATED_QUOTES',
    'b2_model_quotes': 'MODEL_VALIDATED_QUOTES',
    'paired_model_quotes': 'MODEL_VALIDATED_QUOTES',
    'same_policy_dual': 'MODEL_VALIDATED_QUOTES',
    'no_message': 'NONE',
    'exact_source_control': 'EXACT_SOURCE_CONTROL',
}


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(data):
    if not isinstance(data, bytes):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key: ' + key)
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError('nonfinite JSON value: ' + value)
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique,
                      parse_constant=nonfinite)


def audit(registration_path, fixtures_path, run_dir=None, source_root=None, installed_home=None):
    errors, unverified = [], []
    def check(condition, code):
        if not condition:
            errors.append(code)
    def load(path, code):
        try:
            return read_json(path)
        except (OSError, ValueError, UnicodeError, TypeError) as exc:
            errors.append(code + ':' + type(exc).__name__)
            return None

    reg = load(registration_path, 'REGISTRATION_UNREADABLE')
    fixture = load(fixtures_path, 'FIXTURE_UNREADABLE')
    if not isinstance(reg, dict) or not isinstance(fixture, dict):
        return {'schema': SCHEMA, 'status': 'REFUSED', 'errors': errors or ['INVALID_INPUT'],
                'unverified': [], 'gate_promotion': False, 'native_model_runs': 0}

    check(reg.get('schema') == REG_SCHEMA and reg.get('status') == 'REGISTERED_NOT_RUN', 'REGISTRATION_SCHEMA_STATUS')
    check(reg.get('scope') == SCOPE and reg.get('gate_promotion') is False, 'REGISTRATION_SCOPE_PROMOTION')
    check(reg.get('historical_step2_utility') == 'UTILITY_FAIL_UNCHANGED', 'HISTORICAL_GATE_CHANGED')
    check(reg.get('numeric_utility_gate') == 'NO_UTILITY_PROMOTION_FOR_DIAGNOSTIC_PILOT', 'PILOT_GATE_CHANGED')
    check(reg.get('fixture_ids') == list(IDS), 'FIXTURE_ID_SELECTION')
    check(reg.get('variant_order') == list(ARMS), 'ARM_ORDER')
    check(reg.get('max_rows') == 18 and reg.get('max_native_calls') == 42, 'REGISTERED_BUDGET')
    check(isinstance(reg.get('device'), dict) and type(reg['device'].get('android')) is bool, 'DEVICE_REGISTRATION')
    check(type(reg.get('row_seconds')) is int and 5 <= reg['row_seconds'] <= 600 and
          type(reg.get('producer_tokens')) is int and 32 <= reg['producer_tokens'] <= 256 and
          type(reg.get('consumer_tokens')) is int and 16 <= reg['consumer_tokens'] <= 1024, 'TOKEN_TIME_BOUNDS')
    expected_order = [[fid, arm] for fid in IDS for arm in ARMS]
    check(reg.get('row_order') == expected_order, 'ROW_ORDER')
    expected_variants = {k: {'roles': v, 'delivery': DELIVERY[k]} for k, v in ARMS.items()}
    check(reg.get('variants') == expected_variants, 'VARIANT_BINDINGS')
    check(type(reg.get('row_seconds')) is int and reg.get('max_total_row_seconds') == 18 * reg['row_seconds'], 'ROW_TIME_BUDGET')
    config = reg.get('config') if isinstance(reg.get('config'), dict) else {}
    check(config.get('learning_mode') == 'RECORD_ONLY' and
          config.get('teacher_enabled') is False, 'LEARNING_MODE_CHANGED')
    check(fixture.get('scope') == SCOPE and fixture.get('gate_promotion') is False and
          fixture.get('native_runs') == 0, 'FIXTURE_DIAGNOSTIC_SCOPE')
    selected = fixture.get('fixtures', [])
    check(isinstance(selected, list) and len(selected) == 3 and
          [f.get('id') for f in selected if isinstance(f, dict)] == list(IDS) and
          [f.get('oracle', {}).get('action') for f in selected if isinstance(f, dict)] == list(ACTIONS) and
          all(f.get('kind') == 'complementary' for f in selected if isinstance(f, dict)), 'FIXTURE_GEOMETRY')
    check(fixture.get('selected_ids') == list(IDS), 'FIXTURE_SELECTED_IDS')
    check(reg.get('fixtures_sha256') == digest(canonical(fixture)), 'FIXTURE_HASH')
    bindings = reg.get('source_bindings')
    check(isinstance(bindings, dict) and len(bindings) >= 3, 'SOURCE_BINDING_SET')
    installed = reg.get('installed_bindings')
    check(isinstance(installed, dict) and isinstance(installed.get('models'), dict) and
          set(installed.get('models', {})) == {'B1_DETAIL', 'B2_GIST', 'C3_LANGUAGE'}, 'MODEL_BINDING_SET')

    if source_root is None:
        unverified.append('SOURCE_BYTES_NOT_RECHECKED')
    elif isinstance(bindings, dict):
        root = Path(source_root).resolve()
        for relative, expected in sorted(bindings.items()):
            path = (root / relative).resolve()
            try:
                matches = path.is_relative_to(root) and path.is_file() and file_hash(path) == expected
            except OSError:
                matches = False
            if not matches:
                errors.append('SOURCE_HASH_MISMATCH:' + relative)

    if installed_home is None:
        unverified.append('INSTALLED_MODEL_RUNNER_BYTES_NOT_RECHECKED')
    elif isinstance(installed, dict):
        home = Path(installed_home)
        targets = []
        for role, info in sorted(installed.get('models', {}).items()):
            if isinstance(info, dict):
                targets.append(('MODEL:' + role, Path(info.get('path', '')), info.get('sha256')))
        runner = installed.get('runner', {})
        if isinstance(runner, dict):
            path = Path(runner.get('path', ''))
            targets.append(('RUNNER', path, runner.get('sha256')))
            libraries = installed.get('runtime_libraries')
            if not isinstance(libraries, dict):
                errors.append('INVALID_RUNTIME_LIBRARY_BINDINGS')
                libraries = {}
            for name, expected in sorted(libraries.items()):
                if Path(name).name != name:
                    errors.append('UNSAFE_LIBRARY_NAME')
                else:
                    targets.append(('LIB:' + name, path.parent / name, expected))
        targets.append(('MODELS_MANIFEST', home / 'config/models.json', installed.get('models_manifest_sha256')))
        for label, path, expected in targets:
            try:
                matches = path.is_file() and isinstance(expected, str) and file_hash(path) == expected
            except OSError:
                matches = False
            if not matches:
                errors.append('INSTALLED_HASH_MISMATCH:' + label)

    report = None
    if run_dir is not None:
        run_dir = Path(run_dir)
        saved_reg = load(run_dir / 'registration.json', 'RUN_REGISTRATION_UNREADABLE')
        report = load(run_dir / 'report.json', 'RUN_REPORT_UNREADABLE')
        check(saved_reg == reg, 'RUN_REGISTRATION_CHANGED')
        if isinstance(report, dict):
            check(report.get('schema') == REPORT_SCHEMA and report.get('scope') == SCOPE, 'RUN_REPORT_SCHEMA_SCOPE')
            check(report.get('registration_sha256') == digest(canonical(reg)), 'RUN_REGISTRATION_HASH')
            check(report.get('status') == 'RECORDED' and report.get('coverage_complete') is True and
                  report.get('final_bindings_unchanged') is True, 'RUN_NOT_COMPLETED')
            check(report.get('gate_promotion') is False and
                  report.get('historical_step2_utility') == 'UTILITY_FAIL_UNCHANGED', 'RUN_GATE_CHANGED')
            check(report.get('evidence_level') == 'NATIVE_RUNNER_BOUNDARY', 'RUN_EVIDENCE_LEVEL')
            device = reg.get('device') if isinstance(reg.get('device'), dict) else {}
            check(report.get('phone_measured') is (device.get('android') is True), 'RUN_DEVICE_CONFLICT')
            rows = report.get('rows', [])
            check(isinstance(rows, list) and len(rows) == 18, 'RUN_ROW_COUNT')
            if isinstance(rows, list):
                check([[r.get('fixture'), r.get('variant')] for r in rows if isinstance(r, dict)] == expected_order,
                      'RUN_ROW_ORDER')
                hashes = report.get('row_sha256')
                check(isinstance(hashes, dict) and set(hashes) == {fid + ':' + arm for fid, arm in expected_order},
                      'RUN_ROW_HASH_SET')
                for row in rows:
                    if not isinstance(row, dict):
                        errors.append('INVALID_ROW_TYPE')
                        continue
                    fid, arm = row.get('fixture'), row.get('variant')
                    if fid not in IDS or arm not in ARMS:
                        errors.append('UNKNOWN_ROW')
                        continue
                    key = fid + ':' + arm
                    check(isinstance(hashes, dict) and hashes.get(key) == digest(canonical(row)), 'ROW_HASH:' + key)
                    saved_row = load(run_dir / (fid + '__' + arm + '.json'), 'ROW_FILE_UNREADABLE:' + key)
                    check(saved_row == row, 'ROW_FILE_DIFFERS:' + key)
                    check(row.get('status') == 'RECORDED' and row.get('processes_reaped') is True,
                          'ROW_NOT_RECORDED:' + key)
                    check(row.get('gate_promotion') is False and
                          row.get('historical_step2_utility') == 'UTILITY_FAIL_UNCHANGED', 'ROW_GATE_CHANGED:' + key)
                    calls = row.get('calls')
                    expected_roles = ARMS[arm] + ['C3_LANGUAGE']
                    check(isinstance(calls, list) and [c.get('role') for c in calls if isinstance(c, dict)] == expected_roles,
                          'CALL_ROLE_ORDER:' + key)
                    releases = row.get('process_releases')
                    check(isinstance(releases, list) and len(releases) == len(expected_roles) and
                          [r.get('role') for r in releases if isinstance(r, dict)] == expected_roles and
                          all(isinstance(r, dict) and r.get('process_reaped') is True for r in releases),
                          'PROCESS_RELEASE_BINDING:' + key)
                    if isinstance(calls, list):
                        for i, call in enumerate(calls):
                            if not isinstance(call, dict):
                                errors.append('CALL_TYPE:' + key)
                                continue
                            metrics = call.get('metrics') if isinstance(call.get('metrics'), dict) else {}
                            check(call.get('status') == 'FINAL' and metrics.get('status') == 'FINAL',
                                  'CALL_NOT_FINAL:' + key + ':' + str(i))
                            check(call.get('max_tokens') == (reg.get('consumer_tokens') if i == len(expected_roles) - 1
                                                           else reg.get('producer_tokens')) and
                                  call.get('seed') == config.get('seed'),
                                  'CALL_BUDGET_SEED:' + key + ':' + str(i))
        else:
            errors.append('RUN_REPORT_NOT_OBJECT')

    if errors:
        status = 'REFUSED'
    elif run_dir is None:
        status = 'PREPARED_NOT_RUN'
    else:
        status = 'ARTIFACT_CONSISTENCY_PASS_NOT_QUALITY_GATE'
        unverified.append('MODEL_EXECUTION_AUTHENTICITY_NOT_EXTERNALLY_ATTESTED')
        unverified.append('UTILITY_SCORE_NOT_INDEPENDENTLY_RECOMPUTED')
    return {'schema': SCHEMA, 'status': status, 'errors': sorted(set(errors)),
            'unverified': sorted(set(unverified)), 'registration_sha256': digest(canonical(reg)),
            'rows_audited': len(report.get('rows', [])) if isinstance(report, dict) else 0,
            'gate_promotion': False, 'native_model_runs': 0,
            'historical_step2_utility': 'UTILITY_FAIL_UNCHANGED'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration', type=Path, required=True)
    parser.add_argument('--fixtures', type=Path, required=True)
    parser.add_argument('--run-dir', type=Path)
    parser.add_argument('--source-root', type=Path)
    parser.add_argument('--installed-home', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args(argv)
    result = audit(args.registration, args.fixtures, args.run_dir, args.source_root, args.installed_home)
    rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n'
    if args.out:
        if args.out.exists():
            parser.error('refusing to overwrite audit report')
        args.out.write_text(rendered, encoding='utf-8')
    print(rendered, end='')
    return 2 if result['status'] == 'REFUSED' else 0


if __name__ == '__main__':
    raise SystemExit(main())
