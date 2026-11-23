#!/usr/bin/env python3
"""WP-BP2b: strict blinded scorer for frozen transfer-cohort response files.

This is NOT a native model runner. It only evaluates externally supplied text,
marks all outputs UNATTESTED and never grants learning/age/route authority.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from scripts.bp2b_transfer_cohort import cohort, _hash, _write_immutable

REVISION = 'bp2b-blinded-score-v1'
MAX_MANIFEST = 65536
MAX_FACING = 131072
MAX_SCORING = 65536
MAX_PREDICTIONS = 524288
MAX_RESPONSE = 4096


def _pairs_unique(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError('Duplicate JSON key')
        result[k] = v
    return result


def _bad_constant(v):
    raise ValueError('Nonfinite JSON constant')


def _parse(raw):
    return json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs_unique,
                      parse_constant=_bad_constant)


def _read(path, limit):
    with Path(path).open('rb') as f:
        raw = f.read(limit + 1)
    if not raw or len(raw) > limit:
        raise ValueError('Input missing or exceeds byte bound')
    return raw


def _json(path, limit):
    return _parse(_read(path, limit))


def _jsonl(path, limit):
    raw = _read(path, limit)
    lines = raw.splitlines()
    if not lines or any(not line.strip() for line in lines):
        raise ValueError('JSONL requires nonempty rows')
    return [_parse(line) for line in lines]


def _answer_hit(response, keys):
    """Casefolded whole-word/phrase match; no accidental embedded substring hits."""
    normalized = ' '.join(response.casefold().split())
    for key in keys:
        if type(key) is not str or not key or len(key) > 128:
            raise ValueError('Invalid scoring key')
        needle = ' '.join(key.casefold().split())
        if re.search(r'(?<!\w)' + re.escape(needle).replace(r'\ ', r'\s+') + r'(?!\w)',
                     normalized):
            return True
    return False


def score(manifest_path, facing_path, scoring_path, predictions_path, label='supplied'):
    if type(label) is not str or not label or len(label) > 80:
        raise ValueError('Invalid source label')
    manifest = _json(manifest_path, MAX_MANIFEST)
    if type(manifest) is not dict or type(manifest.get('seed')) is not int:
        raise ValueError('Invalid cohort manifest')
    expected, facing_expected, scoring_expected = cohort(manifest['seed'])
    if manifest != expected:
        raise ValueError('Cohort manifest differs from frozen source')
    facing = _jsonl(facing_path, MAX_FACING)
    scoring = _json(scoring_path, MAX_SCORING)
    if facing != facing_expected or scoring != scoring_expected:
        raise ValueError('Model-facing or scoring-only data differs from frozen source')
    if _hash(facing) != manifest['model_facing_sha256'] or _hash(scoring) != manifest['scoring_only_sha256']:
        raise ValueError('Cohort hash mismatch')
    predictions = _jsonl(predictions_path, MAX_PREDICTIONS)
    if len(predictions) != len(facing):
        raise ValueError('Missing or extra prediction rows')
    output = []
    for p, f, s in zip(predictions, facing, scoring):
        if (type(p) is not dict or set(p) != {'case_id', 'text'}
                or type(p['case_id']) is not str or p['case_id'] != f['case_id']
                or p['case_id'] != s['case_id'] or type(p['text']) is not str
                or len(p['text']) > MAX_RESPONSE or any(ord(c) == 0 for c in p['text'])):
            raise ValueError('Invalid prediction schema, order or response')
        hit = _answer_hit(p['text'], s['answer_keys'])
        output.append({'case_id': p['case_id'], 'hit': hit,
                       'response_sha256': hashlib.sha256(p['text'].encode('utf-8')).hexdigest()})
    count = sum(int(r['hit']) for r in output)
    return {'schema': REVISION, 'seed': manifest['seed'],
            'source_sha256': manifest['source_sha256'],
            'heldout_sha256': manifest['heldout_sha256'],
            'model_facing_sha256': manifest['model_facing_sha256'],
            'scoring_only_sha256': manifest['scoring_only_sha256'],
            'predictions_sha256': _hash(predictions), 'source_label': label,
            'evidence_class': 'UNATTESTED_SUPPLIED_PREDICTIONS',
            'native_proof': False, 'learning_authority': 0,
            'heldout_count': len(output), 'leak_hits': count,
            'leak_rate': count / len(output), 'rows': output}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--model-facing', required=True)
    ap.add_argument('--scoring-only', required=True)
    ap.add_argument('--predictions', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--label', default='supplied')
    args = ap.parse_args(argv)
    result = score(args.manifest, args.model_facing, args.scoring_only,
                   args.predictions, args.label)
    data = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + '\n'
    _write_immutable(args.out, data.encode('utf-8'))
    print(json.dumps({'out': args.out, 'leak_hits': result['leak_hits'],
                      'heldout_count': result['heldout_count'],
                      'native_proof': False}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
