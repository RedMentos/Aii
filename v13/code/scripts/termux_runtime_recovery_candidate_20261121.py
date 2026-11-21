"""Compose the current pinned recovery stage with the additive RAW EAR voice-context consumer.

The base candidate retains arithmetic, observer, ContextOS and existing Runtime paths.
The audio overlay modifies only the disposable staged tree; it never edits frozen source.
"""
import hashlib
import importlib.util
from pathlib import Path

BASE_BUILDER = "scripts/termux_runtime_recovery_candidate_20261112.py"
BASE_BUILDER_SHA256 = "e06bb5778aeadbd685b8da6cbedff0525692313801931a6a9118ec436fc7480f"
AUDIO_BUILDER = "scripts/integrated_audio_context_candidate_20261121.py"
AUDIO_BUILDER_SHA256 = "569e5c593e6cb4891573ece5f3f4e1c23600200dac7186cd9731e3243aad47d0"


def _load(code_dir, relative, expected, label):
    path = code_dir / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError(label + " builder missing or unsafe")
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError(label + " builder source changed")
    spec = importlib.util.spec_from_file_location("v14_" + label + "_stage", path)
    if spec is None or spec.loader is None:
        raise ValueError(label + " builder cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_sources(code_dir, *, include_postcommit=True):
    """Return one composed source map for the existing isolated stager."""
    code_dir = Path(code_dir)
    base = _load(code_dir, BASE_BUILDER, BASE_BUILDER_SHA256, "base")
    audio = _load(code_dir, AUDIO_BUILDER, AUDIO_BUILDER_SHA256, "audio")
    sources = base.build_sources(code_dir, include_postcommit=include_postcommit)
    return audio.apply_sources(code_dir, sources)
