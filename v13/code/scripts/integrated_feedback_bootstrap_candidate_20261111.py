"""Compose event-bound feedback previews and offline dataset catalog with V13."""
import hashlib
import importlib.util
from pathlib import Path

BASE_BUILDER_SHA = '9c55c04c8dd88255a47d0823e0e7bd3aefea05d2f43aadcad33469129979bcb5'
PINS = {
    'v13/inputs.py': '235cce055cdc5eb1c889593dd279d9c837a718f0630b8427223a3883c5079539',
    'v13/actionlearn.py': '603e874d8fbb37f41aee1fae5fcb6c07007310388dc2c653f1b84ec5d264a7d6',
    'v13/world_semantic_evidence_candidate.py': '354306bb763fda116728bd13e8502d81ed8e6a790c4387d98e0920960a87b8a5',
    'v13/local_error_route_shadow_candidate.py': '87bb77ed43b739fb890308fa565d0ca4a84278992a2312e219122c358f2c5187',
    'v13/c5_feedback_shadow_store_candidate.py': '20096bd965100c7d3fb1c6084c6f49c361567f331a2a5f374f5e2afa539a87bc',
    'v13/c5_feedback_ledger_candidate.py': '6e86e4fa2e6f359a13a0a6567be5bb095c4ba6b7e0254f536588d46b96563c21',
    'v13/skill_parity_shadow_candidate.py': 'd6d14a22a5d7cc06191edba97ece3412b84346de7896604ed18b73f3abd51756',
    'v13/dataset_probe_candidate.py': '7a2c5615cf9742f87ae67a6f599d3a8c084866c7a899a95e9e15f42eee939c16',
    'specs/bootstrap_dataset_catalog_20261109.json': '53c4d35d0b7b9348282b8e5e5877156969e1bcf6f37aa8bd8ee25aa751f1df2b',
    'candidates/feedback_semantic_20261111/inputs.py.txt': 'e9ecad21980e07c91807f7f9fe7f4472c5ec0e2a07c5cadc666962d8e61e2942',
    'candidates/feedback_semantic_20261111/actionlearn.py.txt': 'eff43a5f6590130b478d5c288debaa548b01ac1133d4b46ba500ec63beee546e',
}
OLD_STORE = 'fe66f92533b20738b5ec384e9d7c0b5ac8b4b4f658c6c1ad23792d813ff29980'
OLD_MEMORY = '391668fff0b4ad3d7c36d5d7a9823055ff74821c10f71b945e87edaa62597484'


def _replace_once(data, old, new, label):
    if data.count(old) != 1:
        raise ValueError('unexpected feedback ' + label + ' source')
    return data.replace(old, new, 1)


def build_sources(code_dir):
    code_dir = Path(code_dir)
    builder = code_dir / 'scripts/integrated_memory_world_candidate_20261111.py'
    if hashlib.sha256(builder.read_bytes()).hexdigest() != BASE_BUILDER_SHA:
        raise ValueError('memory/world builder source changed')
    raw = {}
    for name, expected in PINS.items():
        data = (code_dir / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('feedback/bootstrap source changed: ' + name)
        raw[name] = data
    spec = importlib.util.spec_from_file_location('verified_memory_world_builder', builder)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.build_sources(code_dir)
    semantic = raw['v13/world_semantic_evidence_candidate.py']
    for name, old in (('store.py', OLD_STORE), ('memory.py', OLD_MEMORY)):
        semantic = _replace_once(semantic, old.encode(),
                                 hashlib.sha256(result['v13/' + name]).hexdigest().encode(), name + ' pin')
    local = _replace_once(raw['v13/local_error_route_shadow_candidate.py'],
                          PINS['v13/world_semantic_evidence_candidate.py'].encode(),
                          hashlib.sha256(semantic).hexdigest().encode(), 'semantic pin')
    result['v13/inputs.py'] = raw['candidates/feedback_semantic_20261111/inputs.py.txt']
    result['v13/actionlearn.py'] = raw['candidates/feedback_semantic_20261111/actionlearn.py.txt']
    result['v13/world_semantic_evidence_candidate.py'] = semantic
    result['v13/local_error_route_shadow_candidate.py'] = local
    return result
