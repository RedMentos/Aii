"""Compose reviewed Body-JEPA safeguards with the integrated World test copy."""
import hashlib
import importlib.util
from pathlib import Path

WORLD_BUILDER_SHA = 'd06103b6a10e1534cb3fb042bac20b72cc0372e31cc31b9a88827e60256a8ca6'
BODY_BUILDER_SHA = '00a02f3ad8e7f87d3f3e892c71046190e63773e51a4830a519200d20ac5eff47'


def _load_verified(path, expected, label):
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError(label + ' builder source changed')
    spec = importlib.util.spec_from_file_location('verified_' + label, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_sources(code_dir):
    code_dir = Path(code_dir)
    world = _load_verified(code_dir / 'scripts/integrated_predictor_history_guard_20261110.py',
                           WORLD_BUILDER_SHA, 'world')
    body = _load_verified(code_dir / 'scripts/body_jepa_anchor_guard_reconcile_candidate_20261110.py',
                          BODY_BUILDER_SHA, 'body')
    sources = world.build_sources(code_dir)
    additions = body.build_sources(code_dir)
    collisions = set(sources).intersection(additions)
    if collisions:
        raise ValueError('Body and World candidate paths overlap: ' + ', '.join(sorted(collisions)))
    sources.update(additions)
    return sources
