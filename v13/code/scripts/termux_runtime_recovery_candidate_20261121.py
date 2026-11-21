"""Composed V13 staged runtime builder with the reviewed A5 audio overlay."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

BASE_BUILDER = "scripts/termux_runtime_recovery_candidate_20261112.py"
BASE_BUILDER_SHA256 = "16ba5fc3a6535c737502151a0a6362f067acedcd7102425086df4721b071b34a"
AUDIO_BUILDER = "scripts/integrated_audio_context_candidate_20261121.py"
AUDIO_BUILDER_SHA256 = "c1bcef1ccc7c0a40747f68b6245ee141e4b1f3f72f39b482fbaf4b2a61f4db91"


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
    return audio.apply_sources(code_dir, sources)
