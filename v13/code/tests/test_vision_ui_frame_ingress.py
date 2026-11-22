"""Synthetic MediaProjection frame tests for the RAW EYE UI adapter."""
from contextlib import contextmanager
from io import BytesIO
import hashlib
import os
import threading
import time
from types import SimpleNamespace

import numpy as np

import pytest
from PIL import Image, ImageDraw

from v13.a5_ui_admission_bridge import A5UIRuntimeAdapter, ui_observation_lease
from v13.vision_ui_frame_ingress import (
    ProviderFrameVerifier, _issue_provider_frame_verifier,
    _load_local_tile_projector, consume_projected_frame,
)


class _Attention:
    def perceive(self, event_id, segments, *, goal="", file_requests=True):
        assert file_requests is False
        return {
            "segments": [{"index": i, "score": 0.25, "source_ref": x["source_ref"]}
                         for i, x in enumerate(segments)],
            "highres": [], "requests": [], "truth_authority": 0,
        }


class _Cursor:
    def fetchone(self):
        return None


class _Connection:
    def execute(self, *args, **kwargs):
        return _Cursor()


class _Store:
    def __init__(self, lock):
        self.mutex = lock
        self._state = {}

    def state(self, key, default=None):
        return self._state.get(key, default), 0

    @contextmanager
    def tx(self):
        yield _Connection()


def make_runtime(monkeypatch, with_store=False):
    runtime = SimpleNamespace(
        turn_event={"event_id": "evt_ui_frame_1", "brain_generation_id": "gen_ui_frame_1"},
        current="turn",
        cancel_event=threading.Event(),
    )
    if with_store:
        runtime.store = _Store(threading.RLock())
    monkeypatch.setattr(
        "v13.vision_ui_frame_ingress.attention_module.controller",
        lambda _runtime: _Attention(),
    )
    return runtime


def observation(finality="FINAL", method="MEDIA_PROJECTION", event_kind="SCREEN_FRAME_AVAILABLE"):
    value = {
        "schema": "v14.a5.ui-observation/1",
        "modality": "ui",
        "source_id": "ui-frame-source-0001",
        "capture_session_id": "ui-frame-session-0001",
        "consent_receipt_ref": "receipt-frame-0001",
        "capture_method": method,
        "capture_scope": "FULL_DISPLAY" if method == "MEDIA_PROJECTION" else "ACCESSIBILITY_TREE",
        "api_level": 34,
        "clock": "ELAPSED_REALTIME",
        "event_kind": event_kind,
        "start_ms": 1000,
        "end_ms": 1033,
        "finality": finality,
        "action_authority": False,
        "learning_authority": False,
        "raw_capture_persisted": False,
    }
    if method == "ACCESSIBILITY_ASSISTIVE":
        value["accessibility_purpose"] = "DISABILITY_ASSISTANCE"
    return value


def image_buffer():
    image = Image.new("RGB", (64, 64), (8, 8, 8))
    draw = ImageDraw.Draw(image)
    draw.rectangle((38, 14, 59, 52), fill=(230, 20, 18))
    draw.rectangle((8, 8, 19, 24), fill=(12, 180, 220))
    output = BytesIO()
    image.save(output, format="PNG")
    image.close()
    return bytearray(output.getvalue())


def provider_verifier(lease, obs, frame, *, result=True, failure=None):
    expected_sha = hashlib.sha256(frame).hexdigest()
    expected_size = len(frame)

    def verify(candidate, frame_sha256, frame_size):
        if failure is not None:
            raise failure
        return (
            result is True
            and candidate == obs
            and frame_sha256 == expected_sha
            and frame_size == expected_size
        )

    return _issue_provider_frame_verifier(lease, obs, verify)


def consume_with_provider_verifier(runtime, obs, frame, *, consent_lease, frame_verifier=None, **kwargs):
    if frame_verifier is None:
        frame_verifier = provider_verifier(consent_lease, obs, frame)
    return consume_projected_frame(
        runtime, obs, frame, consent_lease=consent_lease,
        frame_verifier=frame_verifier, **kwargs,
    )



def install_student_projector(runtime, tmp_path):
    """Train a tiny synthetic tile projector on a shifted UI image (held-out frame)."""
    from v13 import vision

    training = Image.new("RGB", (64, 64), (8, 8, 8))
    draw = ImageDraw.Draw(training)
    draw.rectangle((36, 12, 57, 50), fill=(230, 20, 18))
    draw.rectangle((8, 8, 19, 24), fill=(12, 180, 220))
    features, labels = [], []
    for region in vision.boxes(64, 64, 4):
        if not region["region_id"].startswith("r"):
            continue
        box = region["box"]
        tile = training.crop(tuple(box))
        try:
            features.append(vision.tile_features(tile, 32))
        finally:
            tile.close()
        x0, y0, x1, y1 = box
        red_overlap = max(0, min(x1, 58) - max(x0, 36)) * max(0, min(y1, 51) - max(y0, 12))
        blue_overlap = max(0, min(x1, 20) - max(x0, 8)) * max(0, min(y1, 25) - max(y0, 8))
        if red_overlap >= 50:
            labels.append("red panel")
        elif blue_overlap >= 25:
            labels.append("blue icon")
        else:
            labels.append(vision.BACKGROUND)
    training.close()

    projector = vision.Projector(0.1).fit(
        np.stack(features),
        np.stack([vision.hashed_embed(label) for label in labels]),
    )
    path = tmp_path / "data" / "vision" / "tiles-test.npz"
    path.parent.mkdir(parents=True, exist_ok=True)
    sha = projector.save(path)
    runtime.home = tmp_path
    runtime.store._state[vision.KEY] = {
        "tile_projector": {
            "path": "data/vision/tiles-test.npz",
            "sha256": sha,
            "n": len(features),
            "encoder": "hashed_bow",
            "authority": "LAB_SHADOW_ONLY",
        }
    }
    return path, sha


def lease_for(runtime, obs, callbacks=None, lock=None):
    lock = lock or threading.RLock()

    def check(*_args):
        return True

    @contextmanager
    def guard(*_args):
        with lock:
            yield True

    def subscribe(source_id, receipt, session, request_cancel, on_revoked):
        if callbacks is not None:
            callbacks[source_id] = (request_cancel, on_revoked)
        def unsubscribe():
            if callbacks is not None:
                callbacks.pop(source_id, None)
        return unsubscribe

    return ui_observation_lease(
        runtime, obs, runtime.turn_event["brain_generation_id"],
        check, guard, subscribe,
    )


def test_media_projection_frame_reaches_a5_a4_and_existing_ui_context(monkeypatch):
    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = image_buffer()
    expected_hash = hashlib.sha256(frame).hexdigest()
    prompt = "Describe only the visible UI state; preserve this exact request."

    with lease_for(runtime, obs) as lease:
        result = consume_with_provider_verifier(
            runtime, obs, frame, consent_lease=lease,
            current_source=prompt, goal="red panel", token_budget=512,
        )
        packets = A5UIRuntimeAdapter(runtime).context(runtime.turn_event["event_id"], lease)
        assert packets == (result["packet"],)
        assert result["status"] == "WIRED_SYNTHETIC"
        assert result["packet"]["modality"] == "ui"
        assert result["packet"]["frame_sha256"] == expected_hash
        assert len(result["packet"]["segments"]) == 18  # UI event + global + 16 tiles
        assert result["packet"]["raw_capture_persisted"] is False
        assert result["packet"]["derived_packet_persisted"] is False
        assert result["packet"]["teacher_used"] is False
        assert result["packet"]["student_projector_used"] is False
        assert result["packet"]["learning_authority"] is False
        assert result["packet"]["action_authority"] is False
        assert result["a4"]["truth_authority"] == 0
        assert result["context_envelope"].current_source == prompt
        assert result["context_packet_count"] == 1
        assert result["caller_buffer_overwritten"] is True
        assert not any(frame)


def test_verified_frame_snapshot_prevents_post_receipt_buffer_swap(monkeypatch):
    from v13 import vision
    from v13.vision_ui_frame_ingress import _issue_provider_frame_verifier

    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = image_buffer()
    replacement_image = Image.new("RGB", (64, 64), (220, 20, 18))
    replacement_stream = BytesIO()
    replacement_image.save(replacement_stream, format="PNG")
    replacement_image.close()
    replacement = bytearray(replacement_stream.getvalue())
    original_hash = hashlib.sha256(frame).hexdigest()
    decoded = []
    original_decode = vision.decode

    def tracked_decode(data, cfg):
        decoded.append((hashlib.sha256(data).hexdigest(), data))
        return original_decode(data, cfg)

    monkeypatch.setattr("v13.vision_ui_frame_ingress.vision.decode", tracked_decode)

    def verify_then_mutate(candidate, digest, size):
        accepted = candidate == obs and digest == original_hash and size == len(frame)
        frame[:] = replacement
        return accepted

    with lease_for(runtime, obs) as lease:
        verifier = _issue_provider_frame_verifier(lease, obs, verify_then_mutate)
        result = consume_projected_frame(
            runtime, obs, frame, consent_lease=lease,
            frame_verifier=verifier, current_source="Describe this screen.",
            goal="red panel", token_budget=512,
        )

    assert decoded[0][0] == original_hash
    assert result["packet"]["frame_sha256"] == original_hash
    assert not any(frame)
    assert not any(decoded[0][1])
    replacement[:] = b"\x00" * len(replacement)


def test_provisional_frame_is_never_admitted_to_c3_context(monkeypatch):
    runtime = make_runtime(monkeypatch)
    obs = observation(finality="PROVISIONAL")
    frame = image_buffer()
    prompt = "Keep the exact source."

    with lease_for(runtime, obs) as lease:
        result = consume_with_provider_verifier(
            runtime, obs, frame, consent_lease=lease,
            current_source=prompt, token_budget=512,
        )
        assert result["admission"].status == "EMPTY_OR_UNAUTHORIZED"
        assert result["context_envelope"].current_source == prompt
        assert result["context_envelope"].optional_context == ""
        assert result["context_packet_count"] == 0
        assert A5UIRuntimeAdapter(runtime).context(runtime.turn_event["event_id"], lease) == ()
        assert result["caller_buffer_overwritten"] is True


def test_wrong_receipt_and_non_projection_events_fail_closed(monkeypatch):
    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = image_buffer()
    with lease_for(runtime, obs) as lease:
        wrong = dict(obs, consent_receipt_ref="receipt-other")
        with pytest.raises(PermissionError, match="lease"):
            consume_with_provider_verifier(
                runtime, wrong, frame, consent_lease=lease,
                current_source="Describe this.",
            )
        assert not any(frame)

    runtime = make_runtime(monkeypatch)
    obs = observation(method="ACCESSIBILITY_ASSISTIVE", event_kind="WINDOW_CONTENT_CHANGED")
    frame = image_buffer()
    with lease_for(runtime, obs) as lease:
        with pytest.raises(PermissionError, match="MediaProjection"):
            consume_with_provider_verifier(
                runtime, obs, frame, consent_lease=lease,
                current_source="Describe this.",
            )
        assert not any(frame)


def test_cancelled_lease_cannot_cache_frame_and_overwrites_buffer(monkeypatch):
    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = image_buffer()
    with lease_for(runtime, obs) as lease:
        runtime.cancel_event.set()
        with pytest.raises(PermissionError, match="lease"):
            consume_with_provider_verifier(
                runtime, obs, frame, consent_lease=lease,
                current_source="Describe this.",
            )
        assert obs["source_id"] not in getattr(runtime, "_a5_ui_context_cache", {})
        assert not any(frame)


def test_revocation_clears_ephemeral_visual_packet_cache(monkeypatch):
    runtime = make_runtime(monkeypatch, with_store=True)
    obs = observation()
    frame = image_buffer()
    callbacks = {}
    with lease_for(runtime, obs, callbacks=callbacks, lock=runtime.store.mutex) as lease:
        result = consume_with_provider_verifier(
            runtime, obs, frame, consent_lease=lease,
            current_source="Describe this.",
        )
        assert A5UIRuntimeAdapter(runtime).context(runtime.turn_event["event_id"], lease)
        request_cancel, on_revoked = callbacks[obs["source_id"]]
        assert request_cancel() is True
    cleanup = on_revoked()
    assert cleanup["cache_cleared"] is True
    assert obs["source_id"] not in runtime._a5_ui_context_cache
    assert result["caller_buffer_overwritten"] is True


def test_zero_budget_preserves_current_source_and_bad_frames_are_overwritten(monkeypatch):
    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = image_buffer()
    prompt = "Never truncate this exact current user source."
    with lease_for(runtime, obs) as lease:
        result = consume_with_provider_verifier(
            runtime, obs, frame, consent_lease=lease,
            current_source=prompt, token_budget=0, context_budget_chars=0,
        )
        assert result["admission"].status == "EMPTY_OR_UNAUTHORIZED"
        assert result["context_envelope"].current_source == prompt
        assert result["context_envelope"].optional_context == ""

    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = bytearray(b"not an image")
    with lease_for(runtime, obs) as lease:
        with pytest.raises(ValueError):
            consume_with_provider_verifier(
                runtime, obs, frame, consent_lease=lease,
                current_source="Describe this.",
            )
        assert not any(frame)


def test_provider_frame_receipt_must_match_exact_frame_digest(monkeypatch):
    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = image_buffer()
    with lease_for(runtime, obs) as lease:
        with pytest.raises(PermissionError, match="digest"):
            consume_with_provider_verifier(
                runtime, obs, frame, consent_lease=lease,
                frame_verifier=provider_verifier(lease, obs, frame, result=False),
                current_source="Describe this.",
            )
        assert not any(frame)


def test_frame_receipt_verifier_is_mandatory_and_oversized_buffer_is_rejected(monkeypatch):
    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = image_buffer()
    with lease_for(runtime, obs) as lease:
        with pytest.raises(PermissionError, match="verifier"):
            consume_projected_frame(
                runtime, obs, frame, consent_lease=lease,
                frame_verifier=None, current_source="Describe this.",
            )
        assert not any(frame)

    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = bytearray(b"x" * (8 * 1024 * 1024 + 1))
    with lease_for(runtime, obs) as lease:
        with pytest.raises(ValueError, match="8 MiB"):
            consume_with_provider_verifier(
                runtime, obs, frame, consent_lease=lease,
                current_source="Describe this.",
            )
        assert not any(frame)


def test_provider_verifier_exception_fails_closed_without_context_cache(monkeypatch):
    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = image_buffer()

    def verifier_failure(*_args):
        raise RuntimeError("provider receipt unavailable")

    with lease_for(runtime, obs) as lease:
        with pytest.raises(PermissionError, match="digest"):
            consume_with_provider_verifier(
                runtime, obs, frame, consent_lease=lease,
                frame_verifier=_issue_provider_frame_verifier(lease, obs, verifier_failure),
                current_source="Describe this.",
            )
        assert obs["source_id"] not in getattr(runtime, "_a5_ui_context_cache", {})
        assert not any(frame)


def test_local_a3_student_projector_scores_heldout_ui_tiles_and_reaches_a5(monkeypatch, tmp_path):
    runtime = make_runtime(monkeypatch, with_store=True)
    install_student_projector(runtime, tmp_path)
    obs = observation()
    frame = image_buffer()

    with lease_for(runtime, obs, lock=runtime.store.mutex) as lease:
        result = consume_with_provider_verifier(
            runtime, obs, frame, consent_lease=lease,
            current_source="What is on this screen?",
            goal="red panel", token_budget=8192, context_budget_chars=4096,
        )
        margins = result["student_goal_margins"]
        red = max(margins[key] for key in ("r12", "r13", "r22", "r23", "r32", "r33"))
        blue = max(margins[key] for key in ("r00", "r10"))
        assert result["student_projector_used"] is True
        assert result["student_projector_status"] == "USED"
        assert red > blue + 0.2
        assert result["packet"]["student_projector_used"] is True
        assert result["packet"]["student_estimate"]["authority"] == "STUDENT_ESTIMATE"
        assert result["packet"]["student_estimate"]["encoder"] == "hashed_bow"
        assert any("student_goal_margin=" in line for line in result["context_envelope"].optional_context.splitlines())
        assert result["packet"]["teacher_used"] is False
        assert result["packet"]["learning_authority"] is False
        assert result["packet"]["action_authority"] is False
        assert result["caller_buffer_overwritten"] is True


def test_tampered_local_student_projector_hash_skips_a3_without_breaking_raw_eye(monkeypatch, tmp_path):
    from v13 import vision

    runtime = make_runtime(monkeypatch, with_store=True)
    install_student_projector(runtime, tmp_path)
    runtime.store._state[vision.KEY]["tile_projector"]["sha256"] = "0" * 64
    obs = observation()
    frame = image_buffer()

    with lease_for(runtime, obs, lock=runtime.store.mutex) as lease:
        result = consume_with_provider_verifier(
            runtime, obs, frame, consent_lease=lease,
            current_source="Describe this screen.", goal="red panel",
        )
        assert result["student_projector_used"] is False
        assert result["student_projector_status"] == "PROJECTOR_HASH_MISMATCH"
        assert result["packet"]["student_projector_used"] is False
        assert result["status"] == "WIRED_SYNTHETIC"
        assert len(result["packet"]["segments"]) == 18
        assert result["caller_buffer_overwritten"] is True


def test_symlinked_local_student_projector_is_rejected(monkeypatch, tmp_path):
    runtime = make_runtime(monkeypatch, with_store=True)
    path, _sha = install_student_projector(runtime, tmp_path)
    outside = tmp_path / "outside-projector.npz"
    path.replace(outside)
    path.symlink_to(outside)
    obs = observation()
    frame = image_buffer()

    with lease_for(runtime, obs, lock=runtime.store.mutex) as lease:
        result = consume_with_provider_verifier(
            runtime, obs, frame, consent_lease=lease,
            current_source="Describe this screen.", goal="red panel",
        )
        assert result["student_projector_used"] is False
        assert result["student_projector_status"] == "PROJECTOR_FILE_UNAVAILABLE"
        assert result["packet"]["student_projector_used"] is False
        assert result["status"] == "WIRED_SYNTHETIC"
        assert result["caller_buffer_overwritten"] is True


def test_untrusted_always_true_callback_cannot_cross_provider_capability_boundary(monkeypatch):
    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = image_buffer()
    with pytest.raises(PermissionError, match="issued only"):
        ProviderFrameVerifier(None, obs, lambda *_args: True)

    with lease_for(runtime, obs) as lease:
        with pytest.raises(PermissionError, match="provider-owned"):
            consume_projected_frame(
                runtime, obs, frame, consent_lease=lease,
                frame_verifier=lambda *_args: True,
                current_source="Describe this.",
            )
        assert not any(frame)


def test_provider_verifier_is_bound_to_session_and_one_shot(monkeypatch):
    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = image_buffer()
    frame_sha = hashlib.sha256(frame).hexdigest()
    with lease_for(runtime, obs) as lease:
        verifier = provider_verifier(lease, obs, frame)
        assert verifier.verify(runtime, lease, obs, frame_sha, len(frame)) is True
        assert verifier.verify(runtime, lease, obs, frame_sha, len(frame)) is False

        calls = []
        verifier = _issue_provider_frame_verifier(
            lease, obs, lambda *_args: calls.append(True) or True,
        )
        wrong = dict(obs, capture_session_id="other-session")
        assert verifier.verify(runtime, lease, wrong, frame_sha, len(frame)) is False
        assert calls == []


def test_fifo_tile_projector_is_rejected_without_blocking(monkeypatch, tmp_path):
    if not hasattr(os, "mkfifo"):
        pytest.skip("POSIX FIFO support is unavailable")
    runtime = make_runtime(monkeypatch, with_store=True)
    path, _sha = install_student_projector(runtime, tmp_path)
    path.unlink()
    os.mkfifo(path)

    def delayed_writer():
        time.sleep(1.5)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
            os.close(fd)
        except OSError:
            pass

    threading.Thread(target=delayed_writer, daemon=True).start()
    started = time.monotonic()
    result = _load_local_tile_projector(runtime, {"hash_dim": 256}, "red panel")
    elapsed = time.monotonic() - started
    assert result["status"] == "INVALID_PROJECTOR_FILE"
    assert elapsed < 0.8

