"""Compose the current pinned recovery/runtime candidate with consent-bound RAW EAR.

The existing V13 arithmetic, source-span C4 and postcommit overlays remain
owned by the base builder. This wrapper adds only the A5 audio consumer.
"""
import hashlib
import importlib.util
from pathlib import Path

BASE_BUILDER = "scripts/termux_runtime_recovery_candidate_20261112.py"
BASE_BUILDER_BLOB_SHA1 = "2b4a5bdb8ce84a675f206685875f4d68eccee57d"
AUDIO_BUILDER = "scripts/integrated_audio_context_candidate_20261121.py"
AUDIO_BUILDER_BLOB_SHA1 = "39f7f7bb81529bd8875132ee4ac4e5a3a7e8d9ac"


def _git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _load(code_dir: Path, relative: str, expected: str):
    path = code_dir / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError("pinned audio composition input missing or unsafe: " + relative)
    if _git_blob_sha1(path.read_bytes()) != expected:
        raise ValueError("pinned audio composition input changed: " + relative)
    spec = importlib.util.spec_from_file_location("v14_audio_" + path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("pinned audio composition input is not loadable: " + relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_sources(code_dir: Path, *, include_postcommit=True):
    code_dir = Path(code_dir).resolve(strict=True)
    base = _load(code_dir, BASE_BUILDER, BASE_BUILDER_BLOB_SHA1)
    audio = _load(code_dir, AUDIO_BUILDER, AUDIO_BUILDER_BLOB_SHA1)

    result = base.build_sources(code_dir, include_postcommit=include_postcommit)
    focal_before = result.get("v13/focal.py")
    runtime_before = result.get("v13/runtime.py")
    if not isinstance(focal_before, bytes) or b"SCALE_AWARE_C4_RULE" not in focal_before:
        raise ValueError("base stage no longer contains the reviewed source-span C4 overlay")
    if not isinstance(runtime_before, bytes) or b"LOCAL_EXACT_ARITHMETIC" not in runtime_before:
        raise ValueError("base stage no longer contains the reviewed bounded arithmetic route")

    composed = audio.apply_sources(code_dir, result)
    if composed.get("v13/focal.py") != focal_before:
        raise ValueError("A5 audio composition must not replace the existing C4 body integration")
    if b"LOCAL_EXACT_ARITHMETIC" not in composed.get("v13/runtime.py", b""):
        raise ValueError("A5 audio composition removed the existing exact arithmetic path")
    if b"audio_consent_lease" not in composed.get("v13/runtime.py", b""):
        raise ValueError("Runtime-wide A5 consent lease was not composed")
    if "v13/audio_context_store.py" not in composed:
        raise ValueError("consent-bound audio context store was not produced")
    return composed
