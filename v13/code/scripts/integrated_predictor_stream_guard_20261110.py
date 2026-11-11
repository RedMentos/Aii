"""Layer source-bound streaming admission over the #1716 JEPA test copy.

Only materializes reviewed source bytes for disposable copies; the frozen
production Runtime and predictor are never changed by this script.
"""
import hashlib
import importlib.util
from pathlib import Path

JEPA_BUILDER_SHA = 'dccda1145833c6c8b5a7440d9e2345e67b0078ca1a4d130e6aaa86f169f951ef'
PREVIOUS_WORLD_SHA = '027f51b9c0fff5e69369adff7faf48343dd7da606154c69c7d5c967f9cf7356d'
WORLD_MODEL_OLD = b"        self.model=OnlinePredictor(7,len(world_model.ACTIONS),self.home,lr=lr,replay=replay)\n"
WORLD_MODEL_NEW = WORLD_MODEL_OLD + b"        self.model._world_source_bound=True\n"
STREAM_OLD = b'''        if type(checkpoint_every) is not int or not 1<=checkpoint_every<=1024:
            raise ValueError('Invalid checkpoint cadence')
        count=0;last=None
'''
STREAM_NEW = b'''        if type(checkpoint_every) is not int or not 1<=checkpoint_every<=1024:
            raise ValueError('Invalid checkpoint cadence')
        # Bound models require per-source validation and co-committed receipts.
        # Reject before consuming the iterator or touching weights/replay/RNG.
        if getattr(self,'_world_source_bound',False) or self.metadata is not None:
            raise ValueError('Source-bound predictor requires the validated OnlineWorld update path')
        count=0;last=None
'''


def _replace_once(data, old, new, label):
    if data.count(old) != 1:
        raise ValueError('unexpected ' + label + ' source')
    return data.replace(old, new, 1)


def build_sources(code_dir):
    code_dir = Path(code_dir)
    builder = code_dir / 'scripts/integrated_jepa_guard_candidate_20261110.py'
    if hashlib.sha256(builder.read_bytes()).hexdigest() != JEPA_BUILDER_SHA:
        raise ValueError('JEPA integration builder source changed')
    spec = importlib.util.spec_from_file_location('verified_jepa_builder', builder)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.build_sources(code_dir)
    world = result['v13/online_world.py']
    if hashlib.sha256(world).hexdigest() != PREVIOUS_WORLD_SHA:
        raise ValueError('integrated OnlineWorld source changed')
    world = _replace_once(world, WORLD_MODEL_OLD, WORLD_MODEL_NEW, 'OnlineWorld binding')
    predictor = result['v13/continuous_predictor.py']
    result['v13/continuous_predictor.py'] = _replace_once(predictor, STREAM_OLD, STREAM_NEW, 'predictor stream')
    guard = result['v13/world_jepa_runtime_guard_candidate.py']
    guard = _replace_once(guard, PREVIOUS_WORLD_SHA.encode(), hashlib.sha256(world).hexdigest().encode(), 'JEPA World source pin')
    result['v13/online_world.py'] = world
    result['v13/world_jepa_runtime_guard_candidate.py'] = guard
    return result
