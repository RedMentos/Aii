"""Bounded local-TTY pair matrix for native input-embedding diagnostics.

This runs four fixed B1/B2 -> B1/B2/C3 pairs sequentially against one exact
FINAL source and the already-installed model revisions. It is diagnostic-only:
no production B3 routing, learned alignment, weight update or model swap.
"""
from __future__ import annotations

import time

from .common import dumps
from . import native_probe_approval as approval

MATRIX_SCHEMA = "v14.native-probe-matrix-approval/1"
RESULT_SCHEMA = "v14.native-probe-matrix/1"
ROLES = ("B1_DETAIL", "B2_GIST", "C3_LANGUAGE")
PAIRS = (
    ("B1_DETAIL", "B2_GIST"),
    ("B1_DETAIL", "C3_LANGUAGE"),
    ("B2_GIST", "B1_DETAIL"),
    ("B2_GIST", "C3_LANGUAGE"),
)
MAX_TOTAL_SECONDS = 240.0
PAIR_DEADLINE_SECONDS = 60.0


def _pairs_json():
    return [list(pair) for pair in PAIRS]


def arm_matrix(runtime, *, now=None):
    """Bind one local approval to all four fixed pairs and all three model files."""
    approval._require_local_tty()
    runtime.require_idle()
    event, source_ref = approval._current_event(runtime)
    models = {role: approval._model_binding(runtime, role) for role in ROLES}

    clock = approval._clock(now)
    runtime_nonce = approval._runtime_nonce(runtime)
    current, version = runtime.store.state(approval.KEY, None)
    if isinstance(current, dict) and current.get("status") == "PENDING":
        expires = current.get("expires_at")
        if (
            current.get("runtime_nonce") == runtime_nonce
            and isinstance(expires, (int, float))
            and not isinstance(expires, bool)
            and clock < expires
        ):
            raise PermissionError(
                "a native probe approval is already pending; revoke it first"
            )

    import secrets

    nonce = secrets.token_hex(16)
    record = {
        "schema": MATRIX_SCHEMA,
        "status": "PENDING",
        "nonce": nonce,
        "runtime_nonce": runtime_nonce,
        "issued_at": clock,
        "expires_at": int(clock) + approval.TTL_SECONDS,
        "session_id": runtime.session,
        "event_id": event["event_id"],
        "brain_generation_id": event["brain_generation_id"],
        "source_ref": dict(source_ref),
        "pairs": _pairs_json(),
        "models": models,
        "max_total_seconds": MAX_TOTAL_SECONDS,
        "pair_deadline_seconds": PAIR_DEADLINE_SECONDS,
    }
    runtime.store.set_state(approval.KEY, record, expected=version)
    return {
        "status": "ARMED",
        "approval_id": nonce[:12],
        "expires_in_seconds": approval.TTL_SECONDS,
        "pair_count": len(PAIRS),
        "pairs": _pairs_json(),
        "source_bound": True,
        "all_three_model_revisions_hashes_paths_and_file_identities_bound": True,
        "runtime_instance_scoped": True,
        "max_total_seconds": MAX_TOTAL_SECONDS,
        "per_pair_deadline_seconds": PAIR_DEADLINE_SECONDS,
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }


def consume_matrix(runtime, event, source_ref, *, now=None, lease_token=None):
    """Revalidate source, models and per-model headroom before consuming once."""
    approval._require_local_tty()
    if lease_token is None:
        runtime.require_idle()
    else:
        approval._require_runtime_probe_lease(runtime, lease_token)

    clock = approval._clock(now)
    record, version = runtime.store.state(approval.KEY, None)
    if (
        not isinstance(record, dict)
        or record.get("schema") != MATRIX_SCHEMA
        or record.get("status") != "PENDING"
    ):
        raise PermissionError(
            "native pair matrix requires a fresh local :callosum arm-probe-matrix approval"
        )
    if record.get("runtime_nonce") != approval._runtime_nonce(runtime):
        raise PermissionError("native pair-matrix approval expired across Runtime restart")
    expires = record.get("expires_at")
    if (
        isinstance(expires, bool)
        or not isinstance(expires, (int, float))
        or not clock < expires
    ):
        raise PermissionError("native pair-matrix local approval expired")
    if record.get("pairs") != _pairs_json():
        raise PermissionError("native pair-matrix pair set differs from the fixed approved matrix")

    current_event, current_ref = approval._current_event(runtime)
    if (
        not isinstance(event, dict)
        or event.get("event_id") != current_event.get("event_id")
        or event.get("brain_generation_id") != current_event.get("brain_generation_id")
        or source_ref != current_ref
        or record.get("session_id") != runtime.session
        or record.get("event_id") != current_event.get("event_id")
        or record.get("brain_generation_id") != current_event.get("brain_generation_id")
        or record.get("source_ref") != current_ref
    ):
        raise PermissionError("native pair-matrix source/session/event changed after approval")

    models = {role: approval._model_binding(runtime, role) for role in ROLES}
    if record.get("models") != models:
        raise PermissionError("native pair-matrix model revision/hash/path changed after approval")
    if runtime.cancel_event.is_set():
        raise InterruptedError("native pair matrix cancelled before execution; approval remains pending")

    resource_preflight = {}
    for role in ROLES:
        resource_preflight[role] = approval._resource_preflight(runtime, models[role])
        clock = approval._clock(now)
        if clock >= expires:
            raise PermissionError("native pair-matrix approval expired during resource preflight")
        if runtime.cancel_event.is_set():
            raise InterruptedError("native pair matrix cancelled during resource preflight; approval remains pending")

    consumed = dict(record)
    consumed.update({"status": "CONSUMED", "consumed_at": clock})
    runtime.store.set_state(approval.KEY, consumed, expected=version)
    return {
        "approval_id": record["nonce"][:12],
        "event_id": record["event_id"],
        "pairs": _pairs_json(),
        "consumed": True,
        "resource_preflight": resource_preflight,
    }


def revoke_matrix(runtime, *, now=None):
    """Revoke only a pending matrix approval; never revoke a single-pair approval."""
    approval._require_local_tty()
    runtime.require_idle()
    clock = approval._clock(now)
    record, version = runtime.store.state(approval.KEY, None)
    if (
        not isinstance(record, dict)
        or record.get("schema") != MATRIX_SCHEMA
        or record.get("status") != "PENDING"
    ):
        return {"status": "NO_PENDING_MATRIX_APPROVAL"}
    revoked = dict(record)
    revoked.update({"status": "REVOKED", "revoked_at": clock})
    runtime.store.set_state(approval.KEY, revoked, expected=version)
    return {
        "status": "REVOKED",
        "approval_id": str(record.get("nonce", ""))[:12],
        "matrix": True,
    }


def _packet_summary(packet_value, sender, receiver):
    from .native_latent_receiver import validate_packet

    packet_value = validate_packet(packet_value)
    if packet_value.get("sender_role") != sender or packet_value.get("receiver_role") != receiver:
        raise ValueError("native pair-matrix receiver returned a different role pair")
    fields = (
        "status",
        "input_rows",
        "input_dim",
        "receiver_input_dim",
        "output_dim",
        "native_input_consumed",
        "input_effect_detected",
        "input_effect_rms",
        "receiver_next_token_id",
        "zero_control_next_token_id",
        "shuffle_control_next_token_id",
        "row_shuffle_control_next_token_id",
        "repeat_next_token_id",
        "receiver_next_token_margin",
        "logit_effect_rms",
        "logit_cosine",
        "next_token_effect_detected",
        "next_token_changed_vs_zero",
        "next_token_changed_vs_shuffle",
        "next_token_changed_vs_row_shuffle",
        "repeat_next_token_stable",
        "row_shuffle_control_applicable",
        "row_shuffle_control_cosine",
    )
    return {
        "sender_role": sender,
        "receiver_role": receiver,
        **{name: packet_value.get(name) for name in fields},
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }


def run_matrix(runtime):
    """Run the fixed matrix serially under one exclusive Runtime lease."""
    approval._require_local_tty()
    with approval.runtime_probe_lease(runtime) as lease_token:
        event, source_ref = approval._current_event(runtime)
        armed = consume_matrix(
            runtime,
            event,
            source_ref,
            lease_token=lease_token,
        )
        started = time.monotonic()
        results = []
        error_type = None
        for sender, receiver in PAIRS:
            remaining = MAX_TOTAL_SECONDS - (time.monotonic() - started)
            if remaining <= 0:
                error_type = "MatrixDeadline"
                break
            deadline = time.monotonic() + min(PAIR_DEADLINE_SECONDS, remaining)
            try:
                packet_value = approval._native_receive_interruptibly(
                    runtime, sender, receiver, event, source_ref, deadline,
                )
                results.append(_packet_summary(packet_value, sender, receiver))
            except Exception as exc:
                error_type = type(exc).__name__
                break
            finally:
                try:
                    runtime.pool.unload()
                except Exception as exc:
                    error_type = error_type or ("PoolUnload_" + type(exc).__name__)
            if error_type:
                break

        duration = time.monotonic() - started
        status = "COMPLETE" if len(results) == len(PAIRS) else (
            "CANCELLED" if error_type == "InterruptedError" else "PARTIAL"
        )
        summary = {
            "schema": RESULT_SCHEMA,
            "status": status,
            "approval_id": armed["approval_id"],
            "pair_count": len(PAIRS),
            "completed_pairs": len(results),
            "duration_s": duration,
            "pairs": results,
            "error_type": error_type,
            "production_route": False,
            "semantic_use_proven": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
            "limitations": [
                "separate-context input-effect probe only",
                "no trained cross-model alignment or semantic utility proof",
                "no production B3 route and no weight update",
            ],
        }
        runtime.store.log(
            "native_latent_receiver_matrix",
            event["event_id"],
            {
                **summary,
                "source_id": source_ref["source_id"],
                "resource_preflight": armed["resource_preflight"],
            },
        )
        return dumps(summary)


def operator_command(runtime, args):
    if args == ["arm-probe-matrix", "--last-source", "--confirm"]:
        return dumps(arm_matrix(runtime))
    if args == ["native-probe-matrix", "--last-source", "--confirm"]:
        return run_matrix(runtime)
    if args == ["revoke-probe-matrix"]:
        return dumps(revoke_matrix(runtime))
    raise ValueError(
        ":callosum [arm-probe-matrix --last-source --confirm|"
        "native-probe-matrix --last-source --confirm|revoke-probe-matrix]"
    )
