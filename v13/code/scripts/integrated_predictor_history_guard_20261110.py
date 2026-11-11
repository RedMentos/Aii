"""Fence source-bound predictor updates and predictions in a test copy."""
import hashlib
import importlib.util
from pathlib import Path

STREAM_BUILDER_SHA = '474d6bf02e60f481c25f30e49a4d3db2dd95c22d3bd7748e1e9860947f4dd3a1'
HISTORY_GUARD_SHA = '84600fbde2458b3a5ce8908f54721b3caa57f3d3c31a411a95368a437c9405de'
WORLD_CLASS_OLD = b'class OnlineWorld:\n'
WORLD_CLASS_NEW = b'class OnlineWorld:\n    MAX_HISTORY_RECEIPTS=MAX_RECEIPTS\n'
UPDATE_OLD = b'''            return self._update(limit,allowed)
'''
UPDATE_NEW = b'''            from .online_world_history_guard_candidate import guarded
            return guarded(self,lambda:self._update(limit,allowed))
'''
PREDICT_OLD = b'''            if self._unusable:raise RuntimeError('Online world needs review after stale source or failed recovery')
            return self.model.predict(x,world_model.ACTIONS.index(action))[4:].tolist()
'''
PREDICT_NEW = b'''            from .online_world_history_guard_candidate import guarded
            return guarded(self,lambda:self.model.predict(x,world_model.ACTIONS.index(action))[4:].tolist())
'''


def _replace_once(data, old, new, label):
    if data.count(old) != 1:
        raise ValueError('unexpected ' + label + ' source')
    return data.replace(old, new, 1)


def build_sources(code_dir):
    code_dir = Path(code_dir)
    builder = code_dir / 'scripts/integrated_predictor_stream_guard_20261110.py'
    if hashlib.sha256(builder.read_bytes()).hexdigest() != STREAM_BUILDER_SHA:
        raise ValueError('predictor stream builder source changed')
    guard = (code_dir / 'v13/online_world_history_guard_candidate.py').read_bytes()
    if hashlib.sha256(guard).hexdigest() != HISTORY_GUARD_SHA:
        raise ValueError('predictor history guard source changed')
    spec = importlib.util.spec_from_file_location('verified_stream_builder', builder)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.build_sources(code_dir)
    world = result['v13/online_world.py']
    old_world_sha = hashlib.sha256(world).hexdigest()
    world = _replace_once(world, WORLD_CLASS_OLD, WORLD_CLASS_NEW, 'OnlineWorld class')
    world = _replace_once(world, UPDATE_OLD, UPDATE_NEW, 'OnlineWorld update')
    world = _replace_once(world, PREDICT_OLD, PREDICT_NEW, 'OnlineWorld predict')
    jepa_guard = result['v13/world_jepa_runtime_guard_candidate.py']
    result['v13/world_jepa_runtime_guard_candidate.py'] = _replace_once(
        jepa_guard, old_world_sha.encode(), hashlib.sha256(world).hexdigest().encode(), 'JEPA World source pin')
    result['v13/online_world.py'] = world
    result['v13/online_world_history_guard_candidate.py'] = guard
    return result
