"""Short-lived, local-TTY approval for one source/model-bound native receiver probe.

This module grants no production routing, learning, shell, network, or model-swap
authority. The approval is tied to one Runtime instance and one completed turn.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import secrets
import stat
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from .models import model_key
from .common import dumps

KEY = "v14.native_probe_approval"
SCHEMA = "v14.native-probe-approval/1"
TTL_SECONDS = 120
MIN_EXTRA_HEADROOM_BYTES = 256 * 1024 * 1024
MIN_MODEL_HEADROOM_RATIO = 0.20
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
    nonblock = getattr(os, "O_NONBLOCK", None)
    if nofollow is None or nonblock is None:
        raise PermissionError("native probe platform lacks safe no-follow/nonblocking model open")
    # O_NOFOLLOW prevents a final symlink; O_NONBLOCK prevents a FIFO/device
    # from hanging the approval path before fstat can reject non-regular files.
    flags = os.O_RDONLY | nofollow | nonblock | getattr(os, "O_CLOEXEC", 0)
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
    return {
        "model_key": key,
        "revision": revision,
        "sha256": digest,
        # Persist both the canonical route and the identity of the exact inode
        # whose bytes were hashed. Recomputing only at consume would miss a
        # coordinated manifest+router redirect to a byte-identical copy.
        "canonical_path": str(resolved),
        "file_identity": list(verified_identity),
    }


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


def _require_local_tty():
    """Do not let a caller-supplied Operator origin impersonate a human TTY."""
    try:
        interactive = os.isatty(0)
    except (OSError, ValueError):
        interactive = False
    if interactive is not True:
        raise PermissionError("native probe approval requires an interactive local TTY")


def arm(runtime, sender_role, receiver_role, *, now=None):
    """Arm one exact probe only from an interactive local terminal."""
    _require_local_tty()
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
        "model_paths_and_file_identity_bound": True,
        "runtime_instance_scoped": True,
        "production_route": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }



@contextmanager
def runtime_probe_lease(runtime):
    """Exclusively reserve the idle Runtime while one approved native probe runs."""
    lock = getattr(runtime, "lock", None)
    if lock is None:
        raise ValueError("native probe cannot acquire the Runtime lock")
    token = secrets.token_hex(16)
    with lock:
        if getattr(runtime, "closed", False) or runtime.stop.is_set():
            raise ValueError("native probe cannot run on a closed Runtime")
        if (runtime.current is not None or not runtime.jobs.empty()
                or runtime.store.queue_stats().get("count", 0) != 0):
            raise ValueError("native probe requires an idle Runtime with no queued work")
        if runtime.paused or runtime.store.queue_paused():
            raise ValueError("native probe cannot override a paused Runtime")
        if getattr(runtime, "_native_probe_lease_nonce", None):
            raise ValueError("another native probe Runtime lease is already active")
        runtime.current = "probe"
        runtime.paused = True
        runtime.status = "probe"
        runtime._native_probe_lease_nonce = token
        runtime.cancel_event.clear()
        runtime.wake.set()
    try:
        yield token
    finally:
        with lock:
            if getattr(runtime, "_native_probe_lease_nonce", None) == token:
                if runtime.current == "probe":
                    runtime.current = None
                delattr(runtime, "_native_probe_lease_nonce")
                persisted_pause = bool(runtime.store.queue_paused())
                runtime.paused = persisted_pause or runtime.current is not None
                if runtime.current is None:
                    runtime.status = "Beendet" if runtime.stop.is_set() else ("Pausiert" if runtime.paused else "Bereit")
                runtime.wake.set()


def _require_runtime_probe_lease(runtime, lease_token):
    with runtime.lock:
        if (not isinstance(lease_token, str) or not lease_token
                or runtime.current != "probe"
                or getattr(runtime, "_native_probe_lease_nonce", None) != lease_token):
            raise PermissionError("native probe requires its active exclusive Runtime lease")
        if runtime.stop.is_set():
            raise InterruptedError("native probe Runtime stopped during its exclusive lease")
        if (not runtime.jobs.empty()
                or runtime.store.queue_stats().get("count", 0) != 0):
            raise PermissionError("native probe Runtime lease lost its empty queue")


def _resource_preflight(runtime, receiver_binding):
    """Unload body runners and refuse residency in the known managed-model census."""
    pool = getattr(runtime, "pool", None)
    unload = getattr(pool, "unload", None)
    if not callable(unload):
        raise PermissionError("native probe cannot verify B1/B2/C3 unload")
    try:
        unload()
    except Exception as exc:
        raise PermissionError("native probe could not unload B1/B2/C3 runners") from exc

    semantic_keys = getattr(getattr(runtime, "memory", None), "semantic_keys", None)
    encoder = getattr(semantic_keys, "encoder", None)
    owners = (
        ("B1/B2/C3", pool),
        ("C2", getattr(runtime, "needle", None)),
        ("semantic encoder", encoder),
    )
    process_counts = {}
    for label, owner in owners:
        pids_fn = getattr(owner, "pids", None)
        if not callable(pids_fn):
            raise PermissionError("native probe cannot verify " + label + " process residency")
        try:
            pids = pids_fn()
        except Exception as exc:
            raise PermissionError("native probe cannot inspect " + label + " process residency") from exc
        if not isinstance(pids, (list, tuple, set)):
            raise PermissionError("native probe received invalid " + label + " process census")
        process_counts[label] = len(pids)
        if pids:
            raise PermissionError(
                "native probe requires zero known managed model processes; "
                + label + " still has " + str(len(pids))
            )

    resources_fn = getattr(runtime, "resources", None)
    if not callable(resources_fn):
        raise PermissionError("native probe cannot verify MemAvailable")
    try:
        snapshot = resources_fn()
    except Exception as exc:
        raise PermissionError("native probe cannot read resource snapshot") from exc
    if not isinstance(snapshot, dict):
        raise PermissionError("native probe resource snapshot is invalid")
    available = snapshot.get("mem_available_bytes")
    if type(available) is not int or available <= 0:
        raise PermissionError("native probe requires a valid MemAvailable byte count")

    identity = receiver_binding.get("file_identity")
    if not isinstance(identity, (list, tuple)) or len(identity) < 3:
        raise PermissionError("native probe receiver model identity is incomplete")
    model_bytes = identity[2]
    if type(model_bytes) is not int or model_bytes <= 0:
        raise PermissionError("native probe receiver model size is invalid")
    extra = max(MIN_EXTRA_HEADROOM_BYTES, math.ceil(model_bytes * MIN_MODEL_HEADROOM_RATIO))
    required = model_bytes + extra
    if available < required:
        raise PermissionError(
            "native probe MemAvailable is insufficient: requires at least "
            + str(required) + " bytes for model plus headroom; found " + str(available)
        )
    return {
        "status": "PASS",
        "mem_available_bytes": available,
        "receiver_model_bytes": model_bytes,
        "minimum_extra_headroom_bytes": extra,
        "required_headroom_bytes": required,
        "headroom_margin_bytes": available - required,
        "known_managed_model_processes": sum(process_counts.values()),
        "process_counts": process_counts,
        "census_scope": [
            "runtime.pool (B1/B2/C3)",
            "runtime.needle (C2)",
            "runtime.memory.semantic_keys.encoder",
        ],
        "global_native_process_census": False,
        "uncovered_process_managers": [
            "independent audio/voice processes",
            "future B3 or other native process managers",
        ],
        "body_models_unloaded": True,
        "estimate": "receiver file size plus max(256 MiB, 20%); known-manager census only, not a global process census or OOM guarantee",
    }


def consume(runtime, sender_role, receiver_role, event, source_ref, *, now=None, lease_token=None):
    """Consume the local approval atomically before any native receiver work."""
    _require_local_tty()
    if lease_token is None:
        runtime.require_idle()
    else:
        _require_runtime_probe_lease(runtime, lease_token)
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
    if runtime.cancel_event.is_set():
        raise InterruptedError("native probe cancelled before execution; local approval remains pending")
    resource_preflight = _resource_preflight(runtime, models[receiver_role])
    # Hashing and resource checks can be slow for large GGUFs; re-check expiry and cancellation.
    clock = _clock(now)
    if clock >= expires:
        raise PermissionError("native probe local approval expired")
    if runtime.cancel_event.is_set():
        raise InterruptedError("native probe cancelled before execution; local approval remains pending")
    consumed = dict(record)
    consumed.update({"status": "CONSUMED", "consumed_at": clock})
    runtime.store.set_state(KEY, consumed, expected=version)
    return {
        "approval_id": record["nonce"][:12],
        "sender_role": sender_role,
        "receiver_role": receiver_role,
        "event_id": record["event_id"],
        "consumed": True,
        "resource_preflight": resource_preflight,
    }


def revoke(runtime, *, now=None):
    """Revoke a pending local probe approval without invoking the native runner."""
    _require_local_tty()
    runtime.require_idle()
    clock = _clock(now)
    record, version = runtime.store.state(KEY, None)
    if not isinstance(record, dict) or record.get("status") != "PENDING":
        return {"status": "NO_PENDING_APPROVAL"}
    revoked = dict(record)
    revoked.update({"status": "REVOKED", "revoked_at": clock})
    runtime.store.set_state(KEY, revoked, expected=version)
    return {"status": "REVOKED", "approval_id": str(record.get("nonce", ""))[:12]}


def _native_receive_interruptibly(runtime, sender, receiver, event, source_ref, deadline):
    """Let Ctrl+C signal the native subprocess through Runtime.cancel_event."""
    outcome = {}

    def invoke():
        try:
            outcome["packet"] = runtime.cognition.native_receive(
                sender, receiver, event, source_ref, deadline,
            )
        except BaseException as exc:
            outcome["error"] = exc

    worker = threading.Thread(target=invoke, name="v14-native-probe", daemon=True)
    worker.start()
    interrupted = False
    late_interrupt = False
    while worker.is_alive():
        try:
            worker.join(0.1)
        except KeyboardInterrupt:
            if worker.is_alive():
                runtime.cancel_event.set()
                interrupted = True
                # The native receiver checks this event while waiting on its child
                # process. Keep the exclusive Runtime lease until that child exits.
            else:
                late_interrupt = True
    if interrupted:
        raise InterruptedError("Native probe cancelled by local operator")
    error = outcome.get("error")
    if error is not None:
        raise error
    packet = outcome.get("packet")
    if not isinstance(packet, dict):
        raise RuntimeError("Native receiver returned no result packet")
    # A Ctrl+C arriving after the worker completed must not misreport a
    # completed, persisted probe as cancelled.
    return packet


def operator_command(runtime, args):
    """Local :callosum native-probe workflow; every stage requires a real TTY."""
    if (len(args) == 5 and args[0] == "arm-probe"
            and args[3:] == ["--last-source", "--confirm"]):
        return dumps(arm(runtime, args[1], args[2]))
    if args == ["revoke-probe"]:
        return dumps(revoke(runtime))
    if (len(args) == 5 and args[0] == "native-probe"
            and args[3:] == ["--last-source", "--confirm"]):
        sender, receiver = args[1], args[2]
        _roles(sender, receiver)
        with runtime_probe_lease(runtime) as lease_token:
            last = runtime.last_answer()
            if not last or last.get("status") != "FINAL" or not last.get("event_id"):
                raise ValueError("Native probe requires a completed FINAL answer")
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
            approval = consume(
                runtime, sender, receiver, event, source_ref, lease_token=lease_token,
            )
            runtime.models.path_for(receiver)
            deadline = time.monotonic() + 120.0
            try:
                packet = _native_receive_interruptibly(
                    runtime, sender, receiver, event, source_ref, deadline,
                )
            finally:
                runtime.pool.unload()
            return dumps({
                **packet,
                "queued": False,
                "completed": True,
                "sender_role": sender,
                "receiver_role": receiver,
                "approval_id": approval["approval_id"],
                "local_approval_consumed": True,
                "resource_preflight": approval["resource_preflight"],
                "runtime_exclusive": True,
                "requires_explicit_confirmation": False,
                "production_route": False,
                "semantic_use_proven": False,
                "training_authority": 0,
                "native_receiver_authority": 0,
                "notice": "Synchronous probe under an exclusive Runtime lease after one-shot local TTY approval; no weight or routing change",
            })
    raise ValueError(
        ":callosum [status|shadow|active|degrade|promote <direction>|"
        "arm-probe <sender> <receiver> --last-source --confirm|"
        "native-probe <sender> <receiver> --last-source --confirm|revoke-probe]"
    )
