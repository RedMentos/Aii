"""Opt-in STEP2 four-arm native evidence collector candidate.

Registration and mocked tests are software-only. --execute-native requires an
external SHA-pinned registration, explicit owner confirmation and installed
coordinator lock; it does not authorize itself or promote any Canon gate.
"""
import argparse
import fcntl
import hashlib
import json
import os
import platform
import stat
import subprocess
from pathlib import Path

SCHEMA = 'V13_STEP2_FOURARM_NATIVE_REG_V1'
EVIDENCE_SCHEMA = 'V13_STEP2_FOURARM_EVIDENCE_V1'
ARMS = ('TC', 'TP', 'SC', 'SP')
SEEDS = (27, 28, 29)
MAX_RAW = 64 * 1024 * 1024


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pairs(items):
    d = {}
    for k, v in items:
        require(k not in d, 'Duplicate registration JSON key')
        d[k] = v
    return d


def _read_file(path, limit=MAX_RAW):
    fd = os.open(os.fspath(path), os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_size <= limit,
                'Missing or oversized regular evidence file')
        chunks = []
        total = 0
        while True:
            part = os.read(fd, min(65536, limit + 1 - total))
            if not part:
                break
            total += len(part)
            require(total <= limit, 'Evidence exceeds size limit')
            chunks.append(part)
        after = os.fstat(fd)
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
                'Evidence changed while reading')
        return b''.join(chunks)
    finally:
        os.close(fd)


VARIANTS = ('b1_only', 'b2_only', 'both_none', 'both_exact',
            'both_control', 'same_policy_dual', 'prompt_only_dual')


def verify_native_reports(raw_step2, raw_tool, fixture_ids, fixture_sha256):
    """Refuse altered/incomplete 70-row native and tool-replay evidence.

    The STEP2 harness and tool replay each persist digest(dumps(row)); our
    canonical() uses exactly that JSON encoding. No generated judge is used.
    """
    def decode(data):
        def invalid(x):
            raise ValueError('Nonfinite native report: ' + x)
        return json.loads(data.decode('utf-8'), object_pairs_hook=pairs,
                          parse_constant=invalid)
    source, tool = decode(raw_step2), decode(raw_tool)
    require(type(source) is dict and type(tool) is dict,
            'Native report is not a JSON object')
    expected = {f'{fid}:{v}' for fid in fixture_ids for v in VARIANTS}
    require(len(fixture_ids) == 10 and len(set(fixture_ids)) == 10 and
            source.get('fixture_sha256') == fixture_sha256 and
            [f.get('id') for f in source.get('fixtures', [])] == list(fixture_ids) and
            source.get('status') in ('UTILITY_FAIL', 'UTILITY_PASS_SCOPED') and
            source.get('all_structural_checks_passed') is True and
            source.get('source_unchanged') is True and
            source.get('installed_artifacts_unchanged') is True and
            tool.get('status') in ('TOOL_UTILITY_FAIL', 'TOOL_UTILITY_PASS_SCOPED') and
            tool.get('installed_artifacts_unchanged') is True,
            'Native report provenance/structural checks incomplete')
    for report in (source, tool):
        rows, hashes = report.get('rows'), report.get('row_sha256')
        require(type(rows) is list and len(rows) == len(expected) and
                type(hashes) is dict and set(hashes) == expected,
                'Native rows/digests are not complete')
        seen = set()
        for row in rows:
            require(type(row) is dict, 'Malformed native row')
            key = str(row.get('fixture')) + ':' + str(row.get('variant'))
            require(key in expected and key not in seen and
                    row.get('status') == 'RECORDED' and
                    hashes[key] == sha(canonical(row)),
                    'Native row missing, repeated or changed')
            seen.add(key)
        require(seen == expected, 'Missing paired native rows')
    return source, tool


def make_registration(source_sha256, artifacts, fixture_ids, fixture_sha256):
    require(type(source_sha256) is dict and len(source_sha256) >= 8 and
            all(type(k) is str and len(v) == 64 for k, v in source_sha256.items()),
            'Incomplete native source closure')
    require(type(artifacts) is dict and type(artifacts.get('model_sha256')) is dict and
            set(artifacts['model_sha256']) == {'B1_DETAIL', 'B2_GIST', 'C3_LANGUAGE'} and
            all(type(x) is str and len(x) == 64 for x in artifacts['model_sha256'].values()) and
            type(artifacts.get('runner_sha256')) is str and len(artifacts['runner_sha256']) == 64,
            'Incomplete installed native artifacts')
    require(len(fixture_ids) == 10 and len(set(fixture_ids)) == 10 and
            type(fixture_sha256) is str and len(fixture_sha256) == 64,
            'Invalid fixture registration')
    require(artifacts['model_sha256']['B1_DETAIL'] != artifacts['model_sha256']['B2_GIST'],
            'Two-distinct arm requires different pinned B1 and B2 weights')
    return {'schema': SCHEMA, 'source_sha256': source_sha256,
            'installed_artifacts': artifacts, 'fixture_ids': list(fixture_ids),
            'fixture_sha256': fixture_sha256, 'arms': list(ARMS),
            'seeds': list(SEEDS), 'canonical_gate_pass': False,
            'evidence_kind': 'REGISTRATION_NO_INFERENCE'}


def write_new(path, data):
    path = Path(path)
    with path.open('xb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def load_registration(path, expected_sha256):
    require(type(expected_sha256) is str and len(expected_sha256) == 64 and
            all(c in '0123456789abcdef' for c in expected_sha256),
            'External SHA256 pin required')
    raw = _read_file(path, 1024 * 1024)
    require(sha(raw) == expected_sha256, 'Registration SHA256 mismatch')
    def nonfinite(x):
        raise ValueError('Nonfinite registration JSON: ' + x)
    reg = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                     parse_constant=nonfinite)
    require(type(reg) is dict and reg.get('schema') == SCHEMA and
            reg.get('arms') == list(ARMS) and reg.get('seeds') == list(SEEDS) and
            reg.get('canonical_gate_pass') is False,
            'Wrong native registration schema/cohort')
    return reg


def collect(registration_path, external_pin, installed_lock, work,
            source_hashes, installed_artifacts, run_one, evidence_kind,
            exclusive_owner_confirmed=False):
    """Serial native collection; run_one is injected for testability.

    A real run_one must execute the native STEP2 harness. Test mocks never
    constitute measured model evidence, irrespective of labels supplied here.
    """
    require(exclusive_owner_confirmed, 'Explicit native owner confirmation required')
    require(evidence_kind in ('LINUX_NATIVE', 'REDMI_NATIVE'),
            'Unregistered native device class')
    reg = load_registration(registration_path, external_pin)
    require(reg.get('source_sha256') == source_hashes() and
            reg.get('installed_artifacts') == installed_artifacts(),
            'Native source/model/runner drift before execution')
    work = Path(work)
    require(not work.exists(), 'Fresh evidence work directory required')
    lock = Path(installed_lock)
    require(lock.is_file() and not lock.is_symlink(), 'Installed coordinator lock missing')
    with lock.open('r+') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            work.mkdir(parents=True, exist_ok=False)
            entries = []
            for seed in SEEDS:
                for arm in ARMS:
                    require(reg['source_sha256'] == source_hashes() and
                            reg['installed_artifacts'] == installed_artifacts(),
                            'Native binding changed between runs')
                    rid = f'{arm}_s{seed}'
                    run_dir = work / ('native_' + rid)
                    require(not run_dir.exists(), 'Refusing stale native work')
                    summary, step2_path, tool_path, actual_models = run_one(arm, seed, run_dir)
                    require(type(summary) is dict and summary.get('arm') == arm and
                            summary.get('seed') == seed and
                            summary.get('step2_status') in ('UTILITY_FAIL', 'UTILITY_PASS_SCOPED') and
                            summary.get('tool_status') in ('TOOL_UTILITY_FAIL', 'TOOL_UTILITY_PASS_SCOPED'),
                            'Native run did not finish with closed utility verdict')
                    expected = dict(reg['installed_artifacts']['model_sha256'])
                    if arm.startswith('S'):
                        expected['B2_GIST'] = expected['B1_DETAIL']
                    require(actual_models == expected, 'Actual native model hashes differ from registered arm')
                    raw_step2 = _read_file(step2_path)
                    raw_tool = _read_file(tool_path)
                    raw = len(raw_step2).to_bytes(8, 'big') + raw_step2 + \
                          len(raw_tool).to_bytes(8, 'big') + raw_tool
                    require(len(raw) <= MAX_RAW, 'Combined native raw evidence too large')
                    raw_name, summary_name = rid + '.raw', rid + '.json'
                    raw_hash = sha(raw)
                    sealed = dict(summary, registration_sha256=external_pin,
                                  fixture_sha256=reg['fixture_sha256'],
                                  source_sha256=reg['source_sha256'],
                                  model_sha256=actual_models,
                                  runner_sha256=reg['installed_artifacts']['runner_sha256'],
                                  raw_sha256=raw_hash, evidence_kind=evidence_kind,
                                  canonical_gate_pass=False, step2_gate_promoted=False,
                                  jepa_weight=0)
                    data = canonical(sealed)
                    write_new(work / raw_name, raw)
                    write_new(work / summary_name, data)
                    entries.append({'arm': arm, 'seed': seed, 'summary': summary_name,
                                    'summary_sha256': sha(data), 'raw': raw_name,
                                    'raw_sha256': raw_hash})
            require(reg['source_sha256'] == source_hashes() and
                    reg['installed_artifacts'] == installed_artifacts(),
                    'Native binding changed after execution')
            manifest = {'schema': EVIDENCE_SCHEMA,
                        'fixture_ids': reg['fixture_ids'], 'runs': entries}
            data = canonical(manifest)
            write_new(work / 'manifest.json', data)
            return {'manifest_sha256': sha(data), 'runs': len(entries),
                    'canonical_gate_pass': False, 'step2_gate_promoted': False,
                    'evidence_kind': evidence_kind,
                    'claim_limit': 'Raw native evidence collected; scorer, owner and gate review still required'}
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _device_kind(value):
    if value == 'LINUX_NATIVE':
        require(platform.system() == 'Linux' and not os.environ.get('ANDROID_ROOT'),
                'Not a Linux non-Android host')
    elif value == 'REDMI_NATIVE':
        require(bool(os.environ.get('ANDROID_ROOT')), 'Android runtime not detected')
        try:
            model = subprocess.check_output(['getprop', 'ro.product.model'],
                                            timeout=3, text=True).strip()
        except (OSError, subprocess.SubprocessError) as exc:
            raise ValueError('Redmi model cannot be verified') from exc
        require('Redmi Note 10 Pro' in model, 'Not registered Redmi Note 10 Pro')
    else:
        raise ValueError('Device kind must be explicit Linux or verified Redmi')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--installed-home', required=True)
    p.add_argument('--registration', required=True)
    p.add_argument('--register-only', action='store_true')
    p.add_argument('--execute-native', action='store_true')
    p.add_argument('--registration-sha256')
    p.add_argument('--work')
    p.add_argument('--device-kind')
    p.add_argument('--exclusive-owner-confirmed', action='store_true')
    a = p.parse_args(argv)
    if a.register_only == a.execute_native:
        p.error('Choose exactly one of --register-only or --execute-native')
    from scripts import step2_longnote_runner_preflight as pre
    from v13.common import file_hash
    root = Path(__file__).resolve().parents[1]
    installed = Path(a.installed_home).resolve()
    paths = (Path(__file__).resolve(), Path(pre.__file__).resolve(),
             Path(pre.corpus.__file__).resolve(), Path(pre.z2.__file__).resolve(),
             Path(pre.z2b.__file__).resolve(), root / 'tests/integration_step2_utility.py',
             root / 'scripts/step2_tool_replay.py', root / 'v13/cognition.py',
             root / 'v13/runners.py', root / 'v13/agi/eligibility.py')
    def sources():
        return {str(path.relative_to(root)): file_hash(path) for path in paths}
    def artifacts():
        return pre.z2.harness().installed_artifacts(installed)
    if a.register_only:
        dry = pre.dry_run()
        reg = make_registration(sources(), artifacts(),
                                [f['id'] for f in pre.corpus.FIXTURES],
                                dry['registered']['fixture_sha256'])
        raw = canonical(reg)
        write_new(a.registration, raw)
        print(json.dumps({'status': 'REGISTRATION_NO_INFERENCE',
                          'sha256': sha(raw), 'path': a.registration}))
        return 0
    if not a.work or not a.registration_sha256 or not a.device_kind:
        p.error('Native execution requires --work, --registration-sha256 and --device-kind')
    _device_kind(a.device_kind)
    def invoke(arm, seed, run_dir):
        with pre.configured():
            summary = pre.z2b.run_one(installed, run_dir, arm, seed)
        rid = f'{arm}_s{seed}'
        report_path = run_dir / ('step2_' + rid + '.json')
        tool_path = run_dir / ('tool_' + rid + '.json')
        report, tool = verify_native_reports(
            _read_file(report_path), _read_file(tool_path),
            [f['id'] for f in pre.corpus.FIXTURES],
            pre.dry_run()['registered']['fixture_sha256'])
        preparations = report.get('preparations')
        require(type(preparations) is list and preparations and
                all(p.get('status') == 'RECORDED' and
                    p.get('model_sha256') == preparations[0].get('model_sha256')
                    for p in preparations), 'Incomplete native model provenance')
        return summary, report_path, tool_path, preparations[0]['model_sha256']
    result = collect(a.registration, a.registration_sha256,
                     installed / 'data/coordinator.lock', a.work,
                     sources, artifacts, invoke, a.device_kind,
                     a.exclusive_owner_confirmed)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
