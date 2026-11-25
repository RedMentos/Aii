"""One-shot source-bound native tokenwise B1/B2 -> B1/B2/C3 pair capture.

The sender side is the existing Cognition.tap / Cognition.read_tap final-RMSNorm
path. The receiver side is the pinned native input-embedding row extractor.
Both tokenizer piece streams are requested from their exact role runners with
add_special=false and aligned by the Perception-owned UTF-8 byte-overlap helper.

A local TTY one-shot approval is required. Cognition.tap persists its ordinary
source-bound LatentTapPacket/blob locally; receiver rows and the paired vectors
remain in memory and are not persisted. No inference, weight update, B3 route,
or native receiver authority is granted.
"""
from __future__ import annotations

import hashlib
import math
import time
from pathlib import Path

from .native_input_embedding_capture import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_SOURCE_BYTES,
    _managed_pids,
    _tokenize_items,
    _unload_pool,
)

PROBE_KIND = "TOKENWISE_PAIR_CAPTURE"
SCHEMA = "v14.native-tokenwise-pair-capture/1"
RUNNER_REVISION = "b10964"
RECEIVER_TAP_IDS = {
    "B1_DETAIL": "b1.input-embedding.v1",
    "B2_GIST": "b2.input-embedding.v1",
    "C3_LANGUAGE": "c3.input-embedding.v1",
}


class NativeTokenwisePairCaptureError(RuntimeError):
    pass


MAX_IN_MEMORY_PAIR_RECORDS = 8
MAX_IN_MEMORY_PAIR_VECTOR_BYTES = 64 * 1024 * 1024
MAX_SINGLE_PAIR_VECTOR_BYTES = 8 * 1024 * 1024


def _in_memory_pair_record_bytes(record):
    if (not isinstance(record, dict)
            or record.get("schema") != "v14.native-tokenwise-pairing/1"
            or record.get("status") != "PAIRED_DIAGNOSTIC"
            or record.get("persisted") is not False
            or record.get("production_route") is not False
            or record.get("semantic_use_proven") is not False
            or record.get("training_authority") != 0
            or record.get("native_receiver_authority") != 0):
        raise NativeTokenwisePairCaptureError("only authority-zero in-memory pair records may be staged")
    pairs = record.get("pairs")
    if not isinstance(pairs, list) or not 1 <= len(pairs) <= 64:
        raise NativeTokenwisePairCaptureError("in-memory pair record must contain 1..64 aligned rows")
    vector_bytes = 0
    for pair in pairs:
        if not isinstance(pair, dict):
            raise NativeTokenwisePairCaptureError("pair record contains a malformed row")
        for key in ("sender_vector", "receiver_vector"):
            vector = pair.get(key)
            if not isinstance(vector, (list, tuple)) or not 1 <= len(vector) <= 8192:
                raise NativeTokenwisePairCaptureError("pair vector geometry is outside the local memory bound")
            for value in vector:
                if type(value) not in (int, float) or not math.isfinite(float(value)):
                    raise NativeTokenwisePairCaptureError("pair vector contains a non-finite value")
            vector_bytes += len(vector) * 8
    if vector_bytes > MAX_SINGLE_PAIR_VECTOR_BYTES:
        raise NativeTokenwisePairCaptureError("single pair record exceeds the 8 MiB vector bound")
    # Account for Python list/float overhead without serializing the vectors.
    return vector_bytes * 2


def _check_live(runtime, deadline, stage):
    if runtime.cancel_event.is_set():
        raise InterruptedError("native tokenwise pair capture cancelled at " + stage)
    if runtime.stop.is_set():
        raise InterruptedError("Runtime stopped during native tokenwise pair capture")
    if time.monotonic() >= deadline:
        raise TimeoutError("native tokenwise pair capture deadline expired at " + stage)


def _tokenizer_revision(model_binding, runner_revision):
    model_sha = model_binding.get("sha256")
    if (type(model_binding.get("revision")) is not str or not model_binding["revision"]
            or type(model_sha) is not str or len(model_sha) != 64
            or any(ch not in "0123456789abcdef" for ch in model_sha)
            or runner_revision != RUNNER_REVISION):
        raise NativeTokenwisePairCaptureError("tokenizer identity is not bound to the pinned runner and GGUF")
    # The tokenizer is embedded in the immutable GGUF. Bind both that file and
    # the runner implementation rather than relabelling the model revision.
    return "llama-server:" + runner_revision + ";gguf:" + model_sha


def _verify_pair_record(record, *, source_ref, event, session_id, sender_role,
                        receiver_role, sender_binding, receiver_binding, tap_packet):
    if not isinstance(record, dict):
        raise NativeTokenwisePairCaptureError("tokenwise pair builder returned no record")
    if (record.get("schema") != "v14.native-tokenwise-pairing/1"
            or record.get("status") != "PAIRED_DIAGNOSTIC"
            or record.get("persisted") is not False
            or record.get("production_route") is not False
            or record.get("semantic_use_proven") is not False
            or record.get("training_authority") != 0
            or record.get("native_receiver_authority") != 0):
        raise NativeTokenwisePairCaptureError("tokenwise pair record carries an unsupported status or authority")
    expected_ref = {
        "source_id": source_ref.get("source_id"),
        "sha256": source_ref.get("sha256"),
        "char_start": source_ref.get("char_start"),
        "char_end": source_ref.get("char_end"),
    }
    sender = record.get("sender")
    receiver = record.get("receiver")
    if (record.get("source_ref") != expected_ref
            or record.get("session_id") != session_id
            or record.get("event_id") != event.get("event_id")
            or record.get("brain_generation_id") != event.get("brain_generation_id")
            or not isinstance(sender, dict) or not isinstance(receiver, dict)
            or sender.get("role") != sender_role
            or sender.get("model_revision") != sender_binding.get("revision")
            or sender.get("model_sha256") != sender_binding.get("sha256")
            or sender.get("tap_id") != tap_packet.get("tap_id")
            or sender.get("feature_sha256") != tap_packet.get("feature_sha256")
            or receiver.get("role") != receiver_role
            or receiver.get("model_revision") != receiver_binding.get("revision")
            or receiver.get("model_sha256") != receiver_binding.get("sha256")
            or receiver.get("tap_id") != RECEIVER_TAP_IDS[receiver_role]
            or not isinstance(record.get("pairs"), list)
            or len(record.get("pairs")) != record.get("pair_count")):
        raise NativeTokenwisePairCaptureError("tokenwise pair record lost its source/session/model/tap binding")
    pair_count = record.get("pair_count")
    if type(pair_count) is not int or not 1 <= pair_count <= 64:
        raise NativeTokenwisePairCaptureError("tokenwise pair count is invalid")
    for key in ("minimum_coverage", "mean_coverage"):
        value = record.get(key)
        if type(value) not in (int, float) or not 0.80 <= float(value) <= 1.0:
            raise NativeTokenwisePairCaptureError("tokenwise pair coverage is outside the accepted range")
    digest = record.get("record_sha256")
    if (type(digest) is not str or len(digest) != 64
            or any(ch not in "0123456789abcdef" for ch in digest)):
        raise NativeTokenwisePairCaptureError("tokenwise pair record digest is invalid")
    return record


def capture_native_tokenwise_pair_record(
    runtime,
    sender_role,
    receiver_role,
    *,
    timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
    approval_module=None,
    cognition_factory=None,
    extractor_fn=None,
    pair_builder=None,
    return_record=False,
):
    """Capture one approved native pair; optionally return it only to an in-process lab caller."""
    if type(timeout_seconds) is not int or not 10 <= timeout_seconds <= DEFAULT_TIMEOUT_SECONDS:
        raise ValueError("native tokenwise pair timeout must be 10..120 seconds")
    if type(return_record) is not bool:
        raise ValueError("return_record must be boolean")

    if approval_module is None:
        from . import native_probe_approval as approval_module
    if cognition_factory is None:
        from .cognition import Cognition
        cognition_factory = Cognition
    if extractor_fn is None:
        from .native_input_embedding_extractor import extract_native_input_embedding_rows as extractor_fn
    if pair_builder is None:
        from .native_tokenwise_pairing import build_native_tokenwise_pair_record as pair_builder

    approval_module._roles(sender_role, receiver_role)
    started = time.monotonic()

    with approval_module.runtime_probe_lease(runtime) as lease_token:
        event, source_ref = approval_module._current_event(runtime)
        source_text = runtime.store.read_source(source_ref)
        if type(source_text) is not str or not source_text:
            raise NativeTokenwisePairCaptureError("last source is empty or unavailable")
        source_bytes = source_text.encode("utf-8", errors="strict")
        if len(source_bytes) > MAX_SOURCE_BYTES:
            raise NativeTokenwisePairCaptureError("last source exceeds the 4096-byte diagnostic bound")
        if (source_ref.get("char_start") != 0
                or source_ref.get("char_end") != len(source_text)
                or source_ref.get("sha256") != hashlib.sha256(source_bytes).hexdigest()):
            raise NativeTokenwisePairCaptureError("last source is not the exact complete SourceRef span")

        approval = approval_module.consume(
            runtime, sender_role, receiver_role, event, source_ref,
            lease_token=lease_token,
            probe_kind=PROBE_KIND,
        )
        if not isinstance(approval, dict) or not isinstance(approval.get("approval_id"), str):
            raise PermissionError("tokenwise pair capture did not consume a local approval")
        consumed_record, _ = runtime.store.state(approval_module.KEY, None)
        if (not isinstance(consumed_record, dict)
                or consumed_record.get("status") != "CONSUMED"
                or consumed_record.get("probe_kind") != PROBE_KIND
                or consumed_record.get("sender_role") != sender_role
                or consumed_record.get("receiver_role") != receiver_role
                or consumed_record.get("session_id") != runtime.session
                or consumed_record.get("event_id") != event.get("event_id")
                or consumed_record.get("source_ref") != source_ref):
            raise PermissionError("consumed approval state is not the exact tokenwise-pair authorization")

        sender_binding = approval_module._model_binding(runtime, sender_role)
        receiver_binding = approval_module._model_binding(runtime, receiver_role)
        deadline = time.monotonic() + timeout_seconds
        cognition = cognition_factory(runtime)

        # First capture the normal source-bound sender tap. Cognition.tap writes
        # its existing local LatentTapPacket/blob; read_tap verifies the stored
        # packet, source and blob hash before the pair helper may consume it.
        approval_module._resource_preflight(runtime, sender_binding)
        try:
            _check_live(runtime, deadline, "sender tap")
            tap_packet = cognition.tap(sender_role, event, source_ref, deadline)
            sender_tap_data = cognition.read_tap(tap_packet)
            _check_live(runtime, deadline, "sender content tokenization")
            sender_runner = runtime.pool.get_tap(sender_role)
            sender_runner.load(runtime.cancel_event, deadline)
            sender_tokenized = sender_runner._json(
                "POST", "/tokenize",
                {
                    "content": source_text,
                    "add_special": False,
                    "parse_special": False,
                    "with_pieces": True,
                },
                deadline,
                timeout_cap=None,
            )
            sender_token_ids, sender_token_pieces = _tokenize_items(sender_tokenized)
        finally:
            _unload_pool(runtime)

        _check_live(runtime, deadline, "receiver tokenization")
        approval_module._resource_preflight(runtime, receiver_binding)
        try:
            receiver_runner = runtime.pool.get_tap(receiver_role)
            receiver_runner.load(runtime.cancel_event, deadline)
            receiver_tokenized = receiver_runner._json(
                "POST", "/tokenize",
                {
                    "content": source_text,
                    "add_special": False,
                    "parse_special": False,
                    "with_pieces": True,
                },
                deadline,
                timeout_cap=None,
            )
            receiver_token_ids, receiver_token_pieces = _tokenize_items(receiver_tokenized)
        finally:
            _unload_pool(runtime)

        def prepare_idle():
            _check_live(runtime, deadline, "native row extraction")
            if (getattr(runtime, "current", None) != "probe"
                    or not getattr(runtime, "_native_probe_active", False)
                    or getattr(runtime, "_native_probe_lease_nonce", None) != lease_token):
                raise PermissionError("tokenwise pair capture lost its exclusive Runtime lease")
            if not runtime.jobs.empty() or runtime.store.queue_stats().get("count", 0) != 0:
                raise PermissionError("tokenwise pair capture Runtime queue is no longer empty")
            remaining_pids = _managed_pids(runtime)
            if remaining_pids:
                raise PermissionError("managed native processes remain before receiver row extraction")
            approval_module._resource_preflight(runtime, receiver_binding)

        _check_live(runtime, deadline, "native row extraction")
        remaining = int(deadline - time.monotonic())
        if remaining < 1:
            raise TimeoutError("native tokenwise pair deadline expired before receiver row extraction")
        model_path = Path(receiver_binding["canonical_path"])
        model_root = Path(runtime.home) / "models"
        binary_path = Path(runtime.home) / "bin" / "native_input_embedding_extractor"
        extracted = extractor_fn(
            binary_path,
            model_path,
            receiver_binding["revision"],
            receiver_token_ids,
            model_root=model_root,
            expected_model_sha256=receiver_binding["sha256"],
            prepare_idle=prepare_idle,
            timeout_seconds=min(DEFAULT_TIMEOUT_SECONDS, remaining),
        )
        _check_live(runtime, deadline, "pair assembly")
        if not isinstance(extracted, dict) or extracted.get("status") != "COMPLETE":
            raise NativeTokenwisePairCaptureError("native input-row extractor returned no complete result")

        # Rebind the exact source and both installed model files after the native
        # call. The pair builder then verifies tap/blob identity and byte spans.
        event_after, source_ref_after = approval_module._current_event(runtime)
        if (event_after != event or source_ref_after != source_ref
                or runtime.store.read_source(source_ref) != source_text):
            raise NativeTokenwisePairCaptureError("source/event changed during tokenwise pair capture")
        if (approval_module._model_binding(runtime, sender_role) != sender_binding
                or approval_module._model_binding(runtime, receiver_role) != receiver_binding):
            raise NativeTokenwisePairCaptureError("sender or receiver model binding changed during tokenwise pair capture")

        runner_revision = tap_packet.get("runner_revision")
        sender_tokenizer_revision = _tokenizer_revision(sender_binding, runner_revision)
        receiver_tokenizer_revision = _tokenizer_revision(receiver_binding, runner_revision)
        record = pair_builder(
            source_text,
            source_ref,
            sender_token_ids,
            sender_token_pieces,
            tap_packet,
            sender_tap_data,
            receiver_token_ids,
            receiver_token_pieces,
            extracted,
            source_id=source_ref["source_id"],
            session_id=runtime.session,
            event_id=event["event_id"],
            brain_generation_id=event["brain_generation_id"],
            sender_role=sender_role,
            receiver_role=receiver_role,
            sender_tap_id=tap_packet["tap_id"],
            receiver_tap_id=RECEIVER_TAP_IDS[receiver_role],
            sender_model_revision=sender_binding["revision"],
            receiver_model_revision=receiver_binding["revision"],
            sender_model_sha256=sender_binding["sha256"],
            receiver_model_sha256=receiver_binding["sha256"],
            sender_tokenizer_revision=sender_tokenizer_revision,
            receiver_tokenizer_revision=receiver_tokenizer_revision,
        )
        record = _verify_pair_record(
            record,
            source_ref=source_ref,
            event=event,
            session_id=runtime.session,
            sender_role=sender_role,
            receiver_role=receiver_role,
            sender_binding=sender_binding,
            receiver_binding=receiver_binding,
            tap_packet=tap_packet,
        )

        receiver = record["receiver"]
        audit = {
            "operation": "TOKENWISE_PAIR_CAPTURE",
            "sender_role": sender_role,
            "receiver_role": receiver_role,
            "source_ref": {
                "source_id": source_ref["source_id"],
                "sha256": source_ref["sha256"],
                "char_start": source_ref["char_start"],
                "char_end": source_ref["char_end"],
                "modality": "text",
            },
            "event_id": event["event_id"],
            "session_id": runtime.session,
            "sender_model_revision": sender_binding["revision"],
            "sender_model_sha256": sender_binding["sha256"],
            "receiver_model_revision": receiver_binding["revision"],
            "receiver_model_sha256": receiver_binding["sha256"],
            "sender_tap_id": tap_packet["tap_id"],
            "sender_feature_sha256": tap_packet["feature_sha256"],
            "receiver_tap_id": receiver["tap_id"],
            "receiver_manifest_sha256": receiver["manifest_sha256"],
            "record_sha256": record["record_sha256"],
            "pair_count": record["pair_count"],
            "minimum_coverage": round(float(record["minimum_coverage"]), 6),
            "mean_coverage": round(float(record["mean_coverage"]), 6),
            "duration_s": round(time.monotonic() - started, 3),
            "sender_tap_persisted": True,
            "receiver_rows_persisted": False,
            "pair_vectors_persisted": False,
            "pair_record_persisted": False,
            "production_route": False,
            "semantic_use_proven": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
        }
        runtime.store.log("native_tokenwise_pair_capture", event["event_id"], audit)

        if return_record:
            return record
        return {
            "schema": SCHEMA,
            "status": "PAIRED_DIAGNOSTIC",
            "event_id": event["event_id"],
            "session_id": runtime.session,
            "source_sha256": source_ref["sha256"],
            "sender_role": sender_role,
            "receiver_role": receiver_role,
            "sender_model_revision": sender_binding["revision"],
            "receiver_model_revision": receiver_binding["revision"],
            "sender_tokenizer_revision": sender_tokenizer_revision,
            "receiver_tokenizer_revision": receiver_tokenizer_revision,
            "sender_tap_id": tap_packet["tap_id"],
            "receiver_tap_id": receiver["tap_id"],
            "sender_token_count": len(sender_token_ids),
            "sender_activation_rows": len(sender_tap_data["vectors"]),
            "receiver_token_count": len(receiver_token_ids),
            "receiver_embedding_dim": receiver["embedding_dim"],
            "pair_count": record["pair_count"],
            "minimum_coverage": record["minimum_coverage"],
            "mean_coverage": record["mean_coverage"],
            "record_sha256": record["record_sha256"],
            "sender_tap_persisted": True,
            "receiver_rows_persisted": False,
            "pair_vectors_persisted": False,
            "pair_record_persisted": False,
            "production_route": False,
            "semantic_use_proven": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
            "approval_id": approval["approval_id"],
            "runtime_exclusive": True,
            "audit_logged": True,
            "notice": "Sender tap is persisted locally by Cognition.tap; receiver rows and paired vectors remain in memory. This is not receiver inference, learned latent coupling, or production B3.",
        }


def fit_native_tokenwise_pair_cohort(records, train_session_ids, holdout_session_ids):
    """Fit the schema-v4 in-memory candidate from already locally approved pair records.

    The fitter requires at least two whole sessions on each side and rejects
    source/session overlap. It returns an in-memory PCA+ridge candidate only;
    it does not persist the adapter, run inference, change weights, or enable B3.
    Callers must only supply records captured under the separate local TTY
    approvals above.
    """
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("tokenwise cohort requires a non-empty in-memory record list")
    from .native_tokenwise_pairing import fit_adapter_from_native_pair_records
    return fit_adapter_from_native_pair_records(
        records,
        train_session_ids=train_session_ids,
        holdout_session_ids=holdout_session_ids,
    )


def operator_command(runtime, args, *, approval_module=None, capture_fn=None):
    """Local :callosum tokenwise-pair workflow; every operation requires a real TTY."""
    if approval_module is None:
        from . import native_probe_approval as approval_module
    if capture_fn is None:
        capture_fn = capture_native_tokenwise_pair_record
    from .common import dumps

    if (len(args) == 5 and args[0] == "arm-tokenwise-pair"
            and args[3:] == ["--last-source", "--confirm"]):
        return dumps(approval_module.arm(
            runtime, args[1], args[2], probe_kind=PROBE_KIND,
        ))
    if args == ["revoke-tokenwise-pair"]:
        return dumps(approval_module.revoke(runtime))
    if (len(args) == 5 and args[0] == "native-tokenwise-pair"
            and args[3:] == ["--last-source", "--confirm"]):
        records = getattr(runtime, "_native_tokenwise_pair_records", None)
        if records is None:
            records = []
        if not isinstance(records, list):
            raise NativeTokenwisePairCaptureError("Runtime tokenwise lab state is malformed")
        if getattr(runtime, "_native_tokenwise_candidate", None) is not None:
            raise NativeTokenwisePairCaptureError("clear or probe the staged tokenwise candidate before capturing again")
        if len(records) >= MAX_IN_MEMORY_PAIR_RECORDS:
            raise NativeTokenwisePairCaptureError("in-memory tokenwise record cap reached; clear the lab before another capture")
        existing_bytes = sum(_in_memory_pair_record_bytes(item) for item in records)
        if existing_bytes + MAX_SINGLE_PAIR_VECTOR_BYTES * 2 > MAX_IN_MEMORY_PAIR_VECTOR_BYTES:
            raise NativeTokenwisePairCaptureError("in-memory tokenwise vector budget is full; clear the lab before another capture")
        record = capture_fn(runtime, args[1], args[2], return_record=True)
        estimated_bytes = _in_memory_pair_record_bytes(record)
        record_sha = record.get("record_sha256")
        if type(record_sha) is not str or len(record_sha) != 64:
            raise NativeTokenwisePairCaptureError("captured pair record has no canonical digest")
        if any(item.get("record_sha256") == record_sha for item in records):
            raise NativeTokenwisePairCaptureError("duplicate tokenwise pair record refused")
        if existing_bytes + estimated_bytes > MAX_IN_MEMORY_PAIR_VECTOR_BYTES:
            raise NativeTokenwisePairCaptureError("captured pair record exceeds the remaining in-memory vector budget")
        records.append(record)
        runtime._native_tokenwise_pair_records = records
        return dumps({
            "schema": "v14.native-tokenwise-pair-lab/1",
            "status": "PAIRED_DIAGNOSTIC_STAGED",
            "record_sha256": record_sha,
            "session_id": record["session_id"],
            "event_id": record["event_id"],
            "pair_count": record["pair_count"],
            "in_memory_record_count": len(records),
            "estimated_in_memory_bytes": existing_bytes + estimated_bytes,
            "persisted": False,
            "pair_vectors_persisted": False,
            "notice": "Pair vectors remain in bounded Runtime memory only; use fit-tokenwise-cohort for an explicit session-disjoint candidate."
        })
    raise ValueError(
        ":callosum [arm-tokenwise-pair <sender> <receiver> --last-source --confirm|"
        "native-tokenwise-pair <sender> <receiver> --last-source --confirm|"
        "revoke-tokenwise-pair]"
    )
