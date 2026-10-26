#!/usr/bin/env python3
"""Run575: NEW true-live Runtime.submit/_turn paired pilot, source-only until --execute.

Three synthetic Run570 fixtures x CURRENT/LEGACY x four sequential actual user
turns. Unlike Run571, never invokes step2_tool_replay or a frozen C3 consumer.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time

import run496_heldout10_native_pilot as pinned
import run570_current_default_cohort as cohort
import step2_z2_timescale as z2
from v13.utility import score_decision

FIXTURE_IDS = ('Helios', 'Kepler', 'Mistral')
ARMS = ('CURRENT', 'LEGACY')
SEED = 41
TIMEOUT_SECONDS = 45.0
INSTRUCTION = ('Return exactly one JSON object with keys project, action, options. '
               'Each option must have entity, cost, remaining, days, local, eligible. '
               'If required source evidence is missing, use UNKNOWN; do not guess.')
TERMINAL = frozenset(('FINAL', 'CANCELLED', 'DEADLINE', 'ERROR', 'INTERRUPTED', 'REJECTED'))
PLAN = 'RUN575_PLAN.json'
ATTEMPT = 'RUN575_ATTEMPT.json'
PREFLIGHT = 'RUN575_PREFLIGHT.json'
PROGRESS = 'RUN575_PROGRESS.jsonl'
RAW = 'RUN575_LIVE_ROWS.jsonl'
RESULT = 'RUN575_RESULT.json'


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(value):
    return hashlib.sha256(cohort.canonical(value)).hexdigest()


def write_new(path, data):
    with Path(path).open('x', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2,
                           allow_nan=False) + '\n')


def append(path, data):
    with Path(path).open('a', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n')
        f.flush()
        os.fsync(f.fileno())


def registration():
    source = cohort.registration()
    selected = [f for f in source['source_fixtures'] if f['id'] in FIXTURE_IDS]
    require([f['id'] for f in selected] == list(FIXTURE_IDS),
            'EXACT_THREE_DISJOINT_FIXTURES_REQUIRED')
    oracles = {f: source['scoring_oracles_not_for_native_messages'][f]
               for f in FIXTURE_IDS}
    keys = [arm + ':' + fid for arm in ARMS for fid in FIXTURE_IDS]
    require(len(keys) == len(set(keys)) == 6, 'DIALOGUE_KEYS')
    return {'schema': 'V13_RUN575_TRUE_LIVE_PAIRED_SOURCE_ONLY_V1',
            'status': 'TRUE_LIVE_SOURCE_ONLY_NOT_EXECUTED',
            'source_run570_sha256': sha(source),
            'source_fixtures': selected,
            'scoring_oracles_not_for_runtime': oracles,
            'config_snapshots': source['config_snapshots'],
            'instruction': INSTRUCTION, 'seed': SEED,
            'arms': list(ARMS), 'fixture_ids': list(FIXTURE_IDS),
            'dialogue_keys': keys, 'dialogue_keys_sha256': sha(keys),
            'history_turns_per_dialogue': 3,
            'live_turns_per_dialogue': 4,
            'planned_live_turns': 24,
            'model_sha256_expected_not_retrieved':
                source['original_model_sha256_expected_not_retrieved'],
            'runner_sha256_expected_not_retrieved':
                source['original_runner_sha256_expected_not_retrieved'],
            'native_executed': False, 'canonical_gate_pass': False,
            'step2_exit': 'UTILITY_FAIL', 'b3_l1': 'FAIL',
            'body_jepa': 'UNAVAILABLE', 'jepa_weight': 0,
            'redmi_measured': False,
            'claim_limit': 'New actual live Runtime pilot only, not canonical STEP2 or V13 acceptance'}


def prepare_plan(work):
    work = Path(work)
    require(not work.is_symlink(), 'WORK_SYMLINK')
    work.mkdir(parents=True, exist_ok=True)
    require(not any(work.iterdir()), 'FRESH_WORK_REQUIRED')
    data = registration()
    write_new(work / PLAN, data)
    return data


def exact_plan(work):
    p = Path(work) / PLAN
    require(p.is_file() and not p.is_symlink(), 'PLAN_MISSING')
    data = json.loads(p.read_text())
    require(data == registration(), 'PLAN_CHANGED')
    return data


def wait_terminal(runtime, event_id, timeout=TIMEOUT_SECONDS, clock=time.monotonic,
                  sleep=time.sleep):
    require(type(event_id) is int and event_id > 0, 'EVENT_ID_INVALID')
    require(type(timeout) in (int, float) and 0 < timeout <= TIMEOUT_SECONDS,
            'TIMEOUT_INVALID')
    deadline = clock() + timeout
    while clock() < deadline:
        row = runtime.store.one(
            "SELECT event_id,text,status,metadata FROM messages "
            "WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1",
            (event_id,))
        if row is not None:
            require(row['event_id'] == event_id, 'ASSISTANT_EVENT_OWNERSHIP_CHANGED')
            if row['status'] in TERMINAL:
                return {'event_id': event_id, 'status': row['status'],
                        'text': row['text']}
        sleep(.05)
    runtime.cancel()
    raise TimeoutError('LIVE_TURN_TIMEOUT_CANCEL_REQUESTED')


def run_dialogue(installed, work, arm, fixture, cfg, runtime_factory=None,
                 home_factory=None, wait=wait_terminal):
    require(arm in ARMS and fixture['id'] in FIXTURE_IDS, 'DIALOGUE_OUT_OF_SCOPE')
    require(cfg == registration()['config_snapshots'][arm], 'ARM_CONFIG_CHANGED')
    if runtime_factory is None:
        from v13.runtime import Runtime
        runtime_factory = Runtime
    if home_factory is None:
        home_factory = z2.sibling_home
    home = Path(work) / (arm + '_' + fixture['id'] + '-home')
    require(not home.exists() and not home.is_symlink(), 'REUSED_LIVE_HOME')
    home = home_factory(installed, home, dict(cfg, seed=SEED))
    runtime = runtime_factory(home)
    turns = []
    try:
        texts = list(fixture['history']) + [fixture['current'] + '\n' + INSTRUCTION]
        require(len(texts) == 4 and all(type(t) is str and t for t in texts),
                'LIVE_INPUT_SOURCE_INVALID')
        for index, text in enumerate(texts):
            eid = runtime.submit(text)
            terminal = wait(runtime, eid)
            require(terminal['event_id'] == eid and terminal['status'] == 'FINAL',
                    'LIVE_TURN_NOT_FINAL')
            turns.append({'index': index, 'event_id': eid,
                          'input_sha256': hashlib.sha256(text.encode()).hexdigest(),
                          'status': terminal['status'], 'answer': terminal['text']})
        answer = turns[-1]['answer']
        require(type(answer) is str and bool(answer.strip()), 'LIVE_FINAL_EMPTY')
        return {'arm': arm, 'fixture': fixture['id'], 'turns': turns,
                'final_answer': answer, 'native_executed': True}
    finally:
        runtime.close()


def action_of(text):
    try:
        value = json.loads(text)
        return value.get('action') if type(value) is dict else None
    except (ValueError, TypeError):
        return None


def evaluate(dialogue, oracle):
    require(dialogue['native_executed'] is True and len(dialogue['turns']) == 4,
            'LIVE_DIALOGUE_INCOMPLETE')
    score = score_decision(dialogue['final_answer'], oracle)
    require(type(score['utility']) in (float, int) and
            math.isfinite(score['utility']) and 0 <= score['utility'] <= 1,
            'NONFINITE_UTILITY')
    action = action_of(dialogue['final_answer'])
    wrong = action in ('A', 'B', 'NONE') and action != oracle['action']
    return {'arm': dialogue['arm'], 'fixture': dialogue['fixture'],
            'utility': score['utility'], 'exact': score['exact'],
            'action': action, 'wrong_committed': bool(wrong),
            'unknown': action == 'UNKNOWN', 'unsupported': action is None,
            'dialogue_sha256': sha(dialogue)}


def execute(work, installed, runtime_factory=None, home_factory=None,
            wait=wait_terminal):
    work = Path(work)
    require(work.is_dir() and not work.is_symlink(), 'WORK_REQUIRED')
    plan = exact_plan(work)
    require(not any((work / p).exists() for p in
                    (ATTEMPT, PREFLIGHT, PROGRESS, RAW, RESULT)),
            'REFUSE_REUSE_OR_PARTIAL_LIVE_ATTEMPT')
    require(not any((work / (arm + '_' + fid + '-home')).exists()
                    for arm in ARMS for fid in FIXTURE_IDS), 'LIVE_HOME_ALREADY_EXISTS')
    write_new(work / ATTEMPT, {'status': 'EXCLUSIVE_CLAIMED_BEFORE_MODEL_PREFLIGHT',
                               'plan_sha256': hashlib.sha256((work / PLAN).read_bytes()).hexdigest(),
                               'native_executed': False, 'canonical_gate_pass': False})
    verified = pinned.verify_installed(installed)
    require(verified['model_sha256'] == plan['model_sha256_expected_not_retrieved'] and
            verified['runner_sha256'] == plan['runner_sha256_expected_not_retrieved'] and
            bool(verified['runtime_library_sha256']),
            'PINNED_MODEL_OR_RUNNER_CHANGED')
    write_new(work / PREFLIGHT, verified)
    fixtures = {f['id']: f for f in plan['source_fixtures']}
    evaluations = []
    for arm in ARMS:
        for fid in FIXTURE_IDS:
            append(work / PROGRESS, {'arm': arm, 'fixture': fid, 'state': 'STARTED'})
            dialogue = run_dialogue(installed, work, arm, fixtures[fid],
                                    plan['config_snapshots'][arm],
                                    runtime_factory, home_factory, wait)
            append(work / RAW, dialogue)
            result = evaluate(dialogue, plan['scoring_oracles_not_for_runtime'][fid])
            evaluations.append(result)
            append(work / PROGRESS, {'arm': arm, 'fixture': fid, 'state': 'FINISHED',
                                     'dialogue_sha256': result['dialogue_sha256']})
            require(not result['wrong_committed'], 'WRONG_COMMITTED_STOP')
    require(len(evaluations) == 6, 'LIVE_PAIRED_COHORT_INCOMPLETE')
    out = {'schema': 'V13_RUN575_TRUE_LIVE_NATIVE_PILOT_STRUCTURAL_V1',
           'status': 'TRUE_LIVE_PILOT_STRUCTURAL_ONLY',
           'evaluations': evaluations, 'dialogues': 6, 'live_turns': 24,
           'native_executed': True, 'canonical_gate_pass': False,
           'step2_exit': 'UTILITY_FAIL', 'b3_l1': 'FAIL',
           'body_jepa': 'UNAVAILABLE', 'jepa_weight': 0,
           'redmi_measured': False}
    write_new(work / RESULT, out)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--plan', action='store_true')
    modes.add_argument('--execute', action='store_true')
    parser.add_argument('--installed-home', type=Path)
    args = parser.parse_args()
    if args.plan:
        require(args.installed_home is None, 'PLAN_MUST_NOT_LOAD_MODELS')
        p = prepare_plan(args.work)
        print(json.dumps({'status': p['status'], 'planned_live_turns': 24,
                          'native_executed': False}))
    else:
        require(args.installed_home is not None, 'INSTALLED_HOME_REQUIRED')
        print(json.dumps(execute(args.work, args.installed_home), sort_keys=True))


if __name__ == '__main__':
    main()
