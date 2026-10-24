#!/usr/bin/env python3
"""Read-only LP3 evidence verifier. Structural checks are not native proof.

A receipt SHA is only an authenticity anchor if published independently of the
attempt. An attacker able to rewrite the attempt and the anchor can forge both.
"""
import argparse
import ast
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

SEEDS = (31, 37, 41, 43)
ARMS = ('raw', 'predicted', 'wrong_trained', 'value_shift', 'zero_intervention')
PINNED_WEIGHT = '1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e'
PARAMS = {'seeds': list(SEEDS), 'steps': 30, 'temperature': 0.1, 'lr': 0.001,
          'items': 16, 'holdout': 48, 'min_similarity': 0.35, 'min_margin': 0.03}

class EvidenceError(ValueError):
    pass


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def safe_file(path):
    if path.is_symlink() or not path.is_file():
        raise EvidenceError(f'missing/nonregular evidence: {path.name}')
    return path


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def read_json(path):
    try:
        return json.loads(safe_file(path).read_text(encoding='utf-8'),
                          object_pairs_hook=unique_pairs,
                          parse_constant=lambda x: (_ for _ in ()).throw(EvidenceError(f'nonfinite JSON: {x}')))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f'invalid JSON: {path.name}') from exc


def literal_assignment(path, name):
    """Read frozen literal fixtures without importing or executing project code."""
    tree = ast.parse(safe_file(Path(path)).read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            try:
                return ast.literal_eval(node.value)
            except (ValueError, TypeError, SyntaxError) as exc:
                raise EvidenceError(f'nonliteral fixture: {name}') from exc
    raise EvidenceError(f'missing literal fixture: {name}')


def receipt_for(run):
    names = ['run_manifest.json', 'report.json'] + [f'seed-{s}.json' for s in SEEDS]
    return {'schema': 'V13_LP3_CLOSED_RECEIPT_V1',
            'sha256': {name: digest(safe_file(run / name)) for name in names}}


def verdict(rows):
    gains = [r['predicted']['correct'] - r['raw']['correct'] for r in rows]
    control = [r['predicted']['correct'] - max(r['wrong_trained']['correct'],
                                              r['value_shift']['correct']) for r in rows]
    leakage = [r['near_pred_nonabstain'] - r['near_raw_nonabstain'] for r in rows]
    if sum(x >= 4 for x in gains) >= 3 and sum(x >= 8 for x in control) >= 3 and max(leakage) <= 2:
        return 'LP3_MEMORY_KEY_CANDIDATE_SUPPORTED_ONLY'
    return 'LP3_MEMORY_KEY_NOT_SUPPORTED'


def audit(run, *, source=None, lp2=None, lora=None, receipt=None, receipt_sha256=None):
    run = Path(run)
    if not run.is_dir() or run.is_symlink():
        raise EvidenceError('attempt directory missing or symlinked')
    if any(run.glob('failed-seed-*.json')):
        raise EvidenceError('failed seed marker present; cohort not closed')
    manifest = read_json(run / 'run_manifest.json')
    report = read_json(run / 'report.json')
    if manifest.get('schema') != 'V13_LP3_MEMORY_KEY_V1' or manifest.get('params') != PARAMS:
        raise EvidenceError('manifest schema/protocol mismatch')
    if manifest.get('master_sha256') != PINNED_WEIGHT:
        raise EvidenceError('unpinned master')
    if manifest.get('runtime_enabled') is not False or manifest.get('phone_measured') is not False:
        raise EvidenceError('unexpected runtime/phone evidence claim')
    if manifest.get('body_jepa_gate_pass') is not False or manifest.get('step2_gate_pass') is not False:
        raise EvidenceError('unexpected gate promotion')
    binding = manifest.get('snapshot_binding', {})
    if (binding.get('assets_sha256', {}).get('model.safetensors') != PINNED_WEIGHT
            or binding.get('revision') != '55e5a53e8637c4522a0577040fe68682db3fbbb6'):
        raise EvidenceError('snapshot binding mismatch')
    for path, expected in ((source, manifest.get('script_sha256')),
                           (lp2, manifest.get('lp2_fixture_sha256')),
                           (lora, binding.get('fixture_dependencies_sha256', {}).get('lora_bench.py'))):
        if path is not None and digest(safe_file(Path(path))) != expected:
            raise EvidenceError(f'local source hash mismatch: {Path(path).name}')
    fixture_expected = None
    if source is not None and lp2 is not None and lora is not None:
        facts = list(literal_assignment(lora, 'FACTS')) + list(literal_assignment(lp2, 'FACTS_V2'))
        tasks = list(literal_assignment(lp2, 'HELDOUT')) + list(literal_assignment(source, 'HARDER'))
        if len(facts) != 16 or len(tasks) != 48:
            raise EvidenceError('fixture count mismatch')
        fixture_expected = [facts[i][1] for i, _ in tasks]
    if {k: v for k, v in report.items() if k not in ('rows', 'verdict')} != manifest:
        raise EvidenceError('report/manifest binding mismatch')
    rows = report.get('rows')
    if not isinstance(rows, list) or len(rows) != len(SEEDS):
        raise EvidenceError('missing or extra rows')
    if [r.get('seed') for r in rows] != list(SEEDS):
        raise EvidenceError('wrong seed ordering or duplicate')
    for row, seed in zip(rows, SEEDS):
        if read_json(run / f'seed-{seed}.json') != row:
            raise EvidenceError(f'seed-{seed} differs from report')
        expected = row.get('expected')
        if not isinstance(expected, list) or len(expected) != 48:
            raise EvidenceError('expected labels missing')
        if fixture_expected is not None and expected != fixture_expected:
            raise EvidenceError('expected answers differ from source fixtures')
        counts = Counter(expected)
        if len(counts) != 16 or set(counts.values()) != {3} or any(not isinstance(x, str) or not x for x in counts):
            raise EvidenceError('unexpected label cohort')
        if expected[:32:2] != expected[1:32:2] or expected[32:] != expected[:32:2]:
            raise EvidenceError('LP2 heldout/HARDER fixture ordering mismatch')
        outputs = row.get('outputs', {})
        if set(outputs) != set(ARMS):
            raise EvidenceError('arm set mismatch')
        for arm in ARMS:
            actual = outputs[arm]
            if not isinstance(actual, list) or len(actual) != 48:
                raise EvidenceError(f'{arm}: missing predictions')
            if any(v is not None and v not in counts for v in actual):
                raise EvidenceError(f'{arm}: out-of-bank answer')
            calculated = {'correct': sum(a == b for a, b in zip(expected, actual)),
                          'abstain': sum(x is None for x in actual), 'total': 48}
            if row.get(arm) != calculated:
                raise EvidenceError(f'{arm}: aggregate mismatch')
        if any(x is not None for x in outputs['zero_intervention']):
            raise EvidenceError('zero intervention did not abstain')
        near = row.get('near_outputs', {})
        if set(near) != {'raw', 'predicted'}:
            raise EvidenceError('near-miss arms missing')
        if not all(isinstance(near[k], list) and len(near[k]) == 13 for k in near):
            raise EvidenceError('near-miss predictions missing')
        if len(near['raw']) != len(near['predicted']):
            raise EvidenceError('near-miss lengths differ')
        for arm, key in (('raw', 'near_raw_nonabstain'), ('predicted', 'near_pred_nonabstain')):
            if any(x is not None and x not in counts for x in near[arm]):
                raise EvidenceError('near-miss out-of-bank answer')
            if row.get(key) != sum(x is not None for x in near[arm]):
                raise EvidenceError('near-miss aggregate mismatch')
        for key in ('good_loss', 'wrong_loss'):
            value = row.get(key, {})
            if (not isinstance(value, dict) or value.get('steps') != 30 or
                any(not isinstance(value.get(k), (int, float)) or
                    not math.isfinite(value[k]) for k in ('initial_nce', 'final_nce'))):
                raise EvidenceError('missing/nonfinite training loss')
    decision = verdict(rows)
    if report.get('verdict') != decision:
        raise EvidenceError('report verdict does not match rows')
    anchor = 'UNANCHORED_STRUCTURAL_ONLY'
    if receipt is not None or receipt_sha256 is not None:
        if not receipt or not receipt_sha256:
            raise EvidenceError('receipt and independently published SHA required together')
        rp = Path(receipt)
        if digest(safe_file(rp)) != receipt_sha256:
            raise EvidenceError('receipt external SHA mismatch')
        if read_json(rp) != receipt_for(run):
            raise EvidenceError('receipt file hash mismatch')
        anchor = 'RECEIPT_SHA_MATCHES_SUPPLIED_ANCHOR'
    return {'audit': 'STRUCTURAL_PASS', 'evidence': 'LINUX_FILES_ONLY_NOT_NATIVE_REPRODUCTION',
            'anchor': anchor, 'local_source_fixture_consistent': fixture_expected is not None,
            'reported_verdict': decision, 'seeds': list(SEEDS),
            'original_gates': {'step2': 'UTILITY_FAIL', 'b3_l1': 'FAIL', 'body_jepa': 'UNAVAILABLE'}}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--source', type=Path)
    p.add_argument('--lp2', type=Path)
    p.add_argument('--lora', type=Path)
    p.add_argument('--receipt', type=Path)
    p.add_argument('--receipt-sha256')
    p.add_argument('--make-receipt', type=Path, help='write receipt OUTSIDE attempt; publish SHA independently')
    a = p.parse_args()
    try:
        result = audit(a.run, source=a.source, lp2=a.lp2, lora=a.lora,
                       receipt=a.receipt, receipt_sha256=a.receipt_sha256)
        if a.make_receipt:
            data = (json.dumps(receipt_for(a.run), sort_keys=True, indent=2) + '\n').encode()
            with a.make_receipt.open('xb') as f:
                f.write(data); f.flush()
                import os
                os.fsync(f.fileno())
            fd = os.open(a.make_receipt.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
            try: os.fsync(fd)
            finally: os.close(fd)
            result['new_receipt_sha256'] = digest(a.make_receipt)
        print(json.dumps(result, sort_keys=True))
    except (EvidenceError, OSError, KeyError, TypeError) as exc:
        p.exit(2, f'LP3_EVIDENCE_INVALID: {exc}\n')

if __name__ == '__main__':
    main()