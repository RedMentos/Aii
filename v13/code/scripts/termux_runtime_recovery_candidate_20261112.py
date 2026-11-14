"""Compose phone recovery into the existing pinned integrated review tree.

Frozen source files are only read. The ordinary stager writes the complete
review copy, with its source manifest, before any explicit local activation.
"""
import hashlib
import importlib.util
from pathlib import Path

BUILDERS = {
    'scripts/integrated_world_training_resume_candidate_20261111.py': '82e2fd27712d17a489ce5fd2f75d749f3f0e08dcc9d7fcc8852bbe6f738e8e18',
    'scripts/termux_probe_recovery_candidate_20261112.py': '27aec15dc1f003fd2c90d3d5a08d5a4a9af223ab57c188720ea9cd18aebc1b2b',
    'scripts/termux_chat_recovery_candidate_20261112.py': 'e0885ebc04ae16826f2a8d5cc3210ddc2f76d1ef40d22824190deaafaa13ffa8',
    'scripts/termux_idle_recovery_candidate_20261112.py': '97887387b927f9e30a06b9883253e9b866b5c579da97cfbb4f24788d1102817f',
}


def load(code_dir, relative, expected):
    path = code_dir / relative
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('Termux recovery builder source changed: ' + relative)
    spec = importlib.util.spec_from_file_location('recovery_' + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_sources(code_dir):
    code_dir = Path(code_dir)
    modules = [load(code_dir, name, pin) for name, pin in BUILDERS.items()]
    base, probe, chat, idle = modules
    result = base.build_sources(code_dir)
    for name, raw in probe.build_sources(code_dir).items():
        if name in result:
            raise ValueError('Upstream probe source changed; review composition')
        result[name] = raw
    chat.build_sources(code_dir)  # validate frozen inputs as well as anchors
    composed = {name: result.get(name, (code_dir / name).read_bytes())
                for name in chat.SOURCE_PINS}
    result.update(chat.apply_sources(composed))
    result = idle.apply_sources(code_dir, result)
    for name, raw in result.items():
        if name.endswith('.py'):
            compile(raw, name, 'exec')
    return result
