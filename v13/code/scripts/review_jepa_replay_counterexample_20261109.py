"""Exercise exact PR #1652 module with synthetically identifiable rows."""
import json
import numpy as np
from v13.world_jepa_replay import replay_update

class Probe:
    def __init__(self):
        self.batch = None
    def prediction_loss(self, *_args):
        return 1.0
    def partial_fit(self, x, a, y, **_kwargs):
        self.batch = x.copy()

class InvalidAfterUpdate:
    def __init__(self):
        self.weight = 0
        self.calls = 0
    def prediction_loss(self, *_args):
        self.calls += 1
        return 1.0 if self.calls < 3 else float('nan')
    def partial_fit(self, *_args, **_kwargs):
        self.weight = 7

def rows(offset):
    x = np.arange(12, dtype=float).reshape(-1, 1) + offset
    actions = np.zeros((12, 1), dtype=float)
    return x, actions, x + 1

n, r, old, new = rows(0), rows(100), rows(200), rows(300)
m = Probe()
result = replay_update(m, n, r, old, new, steps=1, replay_fraction=.25, seed=3)
observed = sorted(int(x) for x in m.batch[:, 0])
assert result['new_train_rows'] == 3
assert result['replay_train_rows'] == 2
assert set(observed).issubset({0, 1, 2, 100, 101, 102})
failed = InvalidAfterUpdate()
try:
    replay_update(failed, n, r, old, new, steps=1)
except ValueError as exc:
    assert str(exc) == 'nonfinite post-update retention'
else:
    raise AssertionError('expected nonfinite retention to fail')
assert failed.weight == 7
print(json.dumps({'available_new_rows': 12, 'available_replay_rows': 12,
                  'selected_new_rows': result['new_train_rows'],
                  'selected_replay_rows': result['replay_train_rows'],
                  'selected_row_ids': observed, 'model_weight_after_failed_postcheck': failed.weight}, sort_keys=True))
