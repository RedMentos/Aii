"""Strict finite Sleep policy input validation; no authority or sampling changes."""
import math


def validate_quiet_hours(hours):
    if hours is None:
        return
    if not (isinstance(hours, list) and len(hours) == 2 and
            all(type(h) is int and 0 <= h <= 23 for h in hours)):
        raise ValueError('quiet_hours [Start,Ende] in Stunden')


def validate_mix(mix, expected):
    if not isinstance(mix, dict) or set(mix) != set(expected):
        raise ValueError('mix recent/protected_old/failure >=0')
    values = list(mix.values())
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('mix requires finite nonnegative weights')
    try:
        total = math.fsum(values)
    except OverflowError as exc:
        raise ValueError('mix weight sum overflow') from exc
    if not math.isfinite(total) or total <= 0:
        raise ValueError('mix total must be finite and positive')
