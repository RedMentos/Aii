#!/usr/bin/env python3
"""Run574: source-only AST scope audit for Run571 native CURRENT/LEGACY cohort.

Reports a causal *limitation*: frozen STEP2 body offers + C3 tool replay are not
the actual Runtime.submit/_turn live answer-first/JEF path. Never runs models.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATHS = {
    'executor': ROOT / 'scripts/run571_current_default_native.py',
    'producer': ROOT / 'scripts/step2_z2b_seeds.py',
    'replay': ROOT / 'scripts/step2_tool_replay.py',
    'runtime': ROOT / 'v13/runtime.py',
    'config': ROOT / 'v13/config.py',
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def function(tree, name, parent=None):
    nodes = tree.body if parent is None else parent.body
    matches = [x for x in nodes if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))
               and x.name == name]
    require(len(matches) == 1, 'SOURCE_FUNCTION_MISSING_OR_DUPLICATE:' + name)
    return matches[0]


def method(tree, cls, name):
    matches = [x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == cls]
    require(len(matches) == 1, 'SOURCE_CLASS_MISSING_OR_DUPLICATE:' + cls)
    return function(tree, name, matches[0])


def dotted(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return dotted(node.value) + '.' + node.attr
    return ''


def calls(node):
    return [dotted(n.func) for n in ast.walk(node) if isinstance(n, ast.Call)]


def strings(node):
    return [n.value for n in ast.walk(node)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def audit(texts=None):
    if texts is None:
        texts = {k: p.read_text(encoding='utf-8') for k, p in PATHS.items()}
    require(type(texts) is dict and set(texts) == set(PATHS) and
            all(type(v) is str for v in texts.values()),
            'EXACT_SOURCE_SET_REQUIRED')
    trees = {k: ast.parse(text, filename=str(PATHS[k]))
             for k, text in texts.items()}
    executor = function(trees['executor'], 'execute')
    producer = function(trees['producer'], 'run_one')
    replay = function(trees['replay'], 'run')
    tool = function(trees['replay'], 'tool_answer')
    runtime = method(trees['runtime'], 'Runtime', 'submit')
    live_turn = method(trees['runtime'], 'Runtime', '_turn')
    # The call chain is the specific measured scope. Any change requires a
    # new review rather than silently treating historical replay as live.
    require('z2b.run_one' in calls(executor), 'EXECUTOR_NOT_FROZEN_Z2B')
    require('replay.run' in calls(producer), 'PRODUCER_NOT_FROZEN_TOOL_REPLAY')
    rcalls = calls(replay)
    require('runner.generate' in rcalls and 'tool_answer' in rcalls and
            'r.pool.get' in rcalls and 'C3_LANGUAGE' in strings(replay),
            'C3_FROZEN_REPLAY_CALL_GRAPH_CHANGED')
    require('E.decide' in calls(tool), 'FIXED_ELIGIBILITY_TOOL_CHANGED')
    require([a.arg for a in tool.args.args] == ['raw', 'messages'],
            'TOOL_ANSWER_UNEXPECTED_CONFIG_ARGUMENT')
    require(not any(c.endswith('.submit') or c.endswith('._turn')
                    for c in rcalls), 'FROZEN_REPLAY_NOW_CALLS_LIVE_RUNTIME')
    require('tool_answer_first' in strings(live_turn),
            'LIVE_RUNTIME_ANSWER_FIRST_BINDING_MISSING')
    require(runtime.name == 'submit', 'LIVE_RUNTIME_SUBMIT_MISSING')
    config_text = texts['config']
    require('LEGACY_QUOTE_PATH' in config_text and
            'tool_answer_first' in config_text and
            'eligibility_reader' in config_text,
            'CURRENT_LEGACY_CONFIG_SOURCE_MISSING')
    return {
        'schema': 'V13_RUN574_CURRENT_LEGACY_CAUSAL_SCOPE_AUDIT_V1',
        'status': 'BODY_OFFER_PLUS_FROZEN_C3_REPLAY_ONLY',
        'source_sha256': {k: hashlib.sha256(v.encode()).hexdigest()
                          for k, v in texts.items()},
        'measured_path': ['run571.execute', 'step2_z2b_seeds.run_one',
                          'step2_z2_timescale.harness',
                          'step2_tool_replay.run', 'C3_LANGUAGE.generate',
                          'step2_tool_replay.tool_answer', 'E.decide'],
        'actual_live_path': ['Runtime.submit', 'Runtime._turn'],
        'upstream_body_quote_comparison_possible': True,
        'live_end_to_end_verified': False,
        'eligibility_reader_final_effect_isolated': False,
        'tool_answer_first_final_effect_isolated': False,
        'native_executed': False,
        'canonical_gate_pass': False,
        'step2_exit': 'UTILITY_FAIL',
        'b3_l1': 'FAIL',
        'body_jepa': 'UNAVAILABLE',
        'jepa_weight': 0,
        'redmi_measured': False,
        'claim_limit': 'Do not call Run572 frozen C3 replay a real live Runtime.submit/_turn comparison.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'status': result['status'],
                      'live_end_to_end_verified': False,
                      'native_executed': False}, sort_keys=True))


if __name__ == '__main__':
    main()
