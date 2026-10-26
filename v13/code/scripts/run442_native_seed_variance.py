#!/usr/bin/env python3
"""Run442: read-only seed20/21 O-arm native utility variance, no causal claims.

Uses actual independently verified Run427 no-model ZIP, not model weights.
Validates the outer artifact, every inner file, and both O-arm source/tool rows.
Emits only hashes, aggregate utility and identity counts, never source text.
"""
import argparse
import hashlib
import json
import math
import stat
import zipfile
from pathlib import Path

ARTIFACT_SHA = '405e62268b0314c6e852e367a4624a12508e971877afe14afebf05cb2afba6b7'
MANIFEST = 'RUN409_EXPORT_MANIFEST.json'
FIXTURES = ('Alder', 'Beacon', 'Cypress', 'Delta', 'Ember', 'Fable')
VARIANTS = ('b1_only', 'b2_only', 'both_none', 'both_exact', 'both_control',
            'same_policy_dual', 'prompt_only_dual')
PREFIX = {'O_s20', 'P_s20', 'S_s20', 'O_s21'}


def require(ok, why):
    if not ok:
        raise ValueError(why)


def sha(raw):
    return hashlib.sha256(raw.encode() if isinstance(raw, str) else raw).hexdigest()


def canon(v):
    return json.dumps(v, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False)


def safe(name):
    require(type(name) is str and name and not name.startswith('/') and
            '\\' not in name and ':' not in name and
            all(part not in ('', '.', '..') for part in name.split('/')) and
            not any(part.casefold() == 'models' for part in name.split('/')) and
            not name.lower().endswith(('.gguf', '.safetensors', '.ckpt', '.pth', '.pt', '.cact')),
            'UNSAFE_ARCHIVE_PATH')


def rows(z, path):
    d = json.loads(z.read(path))
    require(type(d.get('rows')) is list and type(d.get('row_sha256')) is dict,
            'ROWS_MISSING')
    out = {}
    for row in d['rows']:
        require(type(row) is dict and row.get('status') == 'RECORDED',
                'ROW_NOT_RECORDED')
        key = f"{row.get('fixture')}:{row.get('variant')}"
        require(key not in out and key in {f'{f}:{v}' for f in FIXTURES for v in VARIANTS},
                'ROW_DUPLICATE_OR_UNKNOWN')
        require(d['row_sha256'].get(key) == sha(canon(row)), 'ROW_SHA_MISMATCH')
        out[key] = row
    require(len(out) == 42 and set(d['row_sha256']) == set(out), 'ROW_COVERAGE_MISMATCH')
    return out


def offer_hash(row, role):
    users = [m for m in row['consumer_messages'] if m.get('role') == 'user']
    require(len(users) == 1, 'CONSUMER_USER_MESSAGE_INVALID')
    analysts = json.loads(users[0]['content'])['analysts']
    require(type(analysts) is list, 'ANALYSTS_INVALID')
    selected = [a for a in analysts if a.get('role') == role]
    return sha(canon(selected)) if selected else None


def analyze(archive, expected_sha=ARTIFACT_SHA):
    archive = Path(archive)
    require(archive.is_file() and not archive.is_symlink() and
            archive.stat().st_nlink == 1, 'ARCHIVE_SOURCE_UNSAFE')
    require(type(expected_sha) is str and len(expected_sha) == 64 and
            all(c in '0123456789abcdef' for c in expected_sha), 'SHA_INVALID')
    h = hashlib.sha256()
    with archive.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    require(h.hexdigest() == expected_sha, 'OUTER_SHA_MISMATCH')
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        require(len(names) == len(set(names)) and MANIFEST in names,
                'ZIP_DUPLICATE_OR_MISSING_MANIFEST')
        for item in infos:
            safe(item.filename[:-1] if item.is_dir() else item.filename)
            kind = stat.S_IFMT((item.external_attr >> 16) & 0xffff)
            require(kind in ((0, stat.S_IFDIR) if item.is_dir() else
                             (0, stat.S_IFREG)), 'ZIP_SPECIAL_FILE')
        manifest_raw = z.read(MANIFEST)
        manifest = json.loads(manifest_raw)
        copied = manifest.get('copied')
        require(manifest.get('schema') == 'RUN409_SAFE_NATIVE_EXPORT_V1' and
                manifest.get('canonical_gate_pass') is False and
                manifest.get('step2_exit') == 'UTILITY_FAIL' and
                type(copied) is dict and bool(copied), 'MANIFEST_INVALID')
        require(set(n for n in names if not n.endswith('/')) == set(copied) | {MANIFEST},
                'INVENTORY_MISMATCH')
        total = 0
        for name, meta in copied.items():
            safe(name)
            require(type(meta) is dict and type(meta.get('bytes')) is int and
                    0 <= meta['bytes'] <= 128_000_000, 'FILE_SIZE_INVALID')
            raw = z.read(name)
            require(len(raw) == meta['bytes'] and sha(raw) == meta.get('sha256'),
                    'INNER_SHA_MISMATCH:' + name)
            total += len(raw)
            require(total <= 300_000_000, 'TOTAL_BUDGET_EXCEEDED')
        progress = json.loads(z.read('RUN397_PROGRESS.json'))
        require(set(progress.get('completed', {})) == PREFIX and
                progress.get('canonical_gate_pass') is False and
                progress.get('step2_exit') == 'UTILITY_FAIL' and
                progress.get('failures_preserved') == {}, 'PROGRESS_INVALID')
        source, tool = {}, {}
        for rid in ('O_s20', 'O_s21'):
            path = progress['completed'][rid]['attempt']
            safe(path)
            source[rid] = rows(z, path + '/step2_' + rid + '.json')
            tool[rid] = rows(z, path + '/tool_' + rid + '.json')
            for key, t in tool[rid].items():
                require(t.get('oracle_visible_to_native') is False and
                        t.get('consumer_messages_sha256') ==
                        sha(canon(source[rid][key]['consumer_messages'])),
                        'SOURCE_TOOL_REPLAY_MISMATCH')
        result = {}
        for variant in VARIANTS:
            paired = []
            for fixture in FIXTURES:
                key = f'{fixture}:{variant}'
                t20, t21 = tool['O_s20'][key], tool['O_s21'][key]
                s20, s21 = source['O_s20'][key], source['O_s21'][key]
                u20, u21 = t20['score']['utility'], t21['score']['utility']
                require(all(type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 1
                            for x in (u20, u21)), 'UTILITY_INVALID')
                paired.append({'fixture': fixture, 'u20': u20, 'u21': u21,
                               'same_input': t20['consumer_messages_sha256'] == t21['consumer_messages_sha256'],
                               'same_b1': offer_hash(s20, 'B1_DETAIL') == offer_hash(s21, 'B1_DETAIL'),
                               'same_b2': offer_hash(s20, 'B2_GIST') == offer_hash(s21, 'B2_GIST'),
                               'same_answer': t20['answer'] == t21['answer'],
                               'action20': t20['score']['field_checks'].get('action', False),
                               'action21': t21['score']['field_checks'].get('action', False)})
            result[variant] = {
                'mean_utility_seed20': round(sum(x['u20'] for x in paired) / 6, 12),
                'mean_utility_seed21': round(sum(x['u21'] for x in paired) / 6, 12),
                'mean_delta_seed21_minus20': round(sum(x['u21']-x['u20'] for x in paired) / 6, 12),
                'same_inputs': sum(x['same_input'] for x in paired),
                'same_b1_offers': sum(x['same_b1'] for x in paired),
                'same_b2_offers': sum(x['same_b2'] for x in paired),
                'same_answers': sum(x['same_answer'] for x in paired),
                'action_correct_seed20': sum(x['action20'] for x in paired),
                'action_correct_seed21': sum(x['action21'] for x in paired),
                'per_fixture_delta': {x['fixture']: round(x['u21']-x['u20'], 12) for x in paired},
            }
        return {'schema': 'V13_RUN442_ACTUAL_NATIVE_O_SEED20_21_VARIANCE_V1',
                'source': 'actual Run427 no-model export, independently verified in Run433',
                'artifact_sha256': expected_sha,
                'manifest_sha256': sha(manifest_raw),
                'copied_files_verified': len(copied),
                'rows_verified_in_archive': 168,
                'rows_compared': 84,
                'pairs': result,
                'canonical_gate_pass': False, 'step2_exit': 'UTILITY_FAIL',
                'redmi_measured': False, 'jepa_weight': 0,
                'claim_limit': 'Cross-seed O-arm observational variance, not a causal intervention. 168 structural rows were independently verified in Run433; this analysis rechecks all 131 files and the 84 O-arm source/tool rows. No native rerun, Redmi, JEPA, or STEP2 promotion.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--expected-sha256', default=ARTIFACT_SHA)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    try:
        result = analyze(args.archive, args.expected_sha256)
        status = 0
    except (OSError, ValueError, KeyError, TypeError, IndexError,
            json.JSONDecodeError, zipfile.BadZipFile) as e:
        result = {'schema': 'V13_RUN442_RED_V1', 'status': 'RED_PRESERVED',
                  'error': type(e).__name__ + ':' + str(e)[:240],
                  'canonical_gate_pass': False, 'step2_exit': 'UTILITY_FAIL'}
        status = 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'status': 'PASS' if status == 0 else 'RED',
                      'rows_compared': result.get('rows_compared', 0),
                      'canonical_gate_pass': False, 'step2_exit': 'UTILITY_FAIL'}))
    raise SystemExit(status)


if __name__ == '__main__':
    main()
