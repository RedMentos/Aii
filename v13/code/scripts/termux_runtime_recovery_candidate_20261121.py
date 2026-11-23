"""Compose the current pinned recovery/runtime candidate with consent-bound RAW EAR.

The existing V13 arithmetic, source-span C4 and postcommit overlays remain
owned by the base builder. This wrapper adds only the A5 audio consumer.
"""
import hashlib
import importlib.util
from pathlib import Path

BASE_BUILDER = "scripts/termux_runtime_recovery_candidate_20261112.py"
BASE_BUILDER_BLOB_SHA1 = "d3f2e2d361fa5bb3761463767f470098684b6003"
AUDIO_BUILDER = "scripts/integrated_audio_context_candidate_20261121.py"
AUDIO_BUILDER_BLOB_SHA1 = "ecefd90d533a5b4ad15c34e0a5e5976d41f332d8"
C4_RECEIPT_BUILDER = "scripts/integrated_c4_c3_receipt_candidate_20261122.py"
C4_RECEIPT_SHA256 = "0f3aab12b64454eaa3b49ce4adf22e8a29aeae081c5f82e8376e54a22028dff3"
NATIVE_RECEIVER_BUILDER = "scripts/integrated_native_latent_receiver_candidate_20261122.py"
NATIVE_RECEIVER_BLOB_SHA1 = "13dff8932d020c37be2cbf5a99d2bd228b504ee4"


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
