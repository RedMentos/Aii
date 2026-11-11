"""Opt-in, non-authoritative A0/A1/A3/A5 -> B1/B2 source-view bridge.

This deliberately does not patch frozen Runtime or promote the A3 student.
The event is a real Store event; the PerceptPacket is produced and persisted
by the existing Cognition.percept implementation, never fabricated here.
"""
from .percept_subspan_candidate import source_segments


def run_percept_route(runtime, event, *, width_detail=240, width_gist=960):
    """Return persisted A5 packet and independently revalidated B source views.

    Explicit caller only; no routing, training, answer, or tool authority.
    Raises on source mutation, missing provenance, or packet mismatch.
    """
    if not isinstance(event, dict):
        raise ValueError("event required")
    source = event.get("source_ref")
    if not isinstance(source, dict) or source.get("modality") != "text":
        raise ValueError("text source required")
    for field in ("event_id", "brain_generation_id"):
        if not isinstance(event.get(field), str) or not event[field]:
            raise ValueError("missing event identity")
    # Frozen A5 uses local offsets; reject subspans before persistence.
    # Zero-start but shortened spans are also unsafe unless explicitly
    # represented as full-source input; read_source checks provenance.
    if type(source.get("char_start")) is not int or source["char_start"] != 0:
        raise ValueError("nonzero A5 span requires runtime offset fix")
    # Preflight both consumer widths before Cognition.percept persists A5.
    # The source segmenter rejects these values, but doing so afterwards
    # would leave a persisted packet for a rejected route invocation.
    import sys
    for width in (width_detail, width_gist):
        if type(width) is not int or not 0 < width <= sys.maxsize:
            raise ValueError("B source-view width must be a positive integer")
    # Check source before and after the runtime A5 packet write.
    original = runtime.store.read_source(source)
    percept = runtime.cognition.percept(event)
    if (percept.get("event_id") != event["event_id"] or
            percept.get("brain_generation_id") != event["brain_generation_id"] or
            percept.get("source_ref") != source or
            percept.get("modality") != "text"):
        raise ValueError("A5 packet identity mismatch")
    row = runtime.store.one(
        "SELECT payload FROM packets WHERE id=? AND kind='PerceptPacket'",
        (percept["packet_id"],))
    if not row:
        raise ValueError("A5 packet not persisted")
    import json
    if json.loads(row["payload"]) != percept:
        raise ValueError("A5 packet differs from persisted payload")
    if runtime.store.read_source(source) != original:
        raise ValueError("A0 source changed")
    detail = source_segments(runtime.store, source, width_detail, "fixed")
    gist = source_segments(runtime.store, source, width_gist, "event")
    for view in (detail, gist):
        if "".join(runtime.store.read_source(x["source_ref"]) for x in view) != original:
            raise ValueError("B source view not exact")
    return {
        "schema": "v13.perception.source_route_candidate/1",
        "percept_packet_id": percept["packet_id"],
        "percept_packet": percept,
        "b1_detail_source_view": detail,
        "b2_gist_source_view": gist,
        "a3_mode": percept.get("student_mode", "UNAVAILABLE"),
        "a3_available": bool(percept.get("student_feature_sha256")),
        "a3_receiver_authority": 0,
        "teacher_truth_authority": False,
        "body_inference_executed": False,
        "runtime_activated": False,
        "native_android_verified": False,
    }
