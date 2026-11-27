"""One-shot Runtime consumer for OS-authorized A5 MediaProjection frames.

The provider is an in-process transport supplied by the Android companion. This
module does not authenticate Android itself: its consent_check/guard/revocation
callbacks must be backed by the companion's current OS-issued receipt. The
provider may return at most one already-captured frame for an explicitly
approved observation request; polling must be non-blocking.
"""
from __future__ import annotations

import math
import time


_PROVIDER_METHODS = (
    "poll_visual_frame",
    "consent_check",
    "consent_guard",
    "revocation_subscribe",
)


def set_provider(runtime, provider):
    """Attach/detach the trusted companion adapter outside an active turn.

    A successful attach is only an interface registration, not Android
    permission proof. The live UIObservationLease still checks the companion's
    current receipt and linearizable revocation guard for every consumed frame.
    """
    lock = getattr(runtime, "lock", None)
    if lock is None or not callable(getattr(lock, "__enter__", None)):
        raise RuntimeError("Runtime lock is required for A5 provider registration")
    if provider is not None:
        missing = [name for name in _PROVIDER_METHODS if not callable(getattr(provider, name, None))]
        if missing:
            raise TypeError("A5 provider contract missing: " + ", ".join(missing))
    with lock:
        if getattr(runtime, "current", None) == "turn":
            raise RuntimeError("A5 provider cannot change during an active Runtime turn")
        if getattr(runtime, "closed", False):
            raise RuntimeError("Runtime is closed")
        runtime._a5_visual_provider = provider
    return "DETACHED" if provider is None else "ATTACHED_UNVERIFIED"


def consume_for_turn(runtime, event, goal, lease_stack, deadline):
    """Consume one pending approved frame and return a source-bound C3 context.

    No frame is requested by this function. The companion's non-blocking poll
    returns a frame only after a separate one-shot observe_ui approval. Raw
    bytes and numeric feature vectors are never copied into Store or the C3
    prompt. The UI lease stays open in lease_stack until Runtime finishes C3
    generation; revocation cancels that same turn and clears adapter buffers.
    """
    provider = getattr(runtime, "_a5_visual_provider", None)
    if provider is None:
        return None

    if not isinstance(event, dict):
        raise ValueError("A5 Runtime event is required")
    event_id = event.get("event_id")
    generation_id = event.get("brain_generation_id")
    active = getattr(runtime, "turn_event", None)
    if (
        type(event_id) is not str or not event_id
        or type(generation_id) is not str or not generation_id
        or not isinstance(active, dict)
        or active.get("event_id") != event_id
        or active.get("brain_generation_id") != generation_id
        or getattr(runtime, "current", None) != "turn"
    ):
        raise PermissionError("A5 frame must belong to the current Runtime turn")
    if type(goal) is not str or len(goal) > 512:
        raise ValueError("A5 attention goal must be bounded text")
    if (
        isinstance(deadline, bool)
        or not isinstance(deadline, (int, float))
        or not math.isfinite(float(deadline))
        or time.monotonic() >= float(deadline)
    ):
        raise TimeoutError("A5 frame poll is outside the active turn deadline")
    if not callable(getattr(lease_stack, "enter_context", None)):
        raise TypeError("A5 frame lease requires the Runtime ExitStack")

    cancel_event = getattr(runtime, "cancel_event", None)
    if not callable(getattr(cancel_event, "is_set", None)) or cancel_event.is_set():
        raise PermissionError("Runtime turn is already cancelled")

    poll_started = time.monotonic()
    item = provider.poll_visual_frame(
        event_id=event_id,
        generation_id=generation_id,
        deadline=float(deadline),
    )
    poll_duration_s = time.monotonic() - poll_started
    if item is None:
        return None
    if type(item) is not dict or set(item) != {"observation", "frame_bytes"}:
        raise ValueError("A5 provider must return exactly observation and frame_bytes")

    observation = item["observation"]
    frame_bytes = item["frame_bytes"]
    if type(frame_bytes) not in (bytes, bytearray, memoryview) or not frame_bytes:
        raise ValueError("A5 provider returned an empty or invalid frame")

    from .a5_visual_frame_bridge import A5VisualFrameAdapter

    adapter = getattr(runtime, "_a5_visual_adapter", None)
    if adapter is None:
        adapter = A5VisualFrameAdapter(runtime)
        runtime._a5_visual_adapter = adapter
    if not isinstance(adapter, A5VisualFrameAdapter) or adapter.runtime is not runtime:
        raise PermissionError("A5 visual adapter is not bound to this Runtime")

    grant = lease_stack.enter_context(
        adapter.lease(
            observation,
            provider.consent_check,
            provider.consent_guard,
            provider.revocation_subscribe,
        )
    )
    result = adapter.ingest(
        frame_bytes,
        observation,
        grant,
        goal=goal,
        token_budget=512,
        priority=0,
    )
    # Drop the provider's original frame reference immediately. The adapter
    # keeps only its bounded in-memory descriptor until lease_stack closes.
    del frame_bytes
    del item

    packets = adapter.context(event_id, grant)
    if len(packets) != 1:
        raise RuntimeError("A5 visual adapter did not return exactly one current-turn packet")
    packet_value = packets[0]
    segments = packet_value.get("segments")
    if not isinstance(segments, list) or not segments or not isinstance(segments[0], dict):
        raise ValueError("A5 visual packet has no source-bound summary segment")
    segment = segments[0]
    source_ref = packet_value.get("source_ref")
    if not isinstance(source_ref, dict) or source_ref != segment.get("source_ref"):
        raise ValueError("A5 visual packet source binding is inconsistent")

    a4 = result.get("a4")
    raw_eye_signal = a4.get("raw_eye_signal") if isinstance(a4, dict) else None
    if (
        not isinstance(raw_eye_signal, dict)
        or raw_eye_signal.get("source_ref") != source_ref
        or raw_eye_signal.get("authority") != "ATTENTION_ONLY"
        or raw_eye_signal.get("learned") is not False
    ):
        raise ValueError("A5 adapter did not deliver its source-bound RAW-EYE signal to A4")
    a4_rows = a4.get("segments")
    if not isinstance(a4_rows, list) or len(a4_rows) != 1:
        raise ValueError("A5 visual frame must map to exactly one A4 salience row")
    a4_row = a4_rows[0]

    hypotheses = []
    for candidate in packet_value.get("student_candidates", ())[:3]:
        if not isinstance(candidate, dict):
            continue
        caption = candidate.get("caption")
        region_id = candidate.get("region_id")
        cosine = candidate.get("cosine")
        if type(caption) is not str or not caption.strip() or type(region_id) is not str:
            continue
        if isinstance(cosine, bool) or not isinstance(cosine, (int, float)) or not math.isfinite(float(cosine)):
            continue
        hypotheses.append({
            "region_id": region_id[:80],
            "caption": caption[:200],
            "cosine": round(float(cosine), 6),
            "authority": "STUDENT_ESTIMATE",
            "reference_authority": "REFERENCE_NOT_FACT",
        })

    clean_source_ref = {
        "source_id": source_ref["source_id"],
        "sha256": source_ref["sha256"],
        "char_start": 0,
        "char_end": 0,
        "modality": "visual",
    }
    prompt_context = {
        "modality": "visual",
        "summary": str(segment.get("text", ""))[:512],
        "source_ref": clean_source_ref,
        "raw_eye_structure": round(float(packet_value["raw_eye_structure"]), 6),
        "a4_base_salience": round(float(a4_row["base_score"]), 6),
        "a4_visual_salience": round(float(a4_row["score"]), 6),
        "a4_salience_authority": raw_eye_signal["authority"],
        "a4_salience_learned": raw_eye_signal["learned"],
        "a4_raw_eye_contribution": round(float(a4_row["raw_eye_contribution"]), 6),
        "student_hypotheses": hypotheses,
        "interpretation_limit": (
            "RAW-EYE values describe visual structure, not object identity; "
            "student captions are hypotheses, not facts"
        ),
        "raw_capture_persisted": False,
        "action_authority": False,
        "learning_authority": False,
    }
    audit = {
        "status": "CONSUMED_UNVERIFIED",
        "source_ref": clean_source_ref,
        "raw_frame_sha256": packet_value["raw_frame_sha256"],
        "feature_sha256": result["feature_sha256"],
        "feature_count": result["feature_count"],
        "poll_duration_s": round(poll_duration_s, 6),
        "a4_base_salience": prompt_context["a4_base_salience"],
        "a4_visual_salience": prompt_context["a4_visual_salience"],
        "a4_raw_eye_contribution": prompt_context["a4_raw_eye_contribution"],
        "admission_status": getattr(result.get("admission"), "status", None),
        "student_authority": packet_value.get("student_authority", "UNKNOWN"),
        "raw_capture_persisted": False,
        "action_authority": False,
        "learning_authority": False,
    }
    return {
        "source_ref": clean_source_ref,
        "prompt_context": prompt_context,
        "audit": audit,
    }
