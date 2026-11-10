"""Layer JEPA policy and lineage-bound checkpoints onto #1716's test copy."""
import hashlib
import importlib.util
from pathlib import Path

ONLINE_BUILDER_SHA = '8e3c1f1cf07e9d9c28c2c2eb71d670c07dd412e6db82f0832a95993a760df0a6'
GUARD_SHA = '2b23880b71bd302c9db2035e594b2e27f021f379f0fc02048c64e1efee66ba4f'
CHECKPOINT_SHA = '3e769da6b1b777088d1a5eaea26c04cf6bc116002b6e8dddd58440968442934e'
AGI_OLD = b'''    if args and args[0]=='jepa':
        if len(args)==2 and args[1]=='save':return dumps(r.world_jepa_save())
        if len(args)==2 and args[1]=='restore':return dumps(r.world_jepa_restore())
        if len(args)>3:raise ValueError('Usage: :growth jepa [STEPS] [LIMIT]')
        steps=int(args[1]) if len(args)>1 else 5
        limit=int(args[2]) if len(args)>2 else 256
        if not 1<=steps<=50 or not 16<=limit<=2048:
            raise ValueError('JEPA operator budget outside mobile-safe bounds')
        return dumps(r.world_jepa_update(steps=steps,limit=limit))
'''
AGI_NEW = b'''    if args and args[0]=='jepa':
        from .. import online_world_policy as policy
        if len(args)==2 and args[1]=='save':return dumps(r.world_jepa_save(authority=policy.HUMAN))
        if len(args)==2 and args[1]=='restore':return dumps(r.world_jepa_restore(authority=policy.HUMAN))
        if len(args)==2 and args[1]=='previous':return dumps(r.world_jepa_previous(authority=policy.HUMAN))
        if len(args)>3:raise ValueError('Usage: :growth jepa [STEPS] [LIMIT]')
        steps=int(args[1]) if len(args)>1 else 5
        limit=int(args[2]) if len(args)>2 else 256
        if not 1<=steps<=50 or not 16<=limit<=2048:
            raise ValueError('JEPA operator budget outside mobile-safe bounds')
        return dumps(r.world_jepa_update(steps=steps,limit=limit,authority=policy.HUMAN))
'''
RUNTIME_NEW = b'''    def world_jepa_update(self,steps=10,limit=2048,authority='SYSTEM'):
        from .world_jepa_runtime_guard_candidate import update
        return update(self,steps=steps,limit=limit,authority=authority)
    def world_jepa_save(self,authority='SYSTEM'):
        from .world_jepa_lineage_checkpoint_candidate import save
        return save(self,authority=authority)
    def world_jepa_restore(self,authority='SYSTEM'):
        from .world_jepa_lineage_checkpoint_candidate import restore
        return restore(self,authority=authority)
    def world_jepa_previous(self,authority='SYSTEM'):
        from .world_jepa_lineage_checkpoint_candidate import restore
        return restore(self,authority=authority,previous=True)
'''


def build_sources(code_dir):
    code_dir = Path(code_dir)
    builder_path = code_dir / 'scripts/integrated_online_world_candidate_20261110.py'
    if hashlib.sha256(builder_path.read_bytes()).hexdigest() != ONLINE_BUILDER_SHA:
        raise ValueError('online-world composition source changed')
    guard = (code_dir / 'v13/world_jepa_runtime_guard_candidate.py').read_bytes()
    if hashlib.sha256(guard).hexdigest() != GUARD_SHA:
        raise ValueError('JEPA guard source changed')
    checkpoint = (code_dir / 'v13/world_jepa_lineage_checkpoint_candidate.py').read_bytes()
    if hashlib.sha256(checkpoint).hexdigest() != CHECKPOINT_SHA:
        raise ValueError('JEPA lineage checkpoint source changed')
    spec = importlib.util.spec_from_file_location('verified_online_builder', builder_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.build_sources(code_dir)
    runtime = result['v13/runtime.py']
    start = runtime.index(b'    def world_jepa_update(self,steps=10,limit=2048):\n')
    end = runtime.index(b'    def notice(self,text):', start)
    result['v13/runtime.py'] = runtime[:start] + RUNTIME_NEW + runtime[end:]
    agi = result['v13/agi/__init__.py']
    if agi.count(AGI_OLD) != 1:
        raise ValueError('JEPA operator anchor changed')
    result['v13/agi/__init__.py'] = agi.replace(AGI_OLD, AGI_NEW, 1)
    result['v13/world_jepa_runtime_guard_candidate.py'] = guard
    result['v13/world_jepa_lineage_checkpoint_candidate.py'] = checkpoint
    return result
