"""Posthoc, read-only explicit-equation coverage diagnostic; never a STEP2 gate."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ORIGINAL_SHA256 = '98a61f622b64b792f38d766da3ef50e9101571b7e616f2c587d6e89ab5e31c46'
ORIGINAL_HEAD = '5e802d235c9501879a3aff07e5134c1455e1769b'
ORIGINAL_FIXTURE_SHA256 = 'fe9b86fdf561778ad540dd4767111f04c10a147a8a44cf783fa16f0d2c8a45ca'
ORIGINAL_SCORES = {'A_C3_ONLY': 0, 'B_DEFAULT_BOTH': 10, 'C_ARITH_BOTH': 9}
EQUATION = re.compile(r'(?<!\d)(\d{1,9})\s*-\s*(\d{1,9})\s*=\s*(\d{1,9})(?!\d)')


def equation_diagnostic(fixture, text):
    """Exact source-operand equations on single-option lines, never inferred sums."""
    if not isinstance(fixture, dict) or not isinstance(text, str):
        raise ValueError('INVALID_DIAGNOSTIC_INPUT')
    claims = {'a': set(), 'b': set()}
    ambiguous = {'a': 0, 'b': 0}
    patterns = {key: re.compile(r'(?<!\w)' + re.escape(fixture[key]) + r'(?!\w)', re.I)
                for key in ('a', 'b')}
    for line in text.splitlines():
        # Ignore formatting, but never rewrite words or numerical operands.
        clean = line.replace('€', '').replace('*', '')
        equations = [tuple(map(int, m.groups())) for m in EQUATION.finditer(clean)]
        if not equations:
            continue
        owners = [key for key in ('a', 'b') if patterns[key].search(clean)]
        if len(owners) == 2:
            ambiguous['a'] += 1
            ambiguous['b'] += 1
        elif len(owners) == 1:
            claims[owners[0]].update(equations)
    result = {}
    for key in ('a', 'b'):
        items = sorted(claims[key])
        expected = fixture['budget'] - fixture[key + '_cost']
        if ambiguous[key] and items or len(items) > 1:
            status = 'CONTRADICTORY'
        elif ambiguous[key]:
            status = 'AMBIGUOUS'
        elif not items:
            status = 'MISSING'
        elif items[0][:2] != (fixture['budget'], fixture[key + '_cost']):
            status = 'INVALID_OPERANDS'
        elif items[0][2] != expected:
            status = 'WRONG'
        else:
            status = 'CORRECT'
        result[key] = {'status': status, 'correct': status == 'CORRECT',
                       'expected': expected, 'equations': items,
                       'ambiguous_lines': ambiguous[key]}
    return result


def audit_original_zip(path):
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != ORIGINAL_SHA256:
        raise ValueError('ORIGINAL_ZIP_CHANGED')
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None or len(z.namelist()) != len(set(z.namelist())):
            raise ValueError('ORIGINAL_ZIP_CRC_OR_DUPLICATE')
        if z.read('HEAD.txt').decode().strip() != ORIGINAL_HEAD:
            raise ValueError('ORIGINAL_HEAD_CHANGED')
        report = json.loads(z.read('pilot/report.json'))
        if (report['fixture_sha256'] != ORIGINAL_FIXTURE_SHA256
                or report['score_totals_out_of_18'] != ORIGINAL_SCORES
                or len(report['rows']) != 27
                or report['pilot_gain'] is not False
                or report['comparative_step2_gate_promoted'] is not False
                or report['native_c2_control_proven'] is not False
                or report['redmi_measured'] is not False
                or report['learning_mode'] != 'RECORD_ONLY'
                or report['jepa_weight'] != 0):
            raise ValueError('ORIGINAL_REPORT_CHANGED')
        fixtures = {f['project']: f for f in report['fixtures']}
        rows = []
        for row in report['rows']:
            raw = json.loads(z.read('pilot/raw/' + row['raw_file']))
            if raw['event_id'] != row['event_id'] or raw['output'] != row['final_output']:
                raise ValueError('RAW_OUTPUT_NOT_BOUND')
            expr = equation_diagnostic(fixtures[row['fixture']], row['final_output'])
            lexical = row['score']['diagnostic']
            rows.append({'fixture': row['fixture'], 'arm': row['arm'],
                         'original_lexical': {k: lexical[k]['status'] for k in ('a', 'b')},
                         'expression': expr})
        return {
            'schema': 'v13.step2.expression_sensitivity.posthoc.v1',
            'original_zip_sha256': ORIGINAL_SHA256,
            'original_scores_out_of_18_unchanged': ORIGINAL_SCORES,
            'equation_correct_by_arm_not_a_new_score': {
                arm: sum(int(r['expression'][k]['correct']) for r in rows
                         if r['arm'] == arm for k in ('a', 'b'))
                for arm in ORIGINAL_SCORES},
            'lexical_missing_but_equation_correct': [
                {'fixture': r['fixture'], 'arm': r['arm'], 'option': k}
                for r in rows for k in ('a', 'b')
                if r['original_lexical'][k] == 'MISSING'
                and r['expression'][k]['correct']],
            'rows': rows, 'posthoc_only': True, 'native_run_performed': False,
            'step2_gate_promoted': False, 'native_c2_control_proven': False,
            'redmi_measured': False, 'jepa_weight': 0,
            'whole_system_complete': False,
        }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('original_zip', type=Path)
    p.add_argument('--out', type=Path)
    args = p.parse_args()
    report = json.dumps(audit_original_zip(args.original_zip), indent=2,
                        sort_keys=True, ensure_ascii=False) + '\n'
    if args.out:
        if args.out.exists():
            raise FileExistsError('FRESH_OUTPUT_REQUIRED')
        args.out.write_text(report)
    else:
        print(report, end='')


if __name__ == '__main__':
    main()