"""Require the complete fixed learning grid before the original numerical gates.

Isolated correctness candidate: no model execution, runtime change or learned
utility claim. ``analyze_checked(rows, learn_report, plan_doc)`` takes all Phase
A and B rows, the learn report and the fixed plan document used by the runner.
Only integrity-complete evidence reaches the unchanged original ``analyze``.
"""
import math
import re

from scripts import tool_forecast_learning_check as original

ARMS = ('calc_shift_exp', 'note_shift_exp', 'calc_shift_test', 'calc_in_test',
        'note_shift_test', 'note_in_test')
ACTIONS = {'calc': tuple(original.live.CALC_PHRASE), 'note': tuple(original.live.NOTE_PHRASE)}
WORLDS = {'calc': 'calc_counter', 'note': 'note_edit'}
NOT_CONFIRMED = 'CONTINUAL_LEARNING_NOT_CONFIRMED'


def _valid_mse(value):
    if type(value) not in (int, float) or value < 0:
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def expected_grid(plan_doc):
    """Return exact (arm, action, state) cases; reject duplicate plan states."""
    if not isinstance(plan_doc, dict) or not isinstance(plan_doc.get('plan'), dict):
        raise ValueError('Fixed plan document with plan mapping required')
    plan = plan_doc['plan']
    if set(plan) != set(ARMS):
        raise ValueError('Fixed plan must contain exactly the six learning arms')
    seen = {'calc': set(), 'note': set()}
    grid = []
    for arm in ARMS:
        family = arm.split('_')[0]
        states = plan[arm]
        if not isinstance(states, list) or not states:
            raise ValueError('Plan arm requires a nonempty state list: ' + arm)
        for state in states:
            if family == 'calc':
                lower, upper = (1, 999) if arm == 'calc_in_test' else (1000, 9999)
                valid = type(state) is int and lower <= state <= upper
            else:
                valid = isinstance(state, str) and bool(state.strip()) and '\n' not in state and '\r' not in state
            if not valid:
                raise ValueError('Invalid plan state: ' + arm + ' ' + repr(state))
            if state in seen[family]:
                raise ValueError('Repeated state within/across plan arms: ' + repr(state))
            seen[family].add(state)
            grid.extend((arm, action, state) for action in ACTIONS[family])
    return grid


def validate(rows, learn_report, plan_doc):
    """Validate all planned cases, row identity, execution, scoring and adaptation."""
    errors = []

    def error(code, location, detail=''):
        errors.append({'code': code, 'location': location, 'detail': detail})

    try:
        grid = expected_grid(plan_doc)
    except ValueError as exc:
        return {'pass': False, 'errors': [{'code': 'INVALID_PLAN', 'location': 'plan', 'detail': str(exc)}]}
    expected = set(grid)
    counts = {arm: sum(case[0] == arm for case in grid) for arm in ARMS}
    exp_counts = {WORLDS[family]: counts[family + '_shift_exp'] for family in WORLDS}
    if not isinstance(learn_report, dict) or set(learn_report) != set(WORLDS.values()):
        error('INVALID_LEARN_REPORT', 'learn_report', 'Exactly both expected worlds required')
        learn_report = {}
    for family, world in WORLDS.items():
        report = learn_report.get(world)
        if not isinstance(report, dict):
            error('INVALID_LEARN_WORLD', world)
            continue
        if type(report.get('pass')) is not bool:
            error('INVALID_LEARN_PASS', world)
        if type(report.get('experience_rows')) is not int or report['experience_rows'] != exp_counts[world]:
            error('EXPERIENCE_COUNT_MISMATCH', world, 'Expected ' + str(exp_counts[world]))
        adapted = report.get('adapted_actions')
        if (not isinstance(adapted, list) or any(type(action) is not str or action not in ACTIONS[family] for action in adapted)
                or len(adapted) != len(set(adapted))):
            error('INVALID_ADAPTED_ACTIONS', world)
        elif bool(adapted) != report.get('pass'):
            error('ADAPTED_ACTIONS_PASS_MISMATCH', world)

    if not isinstance(rows, list):
        error('INVALID_ROWS', 'rows', 'List required')
        rows = []
    seen_cases, seen_calls, seen_forecasts = set(), set(), set()
    observed = {arm: 0 for arm in ARMS}
    test_started = False
    for index, row in enumerate(rows):
        where = 'row:' + str(index)
        if not isinstance(row, dict):
            error('INVALID_ROW', where)
            continue
        arm, action, state = row.get('arm'), row.get('action'), row.get('state')
        if not isinstance(arm, str) or arm not in ARMS:
            error('UNEXPECTED_ARM', where)
            continue
        family = arm.split('_')[0]
        if (type(action) is not str or action not in ACTIONS[family]
                or (type(state) is not int if family == 'calc' else type(state) is not str)):
            error('INVALID_CASE', where)
            continue
        case = (arm, action, state)
        if case not in expected:
            error('UNPLANNED_CASE', where, repr(case))
            continue
        if case in seen_cases:
            error('DUPLICATE_CASE', where, repr(case))
        seen_cases.add(case)
        observed[arm] += 1
        if arm not in original.EXP_ARMS:
            test_started = True
        elif test_started:
            error('EXPERIENCE_AFTER_TEST', where)
        for field, prefix, seen in (('call', 'tool', seen_calls), ('forecast_id', 'tfc', seen_forecasts)):
            value = row.get(field)
            if not isinstance(value, str) or re.fullmatch(prefix + r'_[0-9a-f]{32}', value) is None:
                error('INVALID_ID', where + ':' + field)
            elif value in seen:
                error('REUSED_ID', where + ':' + field)
            else:
                seen.add(value)
        if row.get('status') != 'SCORED':
            error('ROW_NOT_SCORED', where)
        if row.get('tool_status') != 'EXECUTED':
            error('CALL_NOT_EXECUTED', where)
        mse = row.get('mse')
        if not isinstance(mse, dict):
            error('INVALID_MSE', where)
            continue
        required = {'forecast', 'copy', 'mean_delta'}
        if arm not in original.EXP_ARMS:
            report = learn_report.get(WORLDS[family], {})
            if isinstance(report, dict) and report.get('pass') is True:
                required.add('adapted')
        for metric in sorted(required - set(mse)):
            error('MISSING_MSE', where + ':' + metric)
        for metric, value in mse.items():
            if not _valid_mse(value):
                error('INVALID_MSE_VALUE', where + ':' + str(metric))
    missing = [list(case) for case in grid if case not in seen_cases]
    if missing:
        error('MISSING_CASES', 'rows', str(len(missing)) + ' planned cases absent')
    if len(rows) != len(grid):
        error('ROW_COUNT_MISMATCH', 'rows', 'Expected ' + str(len(grid)))
    return {'pass': not errors, 'errors': errors, 'expected_rows': len(grid), 'observed_rows': len(rows),
            'expected_by_arm': counts, 'observed_by_arm': observed,
            'experience_rows': sum(exp_counts.values()), 'test_rows': len(grid) - sum(exp_counts.values()),
            'missing_cases': missing}


def _finite_numbers(value):
    if isinstance(value, dict):
        return all(_finite_numbers(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_finite_numbers(item) for item in value)
    return math.isfinite(value) if type(value) in (int, float) else True


def analyze_checked(rows, learn_report, plan_doc):
    """Fail closed on incomplete evidence; retain original numeric gates unchanged."""
    integrity = validate(rows, learn_report, plan_doc)
    result = {'verdict': NOT_CONFIRMED, 'worlds': {}, 'gates': dict(original.GATES),
              'integrity': integrity, 'analysis_ran': False,
              'claim_scope': 'Row integrity and original numerical analysis only; no native/device/provenance gate established',
              'canonical_gate_pass': False, 'phone_measured': False}
    if not integrity['pass']:
        return result
    result['analysis_ran'] = True
    try:
        analysis = original.analyze([row for row in rows if row['arm'] not in original.EXP_ARMS], learn_report)
    except (ArithmeticError, ValueError) as exc:
        result['analysis_error'] = {'code': 'ORIGINAL_ANALYSIS_UNDEFINED', 'type': type(exc).__name__}
        return result
    if not _finite_numbers(analysis):
        result['analysis_error'] = {'code': 'ORIGINAL_ANALYSIS_NONFINITE'}
        return result
    return result | analysis
