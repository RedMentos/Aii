"""Synthetic scheduling regressions; not a Redmi native timing claim."""
import pytest
from v13 import observer_schedule as obs


def test_two_roles_each_receive_a_bounded_slice_and_keep_peer_reentry():
    plan = obs.plan('A_THEN_B_SEQUENTIAL', ['B1_DETAIL', 'B2_GIST'], 'event')
    calls = []
    ticks = iter([0.0, 0.0, 4.0, 4.0])
    def ask(role, peer, role_end):
        calls.append((role, peer, role_end))
        return role
    result = obs.run(plan, ask, 10.0, lambda *_: None,
                     clock=lambda: next(ticks), budgeted=True)
    assert result == ['B1_DETAIL', 'B2_GIST']
    assert calls == [('B1_DETAIL', True, 5.0), ('B2_GIST', True, 10.0)]


def test_fairness_never_extends_global_deadline():
    assert obs.role_deadline(10.0, 4.0, 2) == 7.0
    assert obs.role_deadline(10.0, 12.0, 2) == 10.0
    with pytest.raises(ValueError):
        obs.role_deadline(10.0, 4.0, 0)


def test_legacy_call_signature_unchanged_when_not_budgeted():
    p = obs.plan('B_THEN_A_SEQUENTIAL', ['B1_DETAIL', 'B2_GIST'], 'e')
    calls = []
    result = obs.run(p, lambda role, peer: calls.append((role, peer)) or role,
                     100.0, lambda *_: None, clock=lambda: 0.0)
    assert result == ['B2_GIST', 'B1_DETAIL']
    assert calls == [('B2_GIST', True), ('B1_DETAIL', True)]


def test_first_body_error_does_not_prevent_second_body_attempt():
    p = obs.plan('A_THEN_B_SEQUENTIAL', ['B1_DETAIL', 'B2_GIST'], 'e')
    seen = []
    def ask(role, peer, end):
        seen.append((role, end))
        if role == 'B1_DETAIL':
            raise RuntimeError('native timeout')
        return role
    result = obs.run(p, ask, 10.0, lambda *_: None,
                     clock=lambda: 0.0, budgeted=True)
    assert result == ['B2_GIST']
    assert seen == [('B1_DETAIL', 5.0), ('B2_GIST', 10.0)]
