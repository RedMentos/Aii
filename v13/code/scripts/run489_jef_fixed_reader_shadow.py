#!/usr/bin/env python3
"""Run489: deterministic JEF fixed-reader shadow replay of pinned native378 quotes.

Post-hoc diagnostic: frozen original B1/B2 verified quotes -> existing fixed
reader -> existing rule guard/recipe -> independent score. No native inference,
training, production mutation, learning authority, or STEP2 gate promotion.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from v13.agi import eligibility as E
from v13.common import digest, dumps
import run488_native378_independent_rescore as r488

EXPECTED_ZIP = 'a87acfa38688e66e603fe9c07cbc0762b231a6eb74527a8010c595e487e46afe'
ROLES = ('B1_DETAIL', 'B2_GIST')
ARMS = ('O', 'P', 'S')
SEEDS = (20, 21, 22)
VARIANTS = ('b1_only', 'b2_only', 'both_none', 'both_exact', 'both_control',
            'same_policy_dual', 'prompt_only_dual')


def require(ok, why):
    if not ok:
        raise ValueError(why)


def source_packet(source_row):
    """Validate the exact consumer packet and quote provenance, not hypotheses."""
    messages = source_row.get('consumer_messages')
    require(type(messages) is list and len([m for m in messages
            if type(m) is dict and m.get('role') == 'user']) == 1,
            'CONSUMER_USER_MESSAGE_MISSING_OR_DUPLICATE')
    raw = next(m['content'] for m in messages if m['role'] == 'user')
    packet = json.loads(raw)
    require(type(packet) is dict and type(packet.get('current_source')) is str and
            type(packet.get('analysts')) is list, 'SOURCE_PACKET_SCHEMA')
    evidence = source_row.get('source_evidence')
    require(type(evidence) is list and evidence and
            all(type(e) is dict and type(e.get('text')) is str for e in evidence),
            'SOURCE_EVIDENCE_MISSING')
    require(any(packet['current_source'] == e['text'] for e in evidence),
            'CURRENT_SOURCE_NOT_EVIDENCED')
    quotes = []
    for analyst in packet['analysts']:
        require(type(analyst) is dict and analyst.get('role') in ROLES and
                type(analyst.get('verified_quotes')) is list,
                'UNRECOGNIZED_ANALYST_OR_QUOTES')
        for q in analyst['verified_quotes']:
            require(type(q) is str and bool(q) and
                    any(q in e['text'] for e in evidence), 'QUOTE_NOT_EXACT_SOURCE')
            quotes.append((analyst['role'], q))
    return packet['current_source'], quotes


def shadow(source_row, allowed_roles=ROLES):
    """Produce a decision using source text only; never receives fixture oracle."""
    require(set(allowed_roles) <= set(ROLES), 'UNKNOWN_ROLE_ABLATION')
    current, all_quotes = source_packet(source_row)
    quotes = [q for role, q in all_quotes if role in allowed_roles]
    match = re.fullmatch(r'Project ([A-Za-z]+)\..*', current, re.S)
    require(match is not None, 'PROJECT_NOT_SOURCE_BOUND')
    project = match.group(1)
    try:
        read = E.fixed_read(current, history=(), quotes=quotes)
        require(type(read) is dict and set(read) == {'budget', 'deadline', 'local_only', 'options'},
                'FIXED_READER_SCHEMA')
        decision = E.decide({k: read[k] for k in ('budget', 'deadline', 'local_only')},
                            read['options'], current, quotes)
        answer = dumps({'project': project, 'action': decision['action'],
                        'options': decision['options']})
        return {'status': 'DECIDED' if decision['action'] != 'UNKNOWN' else 'UNKNOWN',
                'answer': answer, 'action': decision['action'],
                'rejected': decision['rejected'],
                'b1_quotes': sum(role == 'B1_DETAIL' for role, _ in all_quotes if role in allowed_roles),
                'b2_quotes': sum(role == 'B2_GIST' for role, _ in all_quotes if role in allowed_roles)}
    except (ValueError, TypeError, KeyError) as exc:
        # Missing exact options cannot be replaced by guessed values.
        return {'status': 'UNSUPPORTED', 'answer': None, 'action': None,
                'rejected': [type(exc).__name__ + ':' + str(exc)[:120]],
                'b1_quotes': sum(role == 'B1_DETAIL' for role, _ in all_quotes if role in allowed_roles),
                'b2_quotes': sum(role == 'B2_GIST' for role, _ in all_quotes if role in allowed_roles)}


def evaluate(source_row, roles=ROLES):
    decision = shadow(source_row, roles)
    # Oracle is only used after shadow has returned its source-only decision.
    expected = r488.oracle(source_row['fixture'])
    score = (r488.score_answer(decision['answer'], expected)
             if decision['answer'] is not None
             else {'utility': 0., 'exact': False})
    require(type(score['utility']) in (int, float) and math.isfinite(score['utility']) and
            0 <= score['utility'] <= 1, 'NONFINITE_SHADOW_SCORE')
    action = decision['action']
    return {'utility': score['utility'], 'exact': score['exact'],
            'wrong_committed': action in ('A', 'B', 'NONE') and action != expected['action'],
            'unknown': action == 'UNKNOWN',
            'unsupported': decision['status'] == 'UNSUPPORTED',
            'action': action, 'status': decision['status'],
            'b1_quotes': decision['b1_quotes'], 'b2_quotes': decision['b2_quotes']}


def summarize(rows):
    require(len(rows) == 18, 'INCOMPLETE_PAIRED_VARIANT')
    return {'mean_utility': math.fsum(r['utility'] for r in rows) / 18,
            'exact': sum(r['exact'] for r in rows),
            'wrong_committed': sum(r['wrong_committed'] for r in rows),
            'unknown': sum(r['unknown'] for r in rows),
            'unsupported': sum(r['unsupported'] for r in rows),
            'b1_quotes': sum(r['b1_quotes'] for r in rows),
            'b2_quotes': sum(r['b2_quotes'] for r in rows)}


def audit(path):
    path = Path(path)
    require(hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED_ZIP,
            'ORIGINAL_SAFE_ZIP_CHANGED')
    prior = r488.audit(path)
    require(prior['rows'] == 378 and prior['canonical_gate_pass'] is False and
            prior['step2_exit'] == 'UTILITY_FAIL', 'ORIGINAL_ANSWER_AUDIT_NOT_GREEN')
    by_arm = {arm: {variant: [] for variant in VARIANTS} for arm in ARMS}
    ablations = {arm: {'without_B1': [], 'without_B2': []} for arm in ARMS}
    statuses = {}
    with zipfile.ZipFile(path) as z:
        progress = json.loads(z.read('RUN397_PROGRESS.json'))
        for arm in ARMS:
            for seed in SEEDS:
                rid = f'{arm}_s{seed}'
                prefix = progress['completed'][rid]['attempt'] + '/'
                source = json.loads(z.read(prefix + 'step2_' + rid + '.json'))
                tool = json.loads(z.read(prefix + 'tool_' + rid + '.json'))
                sr = {(r['fixture'], r['variant']): r for r in source['rows']}
                tr = {(r['fixture'], r['variant']): r for r in tool['rows']}
                expected = {(f, v) for f in r488.SPECS for v in VARIANTS}
                require(set(sr) == set(tr) == expected and len(source['rows']) == 42 and
                        len(tool['rows']) == 42, 'FROZEN_42_ROW_MATRIX_CHANGED')
                for fixture, variant in sorted(expected):
                    row, tool_row = sr[(fixture, variant)], tr[(fixture, variant)]
                    require(row.get('oracle_visible_to_native') is False and
                            tool_row.get('oracle_visible_to_native') is False and
                            row.get('status') == 'RECORDED', 'NATIVE_SOURCE_STATUS_OR_LEAK')
                    require(digest(dumps(row['consumer_messages'])) ==
                            tool_row['consumer_messages_sha256'], 'CONSUMER_MESSAGES_HASH_CHANGED')
                    result = evaluate(row)
                    by_arm[arm][variant].append(result)
                    statuses[(arm, seed, fixture, variant)] = result['status']
                    if variant == 'both_exact':
                        ablations[arm]['without_B1'].append(evaluate(row, ('B2_GIST',)))
                        ablations[arm]['without_B2'].append(evaluate(row, ('B1_DETAIL',)))
    require(len(statuses) == 378 and
            all(len(values) == 18 for arm in by_arm.values() for values in arm.values()),
            'FROZEN_378_ROW_COHORT_INCOMPLETE')
    summary = {arm: {v: summarize(rows) for v, rows in variants.items()}
               for arm, variants in by_arm.items()}
    controls = {arm: {k: summarize(rows) for k, rows in variants.items()}
                for arm, variants in ablations.items()}
    return {'schema': 'V13_RUN489_JEF_FIXED_READER_SHADOW_NATIVE378_V1',
            'status': 'FIXED_JEF_SHADOW_REPLAY_DIAGNOSTIC_ONLY',
            'rows': 378, 'original_safe_zip_sha256': EXPECTED_ZIP,
            'reader_revision': E.REVISION, 'summary': summary,
            'both_exact_role_ablations': controls,
            'canonical_gate_pass': False, 'step2_exit': 'UTILITY_FAIL',
            'b3_l1': 'FAIL', 'body_jepa': 'UNAVAILABLE',
            'jepa_weight': 0, 'latent_authority': 0,
            'redmi_measured': False,
            'claim_limit': 'Post-hoc frozen native quote shadow replay, not native C3 replacement, not preregistered canonical STEP2 ten-episode utility or full V13.'}


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: run489_jef_fixed_reader_shadow.py <original-safe-zip>')
    print(json.dumps(audit(sys.argv[1]), indent=2, sort_keys=True))
