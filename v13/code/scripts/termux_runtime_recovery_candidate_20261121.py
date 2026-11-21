"""Composed V13 staged runtime builder: base + A5 audio + source-bound T8 shadow."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

BASE_BUILDER = "scripts/termux_runtime_recovery_candidate_20261112.py"
BASE_BUILDER_SHA256 = "16ba5fc3a6535c737502151a0a6362f067acedcd7102425086df4721b071b34a"
AUDIO_BUILDER = "scripts/integrated_audio_context_candidate_20261121.py"
AUDIO_BUILDER_SHA256 = "734a6786fec61c4fe15d8861e56b9303496b44967cd76327931908321844a17f"
ONLINE_BUILDER = "scripts/integrated_online_world_candidate_20261110.py"
ONLINE_BUILDER_SHA256 = "9edd375d308f3e1026a93ef0cb4bbe6a4fdc9cb5f4fcab2f73461133b9f514b0"


def _load(code_dir: Path, relative: str, expected_sha256: str):
    path = code_dir / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError("staged builder missing or symlink: " + relative)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("staged builder hash mismatch: " + relative)
    spec = importlib.util.spec_from_file_location("_v14_" + path.stem, path)
    if spec is None or spec.loader is None:
        raise ValueError("staged builder loader unavailable: " + relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_sources(code_dir: Path) -> dict[str, bytes]:
    code_dir = Path(code_dir).resolve(strict=True)
    base = _load(code_dir, BASE_BUILDER, BASE_BUILDER_SHA256)
    sources = base.build_sources(code_dir)
    audio = _load(code_dir, AUDIO_BUILDER, AUDIO_BUILDER_SHA256)
    sources = audio.apply_sources(code_dir, sources)
    # T8 is applied after A5 so its Runtime method composes with the audio turn path.
    online = _load(code_dir, ONLINE_BUILDER, ONLINE_BUILDER_SHA256)
    return online.build_sources(code_dir, base_sources=sources)
