"""Run618 prospective source-disjoint B2-only native semantic retrieval proxy.

Original public pinned B2 weights/runner read-only. No B1, Body-JEPA, receiver
injection, Redmi, automatic memory promotion, or whole-system gate promotion.
"""
import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

import numpy as np

from v13.common import APP, atomic_write, dumps
from v13.runners import TAP_SPECS
from scripts.run617_gist_native_replay import git_blob_sha, replay_case

COHORT = APP / 'docs/proofs/continuation-20261026/run618-prospective-b2-native/RUN618_COHORT.json'
COHORT_BLOB = '00f95e65b01bacb5376b849f43674d88a00c1311'
COHORT_SHA = 'd9e6f89261955fbcf04422a22d33f6734c41f0df1bc95b104f5712191d13a9b3'
SEED = 2026102618
TRAIN = ('acoustics', 'botany', 'meteorology', 'archaeology', 'robotics', 'textiles')
TEST = ('optics', 'linguistics')
MODEL_SHA = '57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf'
MODEL_REV = '8fea620810c4afa23dd6443f999a48574c1611a3'
TAP_ID = 'qwen35.result_norm.final.v1'
GATES = {'STEP2': 'UTILITY_FAIL', 'B3_L1': 'FAIL', 'Body_JEPA': 'UNAVAILABLE',
         'jepa_weight': 0, 'Redmi': 'UNMEASURED', 'V13': 'INCOMPLETE'}


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def load_cohort(path=COHORT):
    path = Path(path)
    if git_blob_sha(path) != COHORT_BLOB or sha(path) != COHORT_SHA:
        raise ValueError('Run618 preregistered cohort changed')
    obj = json.loads(path.read_text())
    rows = obj.get('prompts', [])
    if (obj.get('schema') != 'V13_RUN618_PROSPECTIVE_B2_PARAPHRASE_COHORT_V1' or
        obj.get('seed') != SEED or tuple(obj.get('train_topics', [])) != TRAIN or
        tuple(obj.get('test_topics', [])) != TEST or len(rows) != 80 or
        len({r['id'] for r in rows}) != 80 or len({r['text'] for r in rows}) != 80):
        raise ValueError('Run618 cohort schema/seed/unique rows changed')
    for i, r in enumerate(rows):
        topic = r['topic']
        if (topic not in TRAIN + TEST or r['variant'] not in ('A', 'B') or
            r['id'] != f'{topic}-{(i // 2) % 5 + 1}-{r["variant"]}' or
            r['fact_id'] != r['id'][:-2] or not r['text'].strip()):
            raise ValueError('Run618 malformed pair')
    if (any(rows[i]['variant'] != 'A' or rows[i+1]['variant'] != 'B' or
            rows[i]['fact_id'] != rows[i+1]['fact_id'] for i in range(0, 80, 2)) or
        any(sum(r['topic'] == topic for r in rows) != 10 for topic in TRAIN + TEST)):
        raise ValueError('Run618 paired source/topic imbalance')
    return rows


def unit(v):
    v = np.asarray(v, dtype=float)
    norm = np.linalg.norm(v, axis=1, keepdims=True)
    if not np.isfinite(v).all() or not np.isfinite(norm).all() or (norm < 1e-10).any():
        raise ValueError('Nonfinite/zero native states')
    return v / norm


def ranking(matrix, opposite):
    m = np.asarray(matrix, dtype=float)
    if m.shape != (len(opposite), len(opposite)) or not np.isfinite(m).all():
        raise ValueError('Invalid score matrix')
    ranks = []
    for i, target in enumerate(opposite):
        order = sorted((j for j in range(len(opposite)) if j != i), key=lambda j: (-float(m[i, j]), j))
        ranks.append(order.index(target) + 1)
    return {'top1': sum(k == 1 for k in ranks) / len(ranks),
            'mrr': sum(1. / k for k in ranks) / len(ranks)}


def evaluate(rows, states, controls=200):
    y = np.asarray(states, dtype=float)
    if y.shape != (80, 1024) or controls != 200:
        raise ValueError('Run618 native B2 state shape/controls changed')
    train = [i for i, r in enumerate(rows) if r['topic'] in TRAIN]
    test = [i for i, r in enumerate(rows) if r['topic'] in TEST]
    if len(train) != 60 or len(test) != 20:
        raise ValueError('Run618 train/test split changed')
    ids = [rows[i]['id'] for i in test]
    opposite = [ids.index(rows[i]['fact_id'] + ('-B' if rows[i]['variant'] == 'A' else '-A')) for i in test]
    norm = unit(y)
    raw = norm[test] @ norm[test].T
    centered = unit(norm[test] - norm[train].mean(0))
    center = centered @ centered.T
    sets = [set(re.findall(r'[a-z0-9]+', rows[i]['text'].lower())) for i in test]
    lexical = np.asarray([[len(a & b) / len(a | b) if a | b else 0. for b in sets] for a in sets])
    metrics = {'b2_raw': ranking(raw, opposite), 'b2_centered': ranking(center, opposite),
               'lexical': ranking(lexical, opposite)}
    rng = np.random.default_rng(SEED + 1)
    null = []
    for _ in range(controls):
        while True:
            perm = rng.permutation(len(test))
            shuffled = [int(perm[j]) for j in opposite]
            if all(shuffled[i] != i for i in range(len(test))):
                break
        null.append(ranking(raw, shuffled)['top1'])
    p = (1 + sum(v >= metrics['b2_raw']['top1'] for v in null)) / (controls + 1)
    cases = [replay_case(rows, y, test, i) for i in test]
    replay_top1 = sum(c['opposite_rank_top5'] == 1 for c in cases) / len(cases)
    replay_mrr5 = sum(1. / c['opposite_rank_top5'] if c['opposite_rank_top5'] else 0 for c in cases) / len(cases)
    mismatches = sum(not c['matched_raw_cosine_top5'] for c in cases)
    proxy = (metrics['b2_raw']['top1'] >= .55 and
             metrics['b2_raw']['top1'] - metrics['lexical']['top1'] >= .15 - 1e-12 and
             p <= .05 and mismatches == 0 and abs(replay_top1 - metrics['b2_raw']['top1']) < 1e-12)
    return {'metrics': metrics, 'empirical_p_b2_raw': p, 'null_b2_raw_mean': float(np.mean(null)),
            'controls': controls, 'train_n': 60, 'test_n': 20, 'seed': SEED,
            'replay_queries': len(cases), 'replay_top5_order_mismatches': mismatches,
            'replay_operator_top1': replay_top1, 'replay_operator_mrr_at5': replay_mrr5,
            'scoped_b2_proxy': bool(proxy), 'cases': cases}


def run(home, out, states_path):
    from scripts import run606_cross_body_latent_shadow as R606
    home, out, states_path = Path(home), Path(out), Path(states_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    states_path.parent.mkdir(parents=True, exist_ok=True)
    report = {'schema': 'V13_RUN618_PROSPECTIVE_B2_NATIVE_V1', 'status': 'INCOMPLETE',
              'evidence_level': 'LINUX_NATIVE_B2_READONLY_AND_SQLITE_REPLAY',
              'cohort_blob': COHORT_BLOB, 'seed': SEED, 'gates': GATES,
              'no_weight_updates': True, 'can_latent_inject': False,
              'b3_promoted': False, 'redmi_measured': False,
              'canonical_architecture_complete': False, 'user_full_scope_complete': False}
    def save():
        atomic_write(out, (dumps(report) + '\n').encode())
    save()
    try:
        rows = load_cohort()
        specs = json.loads((APP / 'specs/models.json').read_text())
        if specs['runner']['linux_binaries']['linux-x86_64']['sha256'] != R606.ARCHIVE_SHA:
            raise ValueError('Original native runner archive pin changed')
        server = home / 'bin/llama-server'
        if not server.is_file():
            raise ValueError('Original native server missing')
        report['runner_sha256'] = R606.file_sha(server)
        spec = specs['models']['gist']
        model = home / 'models' / 'gist' / spec['main_file']
        if (R606.file_sha(model) != MODEL_SHA or spec['files'][0]['sha256'] != MODEL_SHA or
            spec['revision'] != MODEL_REV or TAP_SPECS['gist'] != (TAP_ID, 1024)):
            raise ValueError('Original pinned B2 native model/tap changed')
        with tempfile.TemporaryDirectory(prefix='v13-run618-') as td:
            y, receipts = R606.capture(model, server, 'B2_GIST', 'gist', rows, Path(td) / 'gist')
        report['model'] = {'model_id': spec['model_id'], 'revision': MODEL_REV,
                           'sha256': MODEL_SHA, 'tap_id': TAP_ID, 'dimension': 1024, 'rows': len(y)}
        report['receipts'] = receipts
        save()
        if len(receipts) != 80 or any(rec['id'] != row['id'] or rec['prompt_sha256'] != hashlib.sha256(row['text'].encode()).hexdigest() for rec, row in zip(receipts, rows)):
            raise ValueError('Native B2 source receipt mismatch')
        with tempfile.NamedTemporaryFile(dir=states_path.parent, suffix='.npz', delete=False) as f:
            tmp = Path(f.name)
            np.savez_compressed(f, y_b2=y, prompt_ids=np.asarray([r['id'] for r in rows]),
                                train_idx=np.asarray([i for i, r in enumerate(rows) if r['topic'] in TRAIN]),
                                test_idx=np.asarray([i for i, r in enumerate(rows) if r['topic'] in TEST]))
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, states_path)
        result = evaluate(rows, y)
        report.update(result, states_sha256=sha(states_path), states_bytes=states_path.stat().st_size,
                      status='SCOPED_B2_PROXY' if result['scoped_b2_proxy'] else 'NO_SCOPED_B2_GAIN')
        save()
        return report
    except BaseException as exc:
        report.update(status='ERROR', error_type=type(exc).__name__, error=str(exc)[:300])
        save()
        raise


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--home', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--states', required=True)
    args = p.parse_args()
    result = run(args.home, args.out, args.states)
    print(dumps({'status': result['status'], 'metrics': result['metrics'],
                 'replay_top1': result['replay_operator_top1'],
                 'states_sha256': result['states_sha256']}))


if __name__ == '__main__':
    main()
