"""Materialize exact #1652 fixture/row-count corrections only in a test copy.

This corrects the source's selection arithmetic, but does not add atomic
postcheck handling and is not a runtime integration recommendation.
"""
import hashlib
from pathlib import Path

PINS = {
    'v13/world_jepa_replay.py': '57e075c2a0345948b7b8d68422b3b67ea9d357e1b8e18724f9254225e9ed8a52',
    'tests/test_world_jepa_replay_20261109.py': 'def4a0c8b32058eda88ad751d59ccda0d7d9daeed02d992ce6b9eb6e91d3ef5d',
}
REPLACEMENTS = {
    'v13/world_jepa_replay.py': (
        (b'count = min(MAX_ROWS, len(n) + len(r))', b'count = min(MAX_ROWS, len(n[0]) + len(r[0]))'),
        (b'replay_count = min(len(r), round(count * replay_fraction))', b'replay_count = min(len(r[0]), round(count * replay_fraction))'),
        (b'new_count = min(len(n), count - replay_count)', b'new_count = min(len(n[0]), count - replay_count)'),
        (b'ni = rng.choice(len(n), new_count, replace=False)', b'ni = rng.choice(len(n[0]), new_count, replace=False)'),
        (b'ri = rng.choice(len(r), replay_count, replace=False)', b'ri = rng.choice(len(r[0]), replay_count, replace=False)'),
    ),
    'tests/test_world_jepa_replay_20261109.py': (
        (b'np.tile([[1., 0.], [0., 1.]], (n + 1) // 2)[:n]',
         b'np.tile([[1., 0.], [0., 1.]], ((n + 1) // 2, 1))[:n]'),
    ),
}


def build_sources(code_dir):
    code_dir = Path(code_dir)
    result = {}
    for name, expected in PINS.items():
        raw = (code_dir / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('unsupported replay source: ' + name)
        for old, new in REPLACEMENTS[name]:
            if raw.count(old) != 1:
                raise ValueError('ambiguous replay candidate anchor: ' + name)
            raw = raw.replace(old, new, 1)
        result[name] = raw
    return result
