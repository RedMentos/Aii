"""Short-lived, local-TTY approval for one source/model-bound native receiver probe.

This module grants no production routing, learning, shell, network, or model-swap
authority. The approval is tied to one Runtime instance and one completed turn.
"""
from __future__ import annotations

import hashlib
import math
import os
import secrets
import stat
import time
from pathlib import Path

from .models import model_key

KEY = "v14.native_probe_approval"
SCHEMA = "v14.native-probe-approval/1"
TTL_SECONDS = 120
SENDER_ROLES = frozenset({"B1_DETAIL", "B2_GIST"})
RECEIVER_ROLES = frozenset({"B1_DETAIL", "B2_GIST", "C3_LANGUAGE"})


def _clock(value):
    if value is None:
        value = time.time()
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("native probe approval clock is invalid")
    return float(value)


def _runtime_nonce(runtime):
    nonce = getattr(runtime, "_native_probe_approval_runtime_nonce", None)
    if not isinstance(nonce, str) or len(nonce) != 32:
        nonce = secrets.token_hex(16)
        setattr(runtime, "_native_probe_approval_runtime_nonce", nonce)
    return nonce


def _roles(sender_role, receiver_role):
    if sender_role not in SENDER_ROLES:
        raise ValueError("native probe sender must be B1_DETAIL or B2_GIST")
    if receiver_role not in RECEIVER_ROLES or sender_role == receiver_role:
        raise ValueError("native probe receiver must be a distinct B1/B2/C3 role")



def _verify_model_file(path, expected_size, expected_digest):
    """Stream the actual model bytes and bind them to the installed manifest."""
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise PermissionError("native probe platform cannot safely open model without following symlinks")
    flags = os.O_RDONLY | nofollow | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(str(path), flags)
    except OSError as exc:
        raise PermissionError("native probe model cannot be opened safely") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size != expected_size:
            raise PermissionError("native probe model file type or size differs from its manifest")
        digest = hashlib.sha256()
        with os.fdopen(os.dup(fd), "rb") as stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        after = os.fstat(fd)
        identity = lambda value: (
            value.st_dev, value.st_ino, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns,
        )
        try:
            path_stat = os.stat(path, follow_symlinks=False)
        except OSError as exc:
            raise PermissionError("native probe model path changed during verification") from exc
        if (not stat.S_ISREG(path_stat.st_mode)
                or identity(before) != identity(after)
                or identity(after) != identity(path_stat)):
            raise PermissionError("native probe model changed while hashing")
        actual = digest.hexdigest()
        if not secrets.compare_digest(actual, expected_digest):
            raise PermissionError("native probe model file hash differs from its manifest")
        return identity(after)
    finally:
        os.close(fd)

def _model_binding(runtime, role):
    key = model_key(role, runtime.models.b2_control)
    installed = runtime.models.installed.get(key)
    if not isinstance(installed, dict) or installed.get("download_complete") is not True:
        raise PermissionError("native probe requires an already-installed model for " + role)
    revision = installed.get("exact_revision")
    if not isinstance(revision, str) or not revision or runtime.models.revision(role) != revision:
        raise PermissionError("native probe model revision is not the installed pinned revision")
    main_file = installed.get("main_file")
    files = installed.get("files")
    entry = files.get(main_file) if isinstance(files, dict) and isinstance(main_file, str) else None
    if not isinstance(entry, dict):
        raise PermissionError("native probe model manifest is incomplete")
    digest = entry.get("sha256")
    if (not isinstance(digest, str) or len(digest) != 64
            or any(ch not in "0123456789abcdef" for ch in digest)):
        raise PermissionError("native probe model manifest hash is invalid")
    relative_path = entry.get("path")
    if not isinstance(relative_path, str) or not relative_path:
        raise PermissionError("native probe model manifest path is missing")
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise PermissionError("native probe model manifest path is unsafe")
    path = Path(runtime.home) / relative
    if path.is_symlink() or not path.is_file():
        raise PermissionError("native probe model is missing or linked")
    resolved = path.resolve(strict=True)
    models_root = (Path(runtime.home) / "models").resolve(strict=True)
    if not resolved.is_relative_to(models_root):
        raise PermissionError("native probe model escaped home/models")
    size = entry.get("size")
    if type(size) is not int or size < 1:
        raise PermissionError("native probe model size is missing or invalid")
    verified_identity = _verify_model_file(resolved, size, digest)
    # The native receiver later opens ModelManager.path_for(role), which may be
    # redirected by an online model router. Bind approval to that exact route,
    # not merely to another manifest file with matching bytes.
    try:
        selected_path = Path(runtime.models.path_for(role))
        if selected_path.is_symlink():
            raise PermissionError("native probe selected model path is linked")
        selected_resolved = selected_path.resolve(strict=True)
        selected_stat = os.stat(selected_path, follow_symlinks=False)
    except PermissionError:
        raise
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise PermissionError("native probe selected model path is unavailable") from exc
    selected_identity = (
        selected_stat.st_dev, selected_stat.st_ino, selected_stat.st_size,
        selected_stat.st_mtime_ns, selected_stat.st_ctime_ns,
    )
    if (not stat.S_ISREG(selected_stat.st_mode)
            or selected_resolved != resolved
            or selected_identity != verified_identity):
        raise PermissionError("native probe selected model path differs from verified manifest file")
    return {"model_key": key, "revision": revision, "sha256": digest}


def _current_event(runtime):
    last = runtime.last_answer()
    if not last or last.get("status") != "FINAL" or not last.get("event_id"):
        raise PermissionError("native probe requires the latest completed FINAL answer")
    row = runtime.store.one(
        "SELECT packet,session_id FROM events WHERE id=?",
        (last["event_id"],),
    )
    if not row or row["session_id"] != runtime.session:
        raise PermissionError("native probe event is not in the active session")
    import json
    event = json.loads(row["packet"])
    if (event.get("event_id") != last["event_id"]
            or event.get("authority") != "AUTHORITATIVE"
            or event.get("kind") != "USER_TEXT"
            or event.get("brain_generation_id") != runtime.store.generation_id):
        raise PermissionError("native probe event is not current authoritative user input")
    source_ref = event.get("source_ref")
    if (not isinstance(source_ref, dict) or not isinstance(source_ref.get("source_id"), str)
            or source_ref.get("modality") != "text"):
        raise PermissionError("native probe requires the exact text source of the last turn")
    runtime.store.read_source(source_ref)
    return event, source_ref


def arm(runtime, sender_role, receiver_role, *, now=None):
    """Arm one exact probe locally; caller is the local Operator TTY path."""
    runtime.require_idle()
    _roles(sender_role, receiver_role)
    event, source_ref = _current_event(runtime)
    models = {
        sender_role: _model_binding(runtime, sender_role),
        receiver_role: _model_binding(runtime, receiver_role),
    }
    # Start the short approval window only after the full model-byte verification.
    clock = _clock(now)
    runtime_nonce = _runtime_nonce(runtime)
    current, version = runtime.store.state(KEY, None)
    if isinstance(current, dict) and current.get("status") == "PENDING":
        expires = current.get("expires_at")
        if (current.get("runtime_nonce") == runtime_nonce
                and isinstance(expires, (int, float)) and not isinstance(expires, bool)
                and clock < expires):
            raise PermissionError("a native probe approval is already pending; revoke it first")
    nonce = secrets.token_hex(16)
    record = {
        "schema": SCHEMA,
        "status": "PENDING",
        "nonce": nonce,
        "runtime_nonce": runtime_nonce,
        "issued_at": clock,
        "expires_at": int(clock) + TTL_SECONDS,
        "session_id": runtime.session,
        "event_id": event["event_id"],
        "brain_generation_id": event["brain_generation_id"],
        "source_ref": dict(source_ref),
        "sender_role": sender_role,
        "receiver_role": receiver_role,
        "models": models,
    }
    runtime.store.set_state(KEY, record, expected=version)
    return {
        "status": "ARMED",
        "approval_id": nonce[:12],
        "expires_in_seconds": TTL_SECONDS,
        "sender_role": sender_role,
        "receiver_role": receiver_role,
        "source_bound": True,
        "model_revisions_and_hashes_bound": True,
        "runtime_instance_scoped": True,
        "production_route": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }


def consume(runtime, sender_role, receiver_role, event, source_ref, *, now=None):
    """Consume the local approval atomically before any native receiver work."""
    runtime.require_idle()
    _roles(sender_role, receiver_role)
    clock = _clock(now)
    record, version = runtime.store.state(KEY, None)
    if not isinstance(record, dict) or record.get("schema") != SCHEMA or record.get("status") != "PENDING":
        raise PermissionError("native probe requires a fresh local :callosum arm-probe approval")
    if record.get("runtime_nonce") != _runtime_nonce(runtime):
        raise PermissionError("native probe approval expired across Runtime restart")
    expires = record.get("expires_at")
    if (isinstance(expires, bool) or not isinstance(expires, (int, float))
            or not math.isfinite(expires) or clock >= expires):
        raise PermissionError("native probe local approval expired")
    if (record.get("sender_role") != sender_role
            or record.get("receiver_role") != receiver_role):
        raise PermissionError("native probe role pair differs from local approval")
    current_event, current_ref = _current_event(runtime)
    if (not isinstance(event, dict)
            or event.get("event_id") != current_event.get("event_id")
            or event.get("brain_generation_id") != current_event.get("brain_generation_id")
            or source_ref != current_ref
            or record.get("session_id") != runtime.session
            or record.get("event_id") != current_event.get("event_id")
            or record.get("brain_generation_id") != current_event.get("brain_generation_id")
            or record.get("source_ref") != current_ref):
        raise PermissionError("native probe source/session/event changed after local approval")
    models = {
        sender_role: _model_binding(runtime, sender_role),
        receiver_role: _model_binding(runtime, receiver_role),
    }
    if record.get("models") != models:
        raise PermissionError("native probe model revision/hash changed after local approval")
    # Hashing can be slow for large GGUFs; re-check expiry after verification.
    clock = _clock(now)
    if clock >= expires:
        raise PermissionError("native probe local approval expired")
    consumed = dict(record)
    consumed.update({"status": "CONSUMED", "consumed_at": clock})
    runtime.store.set_state(KEY, consumed, expected=version)
    return {
        "approval_id": record["nonce"][:12],
        "sender_role": sender_role,
        "receiver_role": receiver_role,
        "event_id": record["event_id"],
        "consumed": True,
    }


def revoke(runtime, *, now=None):
    """Revoke a pending local probe approval without invoking the native runner."""
    runtime.require_idle()
    clock = _clock(now)
    record, version = runtime.store.state(KEY, None)
    if not isinstance(record, dict) or record.get("status") != "PENDING":
        return {"status": "NO_PENDING_APPROVAL"}
    revoked = dict(record)
    revoked.update({"status": "REVOKED", "revoked_at": clock})
    runtime.store.set_state(KEY, revoked, expected=version)
    return {"status": "REVOKED", "approval_id": str(record.get("nonce", ""))[:12]}
