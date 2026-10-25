"""WP-DS3 selective uncertainty lab: fixed-grid empirical risk/coverage gate.

No Runtime import or live consumer. This is NOT conformal prediction and gives
no guarantee under distribution shift or uncalibrated C3 confidence. No tools
are executed; VERIFY_TOOL_PROPOSAL is only a lab decision label.
"""
import hashlib
import hmac
import json
import math

REVISION = 'ds3-selective-lab-v1'
GRID = (0.5, 0.6, 0.7, 0.8, 0.9, 0.95)
TARGET_RISK = 0.10
DELTA = 0.05
MIN_SELECTED = 200
ACTIONS = ('ANSWER', 'ASK_USER', 'VERIFY_TOOL_PROPOSAL', 'ABSTAIN')


def _score(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1


def _id_hash(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _seal(policy):
    # Tamper-evident checksum, NOT authentication against a malicious writer.
    # No live consumer may trust this self-contained lab checksum as a signature.
    doc = {k: v for k, v in policy.items() if k != 'integrity_sha256'}
    return hashlib.sha256(json.dumps(doc, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def _valid_policy(policy):
    if not isinstance(policy, dict) or policy.get('revision') != REVISION:
        return False
    try:
        if not hmac.compare_digest(policy['integrity_sha256'], _seal(policy)):
            return False
        if (policy.get('authority') != 'LAB_ONLY'
                or policy.get('tool_execution_authority') is not False
                or policy.get('target_risk') != TARGET_RISK
                or policy.get('delta') != DELTA
                or policy.get('grid') != list(GRID)):
            return False
        if policy.get('status') == 'ABSTAIN_ALL':
            return policy.get('threshold') is None
        if policy.get('status') != 'CALIBRATED':
            return False
        t = policy.get('threshold')
        bound = policy.get('risk_upper_bound')
        n = policy.get('selected_count')
        return (type(t) in (int, float) and t in GRID
                and type(bound) in (int, float) and math.isfinite(bound)
                and bound <= TARGET_RISK
                and type(n) is int and n >= MIN_SELECTED)
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


def _rows(rows, split):
    if not isinstance(rows, (list, tuple)):
        raise ValueError('ROWS_NOT_SEQUENCE')
    seen = set()
    out = []
    for row in rows:
        if not isinstance(row, dict) or row.get('split') != split:
            raise ValueError('SPLIT_OR_ROW_INVALID')
        key = row.get('id')
        if not isinstance(key, str) or not key or len(key.encode()) > 128 or key in seen:
            raise ValueError('DUPLICATE_OR_INVALID_SAMPLE_ID')
        if not _score(row.get('confidence')) or type(row.get('correct')) is not bool:
            raise ValueError('INVALID_SCORE_OR_LABEL')
        seen.add(key)
        out.append((key, float(row['confidence']), row['correct']))
    return out


def calibrate(rows):
    """Choose lowest safe threshold on a *fixed* grid; otherwise abstain all.

    One-sided Hoeffding with a grid-size union bound is meaningful only under
    independent, identically distributed calibration/evaluation assumptions.
    """
    data = _rows(rows, 'calibration')
    hashes = sorted(_id_hash(key) for key, _, _ in data)
    digest = hashlib.sha256(json.dumps(hashes, separators=(',', ':')).encode()).hexdigest()
    result = {
        'revision': REVISION, 'authority': 'LAB_ONLY',
        'status': 'ABSTAIN_ALL', 'threshold': None,
        'target_risk': TARGET_RISK, 'delta': DELTA, 'min_selected': MIN_SELECTED,
        'grid': list(GRID), 'calibration_count': len(data),
        'calibration_id_hashes': hashes, 'calibration_digest': digest,
        'selected_count': 0, 'wrong_count': 0,
        'empirical_risk': None, 'risk_upper_bound': None,
        'guarantee_scope': 'IID_FIXED_GRID_ONLY_NOT_NATIVE_C3',
        'tool_execution_authority': False, 'age_promotion': False,
    }
    for threshold in GRID:
        selected = [(key, correct) for key, score, correct in data if score >= threshold]
        n = len(selected)
        if n < MIN_SELECTED:
            continue
        wrong = sum(not correct for _, correct in selected)
        risk = wrong / n
        upper = min(1., risk + math.sqrt(math.log(len(GRID) / DELTA) / (2 * n)))
        if upper <= TARGET_RISK:
            result.update(status='CALIBRATED', threshold=threshold,
                          selected_count=n, wrong_count=wrong,
                          empirical_risk=risk, risk_upper_bound=upper)
            break
    result['integrity_sha256'] = _seal(result)
    return result


def decide(confidence, calibration, *, ask_user=False, tool_permitted=False):
    """Only returns a proposal; no tool call, answer text or live authority."""
    action, reason = 'ABSTAIN', 'UNAVAILABLE_OR_UNCALIBRATED'
    if (type(ask_user) is not bool or type(tool_permitted) is not bool
            or not _valid_policy(calibration)
            or not _score(confidence)):
        reason = 'INVALID_OR_MISSING_INPUT'
    elif (calibration.get('status') == 'CALIBRATED'
          and calibration.get('threshold') in GRID
          and type(calibration.get('threshold')) in (int, float)
          and calibration.get('authority') == 'LAB_ONLY'
          and calibration.get('tool_execution_authority') is False):
        if confidence >= calibration['threshold']:
            action, reason = 'ANSWER', 'SELECTED_BY_LAB_THRESHOLD'
        elif tool_permitted:
            action, reason = 'VERIFY_TOOL_PROPOSAL', 'LOW_CONFIDENCE_TOOL_REQUIRES_APPROVAL'
        elif ask_user:
            action, reason = 'ASK_USER', 'LOW_CONFIDENCE_CLARIFICATION'
        else:
            reason = 'LOW_CONFIDENCE_ABSTENTION'
    return {'action': action, 'reason': reason, 'authority': 'LAB_ONLY',
            'external_action_executed': False, 'model_answer_generated': False,
            'learning_permission': 'NONE', 'age_promotion': False}


def evaluate(rows, calibration):
    """Evaluate on disjoint held-out synthetic labels; no fit or threshold update."""
    if not _valid_policy(calibration):
        raise ValueError('INVALID_CALIBRATION')
    data = _rows(rows, 'test')
    prior = calibration.get('calibration_id_hashes')
    if not isinstance(prior, list) or any(not isinstance(x, str) for x in prior):
        raise ValueError('INVALID_CALIBRATION_PROVENANCE')
    if any(_id_hash(key) in set(prior) for key, _, _ in data):
        raise ValueError('CALIBRATION_TEST_OVERLAP')
    decisions = [decide(score, calibration)['action'] for _, score, _ in data]
    selected = [(correct, action) for (_, _, correct), action in zip(data, decisions)
                if action == 'ANSWER']
    wrong = sum(not correct for correct, _ in selected)
    return {'revision': REVISION, 'authority': 'LAB_ONLY',
            'n_test': len(data), 'answered': len(selected), 'wrong': wrong,
            'coverage': len(selected) / len(data) if data else 0.,
            'selective_risk': wrong / len(selected) if selected else None,
            'all_test_risk': sum(not correct for _, _, correct in data) / len(data)
                             if data else None,
            'external_action_executed': False, 'age_promotion': False}
