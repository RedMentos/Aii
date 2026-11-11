"""Preserved pre-fix actual numeric mutation, run only on its pinned original stage."""
from v13 import authority, world_model
from v13.runtime import Runtime
from integrated_jepa_disposable_cases import populate


def test_original_record_only_counterexample(tmp_path):
    runtime = Runtime(tmp_path)
    try:
        populate(runtime)
        assert runtime.cfg['learning_mode'] == 'RECORD_ONLY'
        assert runtime.store.state(world_model.KEY, None)[0] is None
        result = authority.job(runtime, 'learn_medium')
        state = runtime.store.state(world_model.KEY, None)[0]
        assert result['world_model'] == state['status'] == 'FITTED'
        assert state['n'] >= 32 and any(value for row in state['forward'][0] for value in row)
        print('LEGACY_RECORD_ONLY_COUNTEREXAMPLE confirmed: actual numeric Ridge persisted')
    finally:
        runtime.close()
