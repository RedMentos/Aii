"""Deterministic synthetic software-only replay preview, no runtime updates."""
import json
import platform

import numpy as np

from v13.world_jepa import WorldJEPA
from v13.world_jepa_replay_shadow_candidate import preview_replay


def rows(n, offset):
    x = np.arange(n * 4, dtype=np.float64).reshape(n, 4) / 100 + offset
    a = np.eye(2, dtype=np.float64)[np.arange(n) % 2]
    return x, a, x + np.column_stack((a[:, 0] * .2, a[:, 1] * .3,
                                      np.zeros(n), np.zeros(n)))


def main():
    model = WorldJEPA(seed=3, ensemble=2).fit(*rows(24, -50.), steps=2, log_every=1)
    before = model.enc['W1'].copy()
    staged, report = preview_replay(model, rows(12, 0.), rows(12, 10.),
                                    rows(8, 20.), rows(8, 30.),
                                    steps=2, replay_fraction=.25, seed=3)
    result = {'schema': 'v13-jepa-replay-shadow-smoke-v1',
              'scope': 'SYNTHETIC_NUMPY_ONLY',
              'python': platform.python_version(), 'numpy': np.__version__,
              'model_seed': 3, 'baseline_steps': 2, 'preview_steps': 2,
              'encoder_original_unchanged': bool(np.array_equal(before, model.enc['W1'])),
              'encoder_proposal_delta_l2': float(np.linalg.norm(staged.enc['W1'] - before)),
              'report': report}
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main()
