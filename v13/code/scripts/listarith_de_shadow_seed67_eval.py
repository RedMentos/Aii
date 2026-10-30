"""One-shot frozen seed67 German list_arith SHADOW holdout evaluation.

No model, tool execution, production wiring, learning or gate promotion.
Do not overwrite original holdout output or retune after evaluation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v13.agi import listarith, listarith_de_shadow

FIXTURE_SHA256 = '468b231fd196f28e773fba1d541f4ed7c7436d180d78b835e0ad3eb3f85a3d05'
SCHEMA = 'v13.listarith.de_shadow.seed67.holdout.v1'
ENGLISH = (
    ('Items: A 12, B 30. What is the total?', 'total'),
    ('Items: A 12, B 30. What is the sum?', 'total'),
    ('Items: A 12, B 30. How much more is the largest than the smallest?', 'difference_max_min'),
    ('Items: A 12, B 30. How much less is the smallest than the largest?', 'difference_max_min'),
    ('Items: A 12, B 30. How many total number of entries?', None),
    ('Items: A 12, B 30. What is the average?', None),
    ('Items: A 12, B 30. Add them up.', 'total'),
    ('Items: A 12, B 30. What is the gap between them?', 'difference_max_min'),
)


def canonical_hash(rows):
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def validate_fixture(rows):
    if not isinstance(rows, list) or len(rows) != 48 or canonical_hash(rows) != FIXTURE_SHA256:
        raise ValueError('FIXTURE_PIN_CHANGED')
    ids = [r['id'] for r in rows]
    if len(set(ids)) != 48 or sum(r['split']=='holdout' for r in rows) != 24:
        raise ValueError('HOLDOUT_IDENTITY_CHANGED')
    for label in ('total', 'difference_max_min', None):
        if sum(r['split']=='holdout' and r['expected'] == label for r in rows) != 8:
            raise ValueError('HOLDOUT_BALANCE_CHANGED')
    return True


def decision(correct, false_positive_none, english_ok):
    if not (type(correct) is int and 0 <= correct <= 24 and
            type(false_positive_none) is int and 0 <= false_positive_none <= 8 and
            type(english_ok) is int and 0 <= english_ok <= 8):
        raise ValueError('INVALID_METRIC')
    return ('SHADOW_DE_SUPPORTED' if correct >= 20 and false_positive_none == 0 and english_ok == 8
            else 'SHADOW_DE_NOT_SUPPORTED')


def evaluate(fixture, out):
    fixture, out = Path(fixture).resolve(), Path(out).resolve()
    if out.exists():
        raise FileExistsError('FRESH_HOLDOUT_OUTPUT_REQUIRED')
    rows = json.loads(fixture.read_text())
    validate_fixture(rows)
    out.mkdir(parents=True)
    report = {'schema': SCHEMA, 'fixture_sha256': FIXTURE_SHA256,
              'source_sha256': hashlib.sha256(Path(listarith_de_shadow.__file__).read_bytes()).hexdigest(),
              'status': 'INCOMPLETE', 'holdout_rows': 24, 'correct': 0,
              'false_positive_none': 0, 'english_regressions_pass': 0,
              'authority': 'SHADOW_ONLY', 'live_consumers': 0,
              'native_model_inference': False, 'redmi_measured': False,
              'step2_gate_promoted': False, 'b3_promoted': False,
              'body_jepa_available': False, 'jepa_weight': 0,
              'whole_system_complete': False}
    results = []
    try:
        for row in rows:
            if row['split'] != 'holdout':
                continue
            result = listarith_de_shadow.propose(row['text'])
            if result['authority'] != 'SHADOW_ONLY' or result['proposal'] not in (None, 'total', 'difference_max_min'):
                raise ValueError('SHADOW_AUTHORITY_OR_SCHEMA_CHANGED')
            ok = result['proposal'] == row['expected']
            report['correct'] += int(ok)
            if row['expected'] is None and result['proposal'] is not None:
                report['false_positive_none'] += 1
            results.append({'id': row['id'], 'split': 'holdout', 'expected': row['expected'],
                            'proposal': result['proposal'], 'reason': result['reason'],
                            'authority': result['authority'], 'correct': ok, 'source_text': row['text']})
        if len(results) != 24:
            raise ValueError('HOLDOUT_ROW_COUNT_CHANGED')
        report['english_regressions_pass'] = sum(listarith.operation(text) == want for text, want in ENGLISH)
        report['status'] = decision(report['correct'], report['false_positive_none'],
                                    report['english_regressions_pass'])
    except BaseException as exc:
        report.update(status='EVALUATION_RED', error_type=type(exc).__name__, error=str(exc)[:300])
    finally:
        (out/'holdout_rows.json').write_text(json.dumps(results, indent=2, ensure_ascii=False, sort_keys=True)+'\n')
        (out/'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)+'\n')
        names = ('holdout_rows.json', 'report.json')
        (out/'SHA256SUMS').write_text(''.join(hashlib.sha256((out/n).read_bytes()).hexdigest()+'  ./'+n+'\n'
                                           for n in names))
    print(json.dumps({'status': report['status'], 'correct': report['correct'],
                      'false_positive_none': report['false_positive_none'],
                      'english_regressions_pass': report['english_regressions_pass']}, sort_keys=True))
    return report['status'] != 'EVALUATION_RED'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixture', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    return 0 if evaluate(a.fixture, a.out) else 2


if __name__ == '__main__':
    raise SystemExit(main())