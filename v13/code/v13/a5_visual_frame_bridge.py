"""Lease-bound A5 visual-frame adapter.

MediaProjection pixels are decoded in memory only. The adapter exposes a
compact RAW-EYE feature vector and optional student hypotheses to the active
Runtime turn, but never writes screenshots, pixels, features or transcripts to
the Store. Every read is bound to the current UI observation lease; revocation
and lease exit drop the adapter-held feature buffer.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import math
from pathlib import Path
import threading

from . import attention as attctl
from . import vision
from .a5_ui_admission_bridge import (
    UIObservationLease,
    ui_observation_lease,
    validate_ui_observation,
)
from .contracts import packet, validate
from .percept_admission import Percept, admit


_MAX_STUDENT_CANDIDATES = 3
_MAX_FEATURE_VALUES = 16384


def _bounded_unit(value):
    """Clamp a finite feature proxy; suppress measured float noise from uniform frames."""
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("RAW-EYE structure component is non-finite")
    return 0.0 if value < 1e-4 else min(1.0, max(0.0, value))


def raw_eye_structure(feature_values):
    """Return a non-semantic [0,1] structure proxy from the existing 4x4 RAW-EYE descriptor.

    Components are handcrafted BOOT signals, not object recognition, prediction,
    confidence or learned salience. The max keeps a single strong structural cue
    visible without pretending the component scales are calibrated probabilities.
    """
    np = vision._np()
    values = np.asarray(feature_values, dtype=np.float32).reshape(-1)
    grid = vision.DEFAULTS.get("grid")
    if type(grid) is not int or grid < 1:
        raise ValueError("RAW-EYE grid configuration is invalid")
    expected = 37 + grid * grid * 5
    if values.size != expected or not np.isfinite(values).all():
        raise ValueError("RAW-EYE descriptor shape or values are invalid")
    global_values = values[:37]
    cells = values[37:].reshape(grid * grid, 5)
    components = {
        "global_contrast": _bounded_unit(float(np.mean(global_values[3:6])) * 2.0),
        "global_edge_energy": _bounded_unit(float(global_values[16]) * 4.0),
        "cell_edge_energy": _bounded_unit(float(np.mean(cells[:, 3])) * 4.0),
        "spatial_color": _bounded_unit(float(np.mean(np.std(cells[:, :3], axis=0))) * 2.0),
        "luminance_range": _bounded_unit(float(np.ptp(global_values[21:37]))),
    }
    return max(components.values()), components


def _student_hypotheses(runtime, feature_vector):
    """Use only an already-installed hashed-BOW student; never load a teacher."""
    state = vision.load(runtime.store)
    meta = state.get("projector") if isinstance(state, dict) else None
    if not isinstance(meta, dict):
        return "NO_PROJECTOR", ()
    if meta.get("encoder") != "hashed_bow":
        return "ENCODER_UNAVAILABLE", ()
    captions = meta.get("captions")
    if not isinstance(captions, dict) or not captions:
        return "NO_CAPTIONS", ()
    path_value = meta.get("path")
    digest_value = meta.get("sha256")
    if (
        type(path_value) is not str
        or not path_value
        or type(digest_value) is not str
        or len(digest_value) != 64
        or any(char not in "0123456789abcdef" for char in digest_value)
    ):
        raise ValueError("invalid persisted visual-projector manifest")
    root = (Path(runtime.home) / "data" / "vision").resolve()
    path = (Path(runtime.home) / path_value).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("visual projector path escapes the vision directory") from exc
    if not path.is_file():
        return "PROJECTOR_MISSING", ()

    np = vision._np()
    projector = vision.Projector.load(path, digest_value)
    projected = projector(np.asarray(feature_vector, dtype=np.float32).reshape(1, -1))[0]
    items = [
        (str(region), str(caption)[:200])
        for region, caption in captions.items()
        if type(region) is str and type(caption) is str and caption.strip()
    ][:512]
    if not items:
        return "NO_CAPTIONS", ()
    text_vectors = np.stack([
        vision.hashed_embed(caption, int(projector.W.shape[1]))
        for _region, caption in items
    ])
    scores = text_vectors @ projected
    order = np.argsort(-scores)[:_MAX_STUDENT_CANDIDATES]
    return "STUDENT_ESTIMATE", tuple(
        {
            "region_id": items[int(index)][0],
            "caption": items[int(index)][1],
            "cosine": round(float(scores[int(index)]), 6),
            "authority": "STUDENT_ESTIMATE",
            "reference_authority": "REFERENCE_NOT_FACT",
        }
        for index in order
    )


class A5VisualFrameAdapter:
    """Per-turn MediaProjection consumer with a revocable in-memory feature cache."""

    def __init__(self, runtime):
        self.runtime = runtime
        self._lock = threading.RLock()
        self._owned_sources = set()
        self._packets = {}
        self._features = {}

    @contextmanager
    def lease(self, observation, consent_check, consent_guard, revocation_subscribe):
        observation = validate_ui_observation(observation)
        if observation["capture_method"] != "MEDIA_PROJECTION":
            raise PermissionError("visual frames require an explicit MediaProjection grant")
        source_id = observation["source_id"]
        with self._lock:
            if source_id in self._owned_sources:
                raise ValueError("duplicate visual-frame source")
            self._owned_sources.add(source_id)
        event = getattr(self.runtime, "turn_event", None)
        generation_id = event.get("brain_generation_id") if isinstance(event, dict) else None
        try:
            with ui_observation_lease(
                self.runtime,
                observation,
                generation_id,
                consent_check,
                consent_guard,
                revocation_subscribe,
                revoke_callback=self.revoke,
            ) as grant:
                yield grant
        finally:
            # Raw frames and derived features are turn-local, not retained until
            # a later provider callback. revoke() is idempotent.
            self.revoke(source_id)

    def ingest(self, frame_bytes, observation, grant, *, goal="", token_budget=512, priority=0):
        return consume_visual_frame(
            self.runtime,
            frame_bytes,
            observation,
            consent_lease=grant,
            adapter=self,
            goal=goal,
            token_budget=token_budget,
            priority=priority,
        )

    def _allowed_sources(self, event_id, grants):
        if type(event_id) is not str or not event_id:
            raise ValueError("event id required")
        if type(grants) is UIObservationLease:
            grants = (grants,)
        elif type(grants) not in (tuple, list):
            raise PermissionError("active visual observation lease is required")
        if not grants:
            raise PermissionError("at least one active visual observation lease is required")
        event = getattr(self.runtime, "turn_event", None)
        generation_id = event.get("brain_generation_id") if isinstance(event, dict) else None
        subscriptions = getattr(self.runtime, "_a5_ui_unsubscribe", None)
        if type(subscriptions) is not dict:
            raise PermissionError("visual observation subscriptions are unavailable")
        allowed = set()
        with self._lock:
            owned_sources = set(self._owned_sources)
        for grant in grants:
            if (
                type(grant) is not UIObservationLease
                or not grant.active_for(self.runtime, generation_id)
                or grant.source_id not in owned_sources
                or grant.source_id not in subscriptions
            ):
                raise PermissionError("visual frame lease is stale, revoked or not bound to this turn")
            allowed.add(grant.source_id)
        return allowed, generation_id

    def context(self, event_id, grants):
        allowed, generation_id = self._allowed_sources(event_id, grants)
        with self._lock:
            return tuple(
                packet_value
                for source_id, packet_value in self._packets.items()
                if source_id in allowed
                and packet_value.get("event_id") == event_id
                and packet_value.get("brain_generation_id") == generation_id
                and packet_value.get("modality") == "visual"
                and packet_value.get("finality") == "FINAL"
            )

    def features(self, event_id, grants):
        allowed, generation_id = self._allowed_sources(event_id, grants)
        output = {}
        with self._lock:
            for source_id in allowed:
                item = self._features.get(source_id)
                if (
                    item is not None
                    and item["event_id"] == event_id
                    and item["generation_id"] == generation_id
                ):
                    output[source_id] = tuple(float(value) for value in item["values"])
        return output

    def revoke(self, source_id):
        if type(source_id) is not str or not source_id:
            raise ValueError("visual source id required")
        with self._lock:
            self._owned_sources.discard(source_id)
            packet_value = self._packets.pop(source_id, None)
            feature_item = self._features.pop(source_id, None)
            if feature_item is not None:
                feature_item["values"].fill(0.0)
        subscriptions = getattr(self.runtime, "_a5_ui_unsubscribe", None)
        unsubscribe = subscriptions.pop(source_id, None) if type(subscriptions) is dict else None
        if callable(unsubscribe):
            unsubscribe()
        return {
            "cache_cleared": packet_value is not None or feature_item is not None,
            "raw_capture_persisted": False,
            "feature_buffer_cleared": feature_item is not None,
        }

    def close(self):
        active = getattr(self.runtime, "turn_event", None)
        cancel_event = getattr(self.runtime, "cancel_event", None)
        if (
            isinstance(active, dict)
            and type(active.get("brain_generation_id")) is str
            and getattr(self.runtime, "current", None) == "turn"
        ):
            setter = getattr(cancel_event, "set", None)
            if callable(setter):
                setter()
            raise RuntimeError("A5 visual close requires Runtime turn exit")
        with self._lock:
            sources = tuple(self._owned_sources)
        return tuple(self.revoke(source_id) for source_id in sources)


def consume_visual_frame(
    runtime,
    frame_bytes,
    observation,
    *,
    consent_lease: UIObservationLease,
    adapter: A5VisualFrameAdapter,
    goal="",
    token_budget=512,
    priority=0,
):
    """Decode one authorized screen frame in memory and emit a shadow PerceptPacket."""
    observation = validate_ui_observation(observation)
    event = getattr(runtime, "turn_event", None)
    if not isinstance(event, dict):
        raise ValueError("visual frames must attach to an active Runtime turn")
    event_id = event.get("event_id")
    generation_id = event.get("brain_generation_id")
    if type(event_id) is not str or not event_id or type(generation_id) is not str or not generation_id:
        raise ValueError("active Runtime turn identity is incomplete")
    if (
        observation["capture_method"] != "MEDIA_PROJECTION"
        or observation["event_kind"] != "SCREEN_FRAME_AVAILABLE"
    ):
        raise PermissionError("only MediaProjection screen frames enter the visual adapter")
    if not isinstance(adapter, A5VisualFrameAdapter) or adapter.runtime is not runtime:
        raise PermissionError("visual adapter/runtime mismatch")
    if not isinstance(consent_lease, UIObservationLease) or not consent_lease.matches(
        runtime, observation, generation_id
    ):
        raise PermissionError("a live source/generation/receipt-bound MediaProjection lease is required")
    with adapter._lock:
        if observation["source_id"] not in adapter._owned_sources:
            raise PermissionError("visual source is not owned by this adapter")
    if type(goal) is not str or len(goal) > 512:
        raise ValueError("visual attention goal must be bounded text")
    if type(priority) is not int or not -100 <= priority <= 100:
        raise ValueError("invalid visual admission priority")
    if type(token_budget) is not int or token_budget < 0:
        raise ValueError("invalid visual token budget")
    if observation["finality"] == "PROVISIONAL":
        return {
            "status": "PROVISIONAL_IGNORED",
            "packet": None,
            "feature_count": 0,
            "raw_capture_persisted": False,
            "action_authority": False,
            "learning_authority": False,
        }
    if observation["finality"] != "FINAL":
        raise ValueError("visual frame finality must be FINAL or PROVISIONAL")
    if type(frame_bytes) not in (bytes, bytearray, memoryview) or not frame_bytes:
        raise ValueError("visual frame must be non-empty bytes")
    if len(frame_bytes) > vision.DEFAULTS["max_bytes"]:
        raise ValueError("visual frame exceeds the bounded byte budget")
    if not consent_lease.active_for(runtime, generation_id):
        raise PermissionError("MediaProjection lease expired before frame decoding")

    frame_data = bytes(frame_bytes)
    raw_frame_sha256 = hashlib.sha256(frame_data).hexdigest()
    image = vision.decode(frame_data)
    width, height = image.size
    feature_values = vision.features(image)
    image.close()
    del image
    del frame_data
    np = vision._np()
    feature_values = np.asarray(feature_values, dtype=np.float32).reshape(-1)
    if (
        not feature_values.size
        or feature_values.size > _MAX_FEATURE_VALUES
        or not np.isfinite(feature_values).all()
    ):
        raise ValueError("RAW-EYE feature vector is empty, oversized or non-finite")
    feature_values = feature_values.copy()
    raw_eye_score, raw_eye_components = raw_eye_structure(feature_values)
    feature_bytes = np.asarray(feature_values, dtype="<f4").tobytes(order="C")
    feature_sha256 = hashlib.sha256(feature_bytes).hexdigest()
    feature_shape = [int(feature_values.size)]
    student_status, student_candidates = _student_hypotheses(runtime, feature_values)

    summary = (
        "visual frame observed; RAW-EYE descriptor available; "
        + (
            "student visual hypotheses available"
            if student_candidates
            else "student projector unavailable"
        )
    )
    source_ref = {
        "source_id": observation["source_id"],
        "sha256": raw_frame_sha256,
        "char_start": 0,
        "char_end": 0,
        "modality": "visual",
    }
    segments = [{
        "text": summary,
        "source_ref": source_ref,
        "start_ms": observation["start_ms"],
        "end_ms": observation["end_ms"],
        "clock": observation["clock"],
        "finality": "FINAL",
        "capture_method": observation["capture_method"],
        "capture_scope": observation["capture_scope"],
        "capture_session_id": observation["capture_session_id"],
        "consent_receipt_ref": observation["consent_receipt_ref"],
        "raw_frame_sha256": raw_frame_sha256,
        "feature_sha256": feature_sha256,
        "feature_shape": feature_shape,
        "modality": "visual",
        "producer_component": "A5_VISUAL",
        "raw_eye_structure": raw_eye_score,
        "raw_eye_components": raw_eye_components,
        "student_authority": student_status,
        "action_authority": False,
        "learning_authority": False,
        "raw_capture_persisted": False,
    }]
    for candidate in student_candidates:
        segments.append({
            "text": (
                "student visual hypothesis: " + candidate["caption"]
                + "; authority=STUDENT_ESTIMATE; reference=REFERENCE_NOT_FACT"
            ),
            "source_ref": source_ref,
            "start_ms": observation["start_ms"],
            "end_ms": observation["end_ms"],
            "clock": observation["clock"],
            "finality": "FINAL",
            "authority": "STUDENT_ESTIMATE",
            "reference_authority": "REFERENCE_NOT_FACT",
            "action_authority": False,
            "learning_authority": False,
            "raw_capture_persisted": False,
        })

    percept_packet = packet(
        "PerceptPacket",
        "A5_VISUAL",
        event_id,
        generation_id,
        [source_ref],
        source_ref=source_ref,
        segments=segments,
        modality="visual",
        capture_session_id=observation["capture_session_id"],
        consent_receipt_ref=observation["consent_receipt_ref"],
        capture_method=observation["capture_method"],
        capture_scope=observation["capture_scope"],
        clock=observation["clock"],
        finality="FINAL",
        raw_frame_sha256=raw_frame_sha256,
        feature_sha256=feature_sha256,
        feature_shape=feature_shape,
        raw_eye_structure=raw_eye_score,
        raw_eye_components=raw_eye_components,
        student_authority=student_status,
        student_candidates=list(student_candidates),
        raw_capture_persisted=False,
        action_authority=False,
        learning_authority=False,
    )
    validate("PerceptPacket", percept_packet)

    if not consent_lease.active_for(runtime, generation_id):
        feature_values.fill(0.0)
        raise PermissionError("MediaProjection lease was revoked during frame processing")
    stale_source = None
    with adapter._lock:
        if observation["source_id"] not in adapter._owned_sources:
            feature_values.fill(0.0)
            raise PermissionError("visual source was revoked during frame processing")
        adapter._packets[observation["source_id"]] = percept_packet
        adapter._features[observation["source_id"]] = {
            "event_id": event_id,
            "generation_id": generation_id,
            "values": feature_values,
            "feature_sha256": feature_sha256,
        }
        if len(adapter._packets) > 16:
            stale_source = next(iter(adapter._packets))
    if stale_source is not None:
        adapter.revoke(stale_source)

    attention = attctl.controller(runtime)
    a4 = attention.perceive(event_id, segments, goal=goal, file_requests=False)
    candidate = Percept(
        observation["source_id"],
        "visual",
        observation["start_ms"],
        observation["end_ms"],
        summary,
        True,
        True,
        priority,
    )
    admission = admit((candidate,), token_budget)
    if not consent_lease.active_for(runtime, generation_id):
        adapter.revoke(observation["source_id"])
        raise PermissionError("MediaProjection lease was revoked before visual admission completed")
    return {
        "status": "WIRED_SYNTHETIC",
        "packet": percept_packet,
        "source_ref": source_ref,
        "a4": a4,
        "admission": admission,
        "feature_count": int(feature_values.size),
        "feature_sha256": feature_sha256,
        "raw_eye_structure": raw_eye_score,
        "raw_eye_components": raw_eye_components,
        "student_authority": student_status,
        "raw_capture_persisted": False,
        "action_authority": False,
        "learning_authority": False,
    }
