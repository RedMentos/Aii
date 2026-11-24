"""Read-only, hash-pinned on-disk input for the STEP2 four-arm scorer.

No native execution, file writes, or gate promotion. A trusted external pin
must be supplied for the manifest. Source/model hashes remain claims until
independently verified against their referenced files by the collector.
"""
import argparse
import hashlib
import json
import os
import re
import stat
from pathlib import Path

from scripts.step2_longnote_fourarm_analysis import ARMS, SEEDS, analyze

SCHEMA = 'V13_STEP2_FOURARM_EVIDENCE_V1'
NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')
MAX_MANIFEST = 128 * 1024
MAX_SUMMARY = 4 * 1024 * 1024
MAX_RAW = 64 * 1024 * 1024


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _pin(value):
    return type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _name(value):
    return type(value) is str and NAME.fullmatch(value) is not None and '..' not in value


def _read(rootfd, name, limit):
    if not _name(name):
        raise ValueError('Unsafe evidence filename')
    flags = os.O_RDONLY | getattr(os, 'O_CLOEXEC', 0) | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(name, flags, dir_fd=rootfd)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError('Evidence file is not regular or exceeds limit')
        chunks = []
        total = 0
        while True:
            chunk = os.read(fd, min(65536, limit + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > limit:
                raise ValueError('Evidence file exceeds limit')
            chunks.append(chunk)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError('Evidence changed during read')
        return b''.join(chunks)
    finally:
        os.close(fd)


def _pairs(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError('Duplicate JSON key')
        result[k] = v
    return result


def _json(data):
    def invalid(value):
        raise ValueError('Nonfinite JSON constant: ' + value)
    return json.loads(data.decode('utf-8'), object_pairs_hook=_pairs,
                      parse_constant=invalid)



def _native_pair(raw):
    """Decode the collector's exact two length-prefixed native reports."""
    if len(raw) < 16:
        raise ValueError('Native raw bundle missing length framing')
    n1 = int.from_bytes(raw[:8], 'big')
    if not 0 < n1 <= MAX_RAW or 8 + n1 + 8 > len(raw):
        raise ValueError('Native STEP2 report length invalid')
    offset = 8 + n1
    n2 = int.from_bytes(raw[offset:offset + 8], 'big')
    if not 0 < n2 <= MAX_RAW or offset + 8 + n2 != len(raw):
        raise ValueError('Native tool report length invalid')
    return raw[8:offset], raw[offset + 8:]


def _bind_native(raw, report, fixture_ids):
    """Reject sealed native summaries not derived from the closed raw rows.

    A correctly bound report is still not independent proof that native
    inference occurred; execution/device provenance needs external review.
    """
    from scripts.step2_fourarm_native_collector_candidate import (
        canonical, sha, verify_native_reports,
    )
    from scripts.step2_z2_timescale import error_profile
    step2_bytes, tool_bytes = _native_pair(raw)
    source, tool = verify_native_reports(
        step2_bytes, tool_bytes, fixture_ids, report['fixture_sha256'])
    fixtures = source['fixtures']
    if sha(canonical(fixtures)) != report['fixture_sha256']:
        raise ValueError('Raw fixture content differs from registered corpus')
    run = source.get('z2b_run')
    if (type(run) is not dict or run.get('arm') != report['arm'] or
            run.get('seed') != report['seed'] or
            run.get('enable') != report['enable'] or
            source.get('z2b_queried_offers') != report['queried_offers']):
        raise ValueError('Native arm, seed, controls or JEF query counts disagree')
    if (source['status'] != report['step2_status'] or
            tool['status'] != report['tool_status']):
        raise ValueError('Native status differs from scored summary')
    preparations = source.get('preparations')
    if (type(preparations) is not list or not preparations or
            any(type(p) is not dict or p.get('status') != 'RECORDED' or
                p.get('model_sha256') != report['model_sha256'] or
                p.get('runner_sha256') != report['runner_sha256']
                for p in preparations)):
        raise ValueError('Native preparation model/runner provenance disagrees')
    utility = {row['fixture'] + ':' + row['variant']: row['score']['utility']
               for row in tool['rows']}
    if utility != report['episode_utility_tool']:
        raise ValueError('Native raw tool utility differs from scored summary')
    computed = error_profile(tool['rows'], {f['id']: f for f in fixtures})
    if any(report['error_profile_tool'][v] != computed[v]
           for v in ('b1_only', 'b2_only')):
        raise ValueError('Native raw complementary error profile differs')



def load(root, manifest_name, expected_manifest_sha256, fixture_ids,
         expected_fixture_sha256=None):
    """Read twelve immutable-pinned pairs; validate complete pairing.

    The supplied expected manifest hash is an external operator pin, not a
    self-attestation taken from the manifest itself.
    """
    if not _pin(expected_manifest_sha256):
        raise ValueError('Missing externally pinned manifest SHA256')
    rootfd = os.open(os.fspath(root), os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        manifest_bytes = _read(rootfd, manifest_name, MAX_MANIFEST)
        if _hash(manifest_bytes) != expected_manifest_sha256:
            raise ValueError('Manifest bytes do not match external pin')
        manifest = _json(manifest_bytes)
        if type(manifest) is not dict or manifest.get('schema') != SCHEMA:
            raise ValueError('Unknown manifest schema')
        if manifest.get('fixture_ids') != list(fixture_ids):
            raise ValueError('Manifest fixture identities do not match source')
        items = manifest.get('runs')
        if type(items) is not list or len(items) != len(ARMS) * len(SEEDS):
            raise ValueError('Incomplete manifest run inventory')
        reports = []
        used = {manifest_name}
        for entry in items:
            if type(entry) is not dict or set(entry) != {
                    'arm', 'seed', 'summary', 'summary_sha256', 'raw', 'raw_sha256'}:
                raise ValueError('Invalid manifest run entry')
            if (entry['arm'] not in ARMS or type(entry['seed']) is not int or
                    entry['seed'] not in SEEDS or not _pin(entry['summary_sha256']) or
                    not _pin(entry['raw_sha256'])):
                raise ValueError('Invalid run identity or digest')
            names = (entry['summary'], entry['raw'])
            if any(not _name(name) or name in used for name in names) or names[0] == names[1]:
                raise ValueError('Reused or unsafe evidence path')
            used.update(names)
            summary = _read(rootfd, entry['summary'], MAX_SUMMARY)
            raw = _read(rootfd, entry['raw'], MAX_RAW)
            if _hash(summary) != entry['summary_sha256'] or _hash(raw) != entry['raw_sha256']:
                raise ValueError('Evidence bytes do not match manifest')
            report = _json(summary)
            if (type(report) is not dict or report.get('arm') != entry['arm'] or
                    report.get('seed') != entry['seed'] or
                    report.get('raw_sha256') != entry['raw_sha256']):
                raise ValueError('Run metadata differs from sealed files')
            if (expected_fixture_sha256 is not None and
                    report.get('fixture_sha256') != expected_fixture_sha256):
                raise ValueError('Fixture hash differs from source')
            if report.get('evidence_kind') in ('LINUX_NATIVE', 'REDMI_NATIVE'):
                if not _pin(expected_fixture_sha256):
                    raise ValueError('External registered fixture SHA256 required for native evidence')
                _bind_native(raw, report, fixture_ids)
            reports.append(report)
        return analyze(reports, fixture_ids)
    finally:
        os.close(rootfd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', required=True)
    parser.add_argument('--manifest', default='manifest.json')
    parser.add_argument('--manifest-sha256', required=True)
    args = parser.parse_args(argv)
    from scripts import step2_longnote_revision_fixtures as corpus
    ids = [f['id'] for f in corpus.FIXTURES]
    raw = json.dumps(corpus.FIXTURES, sort_keys=True, ensure_ascii=False,
                     separators=(',', ':'), allow_nan=False).encode('utf-8')
    report = load(Path(args.evidence_dir), args.manifest, args.manifest_sha256,
                  ids, _hash(raw))
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
