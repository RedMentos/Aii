"""Compose the current pinned recovery/runtime candidate with consent-bound RAW EAR and an exact greeting/ack reflex.

The existing V13 arithmetic, source-span C4 and postcommit overlays remain
owned by the base builder. This wrapper composes the A5 audio consumer, then a bounded exact greeting/ack reflex.
"""
import hashlib
import importlib.util
from pathlib import Path

BASE_BUILDER = "scripts/termux_runtime_recovery_candidate_20261112.py"
BASE_BUILDER_BLOB_SHA1 = "ee1b710b3ae665b1d2aeca7b6240a2bf43b5565c"
AUDIO_BUILDER = "scripts/integrated_audio_context_candidate_20261121.py"
AUDIO_BUILDER_BLOB_SHA1 = "3b71ea51272a3bc1bc82cb12ebae3bd5e96f51e1"
C4_RECEIPT_BUILDER = "scripts/integrated_c4_c3_receipt_candidate_20261122.py"
C4_RECEIPT_SHA256 = "0f3aab12b64454eaa3b49ce4adf22e8a29aeae081c5f82e8376e54a22028dff3"
NATIVE_RECEIVER_BUILDER = "scripts/integrated_native_latent_receiver_candidate_20261122.py"
NATIVE_RECEIVER_BLOB_SHA1 = "e237cbdb41defd0fde2f05c6baff6ad0ff9e1ad0"
GREETING_FASTPATH_BUILDER = "scripts/integrated_greeting_fastpath_candidate_20261127.py"
GREETING_FASTPATH_BLOB_SHA1 = "3c71a71b4171f49c20b57fadee190b22576fa953"


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



AUDIO_COGNITION_CURRENT_BLOB_SHA1 = "deb8c274022e2a4419dd38adb11ca14481c4bd91"


def _verify_audio_cognition_pin(code_dir: Path, audio) -> None:
    """Require Perception's own composer to pin the exact current Cognition bytes.

    Core verifies the cross-lane contract but never rewrites a Perception-owned
    source pin at runtime.
    """
    path = code_dir / "v13/cognition.py"
    if path.is_symlink() or not path.is_file():
        raise ValueError("current Perception Cognition source missing or unsafe")
    actual = _git_blob_sha1(path.read_bytes())
    if actual != AUDIO_COGNITION_CURRENT_BLOB_SHA1:
        raise ValueError("current Perception Cognition source differs from the reviewed exact blob")
    pins = getattr(audio, "SOURCE_BLOBS", None)
    if not isinstance(pins, dict) or pins.get("v13/cognition.py") != actual:
        raise ValueError("Perception audio Cognition pin does not match the current exact blob")



_PREANSWER_SIGNATURE = b"    def offer(self,role,e,version,deadline,peer=None,*,valid_until=None,focus=None):\n"
_PREANSWER_BUDGET_SIGNATURE = b"    def offer(self,role,e,version,deadline,peer=None,*,valid_until=None,focus=None,preanswer_budgeted=None):\n"
_PREANSWER_BODY = b"        preanswer_observer = valid_until is not None\n"
_PREANSWER_BUDGET_BODY = (
    b"        if preanswer_budgeted is not None and type(preanswer_budgeted) is not bool:\n"
    b"            raise ValueError(\"preanswer_budgeted must be bool\")\n"
    b"        preanswer_observer = (valid_until is not None if preanswer_budgeted is None else preanswer_budgeted)\n"
)


def _normalize_preanswer_budget_contract(raw: bytes):
    """Temporarily expose the exact Cognition.offer anchor expected by the audio layer."""
    if not isinstance(raw, bytes):
        raise ValueError("Core Cognition source is missing or not bytes")
    budget_signature_count = raw.count(_PREANSWER_BUDGET_SIGNATURE)
    budget_body_count = raw.count(_PREANSWER_BUDGET_BODY)
    base_signature_count = raw.count(_PREANSWER_SIGNATURE)
    base_body_count = raw.count(_PREANSWER_BODY)
    if (budget_signature_count == 1 and budget_body_count == 1
            and base_signature_count == 0 and base_body_count == 0):
        normalized = raw.replace(_PREANSWER_BUDGET_SIGNATURE, _PREANSWER_SIGNATURE, 1)
        normalized = normalized.replace(_PREANSWER_BUDGET_BODY, _PREANSWER_BODY, 1)
        return normalized, True
    if (budget_signature_count == 0 and budget_body_count == 0
            and base_signature_count == 1 and base_body_count == 1):
        return raw, False
    raise ValueError("Core pre-answer budget contract changed or is ambiguous before audio composition")


def _restore_preanswer_budget_contract(raw: bytes, changed: bool) -> bytes:
    """Restore the Core-only flag after the pinned Perception audio transform."""
    if not changed:
        return raw
    if (not isinstance(raw, bytes)
            or raw.count(_PREANSWER_SIGNATURE) != 1
            or raw.count(_PREANSWER_BODY) != 1
            or raw.count(_PREANSWER_BUDGET_SIGNATURE) != 0
            or raw.count(_PREANSWER_BUDGET_BODY) != 0):
        raise ValueError("audio composition changed the normalized Core pre-answer budget anchors")
    restored = raw.replace(_PREANSWER_SIGNATURE, _PREANSWER_BUDGET_SIGNATURE, 1)
    return restored.replace(_PREANSWER_BODY, _PREANSWER_BUDGET_BODY, 1)



_CONTEXT_PROVENANCE_BASE = (
    b"provenance=[e['source_ref']],budget_scale=body['modulation'].get('context_budget_scale',1.))"
)
_CONTEXT_PROVENANCE_RECALL = (
    b"provenance=[e['source_ref']]+meta.get('source_recall_refs',[]),budget_scale=body['modulation'].get('context_budget_scale',1.))"
)
_CONTEXT_PROVENANCE_AUDIO = (
    b"provenance=[e['source_ref']]+([audio_source_ref] if audio_source_ref else []),budget_scale=body['modulation'].get('context_budget_scale',1.))"
)
_CONTEXT_PROVENANCE_RECALL_AUDIO = (
    b"provenance=[e['source_ref']]+meta.get('source_recall_refs',[])+([audio_source_ref] if audio_source_ref else []),budget_scale=body['modulation'].get('context_budget_scale',1.))"
)


def _normalize_context_provenance_contract(raw: bytes):
    """Expose the Perception audio anchor without discarding Core recall lineage."""
    if not isinstance(raw, bytes):
        raise ValueError("Core Runtime Context OS provenance is missing or not bytes")
    recall_count = raw.count(_CONTEXT_PROVENANCE_RECALL)
    base_count = raw.count(_CONTEXT_PROVENANCE_BASE)
    if recall_count == 1 and base_count == 0:
        return raw.replace(_CONTEXT_PROVENANCE_RECALL, _CONTEXT_PROVENANCE_BASE, 1), True
    if recall_count == 0 and base_count == 1:
        return raw, False
    raise ValueError("Core Context OS provenance contract changed or is ambiguous before audio composition")


def _restore_context_provenance_contract(raw: bytes, changed: bool) -> bytes:
    """Restore Core source-recall refs in normal and consent-revocation plans."""
    if not changed:
        return raw
    if (not isinstance(raw, bytes)
            or raw.count(_CONTEXT_PROVENANCE_AUDIO) != 1
            or raw.count(_CONTEXT_PROVENANCE_BASE) != 1
            or raw.count(_CONTEXT_PROVENANCE_RECALL) != 0):
        raise ValueError("audio composition changed the normalized Core Context OS provenance anchors")
    restored = raw.replace(
        _CONTEXT_PROVENANCE_AUDIO, _CONTEXT_PROVENANCE_RECALL_AUDIO, 1
    )
    if restored.count(_CONTEXT_PROVENANCE_BASE) != 1:
        raise ValueError("audio composition made the revoke provenance anchor ambiguous")
    return restored.replace(_CONTEXT_PROVENANCE_BASE, _CONTEXT_PROVENANCE_RECALL, 1)

_CONTEXT_REFS_BASE = (
    b"context_refs=[e['source_ref'],*self.consolidation.source_refs(memories),*history_refs,*meta.get('duplex_handoff_refs',[])]"
)
_CONTEXT_REFS_AUDIO = (
    b"context_refs=[e['source_ref'],*meta.get('audio_source_refs',[]),*self.consolidation.source_refs(memories),*history_refs,*meta.get('duplex_handoff_refs',[])]"
)


def _normalize_audio_context_refs(raw: bytes):
    """Let the pinned audio overlay add its ref while retaining Core's other refs."""
    if not isinstance(raw, bytes):
        raise ValueError("Core Runtime context refs are missing or not bytes")
    lines = raw.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines) if b"context_refs=[e['source_ref']," in line]
    if len(matches) != 1:
        raise ValueError("Core Runtime context refs changed or are ambiguous before audio composition")
    index = matches[0]
    original = lines[index]
    body = original.rstrip(b"\r\n")
    ending = original[len(body):]
    prefix, marker, tail = body.partition(b"context_refs=[e['source_ref'],")
    if (not marker or not body.endswith(b"]") or b"audio_source_refs" in body
            or b"self.consolidation.source_refs(memories)" not in body
            or b"history_refs" not in body
            or b"meta.get('duplex_handoff_refs',[])" not in body):
        missing = [name for name, marker in (
            ("consolidation", b"self.consolidation.source_refs(memories)"),
            ("history", b"history_refs"),
            ("duplex", b"meta.get('duplex_handoff_refs',[])"),
        ) if marker not in body]
        raise ValueError(
            "Core Runtime context refs no longer match the reviewed audio insertion contract; "
            + "line=" + repr(body) + "; missing=" + repr(missing)
            + "; closed=" + str(body.endswith(b"]"))
        )
    lines[index] = prefix + _CONTEXT_REFS_BASE + ending
    return b"".join(lines), original


def _restore_audio_context_refs(raw: bytes, original: bytes) -> bytes:
    """Reinsert audio SourceRefs into the original Core context-ref expression."""
    if not isinstance(raw, bytes) or not isinstance(original, bytes):
        raise ValueError("audio context-ref restoration input is invalid")
    if raw.count(_CONTEXT_REFS_AUDIO) != 1:
        raise ValueError("audio composition changed or duplicated the C3 context-ref anchor")
    body = original.rstrip(b"\r\n")
    prefix, marker, tail = body.partition(b"context_refs=[e['source_ref'],")
    if not marker or not body.endswith(b"]") or b"audio_source_refs" in body:
        raise ValueError("saved Core context-ref expression is not restorable")
    restored_expr = b"context_refs=[e['source_ref'],*meta.get('audio_source_refs',[])," + tail
    return raw.replace(_CONTEXT_REFS_AUDIO, restored_expr, 1)

def build_sources(code_dir: Path, *, include_postcommit=True):
    code_dir = Path(code_dir).resolve(strict=True)
    base = _load(code_dir, BASE_BUILDER, BASE_BUILDER_BLOB_SHA1)
    audio = _load(code_dir, AUDIO_BUILDER, AUDIO_BUILDER_BLOB_SHA1)
    _verify_audio_cognition_pin(code_dir, audio)

    result = base.build_sources(code_dir, include_postcommit=include_postcommit)
    focal_before = result.get("v13/focal.py")
    runtime_before = result.get("v13/runtime.py")
    if not isinstance(focal_before, bytes) or b"SCALE_AWARE_C4_RULE" not in focal_before:
        raise ValueError("base stage no longer contains the reviewed source-span C4 overlay")
    if not isinstance(runtime_before, bytes) or b"LOCAL_EXACT_ARITHMETIC" not in runtime_before:
        raise ValueError("base stage no longer contains the reviewed bounded arithmetic route")

    # The base builder applies the Core fair-budget overlay before the
    # Perception audio overlay. That adds one Core-only optional argument to
    # Cognition.offer, while the pinned audio composer uses the original
    # signature as its insertion anchor. Normalize only that exact signature
    # and its paired decision line for the duration of the audio transform,
    # then restore them. No Perception-owned source pin is changed or weakened.
    audio_input = dict(result)
    cognition_before_audio = audio_input.get("v13/cognition.py")
    normalized_cognition, had_preanswer_budget = _normalize_preanswer_budget_contract(
        cognition_before_audio
    )
    audio_input["v13/cognition.py"] = normalized_cognition
    runtime_before_audio = audio_input.get("v13/runtime.py")
    normalized_runtime, had_context_provenance = _normalize_context_provenance_contract(
        runtime_before_audio
    )
    normalized_runtime, original_context_refs = _normalize_audio_context_refs(normalized_runtime)
    audio_input["v13/runtime.py"] = normalized_runtime
    try:
        composed = audio.apply_sources(code_dir, audio_input)
    except ValueError as exc:
        if "audio candidate semantic anchor mismatch" not in str(exc):
            raise
        runtime_bytes = audio_input.get("v13/runtime.py", b"")
        anchors = [line.decode("utf-8", "replace") for line in runtime_bytes.splitlines()
                   if b"ctxos.controller" in line or b"provenance=" in line or b"context_refs=" in line]
        raise ValueError(
            str(exc) + "; Core runtime sha256="
            + hashlib.sha256(runtime_bytes).hexdigest()
            + "; Core runtime context anchors=" + repr(anchors[:6])
        ) from exc
    composed["v13/cognition.py"] = _restore_preanswer_budget_contract(
        composed.get("v13/cognition.py"), had_preanswer_budget
    )
    composed["v13/runtime.py"] = _restore_context_provenance_contract(
        composed.get("v13/runtime.py"), had_context_provenance
    )
    composed["v13/runtime.py"] = _restore_audio_context_refs(
        composed.get("v13/runtime.py"), original_context_refs
    )
    # The audio overlay must preserve the fair B1/B2 observer path; fail closed
    # rather than reapplying Runtime or broadening a source pin.
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
    greeting_fastpath = _load(code_dir, GREETING_FASTPATH_BUILDER, GREETING_FASTPATH_BLOB_SHA1)
    composed = greeting_fastpath.apply_sources(code_dir, composed)
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
