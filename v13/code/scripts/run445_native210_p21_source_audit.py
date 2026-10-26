#!/usr/bin/env python3
"""Run445: independent actual native210 P_s21 source-identity/utility audit.

Read-only existing Run437 no-model artifact; no causal pointer claim.
"""
import argparse
import hashlib
import json
import math
import stat
import zipfile
from pathlib import Path
import run442_native_seed_variance as base

ARTIFACT_SHA = '280bcf57f5dd956f9776174143acdbeb1e8df0c6adad18d0824db893e8ba32b7'
COMPLETED = {'O_s20', 'O_s21', 'P_s20', 'P_s21', 'S_s20'}
COMPARE = (('P_s21', 'O_s21'), ('P_s21', 'P_s20'), ('O_s21', 'O_s20'))


def analyze(archive, expected_sha=ARTIFACT_SHA):
    archive = Path(archive)
    base.require(archive.is_file() and not archive.is_symlink() and
                 archive.stat().st_nlink == 1, 'ARCHIVE_SOURCE_UNSAFE')
    base.require(type(expected_sha) is str and len(expected_sha) == 64 and
                 all(c in '0123456789abcdef' for c in expected_sha), 'SHA_INVALID')
    h = hashlib.sha256()
    with archive.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    base.require(h.hexdigest() == expected_sha, 'OUTER_SHA_MISMATCH')
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        base.require(len(names) == len(set(names)) and base.MANIFEST in names,
                     'ZIP_DUPLICATE_OR_MISSING_MANIFEST')
        for item in infos:
            base.safe(item.filename[:-1] if item.is_dir() else item.filename)
            kind = stat.S_IFMT((item.external_attr >> 16) & 0xffff)
            base.require(kind in ((0, stat.S_IFDIR) if item.is_dir() else
                                  (0, stat.S_IFREG)), 'ZIP_SPECIAL_FILE')
        manifest_raw = z.read(base.MANIFEST)
        manifest = json.loads(manifest_raw)
        copied = manifest.get('copied')
        base.require(manifest.get('schema') == 'RUN409_SAFE_NATIVE_EXPORT_V1' and
                     manifest.get('canonical_gate_pass') is False and
                     manifest.get('step2_exit') == 'UTILITY_FAIL' and
                     type(copied) is dict and bool(copied), 'MANIFEST_INVALID')
        base.require(set(n for n in names if not n.endswith('/')) ==
                     set(copied) | {base.MANIFEST}, 'INVENTORY_MISMATCH')
        total = 0
        for name, meta in copied.items():
            base.safe(name)
            base.require(type(meta) is dict and type(meta.get('bytes')) is int and
                         0 <= meta['bytes'] <= 128_000_000, 'FILE_SIZE_INVALID')
            data = z.read(name)
            base.require(len(data) == meta['bytes'] and
                         base.sha(data) == meta.get('sha256'),
                         'INNER_SHA_MISMATCH:' + name)
            total += len(data)
            base.require(total <= 300_000_000, 'TOTAL_BUDGET_EXCEEDED')
        progress = json.loads(z.read('RUN397_PROGRESS.json'))
        base.require(set(progress.get('completed', {})) == COMPLETED and
                     progress.get('canonical_gate_pass') is False and
                     progress.get('step2_exit') == 'UTILITY_FAIL' and
                     progress.get('failures_preserved') == {}, 'PROGRESS_INVALID')
        frozen = json.loads(z.read('RUN394_PREREGISTERED_FIXTURES.json'))
        base.require(frozen.get('fixture_ids') == list(base.FIXTURES) and
                     frozen.get('seeds') == [20, 21, 22] and
                     set(frozen.get('arms', {})) == {'O', 'P', 'S'},
                     'FROZEN_COHORT_MISMATCH')
        source, tool, receipts = {}, {}, {}
        for rid in sorted(COMPLETED):
            path = progress['completed'][rid]['attempt']
            base.safe(path)
            source_path = path + f'/step2_{rid}.json'
            tool_path = path + f'/tool_{rid}.json'
            source[rid] = base.rows(z, source_path)
            tool[rid] = base.rows(z, tool_path)
            for key, row in tool[rid].items():
                base.require(row.get('oracle_visible_to_native') is False and
                             row.get('consumer_messages_sha256') ==
                             base.sha(base.canon(source[rid][key]['consumer_messages'])),
                             'SOURCE_TOOL_REPLAY_MISMATCH')
            receipts[rid] = {'source_sha256': base.sha(z.read(source_path)),
                             'tool_sha256': base.sha(z.read(tool_path))}
        pairs = {}
        for left, right in COMPARE:
            variants = {}
            for variant in base.VARIANTS:
                observed = []
                for fixture in base.FIXTURES:
                    key = f'{fixture}:{variant}'
                    a, b = tool[left][key], tool[right][key]
                    sa, sb = source[left][key], source[right][key]
                    ua, ub = a['score']['utility'], b['score']['utility']
                    base.require(all(type(x) in (int, float) and math.isfinite(x)
                                     and 0 <= x <= 1 for x in (ua, ub)),
                                 'UTILITY_INVALID')
                    observed.append({'fixture': fixture, 'delta': round(ua-ub, 12),
                                     'same_input': a['consumer_messages_sha256'] == b['consumer_messages_sha256'],
                                     'same_b1': base.offer_hash(sa, 'B1_DETAIL') == base.offer_hash(sb, 'B1_DETAIL'),
                                     'same_b2': base.offer_hash(sa, 'B2_GIST') == base.offer_hash(sb, 'B2_GIST'),
                                     'same_answer': a['answer'] == b['answer']})
                variants[variant] = {
                    'mean_utility_delta': round(sum(x['delta'] for x in observed)/6, 12),
                    'same_inputs': sum(x['same_input'] for x in observed),
                    'same_b1_offers': sum(x['same_b1'] for x in observed),
                    'same_b2_offers': sum(x['same_b2'] for x in observed),
                    'same_answers': sum(x['same_answer'] for x in observed),
                    'per_fixture_delta': {x['fixture']: x['delta'] for x in observed}}
            pairs[left + '_minus_' + right] = variants
        return {'schema': 'V13_RUN445_ACTUAL_NATIVE210_P21_SOURCE_AUDIT_V1',
                'source': 'actual Run437 GitHub Actions safe no-model export',
                'artifact_id': 12627626352, 'artifact_sha256': expected_sha,
                'manifest_sha256': base.sha(manifest_raw),
                'verified_files': len(copied), 'verified_bytes': total,
                'completed': sorted(COMPLETED), 'source_rows_verified': 210,
                'tool_rows_verified': 210, 'source_tool_replay_verified': 210,
                'receipts': receipts, 'pairs': pairs,
                'canonical_gate_pass': False, 'step2_exit': 'UTILITY_FAIL',
                'redmi_measured': False, 'jepa_weight': 0,
                'native_execution_performed_in_this_audit': False,
                'claim_limit': 'Actual Linux-native data, independent read-only postflight; source/offer identity varies, P_s21 vs O_s21 pointer contrast is not automatically causal; no Redmi/STEP2/B3/Body-JEPA promotion.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--expected-sha256', default=ARTIFACT_SHA)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    try:
        result = analyze(args.archive, args.expected_sha256)
        code = 0
    except (OSError, ValueError, KeyError, TypeError, IndexError,
            json.JSONDecodeError, zipfile.BadZipFile) as exc:
        result = {'schema': 'V13_RUN445_RED_V1', 'status': 'RED_PRESERVED',
                  'error': type(exc).__name__ + ':' + str(exc)[:240],
                  'canonical_gate_pass': False, 'step2_exit': 'UTILITY_FAIL'}
        code = 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'status': 'PASS' if code == 0 else 'RED',
                      'rows_verified': result.get('source_tool_replay_verified', 0),
                      'canonical_gate_pass': False, 'step2_exit': 'UTILITY_FAIL'}))
    raise SystemExit(code)


if __name__ == '__main__':
    main()
