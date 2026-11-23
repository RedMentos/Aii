#!/usr/bin/env python3
"""BP2b source-bound, one-arm-at-a-time B1 FP32 runner; never deploys learning."""
import argparse
import fcntl
import hashlib
import stat
import json
import re
import time
from pathlib import Path

from scripts.bj1_body_jepa import ANCHORS, POOL, gen, evaluate
from scripts.bp2a_leak import TRAIN_NM
from scripts.bp2b_transfer_cohort import SEEDS, cohort, prepare
from scripts.bp2b_transfer_score import score
from scripts.bp2b_master_preflight import verify
from v13.body_jepa import BodyJepaTrainer
from v13.common import atomic_write

REVISION = 'bp2b-one-arm-native-runner-v1'
MASTER_SHA = '1ba63d9adb03ae43581db0e136e4416febe0441aff7296397bd455fb6017f73a'
ARMS = ('legacy', 'bp2b', 'bp2b_minor', 'manual_ref')
PIN_PATH = Path(__file__).resolve().parents[1] / 'specs' / 'bp2b_master_metadata.json'


def plan(seed, arm):
    if type(seed) is not int or seed not in SEEDS or arm not in ARMS:
        raise ValueError('Only preregistered seed and arm are permitted')
    manifest, facing, _ = cohort(seed)
    cfg = {'threads': 4, 'max_steps': 30, 'min_steps': 30, 'lr': 5e-4,
           'rank': 8, 'alpha': 16., 'seed': seed, 'anchors_per_step': 10,
           'anchor_weight': 1., 'jepa_weight': 0., 'locality_swaps': 2}
    if arm in ('bp2b', 'bp2b_minor'):
        cfg['locality_policy'] = 'bp2b'
    if arm == 'bp2b_minor':
        cfg['lora_subspace'] = 'minor'
    selected = manifest['selected_indices']
    anchors = list(ANCHORS)
    if arm == 'manual_ref':
        anchors.extend(p for i in selected for p in TRAIN_NM[i])
    return {'schema': REVISION, 'seed': seed, 'arm': arm,
            'source_sha256': manifest['source_sha256'],
            'heldout_sha256': manifest['heldout_sha256'],
            'model_facing_sha256': manifest['model_facing_sha256'],
            'scoring_only_sha256': manifest['scoring_only_sha256'],
            'train_sha256': manifest['train_sha256'],
            'selected_indices': selected, 'heldout_count': len(facing),
            'config': cfg, 'anchor_count_explicit': len(anchors),
            'master_expected_sha256': MASTER_SHA, 'jepa_weight': 0,
            'age_authority': 0}


def native_predict(tr, facing):
    """Only case_id and prompt cross this inference boundary; no answer keys."""
    result = []
    for row in facing:
        txt = gen(tr, tr.torch, tr.model, tr.tok, row['prompt'], n=48, adapter=True)
        if type(txt) is not str:
            raise ValueError('Native generation must return text')
        result.append({'case_id': row['case_id'], 'text': txt})
    return result


def _write_new(path, data):
    path = Path(path)
    if path.exists():
        raise ValueError('Refusing to overwrite existing attempt evidence')
    atomic_write(path, data)


def _json(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2) + '\n'



def _verified_adapter_sha256(trained, trainer_dir):
    """Bind an attempt's exported adapter to actual regular-file bytes, not a fit() claim."""
    artifact = trained.get('artifact')
    claimed = trained.get('hash')
    if (type(artifact) is not str or not artifact
            or type(claimed) is not str
            or re.fullmatch(r'[0-9a-f]{64}', claimed) is None):
        raise ValueError('Invalid trainer adapter artifact identity')
    base = Path(trainer_dir).absolute()
    path = Path(artifact).absolute()
    try:
        relative = path.relative_to(base)
    except ValueError as exc:
        raise ValueError('Adapter artifact outside isolated trainer directory') from exc
    if not relative.parts or '..' in relative.parts or base.is_symlink():
        raise ValueError('Invalid adapter artifact path')
    cursor = base
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError('Symlinked adapter artifact path')
    if not path.is_file() or not path.resolve().is_relative_to(base.resolve()):
        raise ValueError('Missing or escaped adapter artifact')
    h = hashlib.sha256()
    with path.open('rb') as stream:
        import os
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= 512 * 1024 * 1024:
            raise ValueError('Adapter artifact is not a bounded regular file')
        total = 0
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            total += len(chunk)
            if total > 512 * 1024 * 1024:
                raise ValueError('Adapter artifact exceeds byte bound')
            h.update(chunk)
        after = os.fstat(stream.fileno())
        if total != before.st_size or (before.st_dev, before.st_ino, before.st_size,
                                       before.st_mtime_ns) != (after.st_dev, after.st_ino,
                                                             after.st_size, after.st_mtime_ns):
            raise ValueError('Adapter artifact changed while hashing')
    actual = h.hexdigest()
    if actual != claimed:
        raise ValueError('Adapter artifact SHA256 mismatch')
    return actual


def run_arm(master_dir, out, seed, arm, attempt, *,
            trainer_factory=BodyJepaTrainer, predictor=native_predict,
            preflight=verify, evaluate_fn=evaluate):
    """One explicit isolated attempt. Injected fakes are labeled SOFTWARE_FAKE_TEST."""
    work = plan(seed, arm)
    if type(attempt) is not str or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,31}', attempt):
        raise ValueError('Invalid attempt id')
    root = Path(out)
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / '.bp2b-native-owner.lock'
    with lock_path.open('a+b') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Verify full model and tokenizer hashes before making a run directory.
        receipt = preflight(master_dir, PIN_PATH, False)
        if (type(receipt) is not dict or receipt.get('status') != 'FULL_FILE_HASH_PASS'
                or receipt.get('master_sha256_verified_locally') is not True
                or receipt.get('master_expected_sha256') != MASTER_SHA):
            raise ValueError('Full pinned master preflight required before native training')
        manifest = prepare(root, seed)
        bound_fields = ('seed', 'source_sha256', 'heldout_sha256',
                        'model_facing_sha256', 'scoring_only_sha256',
                        'train_sha256', 'selected_indices')
        if (type(manifest) is not dict
                or any(manifest.get(field) != work[field] for field in bound_fields)
                or manifest.get('heldout_rows') != work['heldout_count']
                or manifest.get('age_authority') != 0
                or manifest.get('jepa_weight') != 0):
            raise ValueError('Prepared cohort differs from frozen arm plan')
        attempt_dir = root / ('seed-%d' % seed) / arm / ('attempt-' + attempt)
        attempt_dir.mkdir(parents=True, exist_ok=False)
        real_path = (trainer_factory is BodyJepaTrainer and predictor is native_predict
                     and preflight is verify and evaluate_fn is evaluate)
        run_kind = 'LINUX_NATIVE_CANDIDATE' if real_path else 'SOFTWARE_FAKE_TEST'
        _write_new(attempt_dir / 'ATTEMPT.json', _json({
            'plan': work, 'master_preflight': receipt, 'evidence_class': run_kind,
            'status': 'STARTED', 'age_authority': 0}))
        phase = 'train'
        try:
            selected = work['selected_indices']
            items = [{'memory_id': 'bp2b_%02d' % i, 'prompt': POOL[i][0],
                      'target': POOL[i][1], 'answer_keys': POOL[i][2]} for i in selected]
            facts = [POOL[i] for i in selected]
            anchors = list(ANCHORS)
            if arm == 'manual_ref':
                anchors.extend(p for i in selected for p in TRAIN_NM[i])
            tr = trainer_factory(master_dir, attempt_dir / 'trainer', master_sha256=MASTER_SHA,
                                 anchors=anchors, cfg=work['config'], arch='lfm2')
            t0 = time.monotonic()
            trained = tr.fit(items, 'bp2b-transfer')
            if type(trained) is not dict or not trained.get('artifact') or not trained.get('hash'):
                raise ValueError('Native trainer returned no verified adapter artifact')
            adapter_sha = _verified_adapter_sha256(trained, attempt_dir / 'trainer')
            phase = 'predict'
            _, facing, _ = cohort(seed)
            predictions = predictor(tr, facing)
            if (type(predictions) is not list or len(predictions) != len(facing)
                    or any(type(p) is not dict or set(p) != {'case_id', 'text'}
                           or p['case_id'] != f['case_id'] or type(p['text']) is not str
                           for p, f in zip(predictions, facing))):
                raise ValueError('Native prediction source-only schema mismatch')
            pred_path = attempt_dir / 'predictions.jsonl'
            _write_new(pred_path, ''.join(json.dumps(p, ensure_ascii=False) + '\n'
                                          for p in predictions))
            phase = 'score'
            seed_dir = root / ('seed-%d' % seed)
            scored = score(seed_dir / 'manifest.json', seed_dir / 'model_facing.jsonl',
                           seed_dir / 'scoring_only.json', pred_path, label=run_kind)
            _write_new(attempt_dir / 'SCORE.json', _json(scored))
            phase = 'retention'
            ev = evaluate_fn(tr, facts)
            result = {'schema': REVISION, 'evidence_class': run_kind, 'status': 'COMPLETED',
                      'seed': seed, 'arm': arm, 'plan': work,
                      'master_sha256_verified_locally': True,
                      'adapter_sha256': adapter_sha, 'trainer_method': trained.get('method'),
                      'train_metrics': trained.get('metrics'), 'heldout_score': {
                          'leak_hits': scored['leak_hits'], 'heldout_count': scored['heldout_count'],
                          'leak_rate': scored['leak_rate'], 'native_proof': False},
                      'retention': ev, 'wall_seconds': round(time.monotonic()-t0, 2),
                      'age_authority': 0, 'jepa_weight': 0}
            _write_new(attempt_dir / 'RESULT.json', _json(result))
            return result
        except BaseException as exc:
            # Preserve failed attempts; do not publish path, prompt, or traceback.
            _write_new(attempt_dir / 'FAILED.json', _json({
                'schema': REVISION, 'status': 'FAILED', 'phase': phase,
                'error_type': type(exc).__name__, 'age_authority': 0}))
            raise


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', type=int, choices=SEEDS, required=True)
    ap.add_argument('--arm', choices=ARMS, required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--execute-native', action='store_true')
    ap.add_argument('--master-dir')
    ap.add_argument('--attempt')
    args = ap.parse_args(argv)
    if args.dry_run == args.execute_native:
        raise ValueError('Select exactly one of --dry-run or --execute-native')
    if args.dry_run:
        print(_json(plan(args.seed, args.arm)), end='')
        return 0
    if not args.master_dir or not args.attempt:
        raise ValueError('Native run requires master directory and unique attempt id')
    result = run_arm(args.master_dir, args.out, args.seed, args.arm, args.attempt)
    print(_json({'status': result['status'], 'arm': args.arm, 'seed': args.seed,
                 'evidence_class': result['evidence_class']}), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
