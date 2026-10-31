"""Read-only, non-promoting forensic of an original V13 unittest evidence ZIP.

Nested subprocess stderr inside assertions can repeat failure headers. The final
unittest summary remains authoritative for top-level counts; never rescore it.
"""
import argparse
import collections
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

MAX_ZIP_BYTES = 8_000_000
MAX_MEMBER_BYTES = 4_000_000
HEAD = re.compile(r'(?m)^={70}\n(ERROR|FAIL): ([^\n]+)\n-{70}\n')
RUN = re.compile(r'(?m)^Ran (\d+) tests? in [^\n]+$')
FAILED = re.compile(r'(?m)^FAILED \(([^\n]+)\)$')
CAUSE = re.compile(r'(?m)^([A-Za-z_][\w.]*(?:Error|Exception|Failure)): ([^\n]*)$')


def evidence(path, expected_sha256):
    path = Path(path)
    if path.stat().st_size > MAX_ZIP_BYTES:
        raise ValueError('ZIP_TOO_LARGE')
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha256:
        raise ValueError('ORIGINAL_ZIP_SHA256_MISMATCH')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or any('/' in n or '\\' in n or n.startswith('.') for n in names):
            raise ValueError('ZIP_MEMBER_NAMES_INVALID')
        if 'FULL_RAW.log' not in names or 'SHA256SUMS' not in names or 'FULL_EXIT.txt' not in names:
            raise ValueError('ORIGINAL_EVIDENCE_MISSING')
        if any(i.file_size > MAX_MEMBER_BYTES or i.flag_bits & 1 for i in z.infolist()):
            raise ValueError('ZIP_MEMBER_TOO_LARGE_OR_ENCRYPTED')
        if z.testzip() is not None:
            raise ValueError('ZIP_CRC_RED')
        manifest = z.read('SHA256SUMS').decode('ascii')
        recorded = {}
        for line in manifest.splitlines():
            m = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
            if not m:
                raise ValueError('SHA256SUMS_INVALID')
            item = m.group(2)
            # GitHub Actions find . writes ./name while ZIP entries use name.
            if item.startswith('./'):
                item = item[2:]
            if not item or '/' in item or '\\' in item or item in recorded:
                raise ValueError('SHA256SUMS_INVALID_PATH')
            recorded[item] = m.group(1)
        if set(recorded) != set(names) - {'SHA256SUMS'}:
            raise ValueError('SHA256SUMS_COVERAGE_RED')
        for name, digest in recorded.items():
            if hashlib.sha256(z.read(name)).hexdigest() != digest:
                raise ValueError('SHA256SUMS_CONTENT_RED')
        return z.read('FULL_RAW.log').decode('utf-8'), z.read('FULL_EXIT.txt').decode('ascii').strip(), actual


def parse(text):
    runs = list(RUN.finditer(text))
    finals = list(FAILED.finditer(text))
    if not runs or not finals or finals[-1].start() < runs[-1].end():
        raise ValueError('UNITTEST_TERMINAL_SUMMARY_MISSING')
    parts = {}
    for part in finals[-1].group(1).split(', '):
        key, sep, value = part.partition('=')
        if not sep or key not in {'failures', 'errors', 'skipped'} or not value.isdigit() or key in parts:
            raise ValueError('UNITTEST_SUMMARY_INVALID')
        parts[key] = int(value)
    if 'failures' not in parts or 'errors' not in parts:
        raise ValueError('UNITTEST_SUMMARY_INCOMPLETE')
    matches = list(HEAD.finditer(text))
    if not matches:
        raise ValueError('UNITTEST_FAILURE_HEADERS_MISSING')
    causes = collections.Counter()
    names = collections.Counter()
    for index, match in enumerate(matches):
        block = text[match.end():(matches[index+1].start() if index+1 < len(matches) else len(text))]
        # TRACE classifier, never a replacement for top-level unittest counts.
        found = CAUSE.findall(block)
        kind, detail = (found[-1] if found else ('UNCLASSIFIED', ''))
        causes[(match.group(1), kind, detail[:160])] += 1
        names[match.group(1)] += 1
    return {
        'top_level_unittest': {'tests': int(runs[-1].group(1)), **parts},
        'trace_header_occurrences': dict(sorted(names.items())),
        'trace_causes': [
            {'kind': kind, 'exception': exc, 'detail': detail, 'occurrences': count}
            for (kind, exc, detail), count in sorted(causes.items(), key=lambda x: (-x[1], x[0]))
        ],
        'trace_counts_not_top_level': True,
    }


def source_probe(root):
    """Execute existing strict source checks without modifying their policies."""
    import sys
    root = Path(root).resolve()
    sys.path.insert(0, str(root))
    results = {}
    for module_name in ('source_handoff_candidate', 'native_firing_runtime_candidate'):
        try:
            module = __import__('scripts.' + module_name, fromlist=['sources'])
            live = {name: hashlib.sha256((root/name).read_bytes()).hexdigest()
                    for name in module.NAMES}
            try:
                module.sources(root)
            except (ValueError, OSError, KeyError) as exc:
                verdict = 'STRICT_SOURCE_REFUSAL'
                reason = type(exc).__name__ + ': ' + str(exc)[:220]
            else:
                verdict, reason = 'STRICT_SOURCE_ACCEPT', None
            results[module_name] = {'verdict': verdict, 'reason': reason, 'live_sha256': live}
        except (ImportError, AttributeError, OSError, ValueError) as exc:
            results[module_name] = {'verdict': 'PROBE_UNAVAILABLE',
                                    'reason': type(exc).__name__ + ': ' + str(exc)[:220]}
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--root', help='Optional v13/code root for strict source compatibility checks')
    parser.add_argument('--out', help='Optional JSON output; never overwrites an existing file')
    args = parser.parse_args(argv)
    if not re.fullmatch(r'[0-9a-f]{64}', args.sha256):
        parser.error('--sha256 must be lowercase SHA256')
    raw, exit_code, digest = evidence(args.zip, args.sha256)
    report = {'schema': 'V13_FULLSUITE_SOURCE_COMPAT_TRIAGE_V1',
              'evidence_sha256': digest, 'full_exit': exit_code,
              'forensic_only': True, 'promotion_authority': False,
              'summary': parse(raw)}
    if args.root:
        report['source_compatibility'] = source_probe(args.root)
    output = json.dumps(report, sort_keys=True, indent=2) + '\n'
    if args.out:
        with Path(args.out).open('x', encoding='utf-8') as f:
            f.write(output)
    else:
        print(output, end='')
    return report


if __name__ == '__main__':
    main()
