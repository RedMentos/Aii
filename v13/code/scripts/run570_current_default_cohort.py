#!/usr/bin/env python3
"""Run570: new disjoint STEP2 CURRENT vs LEGACY source registration, NO native execution.

Original Run491/500/504/558 cohorts remain immutable. The output is a source
registration, not evidence of model utility. No --execute mode exists here.
"""
import argparse
import hashlib
import json
from pathlib import Path

import run491_step2_heldout10 as frozen
import step2_z2_timescale as z2
from v13 import config

SPECS = (
    ('Helios', 'SPLIT', (132, 6, True), (95, 4, True), (87, 7, False)),
    ('Iris', 'SPLIT', (86, 5, False), (73, 6, False), (77, 4, True)),
    ('Jade', 'SPLIT', (118, 4, True), (98, 4, True), (102, 3, False)),
    ('Kepler', 'RULE', (105, 5, True), (88, 4, True), (79, 6, True)),
    ('Lyra', 'RULE', (92, 3, False), (81, 4, False), (83, 2, True)),
    ('Mistral', 'DETAIL', (124, 5, True), (109, 6, True), (117, 4, True)),
)
SEED = 41
ARMS = ('CURRENT', 'LEGACY')
VARIANTS = frozen.VARIANTS
CONFIG_KEYS = (
    'offer_quote_context_chars', 'b2_quote_select', 'b2_offer_body_state',
    'offer_quote_min_chars', 'b1_recent_source_chars', 'body_question_scope',
    'eligibility_reader', 'tool_answer_first', 'body_question_b1',
    'body_question_b2', 'answer_language', 'b2_control', 'learning_mode',
    'system_stage', 'latents_enabled', 'teacher_enabled',
    'age_plasticity_policy',
)
CANON_SHA256 = '3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def configs():
    require(all(k in config.DEFAULTS for k in CONFIG_KEYS), 'CURRENT_DEFAULT_KEY_MISSING')
    require(set(config.LEGACY_QUOTE_PATH) <= set(config.DEFAULTS), 'LEGACY_KEY_MISSING')
    current = {k: config.DEFAULTS[k] for k in CONFIG_KEYS}
    old = dict(config.DEFAULTS)
    old.update(config.LEGACY_QUOTE_PATH)
    old['tool_answer_first'] = False  # Explicit historical behavior, not implied by LEGACY_QUOTE_PATH.
    legacy = {k: old[k] for k in CONFIG_KEYS}
    for arm in (current, legacy):
        require(arm['answer_language'] == 'en' and arm['b2_control'] == 'two_body' and
                arm['learning_mode'] == 'RECORD_ONLY' and arm['system_stage'] == 0 and
                arm['latents_enabled'] is False and arm['teacher_enabled'] is False,
                'SAFETY_OR_LANGUAGE_CONFIG_CHANGED')
    require(current['b2_quote_select'] == 'pointer' and
            current['eligibility_reader'] == 'fixed' and
            current['tool_answer_first'] is True and
            current['b1_recent_source_chars'] == 600 and
            current['offer_quote_context_chars'] == 200 and
            current['body_question_scope'] == 'rule_decision',
            'CURRENT_QUOTE_PATH_CHANGED')
    require(legacy['b2_quote_select'] == 'off' and
            legacy['eligibility_reader'] == 'c3' and
            legacy['tool_answer_first'] is False and
            legacy['b1_recent_source_chars'] == 0 and
            legacy['offer_quote_context_chars'] == 0 and
            legacy['body_question_b1'] == '' and legacy['body_question_b2'] == '',
            'LEGACY_QUOTE_PATH_CHANGED')
    require(current != legacy, 'CONTROL_IDENTICAL_TO_CURRENT')
    return {'CURRENT': current, 'LEGACY': legacy}


def validate_fixtures(rows):
    require(type(rows) is list and len(rows) == 6, 'SIX_EPISODES_REQUIRED')
    require([r['id'] for r in rows] == [s[0] for s in SPECS] and
            [r['type'] for r in rows] == [s[1] for s in SPECS],
            'NEW_FIXTURE_ID_OR_TYPE_CHANGED')
    require(rows == [z2.episode(*spec) for spec in SPECS], 'NEW_FIXTURE_SOURCE_CHANGED')
    old_ids = {x[0] for x in z2.EPISODES} | {x[0] for x in frozen.SPECS}
    require(len({r['id'] for r in rows}) == 6 and
            not ({r['id'] for r in rows} & old_ids),
            'REGISTERED_COHORT_OVERLAP')
    require([r['type'] for r in rows].count('SPLIT') == 3 and
            [r['type'] for r in rows].count('RULE') == 2 and
            [r['type'] for r in rows].count('DETAIL') == 1,
            'FIXTURE_TYPE_BALANCE')
    for row in rows:
        kind = row['type']
        history, current = row['history'], row['current']
        require(type(history) is list and len(history) == 3 and
                all(type(h) is str for h in history) and type(current) is str and
                history[1] == z2.DISTRACTOR,
                'THREE_TURN_HISTORY_CHANGED')
        rule = row['rules']
        require(z2.rules_text(rule['budget'], rule['deadline'],
                              rule['local_only']) in history[0] if kind != 'DETAIL'
                else ('budget ' in current and 'deadline ' in current and
                      'local-only requirement:' in current),
                'RULE_SOURCE_MISSING')
        if kind in ('SPLIT', 'DETAIL'):
            position = history[2].find('Option A:')
            require(240 < position < 360 and
                    'Option B:' in history[2][position:] and
                    'Option A:' not in current and 'Option B:' not in current,
                    'B1_B2_DETAIL_WINDOW_CHANGED')
        else:
            require('Option A:' in current and 'Option B:' in current,
                    'RULE_CURRENT_OPTIONS_MISSING')
        if kind in ('SPLIT', 'RULE'):
            require(z2.rules_text(rule['budget'], rule['deadline'],
                                  rule['local_only']) not in current,
                    'HISTORY_RULES_LEAKED_TO_CURRENT')
        require(row['oracle']['action'] in ('A', 'B', 'NONE'),
                'UNSUPPORTED_ORACLE_ACTION')
    return True


def registration():
    original = frozen.registration()  # independently rejects mutated original fixture bytes
    require(original['fixture_sha256'] == frozen.FIXTURE_SHA256 and
            tuple(original['variants']) == VARIANTS and
            tuple(original['seeds']) == frozen.SEEDS and
            tuple(original['arms']) == frozen.ARMS,
            'FROZEN_SOURCE_REGISTRATION_CHANGED')
    rows = [z2.episode(*spec) for spec in SPECS]
    validate_fixtures(rows)
    arms = configs()
    source = [{k: r[k] for k in ('id', 'type', 'history', 'current')} for r in rows]
    oracles = {r['id']: r['oracle'] for r in rows}
    keys = [f'{arm}:{SEED}:{r["id"]}:{variant}'
            for arm in ARMS for r in rows for variant in VARIANTS]
    require(len(keys) == len(set(keys)) == 84 and
            all('oracle' not in r and 'rules' not in r for r in source),
            'ROW_KEY_DUPLICATE_OR_ORACLE_LEAK')
    return {
        'schema': 'V13_RUN570_DISJOINT_CURRENT_LEGACY_SOURCE_PLAN_V1',
        'status': 'SOURCE_ONLY_NEW_COHORT_NOT_EXECUTED',
        'source_constructor': 'step2_z2_timescale.episode',
        'original_frozen_fixture_sha256': frozen.FIXTURE_SHA256,
        'original_model_sha256_expected_not_retrieved': frozen.MODEL_SHA256,
        'original_runner_sha256_expected_not_retrieved': frozen.RUNNER_SHA256,
        'canon_sha256_expected': CANON_SHA256,
        'new_fixture_sha256': digest(rows),
        'source_fixtures': source,
        'scoring_oracles_not_for_native_messages': oracles,
        'config_snapshots': arms,
        'config_snapshot_sha256': digest(arms),
        'seed': SEED, 'arms': list(ARMS), 'variants': list(VARIANTS),
        'row_keys_sha256': digest(keys), 'row_keys': keys,
        'planned_native_consumer_rows': 84,
        'native_executed': False, 'canonical_gate_pass': False,
        'step2_exit': 'UTILITY_FAIL', 'b3_l1': 'FAIL',
        'body_jepa': 'UNAVAILABLE', 'jepa_weight': 0,
        'redmi_measured': False,
        'claim_limit': 'NEW source-only 84-row plan, not original frozen cohort or native utility evidence',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--plan', action='store_true', required=True)
    args = parser.parse_args()
    result = registration()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'status': result['status'],
                      'new_fixture_sha256': result['new_fixture_sha256'],
                      'config_snapshot_sha256': result['config_snapshot_sha256'],
                      'row_keys_sha256': result['row_keys_sha256'],
                      'rows': result['planned_native_consumer_rows'],
                      'native_executed': False}, sort_keys=True))


if __name__ == '__main__':
    main()
