#!/usr/bin/env python3
"""Audit an existing phone ZIP and its complete extracted software suite.

Isolated release candidate; does not change packaging or runtime sources.
Success is Linux software evidence only, never a Redmi or learned-utility gate.
Proof directory must be new. Tests always use full unittest discovery.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import signal
import stat
import subprocess
import sys
import time
import zipfile

PREFIX = 'V13-Phone/'
MANIFEST = PREFIX + 'WORKSPACE_FILES.json'
CHUNK = 1 << 20


def sha256(path):
    with Path(path).open('rb') as stream:
        return _hash_stream(stream)


def _hash_stream(stream):
    digest = hashlib.sha256()
    while block := stream.read(CHUNK):
        digest.update(block)
    return digest.hexdigest()


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate manifest key: ' + key)
        result[key] = value
    return result


def _relative_path(value):
    if (not isinstance(value, str) or not value or '\\' in value or ':' in value
            or '\x00' in value or value.startswith('/')
            or any(part in ('', '.', '..') for part in value.split('/'))
            or str(PurePosixPath(value)) != value):
        raise ValueError('Invalid archive path: ' + repr(value))
    return value


def verify_archive(path):
    """Require exact manifest membership and checksums before any extraction."""
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate ZIP paths')
        for entry in entries:
            if not entry.filename.startswith(PREFIX):
                raise ValueError('ZIP entry outside V13-Phone')
            _relative_path(entry.filename[len(PREFIX):])
            mode = entry.external_attr >> 16
            if entry.is_dir() or stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFREG)):
                raise ValueError('ZIP entry is not a regular file: ' + entry.filename)
        if MANIFEST not in names:
            raise ValueError('Missing WORKSPACE_FILES.json')
        manifest = json.loads(archive.read(MANIFEST), object_pairs_hook=_unique_pairs)
        if (not isinstance(manifest, dict) or type(manifest.get('schema_version')) is not int
                or manifest['schema_version'] != 1 or not isinstance(manifest.get('files'), dict)
                or not manifest['files']):
            raise ValueError('Invalid workspace manifest schema')
        files = manifest['files']
        for relative, digest in files.items():
            _relative_path(relative)
            if relative == 'WORKSPACE_FILES.json' or not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
                raise ValueError('Invalid workspace manifest entry: ' + relative)
        if set(names) != {MANIFEST} | {PREFIX + relative for relative in files}:
            raise ValueError('ZIP membership differs from manifest')
        for relative, digest in files.items():
            with archive.open(PREFIX + relative) as stream:
                if _hash_stream(stream) != digest:
                    raise ValueError('ZIP checksum mismatch: ' + relative)
        if archive.testzip() is not None:
            raise ValueError('ZIP CRC failure')
        return files


TEST_RUNNER = '''import json, pathlib, sys, unittest
suite = unittest.defaultTestLoader.discover('tests', pattern='test_*.py')
result = unittest.TextTestRunner(verbosity=1).run(suite)
summary = dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
               skips=len(result.skipped), expected_failures=len(result.expectedFailures),
               unexpected_successes=len(result.unexpectedSuccesses), successful=result.wasSuccessful(),
               passed=result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped)
                      -len(result.expectedFailures)-len(result.unexpectedSuccesses),
               failure_ids=[case.id() for case, _ in result.failures],
               error_ids=[case.id() for case, _ in result.errors],
               skipped_ids=[case.id() for case, _ in result.skipped],
               skipped_cases=[dict(id=case.id(), reason=reason) for case, reason in result.skipped])
pathlib.Path(sys.argv[1]).write_text(json.dumps(summary, indent=2)+'\\n')
sys.exit(0 if result.wasSuccessful() and result.testsRun > 0 else 1)
'''


def _stop_test_group(process):
    """Signal only the new session owned by this audit, then reap its leader."""
    requested = []
    for number in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, number)
            requested.append(signal.Signals(number).name)
        except ProcessLookupError:
            pass
        if number == signal.SIGTERM:
            # Descendants may ignore TERM even when the leader already exited.
            time.sleep(0.1)
    process.wait(timeout=5)
    return {'signals_sent': requested, 'leader_reaped': True,
            'leader_returncode': process.returncode}


def audit(path, proof_dir, *, timeout=1800):
    """Create closed proof, including failures; never overwrite a previous audit."""
    path, proof_dir = Path(path).resolve(), Path(proof_dir).absolute()
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('Timeout must be finite and positive')
    proof_dir.mkdir(parents=True, exist_ok=False)
    report = {'schema': 'V13_PHONE_RELEASE_AUDIT_CANDIDATE_V1', 'zip': str(path),
              'status': 'FAIL', 'phone_measured': False, 'canonical_gate_pass': False,
              'release_complete': False, 'software_tests_successful': False,
              'learned_utility_proven': False, 'native_model_runs_requested': False,
              'claim_scope': 'Linux extracted software tests only',
              'test_policy': 'complete unittest discovery; nonempty; skips explicitly limit release completeness',
              'archive_verified': False, 'manifest_unchanged_after_tests': False}
    started = time.monotonic()
    try:
        original_sha = sha256(path)
        report['zip_sha256'] = original_sha
        files = verify_archive(path)
        report['manifest_files'] = len(files)
        report['archive_verified'] = True
        extracted = proof_dir / 'extracted'
        with zipfile.ZipFile(path) as archive:
            manifest_sha = hashlib.sha256(archive.read(MANIFEST)).hexdigest()
            archive.extractall(extracted)
        root = extracted / 'V13-Phone'
        # Revalidate actual extracted bytes rather than trusting extractall.
        def unchanged():
            return all((root / name).is_file() and not (root / name).is_symlink()
                       and sha256(root / name) == digest
                       for name, digest in {**files, 'WORKSPACE_FILES.json': manifest_sha}.items())
        if sha256(path) != original_sha or not unchanged():
            raise ValueError('Archive/extracted bytes changed before tests')
        env = dict(os.environ)
        env['PYTHONPATH'] = str(root) + os.pathsep + str(root / 'tests')
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        summary_path = proof_dir / 'suite-summary.json'
        with (proof_dir / 'suite.log').open('wb') as log:
            process = subprocess.Popen([sys.executable, '-c', TEST_RUNNER, str(summary_path)],
                                       cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            try:
                report['suite_returncode'] = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                report['suite_timed_out'] = True
                report['suite_timeout_cleanup'] = _stop_test_group(process)
            except BaseException:
                _stop_test_group(process)
                raise
        if summary_path.is_file():
            report['suite'] = json.loads(summary_path.read_text())
        report['manifest_unchanged_after_tests'] = unchanged()
        report['archive_unchanged_after_tests'] = sha256(path) == original_sha
        suite = report.get('suite', {})
        if (report.get('suite_returncode') == 0 and suite.get('successful')
                and suite.get('tests', 0) > 0
                and report['manifest_unchanged_after_tests'] and report['archive_unchanged_after_tests']):
            report['software_tests_successful'] = True
            report['release_complete'] = suite.get('skips') == 0
            report['status'] = 'SOFTWARE_PASS_WITH_SKIPS' if suite.get('skips') else 'EXTRACTED_SOFTWARE_PASS'
    except (ValueError, OSError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        report['error'] = str(exc)
    report['elapsed_seconds'] = time.monotonic() - started
    report_path = proof_dir / 'audit.json'
    report_path.write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', required=True, type=Path)
    parser.add_argument('--proof-dir', required=True, type=Path)
    parser.add_argument('--timeout', type=float, default=1800)
    args = parser.parse_args()
    report = audit(args.zip, args.proof_dir, timeout=args.timeout)
    print(json.dumps(report, sort_keys=True))
    return 0 if report['software_tests_successful'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
