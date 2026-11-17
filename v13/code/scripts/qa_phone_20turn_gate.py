#!/usr/bin/env python3
"""Conservative V13 receipt-metadata QA. No network, device control, or phone attestation."""
import argparse
import json
import math
import statistics
from pathlib import Path

REQUIRED = {'greeting', 'simple_math', 'nontrivial', 'ambiguity', 'memory_recall', 'body_cooperation'}

def evaluate(payload):
    failures = []
    if not isinstance(payload, dict):
        return {'status': 'BLOCKED', 'failures': ['invalid payload']}
    turns = payload.get('turns')
    if not isinstance(turns, list) or len(turns) < 20:
        return {'status': 'BLOCKED', 'failures': ['at least 20 correlated phone turns required']}
    if payload.get('evidence_origin') != 'owner_consented_redmi_receipt':
        failures.append('no owner-consented real-device receipt label')
    sha = payload.get('installed_sha')
    if not isinstance(sha, str) or len(sha) != 40 or any(c not in '0123456789abcdef' for c in sha):
        failures.append('installed full commit SHA missing')
    ids = set()
    classes = set()
    latencies = []
    ttfts = []
    for i, turn in enumerate(turns):
        if not isinstance(turn, dict):
            failures.append(f'turn {i}: malformed')
            continue
        ident = turn.get('correlation_id')
        if not isinstance(ident, str) or not ident or ident in ids:
            failures.append(f'turn {i}: missing or duplicate correlation')
        ids.add(ident)
        task_class = turn.get('class')
        if not isinstance(task_class, str) or task_class not in REQUIRED:
            failures.append(f'turn {i}: unknown task class')
        else:
            classes.add(task_class)
        if turn.get('status') != 'FINAL' or turn.get('visible_answer') is not True:
            failures.append(f'turn {i}: not a visible FINAL')
        if turn.get('correct') is not True:
            failures.append(f'turn {i}: correctness unverified or failed')
        for key, arr in (('total_ms', latencies), ('first_token_ms', ttfts)):
            value = turn.get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
                failures.append(f'turn {i}: {key} absent/invalid')
            else:
                arr.append(value)
        total = turn.get('total_ms')
        first = turn.get('first_token_ms')
        if (isinstance(total, (int, float)) and not isinstance(total, bool)
                and isinstance(first, (int, float)) and not isinstance(first, bool)
                and math.isfinite(total) and math.isfinite(first) and first > total):
            failures.append(f'turn {i}: first token later than completed turn')
        if task_class == 'body_cooperation':
            offers = turn.get('offers')
            for role in ('B1', 'B2'):
                offer = offers.get(role) if isinstance(offers, dict) else None
                if not isinstance(offer, dict) or not all(offer.get(k) is True for k in ('source_bound', 'delivered', 'consumed_by_c4_c3')):
                    failures.append(f'turn {i}: {role} source-bound delivered/consumed proof missing')
    if not REQUIRED.issubset(classes):
        failures.append('missing task classes: ' + ','.join(sorted(REQUIRED - classes)))
    def percentile(values, q):
        ordered = sorted(values)
        index = (len(ordered) - 1) * q
        lo = math.floor(index)
        hi = math.ceil(index)
        return ordered[lo] + (ordered[hi] - ordered[lo]) * (index - lo)
    metrics = {'turns': len(turns)}
    if len(latencies) == len(turns) and len(ttfts) == len(turns):
        metrics.update(total_p50_ms=statistics.median(latencies), total_p95_ms=percentile(latencies, .95),
                       ttft_p50_ms=statistics.median(ttfts), ttft_p95_ms=percentile(ttfts, .95))
    return {'status': 'METADATA_PASS_UNATTESTED' if not failures else 'BLOCKED', 'failures': failures,
            'metrics': metrics, 'scope': 'Unattested metadata consistency only; independently verify private device provenance; no full Canon or learned latent proof'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('sanitized_receipts_json')
    args = parser.parse_args()
    try:
        result = evaluate(json.loads(Path(args.sanitized_receipts_json).read_text()))
    except (OSError, ValueError) as exc:
        result = {'status': 'BLOCKED', 'failures': [type(exc).__name__]}
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['status'] == 'METADATA_PASS_UNATTESTED' else 2)
