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
    ProviderFrameVerifier, _feature_summary, _issue_provider_frame_verifier,
    _load_local_tile_projector, _summary, consume_projected_frame,
    consume_projected_frame_from_provider, consume_projected_frame_scope,
    temporal_visual_revocation_callback,
)


class _Attention:
    def modulate(self, event_id, *, sal=None, caut=None):
        return {
            "event_id": event_id,
            "salience": dict(sal or {}),
            "caution": dict(caut or {}),
            "truth_authority": 0,
        }

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
        self._deleted_sources = set()

    def state(self, key, default=None):
        return self._state.get(key, default), 0

    def one(self, _sql, params=()):
        source_id = params[0]
        if source_id in self._deleted_sources:
            return {"id": source_id, "deleted": 1, "kind": "IMAGE", "hash": "0" * 64}
        for state in self._state.values():
            images = state.get("images") if type(state) is dict else None
            record = images.get(source_id) if type(images) is dict else None
            ref = record.get("ref") if type(record) is dict else None
            if type(ref) is dict:
                return {
                    "id": source_id, "deleted": 0, "kind": "IMAGE",
                    "hash": ref.get("sha256"),
                }
        return None

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


def image_buffer_variant():
    image = Image.new("RGB", (64, 64), (8, 8, 8))
    draw = ImageDraw.Draw(image)
    draw.rectangle((8, 14, 29, 52), fill=(230, 20, 18))
    draw.rectangle((40, 8, 51, 24), fill=(12, 180, 220))
    output = BytesIO()
    image.save(output, format="PNG")
    image.close()
    return bytearray(output.getvalue())


def provider_verify_fn(obs, frame, *, result=True, failure=None):
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

    return verify


def provider_verifier(lease, obs, frame, *, result=True, failure=None):
    return _issue_provider_frame_verifier(
        lease, obs, provider_verify_fn(obs, frame, result=result, failure=failure),
    )


def consume_with_provider_verifier(
    runtime, obs, frame, *, consent_lease, frame_verifier=None,
    verify_fn=None, **kwargs,
):
    if frame_verifier is None:
        if verify_fn is None:
            verify_fn = provider_verify_fn(obs, frame)
        return consume_projected_frame_from_provider(
            runtime, obs, frame, consent_lease=consent_lease,
            verify_fn=verify_fn, **kwargs,
        )
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
    training_source_id = "ui-training-source-0001"
    training_source_sha = "a" * 64
    runtime.store._state[vision.KEY] = {
        "tile_projector": {
            "path": "data/vision/tiles-test.npz",
            "sha256": sha,
            "n": len(features),
            "encoder": "hashed_bow",
            "authority": "LAB_SHADOW_ONLY",
            "training_sources": [
                {"source_id": training_source_id, "sha256": training_source_sha}
            ],
        },
        "images": {
            training_source_id: {
                "ref": {
                    "source_id": training_source_id,
                    "sha256": training_source_sha,
                    "modality": "image",
                }
            }
        },
    }
    return path, sha


def lease_for(runtime, obs, callbacks=None, lock=None, revoke_callback=None):
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
        check, guard, subscribe, revoke_callback=revoke_callback,
    )


def test_ui_summary_is_content_free_metadata_only():
    summary = _summary(observation())
    assert summary == (
        "ui event=SCREEN_FRAME_AVAILABLE method=MEDIA_PROJECTION "
        "scope=FULL_DISPLAY api=34 clock=ELAPSED_REALTIME interval_ms=33"
    )
    assert len(summary) <= 512
    assert "red panel" not in summary
    assert "blue icon" not in summary


def test_raw_eye_feature_summary_is_bounded_numeric_and_content_free():
    summary = _feature_summary("r00", [0, 0, 16, 16], [0.125] * 37, 0.25)
    assert summary.startswith(
        "raw_eye_v1 authority=RAW_FEATURE_MEASUREMENT region=r00 "
    )
    assert "box=0,0,16,16 salience=0.250" in summary
    assert "rgb=0.125,0.125,0.125" in summary
    assert "hue=" in summary and "orientation=" in summary and "lum4x4=" in summary
    assert len(summary) <= 512
    assert "red panel" not in summary and "blue icon" not in summary

    global_summary = _feature_summary("g", [0, 0, 64, 64], [0.0] * 37, None)
    assert "region=g" in global_summary and "salience=na" in global_summary
    assert len(global_summary) <= 512


def test_raw_eye_feature_summary_rejects_malformed_or_nonfinite_inputs():
    good = [0.1] * 37
    invalid = (
        ([], [0, 0, 16, 16], good, 0.2),
        ("r99", [0, 0, 16, 16], good, 0.2),
        ("r00", [0, 0, 0, 16], good, 0.2),
        ("r00", [0, 0, 16, 16], [0.1] * 36, 0.2),
        ("r00", [0, 0, 16, 16], [float("nan")] + good[1:], 0.2),
        ("r00", [0, 0, 16, 16], [2.1] + good[1:], 0.2),
        ("r00", [0, 0, 16, 16], [True] + good[1:], 0.2),
        ("r00", [0, 0, 16, 16], good, 1.1),
        ("r00", [0, 0, 16, 16], good, True),
    )
    for args in invalid:
        with pytest.raises(ValueError):
            _feature_summary(*args)


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


def test_bounded_frame_config_cannot_expand_capture_limits():
    from v13.vision_ui_frame_ingress import (
        MAX_FRAME_BYTES, MAX_FRAME_PIXELS, _bounded_vision_config,
    )

    cfg = _bounded_vision_config({
        "hash_dim": 512,
        "max_bytes": 64 * 1024 * 1024,
        "max_pixels": 100_000_000,
    })
    assert cfg["hash_dim"] == 512
    assert cfg["max_bytes"] == MAX_FRAME_BYTES == 8 * 1024 * 1024
    assert cfg["max_pixels"] == MAX_FRAME_PIXELS == 4_000_000
    with pytest.raises(ValueError, match="hash_dim"):
        _bounded_vision_config({"hash_dim": True})


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


def test_scoped_frame_consumer_revokes_source_after_success_and_failure(monkeypatch):
    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = image_buffer()
    revoked = []
    monkeypatch.setattr(
        "v13.vision_ui_frame_ingress.revoke_ui_observation",
        lambda _runtime, source_id: revoked.append(source_id),
    )

    with lease_for(runtime, obs) as lease:
        verifier = provider_verifier(lease, obs, frame)
        with consume_projected_frame_scope(
            runtime, obs, frame, consent_lease=lease,
            frame_verifier=verifier, current_source="Describe this screen.",
            goal="red panel", token_budget=512,
        ) as result:
            assert result["status"] == "WIRED_SYNTHETIC"
            assert obs["source_id"] in runtime._a5_ui_context_cache
            assert lease.active_for(runtime, runtime.turn_event["brain_generation_id"])
        assert revoked == [obs["source_id"]]

    runtime2 = make_runtime(monkeypatch)
    obs2 = observation()
    obs2["source_id"] = "ui-frame-source-0002"
    frame2 = image_buffer()
    revoked.clear()
    with lease_for(runtime2, obs2) as lease2:
        verifier2 = provider_verifier(lease2, obs2, frame2)
        with pytest.raises(RuntimeError, match="downstream failure"):
            with consume_projected_frame_scope(
                runtime2, obs2, frame2, consent_lease=lease2,
                frame_verifier=verifier2, current_source="Describe this screen.",
                goal="red panel", token_budget=512,
            ):
                raise RuntimeError("downstream failure")
        assert revoked == [obs2["source_id"]]


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


def test_provider_verifier_factory_rejection_zeroizes_before_consumer_starts(monkeypatch):
    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = image_buffer()
    with lease_for(runtime, obs) as lease:
        with pytest.raises(PermissionError, match="exact active UI lease"):
            consume_projected_frame_from_provider(
                runtime, obs, frame, consent_lease=object(),
                verify_fn=lambda *_args: True,
                current_source="Describe this.",
            )
    assert not any(frame)
    assert obs["source_id"] not in getattr(runtime, "_a5_ui_context_cache", {})


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



def test_temporal_visual_on_off_surface_decays_and_expires():
    from v13.vision_temporal_evidence import TILE_IDS, TemporalVisualEvidence
    state = TemporalVisualEvidence(tau_ms=30, window_ms=50)
    base = {tile: [0.2] * 16 for tile in TILE_IDS}
    bright = {tile: [0.8] * 16 for tile in TILE_IDS}
    assert state.update(start_ms=1000, end_ms=1033, tile_luminance=base)["status"] == "WARMUP"
    brightening = state.update(start_ms=1033, end_ms=1066, tile_luminance=bright)
    assert brightening["on_activity"] > 0.59 and brightening["off_activity"] == 0.0
    assert brightening["temporal_activity_score"] > 0.59
    assert brightening["polarity_delta_by_tile"]["r00"]["on"] > 0.59
    assert brightening["polarity_delta_by_tile"]["r00"]["off"] == 0.0
    quiet = state.update(start_ms=1066, end_ms=1099, tile_luminance=bright)
    assert quiet["change_score"] == 0.0
    assert 0.0 < quiet["temporal_activity_score"] < brightening["temporal_activity_score"]
    expired = state.update(start_ms=1099, end_ms=1132, tile_luminance=bright)
    assert expired["surface_expired"] is True and expired["temporal_activity_score"] == 0.0
    darkening = state.update(start_ms=1132, end_ms=1165, tile_luminance=base)
    assert darkening["off_activity"] > 0.59 and darkening["on_activity"] == 0.0
    assert darkening["polarity_delta_by_tile"]["r00"]["off"] > 0.59


def test_temporal_visual_surface_resets_on_stream_gap():
    from v13.vision_temporal_evidence import TILE_IDS, TemporalVisualEvidence
    state = TemporalVisualEvidence()
    base = {tile: [0.1] * 16 for tile in TILE_IDS}
    bright = {tile: [0.9] * 16 for tile in TILE_IDS}
    state.update(start_ms=1000, end_ms=1033, tile_luminance=base)
    state.update(start_ms=1033, end_ms=1066, tile_luminance=bright)
    reset = state.update(start_ms=3000, end_ms=3033, tile_luminance=bright)
    assert reset["status"] == "WARMUP" and reset["state_reset"] is True
    assert reset["reset_reason"] == "STREAM_GAP" and reset["temporal_activity_score"] == 0.0


def test_provider_revocation_erases_temporal_history(monkeypatch):
    runtime = make_runtime(monkeypatch, with_store=True)
    obs = observation()
    callbacks = {}
    first, second = image_buffer(), image_buffer_variant()
    cleanup = temporal_visual_revocation_callback(runtime, capture_session_id=obs["capture_session_id"])
    with lease_for(runtime, obs, callbacks=callbacks, revoke_callback=cleanup) as lease:
        consume_with_provider_verifier(runtime, obs, first, consent_lease=lease,
                                       current_source="Observe the screen change.")
        next_obs = dict(obs, start_ms=1033, end_ms=1066)
        consume_with_provider_verifier(runtime, next_obs, second, consent_lease=lease,
                                       current_source="Observe the screen change.")
        assert len(runtime._a5_temporal_visual_registry) == 1
    on_revoked = callbacks[obs["source_id"]][1]
    result = on_revoked()
    assert result["cache_cleared"] is True
    assert len(runtime._a5_temporal_visual_registry) == 0
    assert obs["source_id"] not in runtime._a5_ui_context_cache
    assert not any(first) and not any(second)


@pytest.mark.parametrize(
    "failure,expected_status",
    [
        ("forgotten", "PROJECTOR_SOURCE_LINEAGE_STALE"),
        ("hash_mismatch", "PROJECTOR_SOURCE_LINEAGE_STALE"),
        ("source_tombstoned", "PROJECTOR_SOURCE_LINEAGE_STALE"),
        ("missing_lineage", "PROJECTOR_LINEAGE_UNKNOWN"),
        ("malformed_lineage", "PROJECTOR_LINEAGE_INVALID"),
    ],
)
def test_ui_student_projector_requires_live_exact_training_sources(
    monkeypatch, tmp_path, failure, expected_status,
):
    runtime = make_runtime(monkeypatch, with_store=True)
    install_student_projector(runtime, tmp_path)
    from v13 import vision

    state = runtime.store._state[vision.KEY]
    source_id = "ui-training-source-0001"
    if failure == "forgotten":
        state["images"].pop(source_id)
    elif failure == "hash_mismatch":
        state["images"][source_id]["ref"]["sha256"] = "b" * 64
    elif failure == "source_tombstoned":
        runtime.store._deleted_sources.add(source_id)
    elif failure == "missing_lineage":
        state["tile_projector"].pop("training_sources")
    elif failure == "malformed_lineage":
        state["tile_projector"]["training_sources"] = [
            {"source_id": source_id, "sha256": "not-a-sha256"}
        ]

    obs = observation()
    frame = image_buffer()
    with lease_for(runtime, obs, lock=runtime.store.mutex) as lease:
        result = consume_with_provider_verifier(
            runtime, obs, frame, consent_lease=lease,
            current_source="Describe this screen.", goal="red panel",
        )

    assert result["student_projector_used"] is False
    assert result["student_projector_status"] == expected_status
    assert result["packet"]["student_projector_used"] is False
    assert result["status"] == "WIRED_SYNTHETIC"
    assert result["caller_buffer_overwritten"] is True


def test_temporal_visual_evidence_is_source_session_bound_and_drives_a4(monkeypatch):
    from v13.vision_temporal_evidence import TILE_IDS

    runtime = make_runtime(monkeypatch)
    obs = observation()
    first = image_buffer()
    second = image_buffer_variant()
    first_hash = hashlib.sha256(first).hexdigest()
    second_hash = hashlib.sha256(second).hexdigest()

    with lease_for(runtime, obs) as lease:
        first_result = consume_with_provider_verifier(
            runtime, obs, first, consent_lease=lease,
            current_source="Observe the screen change.", token_budget=512,
        )
        next_obs = dict(obs, start_ms=1033, end_ms=1066)
        second_result = consume_with_provider_verifier(
            runtime, next_obs, second, consent_lease=lease,
            current_source="Observe the screen change.", token_budget=512,
        )
        packets = A5UIRuntimeAdapter(runtime).context(runtime.turn_event["event_id"], lease)

    assert first_result["temporal_visual_evidence"]["status"] == "WARMUP"
    evidence = second_result["temporal_visual_evidence"]
    assert evidence["status"] == "MEASURED"
    assert evidence["source_ref"]["sha256"] == second_hash
    assert evidence["capture_session_id"] == obs["capture_session_id"]
    assert evidence["truth_authority"] == 0
    assert evidence["learning_authority"] is False
    assert evidence["action_authority"] is False
    assert evidence["changed_tile_ids"]
    assert second_result["temporal_visual_modulation"]["truth_authority"] == 0
    assert second_result["temporal_visual_modulation"]["salience"]["novelty"] == evidence["attention_novelty"]
    assert second_result["a4"]["temporal_visual_modulation"] == second_result["temporal_visual_modulation"]
    assert any("temporal_change" in segment for segment in second_result["packet"]["segments"])
    assert packets == (second_result["packet"],)
    assert first_result["packet"]["frame_sha256"] == first_hash
    assert not any(first) and not any(second)


def test_temporal_visual_evidence_registry_resets_on_receipt_and_session_end():
    from v13.vision_temporal_evidence import TILE_IDS, TemporalVisualEvidenceRegistry

    registry = TemporalVisualEvidenceRegistry()
    frame = {tile: [0.1] * 16 for tile in TILE_IDS}
    common = dict(
        capture_session_id="session-a", generation_id="gen-a",
        consent_receipt_ref="receipt-a", start_ms=1000, end_ms=1033,
        tile_luminance=frame,
    )
    assert registry.update(**common)["status"] == "WARMUP"
    changed = {tile: [0.8] * 16 for tile in TILE_IDS}
    assert registry.update(**dict(common, start_ms=1033, end_ms=1066, tile_luminance=changed))["status"] == "MEASURED"
    # A new consent receipt cannot inherit the previous frame.
    assert registry.update(**dict(common, consent_receipt_ref="receipt-b", start_ms=1066, end_ms=1099))["status"] == "WARMUP"
    assert registry.reset(capture_session_id="session-a") == 1
    assert len(registry) == 0


def test_temporal_visual_evidence_rejects_out_of_order_and_malformed_tiles():
    from v13.vision_temporal_evidence import (
        TILE_IDS, TemporalVisualEvidence, TemporalVisualEvidenceError,
    )

    state = TemporalVisualEvidence()
    frame = {tile: [0.1] * 16 for tile in TILE_IDS}
    state.update(start_ms=100, end_ms=133, tile_luminance=frame)
    with pytest.raises(TemporalVisualEvidenceError, match="monotonically"):
        state.update(start_ms=90, end_ms=120, tile_luminance=frame)
    malformed = dict(frame)
    malformed["r00"] = [float("nan")] + [0.1] * 15
    with pytest.raises(TemporalVisualEvidenceError, match="finite"):
        state.update(start_ms=133, end_ms=166, tile_luminance=malformed)
    # The rejected frame did not replace the previous valid baseline.
    result = state.update(start_ms=133, end_ms=166, tile_luminance=frame)
    assert result["status"] == "MEASURED"
    assert result["change_score"] == 0.0


def test_end_of_stream_erases_temporal_visual_history(monkeypatch):
    runtime = make_runtime(monkeypatch)
    obs = observation()
    frame = image_buffer()
    with lease_for(runtime, obs) as lease:
        with consume_projected_frame_scope(
            runtime, obs, frame, consent_lease=lease,
            frame_verifier=provider_verifier(lease, obs, frame),
            current_source="Observe one screen frame.", end_of_stream=True,
        ) as result:
            assert result["temporal_visual_evidence"]["status"] == "WARMUP"
            assert len(runtime._a5_temporal_visual_registry) == 1
        assert len(runtime._a5_temporal_visual_registry) == 0
    assert not any(frame)
