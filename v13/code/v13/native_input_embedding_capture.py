"""One-shot Runtime consumer for receipt-bound native receiver input embeddings.

The command is a local diagnostic only. It binds one completed user source and
the selected sender/receiver model revisions, tokenizes the receiver's exact
source bytes with pieces enabled, releases the llama-server pool, then reads
only the requested receiver input-table rows through the pinned native
extractor. Rows remain ephemeral; no training, routing, weight edit, or B3
activation is performed.
"""
from __future__ import annotations

import time
from pathlib import Path

MAX_SOURCE_BYTES = 4096
MAX_TOKENS = 64
DEFAULT_TIMEOUT_SECONDS = 120
SCHEMA = "v14.native-input-embedding-capture/1"


class NativeInputEmbeddingCaptureError(RuntimeError):
    pass


def _tokenize_items(response):
    if not isinstance(response, dict) or not isinstance(response.get("tokens"), list):
        raise NativeInputEmbeddingCaptureError("native tokenizer did not return a token-piece list")
    items = response["tokens"]
    if not 2 <= len(items) <= MAX_TOKENS:
        raise NativeInputEmbeddingCaptureError("native input tap requires 2..64 content tokens")
    token_ids = []
    pieces = []
    for item in items:
        if not isinstance(item, dict) or set(item) != {"id", "piece"}:
            raise NativeInputEmbeddingCaptureError("native tokenizer token-piece item is not canonical")
        token_id = item["id"]
        piece = item["piece"]
        if type(token_id) is not int or not 0 <= token_id <= 2_147_483_647:
            raise NativeInputEmbeddingCaptureError("native tokenizer returned an invalid token ID")
        if type(piece) is str:
            pass
        elif (isinstance(piece, list) and piece
              and all(type(value) is int and 0 <= value <= 255 for value in piece)):
            pass
        else:
            raise NativeInputEmbeddingCaptureError("native tokenizer returned an invalid token piece")
        token_ids.append(token_id)
        pieces.append({"id": token_id, "piece": piece})
    return token_ids, pieces


def _manager_pids(manager, name):
    if manager is None:
        return []
    getter = getattr(manager, "pids", None)
    if not callable(getter):
        raise NativeInputEmbeddingCaptureError(name + " has no verifiable process census")
    values = getter()
    if not isinstance(values, (list, tuple)) or any(type(pid) is not int or pid <= 0 for pid in values):
        raise NativeInputEmbeddingCaptureError(name + " returned an invalid process census")
    return list(values)


def _managed_pids(runtime):
    managers = [
        (getattr(runtime, "pool", None), "RunnerPool"),
        (getattr(runtime, "needle", None), "NeedleRunner"),
    ]
    memory = getattr(runtime, "memory", None)
    semantic_keys = getattr(memory, "semantic_keys", None)
    encoder = getattr(semantic_keys, "encoder", None)
    if encoder is not None:
        managers.append((encoder, "semantic-key encoder"))
    result = []
    for manager, name in managers:
        result.extend(_manager_pids(manager, name))
    return sorted(set(result))


def _unload_pool(runtime):
    result = runtime.pool.unload()
    if isinstance(result, dict) and result.get("process_reaped") is not True:
        raise NativeInputEmbeddingCaptureError("native tokenizer runner was not reaped")
    if _manager_pids(runtime.pool, "RunnerPool"):
        raise NativeInputEmbeddingCaptureError("native tokenizer runner remains resident")
    return result


def capture_native_input_embedding_tap(
    runtime,
    sender_role,
    receiver_role,
    *,
    timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
    approval_module=None,
    extractor_fn=None,
    manifest_builder=None,
):
    """Capture one source-bound receiver input table sample under local approval."""
    if type(timeout_seconds) is not int or not 10 <= timeout_seconds <= DEFAULT_TIMEOUT_SECONDS:
        raise ValueError("native input tap timeout must be 10..120 seconds")
    if approval_module is None:
        from . import native_probe_approval as approval_module
    if extractor_fn is None:
        from .native_input_embedding_extractor import extract_native_input_embedding_rows as extractor_fn
    if manifest_builder is None:
        from .native_input_embedding_tap import build_native_input_embedding_tap_manifest as manifest_builder

    approval_module._roles(sender_role, receiver_role)
    started = time.monotonic()
    with approval_module.runtime_probe_lease(runtime) as lease_token:
        event, source_ref = approval_module._current_event(runtime)
        source_text = runtime.store.read_source(source_ref)
        if type(source_text) is not str or not source_text:
            raise NativeInputEmbeddingCaptureError("last source is empty or unavailable")
        source_bytes = source_text.encode("utf-8")
        if len(source_bytes) > MAX_SOURCE_BYTES:
            raise NativeInputEmbeddingCaptureError("last source exceeds the 4096-byte diagnostic bound")
        if source_ref.get("char_start") != 0 or source_ref.get("char_end") != len(source_text):
            raise NativeInputEmbeddingCaptureError("input tap requires the complete exact last-source span")
        approval = approval_module.consume(
            runtime, sender_role, receiver_role, event, source_ref,
            lease_token=lease_token,
            probe_kind="INPUT_EMBEDDING_TAP",
        )
        model_binding = approval_module._model_binding(runtime, receiver_role)
        model_path = Path(model_binding["canonical_path"])
        model_root = Path(runtime.home) / "models"
        binary_path = Path(runtime.home) / "bin" / "native_input_embedding_extractor"
        deadline = time.monotonic() + timeout_seconds

        # A fresh tap runner supplies IDs and pieces from one exact native
        # /tokenize request. No chat template, BOS, generation, or source rewrite.
        _unload_pool(runtime)
        runner = runtime.pool.get_tap(receiver_role)
        try:
            runner.load(runtime.cancel_event, deadline)
            tokenized = runner._json(
                "POST",
                "/tokenize",
                {
                    "content": source_text,
                    "add_special": False,
                    "parse_special": False,
                    "with_pieces": True,
                },
                deadline,
                timeout_cap=None,
            )
            token_ids, token_pieces = _tokenize_items(tokenized)
        finally:
            _unload_pool(runtime)

        if runtime.cancel_event.is_set():
            raise InterruptedError("native input tap cancelled after tokenization")
        if time.monotonic() >= deadline:
            raise TimeoutError("native input tap deadline expired after tokenization")

        def prepare_idle():
            if runtime.cancel_event.is_set():
                raise InterruptedError("native input tap cancelled before native row extraction")
            if (getattr(runtime, "current", None) != "probe"
                    or not getattr(runtime, "_native_probe_active", False)
                    or not getattr(runtime, "_native_probe_lease_nonce", None)):
                raise PermissionError("native input tap lost its exclusive Runtime lease")
            if runtime.stop.is_set() or not runtime.jobs.empty():
                raise PermissionError("native input tap Runtime is stopping or has queued work")
            if runtime.store.queue_stats().get("count", 0) != 0:
                raise PermissionError("native input tap Runtime queue is no longer empty")
            remaining_pids = _managed_pids(runtime)
            if remaining_pids:
                raise PermissionError("managed native model processes remain before input-row extraction")
            approval_module._resource_preflight(runtime, model_binding)

        remaining = int(deadline - time.monotonic())
        if remaining < 1:
            raise TimeoutError("native input tap deadline expired before row extraction")
        extracted = extractor_fn(
            binary_path,
            model_path,
            model_binding["revision"],
            token_ids,
            model_root=model_root,
            expected_model_sha256=model_binding["sha256"],
            prepare_idle=prepare_idle,
            timeout_seconds=min(DEFAULT_TIMEOUT_SECONDS, remaining),
        )
        if not isinstance(extracted, dict) or extracted.get("status") != "COMPLETE":
            raise NativeInputEmbeddingCaptureError("native input-row extractor returned no complete result")
        manifest_result = manifest_builder(
            receiver_role,
            source_text,
            token_ids,
            token_pieces,
            extracted.get("rows"),
            source_id=source_ref["source_id"],
            event_id=event["event_id"],
            brain_generation_id=event["brain_generation_id"],
            model_revision=model_binding["revision"],
            model_sha256=model_binding["sha256"],
            tokenizer_revision=model_binding["revision"],
            extractor_receipt=extracted.get("receipt"),
        )
        if not isinstance(manifest_result, dict) or not isinstance(manifest_result.get("manifest"), dict):
            raise NativeInputEmbeddingCaptureError("native input-tap manifest builder returned no manifest")
        manifest = manifest_result["manifest"]
        if (manifest.get("source_sha256") != source_ref.get("sha256")
                or manifest.get("event_id") != event.get("event_id")
                or manifest.get("brain_generation_id") != event.get("brain_generation_id")
                or manifest.get("token_ids") != token_ids):
            raise NativeInputEmbeddingCaptureError("native input-tap manifest lost its source/event/token binding")

        receipt = extracted["receipt"]
        audit = {
            # Store.telemetry_metrics admits these bounded fields and redacts
            # arbitrary strings. The manifest hash is recorded as an opaque ID.
            "operation": "PREFILL_TAP",
            "role": receiver_role,
            "model_revision": model_binding["revision"],
            "sha256": model_binding["sha256"],
            "source_ref": {
                "source_id": source_ref["source_id"],
                "sha256": source_ref["sha256"],
                "char_start": source_ref["char_start"],
                "char_end": source_ref["char_end"],
                "modality": "text",
            },
            "id": manifest["manifest_sha256"],
            "n": len(token_ids),
            "embedding_dim": manifest["embedding_dim"],
            "duration_s": round(time.monotonic() - started, 3),
            "native_receiver_authority": 0,
            "semantic_quality_proven": False,
            "training_authority": 0,
        }
        # Only a sanitized digest/measurement record is durable. Source text,
        # token pieces, IDs, and vectors remain in memory for this call only.
        runtime.store.log("native_input_embedding_tap", event["event_id"], audit)
        del manifest_result
        del extracted
        return {
            "schema": SCHEMA,
            "status": "DIAGNOSTIC_ONLY",
            "event_id": event["event_id"],
            "sender_role": sender_role,
            "receiver_role": receiver_role,
            "sender_activation_captured": False,
            "activation_space": "INPUT_EMBEDDING_F32",
            "token_count": len(token_ids),
            "embedding_dim": manifest["embedding_dim"],
            "source_sha256": manifest["source_sha256"],
            "model_revision": model_binding["revision"],
            "model_sha256": model_binding["sha256"],
            "tokenizer_revision": model_binding["revision"],
            "extractor_binary_sha256": receipt["extractor_binary_sha256"],
            "llama_cpp_revision": receipt["llama_cpp_revision"],
            "manifest_sha256": manifest["manifest_sha256"],
            "duration_seconds": audit["duration_s"],
            "vectors_persisted": False,
            "production_route": False,
            "semantic_use_proven": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
            "approval_id": approval["approval_id"],
            "local_approval_consumed": True,
            "resource_preflight": approval["resource_preflight"],
            "runtime_exclusive": True,
            "vectors_returned": False,
            "audit_logged": True,
            "notice": "Receiver input-table rows were read from the pinned native API; this is not a trained latent channel or production B3 activation.",
        }


def operator_command(runtime, args, *, approval_module=None, capture_fn=None):
    """Local :callosum input-tap workflow; every operation requires a real TTY."""
    if approval_module is None:
        from . import native_probe_approval as approval_module
    if capture_fn is None:
        capture_fn = capture_native_input_embedding_tap
    from .common import dumps

    if (len(args) == 5 and args[0] == "arm-input-tap"
            and args[3:] == ["--last-source", "--confirm"]):
        return dumps(approval_module.arm(runtime, args[1], args[2], probe_kind="INPUT_EMBEDDING_TAP"))
    if args == ["revoke-input-tap"]:
        return dumps(approval_module.revoke(runtime))
    if (len(args) == 5 and args[0] == "native-input-tap"
            and args[3:] == ["--last-source", "--confirm"]):
        return dumps(capture_fn(runtime, args[1], args[2]))
    raise ValueError(
        ":callosum [arm-input-tap <sender> <receiver> --last-source --confirm|"
        "native-input-tap <sender> <receiver> --last-source --confirm|revoke-input-tap]"
    )
