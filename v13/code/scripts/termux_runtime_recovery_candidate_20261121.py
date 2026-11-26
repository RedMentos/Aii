"""Compose the current pinned recovery/runtime candidate with consent-bound RAW EAR.

The existing V13 arithmetic, source-span C4 and postcommit overlays remain
owned by the base builder. This wrapper adds only the A5 audio consumer.
"""
import hashlib
import importlib.util
from pathlib import Path

BASE_BUILDER = "scripts/termux_runtime_recovery_candidate_20261112.py"
BASE_BUILDER_BLOB_SHA1 = "1ca110b36637318861c0aa4504fc2bd3ca01382d"
AUDIO_BUILDER = "scripts/integrated_audio_context_candidate_20261121.py"
AUDIO_BUILDER_BLOB_SHA1 = "831080bceec90711bd42e0fa4eba47c669975c98"
C4_RECEIPT_BUILDER = "scripts/integrated_c4_c3_receipt_candidate_20261122.py"
C4_RECEIPT_SHA256 = "0f3aab12b64454eaa3b49ce4adf22e8a29aeae081c5f82e8376e54a22028dff3"
NATIVE_RECEIVER_BUILDER = "scripts/integrated_native_latent_receiver_candidate_20261122.py"
NATIVE_RECEIVER_BLOB_SHA1 = "0efda1003bf845b2a4cf95789ccb2acd95583baa"


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



AUDIO_COGNITION_PREVIOUS_BLOB_SHA1 = "06de0acf2c6d30d50301d5073f5569822edff813"
AUDIO_COGNITION_CURRENT_BLOB_SHA1 = "deb8c274022e2a4419dd38adb11ca14481c4bd91"


def _rebind_audio_cognition_pin(code_dir: Path, audio) -> None:
    """Rebind only the exact Cognition blob updated by the current Perception base.

    The Perception-owned audio composer still pins the prior Cognition blob.
    All its other source pins remain unchanged and are checked by apply_sources().
    """
    path = code_dir / "v13/cognition.py"
    if path.is_symlink() or not path.is_file():
        raise ValueError("current Perception Cognition source missing or unsafe")
    actual = _git_blob_sha1(path.read_bytes())
    if actual != AUDIO_COGNITION_CURRENT_BLOB_SHA1:
        raise ValueError("current Perception Cognition source differs from the reviewed exact blob")
    pins = getattr(audio, "SOURCE_BLOBS", None)
    if (not isinstance(pins, dict)
            or pins.get("v13/cognition.py") != AUDIO_COGNITION_PREVIOUS_BLOB_SHA1):
        raise ValueError("Perception audio Cognition pin changed; a new review is required")
    rebound = dict(pins)
    rebound["v13/cognition.py"] = actual
    audio.SOURCE_BLOBS = rebound


def build_sources(code_dir: Path, *, include_postcommit=True):
    code_dir = Path(code_dir).resolve(strict=True)
    base = _load(code_dir, BASE_BUILDER, BASE_BUILDER_BLOB_SHA1)
    audio = _load(code_dir, AUDIO_BUILDER, AUDIO_BUILDER_BLOB_SHA1)
    _rebind_audio_cognition_pin(code_dir, audio)

    result = base.build_sources(code_dir, include_postcommit=include_postcommit)
    focal_before = result.get("v13/focal.py")
    runtime_before = result.get("v13/runtime.py")
    if not isinstance(focal_before, bytes) or b"SCALE_AWARE_C4_RULE" not in focal_before:
        raise ValueError("base stage no longer contains the reviewed source-span C4 overlay")
    if not isinstance(runtime_before, bytes) or b"LOCAL_EXACT_ARITHMETIC" not in runtime_before:
        raise ValueError("base stage no longer contains the reviewed bounded arithmetic route")

    composed = audio.apply_sources(code_dir, result)
    # The base composer already applies the fair B1/B2 observer overlay. The
    # audio overlay must preserve it; fail closed rather than reapply Runtime.
    if b"minimum_role_slice_s" not in composed.get("v13/cognition.py", b""):
        raise ValueError("A5 audio composition removed the Core observer fair-budget path")
    receipt_path = code_dir / C4_RECEIPT_BUILDER
    if receipt_path.is_symlink() or not receipt_path.is_file():
        raise ValueError("Core C4 receipt overlay missing or unsafe")
    receipt_raw = receipt_path.read_bytes()
    if hashlib.sha256(receipt_raw).hexdigest() != C4_RECEIPT_SHA256:
        raise ValueError("Core C4 receipt overlay source changed")
    receipt_spec = importlib.util.spec_from_file_location(
        "v14_core_c4_c3_receipt", receipt_path)
    if receipt_spec is None or receipt_spec.loader is None:
        raise RuntimeError("Core C4 receipt overlay is not loadable")
    receipt_module = importlib.util.module_from_spec(receipt_spec)
    receipt_spec.loader.exec_module(receipt_module)
    composed = receipt_module.apply_sources(code_dir, composed)
    native_receiver = _load(code_dir, NATIVE_RECEIVER_BUILDER, NATIVE_RECEIVER_BLOB_SHA1)
    composed = native_receiver.apply_sources(code_dir, composed)
    if b"def native_receive(" not in composed.get("v13/cognition.py", b""):
        raise ValueError("native receiver Cognition path was not composed")
    if b"native-probe" not in composed.get("v13/callosum.py", b""):
        raise ValueError("native receiver operator path was not composed")
    if b"c4_offer_context_ready" not in composed.get("v13/cognition.py", b""):
        raise ValueError("Core C4 context-ready receipt was not composed")
    if b"minimum_role_slice_s" not in composed.get("v13/cognition.py", b""):
        raise ValueError("Core observer fair-budget path missing after C4 receipt composition")
    if composed.get("v13/focal.py") != focal_before:
        raise ValueError("A5 audio composition must not replace the existing C4 body integration")
    if b"LOCAL_EXACT_ARITHMETIC" not in composed.get("v13/runtime.py", b""):
        raise ValueError("A5 audio composition removed the existing exact arithmetic path")
    if b"audio_consent_lease" not in composed.get("v13/runtime.py", b""):
        raise ValueError("Runtime-wide A5 consent lease was not composed")
    if "v13/audio_context_store.py" not in composed:
        raise ValueError("consent-bound audio context store was not produced")
    return composed
