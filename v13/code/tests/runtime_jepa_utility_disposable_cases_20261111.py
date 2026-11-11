"""Real Runtime/SQLite WorldJEPA utility readback; synthetic, not Redmi evidence."""
import json
import math
import numpy as np
from v13.runtime import Runtime
from v13.operator import Operator
from v13 import world_model
from v13.world_jepa_action_outcome_adapter import build
from integrated_jepa_disposable_cases import populate

def test_runtime_disjoint_holdout_before_after_restart(tmp_path):
    runtime = Runtime(tmp_path)
    try:
        populate(runtime)  # actual synthetic Runtime turns, committed to SQLite
        operator = Operator(runtime)
        operator.run(':learning shadow')
        rows = world_model.transitions(runtime.store, limit=160)
        split = build(rows)  # canonical content/ID-disjoint split
        assert not (set(split['train_action_ids']) & set(split['holdout_action_ids']))
        assert len(split['holdout_action_ids']) > 0
        first = json.loads(operator.run(':growth jepa 1 160'))
        assert first['trained'] and first['source_verified']
        initial = runtime._world_jepa_online.prediction_loss(*split['holdout'])
        assert math.isfinite(initial)
        second = json.loads(operator.run(':growth jepa 1 160'))
        before, after = second['holdout_loss_before'], second['holdout_loss_after']
        assert math.isfinite(before) and math.isfinite(after)
        assert np.isclose(before, initial, atol=1e-10, rtol=1e-10)
        assert np.isclose(after, runtime._world_jepa_online.prediction_loss(*split['holdout']), atol=1e-10, rtol=1e-10)
        assert runtime._world_jepa_online._fit_steps == 2
        weights = runtime._world_jepa_online.enc['W1'].copy()
        receipt = dict(runtime._world_jepa_lineage)
        assert json.loads(operator.run(':growth jepa save'))['persisted']
        print('JEPA_HOLDOUT', json.dumps({'first':initial,'before':before,'after':after,'delta':after-before,'train_rows':len(split['train_action_ids']),'holdout_rows':len(split['holdout_action_ids'])},sort_keys=True))
        runtime.close()
        runtime = Runtime(tmp_path)
        operator = Operator(runtime)
        operator.run(':learning shadow')
        assert json.loads(operator.run(':growth jepa restore'))['restored']
        assert np.array_equal(runtime._world_jepa_online.enc['W1'], weights)
        assert runtime._world_jepa_lineage == receipt
        restored = runtime._world_jepa_online.prediction_loss(*split['holdout'])
        assert np.isclose(restored, after, atol=1e-10, rtol=1e-10)
        continued = json.loads(operator.run(':growth jepa 1 160'))
        assert continued['trained'] and runtime._world_jepa_online._fit_steps == 3
        assert math.isfinite(continued['holdout_loss_after'])
    finally:
        runtime.close()
