"""Core Redmi P0 observer scheduling: synthetic deadline fairness checks."""
from v13 import observer_schedule as obs


def test_two_sequential_bodies_get_separate_deadline_opportunities():
    p = obs.plan('A_THEN_B_SEQUENTIAL', ['B1_DETAIL', 'B2_GIST'], 'event')
    assert obs.fair_deadline(p, 'B1_DETAIL', 20.0, clock=lambda: 0.0) == 10.0
    assert obs.fair_deadline(p, 'B2_GIST', 20.0, clock=lambda: 10.0) == 20.0


def test_reversed_order_reserves_time_for_b1():
    p = obs.plan('B_THEN_A_SEQUENTIAL', ['B1_DETAIL', 'B2_GIST'], 'event')
    assert obs.fair_deadline(p, 'B2_GIST', 20.0, clock=lambda: 0.0) == 10.0
    assert obs.fair_deadline(p, 'B1_DETAIL', 20.0, clock=lambda: 10.0) == 20.0


def test_single_parallel_and_short_windows_unchanged():
    one = obs.plan('A_THEN_B_SEQUENTIAL', ['B1_DETAIL'], 'event')
    assert obs.fair_deadline(one, 'B1_DETAIL', 20, clock=lambda: 0) == 20
    both = obs.plan('ALWAYS_BOTH_ASYNC', ['B1_DETAIL', 'B2_GIST'], 'event', parallel_ok=True)
    assert obs.fair_deadline(both, 'B1_DETAIL', 20, clock=lambda: 0) == 20
    sequential = obs.plan('A_THEN_B_SEQUENTIAL', ['B1_DETAIL', 'B2_GIST'], 'event')
    assert obs.fair_deadline(sequential, 'B1_DETAIL', 2, clock=lambda: 0) == 2
