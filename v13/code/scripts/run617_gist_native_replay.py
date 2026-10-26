"""Run617: source-bound SQLite/operator REPLAY of original Run614 B2 states.

NO new native inference, no model weights or runtime authority. Mocked tap runner
only replays original SHA-closed Linux-native vectors in ephemeral temporary DBs.
"""
import argparse
import hashlib
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from v13.runtime import Runtime
from v13.operator import Operator
from scripts.run615_crosscohort_shadow import load as load_native, GATES, PINS

COHORT_BLOB = '7068267d41a1719abea3a54c84b1d0223444df1d'
REV = '8fea620810c4afa23dd6443f999a48574c1611a3'
TAP_ID = 'qwen35.result_norm.final.v1'


def git_blob_sha(path):
    raw = Path(path).read_bytes()
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def cohort_rows(path):
    if git_blob_sha(path) != COHORT_BLOB:
        raise ValueError('Original frozen Run614 cohort Git blob changed')
    obj = json.loads(Path(path).read_text())
    rows = obj['prompts']
    if (obj.get('schema') != 'V13_RUN614_INDEPENDENT_PARAPHRASE_COHORT_V1' or
        obj.get('seed') != 2026102614 or len(rows) != 80 or
        sum(r['topic'] in ('literature', 'geography') for r in rows) != 20):
        raise ValueError('Original frozen Run614 cohort shape/seed changed')
    return rows


def validate_receipts(rows, ids, report):
    receipts = report['receipts']['B2_GIST']
    if len(receipts) != 80 or len(rows) != len(ids):
        raise ValueError('Original native receipts count changed')
    for i, (row, rid, receipt) in enumerate(zip(rows, ids, receipts)):
        if (row['id'] != rid or receipt['id'] != rid or
            receipt['prompt_sha256'] != hashlib.sha256(row['text'].encode()).hexdigest() or
            receipt['tap_id'] != TAP_ID or receipt['dimension'] != 1024 or
            receipt['token_count'] < 1):
            raise ValueError('Original native source/receipt mismatch at row %d' % i)
    if (report['models']['B2_GIST']['revision'] != REV or
        report['models']['B2_GIST']['sha256'] != '57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf' or
        report['gates'] != GATES or report['can_latent_inject'] is not False):
        raise ValueError('Original native model/gates/authority changed')


def rank_raw(states, query, candidates):
    q = np.asarray(states[query], dtype=float)
    c = np.asarray(states[candidates], dtype=float)
    if not np.isfinite(q).all() or not np.isfinite(c).all():
        raise ValueError('Nonfinite native state')
    q = q / np.linalg.norm(q)
    c = c / np.linalg.norm(c, axis=1, keepdims=True)
    scores = c @ q
    # Candidate rows are inserted in ascending original order; newer wins exact ties.
    return sorted(range(len(candidates)), key=lambda i: (-float(scores[i]), -i))


def replay_case(rows, states, test_indices, query_idx):
    candidates = [int(i) for i in test_indices if int(i) != query_idx]
    ordering = rank_raw(states, query_idx, candidates)
    with tempfile.TemporaryDirectory(prefix='run617-b2-replay-') as td:
        r = Runtime(Path(td))
        try:
            r.sleep.cycle.set_policy('enabled', 'off')
            runner = MagicMock()
            runner.tap_id = TAP_ID
            runner.tap_dim = 1024
            lookup = {row['text']: np.asarray(states[i], dtype=float).tolist() for i, row in enumerate(rows)}
            runner.tap.side_effect = lambda text, cancel, deadline: {
                'token_ids': [13], 'vectors': [lookup[text]], 'metrics': {}}
            stored = {}
            with patch.object(r.pool, 'get_tap', return_value=runner), \
                 patch.object(r.models, 'revision', return_value=REV), \
                 patch.object(r.learner, 'predict_states', return_value=None):
                for idx in candidates + [query_idx]:
                    event = r.store.event(r.session, rows[idx]['text'])
                    stored[idx] = r.cognition.tap('B2_GIST', event, event['source_ref'], time.monotonic()+30)
                result = json.loads(Operator(r).run(':gist similar 5'))
            if result['status'] != 'READ_ONLY' or result['receiver_injection_authority'] != 0 or result['body_learning_authority'] != 0:
                raise ValueError('Replay gained authority')
            if result['query_packet_id'] != stored[query_idx]['packet_id'] or len(result['matches']) != 5:
                raise ValueError('Replay query or match count mismatch')
            expected = [candidates[i] for i in ordering[:5]]
            actual = []
            for item in result['matches']:
                idx = next((i for i in candidates if stored[i]['packet_id'] == item['packet_id']), None)
                if idx is None or item['source_ref'] != stored[idx]['source_ref'] or item['excerpt'] != rows[idx]['text'][:160]:
                    raise ValueError('Replay source or packet mismatch')
                actual.append(idx)
            if actual != expected:
                raise ValueError('Operator/raw native cosine top-five ordering mismatch')
            if 'feature_path' in json.dumps(result) or 'vectors' in json.dumps(result):
                raise ValueError('Replay leaked native feature path/vector')
            opposite_id = rows[query_idx]['fact_id'] + ('-B' if rows[query_idx]['variant'] == 'A' else '-A')
            target = next(i for i in candidates if rows[i]['id'] == opposite_id)
            rank_full = [candidates[i] for i in ordering].index(target) + 1
            rank5 = actual.index(target) + 1 if target in actual else None
            return {'query_id': rows[query_idx]['id'], 'target_id': rows[target]['id'],
                    'operator_top5_ids': [rows[i]['id'] for i in actual],
                    'opposite_rank_full': rank_full, 'opposite_rank_top5': rank5,
                    'matched_raw_cosine_top5': True}
        finally:
            r.close()


def run(cohort_path, native_folder):
    x, y, ids, train, test = load_native(native_folder, '614')
    rows = cohort_rows(cohort_path)
    report = json.loads((Path(native_folder) / 'RUN614_NATIVE_REPORT.json').read_text())
    validate_receipts(rows, ids, report)
    if len(test) != 20 or any(rows[i]['topic'] not in ('literature', 'geography') for i in test):
        raise ValueError('Original heldout topics changed')
    cases = [replay_case(rows, y, test, int(i)) for i in test]
    top1 = sum(c['opposite_rank_top5'] == 1 for c in cases) / len(cases)
    mrr5 = sum(1. / c['opposite_rank_top5'] if c['opposite_rank_top5'] else 0 for c in cases) / len(cases)
    mrr19 = sum(1. / c['opposite_rank_full'] for c in cases) / len(cases)
    return {'schema': 'V13_RUN617_RECORDED_NATIVE_OPERATOR_REPLAY_V1',
            'status': 'REPLAY_INTEGRATION_PASS' if len(cases) == 20 else 'REPLAY_INCOMPLETE',
            'evidence_level': 'LINUX_SQLITE_REPLAY_OF_PRIOR_NATIVE_READONLY_STATES',
            'native_inference_new': False, 'native_body_training': False, 'receiver_injection': False,
            'cohort_git_blob': COHORT_BLOB, 'states_sha256': PINS['614']['states'],
            'model_revision': REV, 'tap_id': TAP_ID, 'queries': len(cases),
            'operator_raw_cosine_top5_mismatches': sum(not c['matched_raw_cosine_top5'] for c in cases),
            'metrics': {'operator_top1': top1, 'operator_mrr_at5': mrr5, 'independent_raw_mrr_at19': mrr19},
            'original_run614_train_centered_b2_only_top1': .85,
            'not_comparable_to_centered_baseline': True, 'cases': cases,
            'gates': GATES, 'canonical_architecture_complete': False, 'user_full_scope_complete': False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--cohort', required=True)
    p.add_argument('--native', required=True)
    p.add_argument('--out', required=True)
    args = p.parse_args()
    result = run(args.cohort, args.native)
    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(result['status'], result['metrics'])


if __name__ == '__main__':
    main()
