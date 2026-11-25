"""Explicit, source-bound tokenwise pairing diagnostics for the V14 Callosum lane.

The path is local-TTY approved, model/source bound, read-only with respect to
weights and production routing, and persists only manifests/metadata. Raw
receiver rows and aligned vector pairs are discarded after the diagnostic.
"""
from __future__ import annotations

import json
import threading
import time

from .common import dumps
from .native_probe_approval import (
    _require_local_tty,
    _roles,
    arm,
    consume,
    revoke,
    runtime_probe_lease,
)

PURPOSE = "TOKENWISE_PAIR_DIAGNOSTIC"


def _last_final_source(runtime):
    last = runtime.last_answer()
    if not last or last.get("status") != "FINAL" or not last.get("event_id"):
        raise ValueError("Tokenwise pairing requires a completed FINAL answer")
    row = runtime.store.one(
        "SELECT packet,session_id FROM events WHERE id=?",
        (last["event_id"],),
    )
    if not row or row["session_id"] != runtime.session:
        raise ValueError("Last source is not in the active session")
    event = json.loads(row["packet"])
    source_ref = event.get("source_ref")
    if not isinstance(source_ref, dict) or not source_ref.get("source_id"):
        raise ValueError("Last event has no valid SourceRef")
    return event, source_ref


def _pair_interruptibly(runtime, sender, receiver, event, source_ref, lease_token, deadline):
    outcome = {}

    def invoke():
        try:
            outcome["result"] = runtime.cognition.native_tokenwise_pair_probe(
                sender, receiver, event, source_ref, lease_token, deadline,
            )
        except BaseException as exc:
            outcome["error"] = exc

    worker = threading.Thread(target=invoke, name="v14-native-tokenwise-pair", daemon=True)
    worker.start()
    interrupted = False
    while worker.is_alive():
        try:
            worker.join(0.1)
        except KeyboardInterrupt:
            if worker.is_alive():
                runtime.cancel_event.set()
                interrupted = True
    if interrupted:
        raise InterruptedError("Native tokenwise diagnostic cancelled by local operator")
    error = outcome.get("error")
    if error is not None:
        raise error
    if runtime.cancel_event.is_set():
        raise InterruptedError("Native tokenwise diagnostic cancelled by Runtime shutdown")
    result = outcome.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("Native tokenwise diagnostic returned no result")
    return result


def operator_command(runtime, args):
    """Local :callosum commands; no automatic execution from ordinary chat turns."""
    normal_arm = (
        len(args) == 5 and args[0] == "arm-tokenwise"
        and args[3:] == ["--last-source", "--confirm"]
    )
    if normal_arm:
        return dumps(arm(runtime, args[1], args[2], purpose=PURPOSE))
    if args == ["revoke-tokenwise"]:
        return dumps(revoke(runtime, purpose=PURPOSE))

    normal_run = (
        len(args) == 5 and args[0] == "tokenwise-pair"
        and args[3:] == ["--last-source", "--confirm"]
    )
    if normal_run:
        sender, receiver = args[1], args[2]
        _roles(sender, receiver)
        with runtime_probe_lease(runtime) as lease_token:
            event, source_ref = _last_final_source(runtime)
            approval = consume(
                runtime, sender, receiver, event, source_ref,
                lease_token=lease_token, purpose=PURPOSE,
            )
            runtime.models.path_for(receiver)
            deadline = time.monotonic() + 180.0
            try:
                result = _pair_interruptibly(
                    runtime, sender, receiver, event, source_ref, lease_token, deadline,
                )
            finally:
                runtime.pool.unload()
            return dumps({
                **result,
                "queued": False,
                "completed": True,
                "approval_id": approval["approval_id"],
                "local_approval_consumed": True,
                "resource_preflight": approval["resource_preflight"],
                "runtime_exclusive": True,
                "requires_explicit_confirmation": False,
                "production_route": False,
                "semantic_use_proven": False,
                "training_authority": 0,
                "native_receiver_authority": 0,
                "pair_vectors_persisted": False,
                "raw_receiver_rows_persisted": False,
                "notice": "Local one-shot diagnostic; only source-bound manifests and hashes persist. No fitting, inference injection, weight change or production B3 route.",
            })

    if args == ["build-tokenwise-extractor", "--confirm"]:
        _require_local_tty()
        runtime.require_idle()
        with runtime_probe_lease(runtime):
            runtime.pool.unload()
            from .native_input_embedding_extractor_build import build_native_input_embedding_extractor
            result = build_native_input_embedding_extractor(runtime.home, confirmed=True)
        return dumps({
            **result,
            "model_downloaded": False,
            "model_changed": False,
            "production_route_changed": False,
            "notice": "Explicit local Termux source build only; no model weights or permissions changed.",
        })

    raise ValueError(
        ":callosum [arm-tokenwise <B1_DETAIL|B2_GIST> <B1_DETAIL|B2_GIST|C3_LANGUAGE> --last-source --confirm|"
        "tokenwise-pair <sender> <receiver> --last-source --confirm|revoke-tokenwise|"
        "build-tokenwise-extractor --confirm]"
    )
