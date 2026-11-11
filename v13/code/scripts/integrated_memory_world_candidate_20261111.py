"""Compose source lifecycle/archive guards with the C3/Body/World test copy."""
import hashlib
import importlib.util
from pathlib import Path

BASE_BUILDER_SHA = '262bf0a9042a99a85b0171313e33e8940df0f76c3495a83b9ef63881550f3ef1'
LIFECYCLE_BUILDER_SHA = 'a92a9fd220608d1901fd8cdb86cc56aeda93e554cc9b9b258fea8049d202d192'
ORIGINAL_STORE_SHA = 'fe66f92533b20738b5ec384e9d7c0b5ac8b4b4f658c6c1ad23792d813ff29980'


def _load(path, expected, label):
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError(label + ' builder source changed')
    spec = importlib.util.spec_from_file_location('verified_' + label, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_sources(code_dir):
    code_dir = Path(code_dir)
    base = _load(code_dir / 'scripts/integrated_c3_resume_candidate_20261110.py',
                 BASE_BUILDER_SHA, 'C3/Body/World')
    lifecycle = _load(code_dir / 'scripts/source_lifecycle_lock_integration_candidate.py',
                      LIFECYCLE_BUILDER_SHA, 'source lifecycle')
    result = base.build_sources(code_dir)
    additions = {'v13/' + name: data for name, data in lifecycle.build_sources(code_dir / 'v13').items()}
    overlap = set(result).intersection(additions)
    if overlap:
        raise ValueError('lifecycle candidate would replace prior integration: ' + ', '.join(sorted(overlap)))
    guard = result['v13/world_jepa_runtime_guard_candidate.py']
    old = ORIGINAL_STORE_SHA.encode()
    if guard.count(old) != 1:
        raise ValueError('unexpected World-JEPA Store source pin')
    result['v13/world_jepa_runtime_guard_candidate.py'] = guard.replace(
        old, hashlib.sha256(additions['v13/store.py']).hexdigest().encode(), 1)
    result.update(additions)
    return result
