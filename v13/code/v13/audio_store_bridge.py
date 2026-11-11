"""Read-only acoustic A5 replay bridge to B1/B2/JEF shadow views.

Uses the production Store.one packets table, not a parallel JSON store.
No model invocation, Android permission, training or action authority.
"""
from __future__ import annotations

import json
from .audio_views import acoustic_views


def replay_acoustic_packet(store, packet_id: str, *, max_detail: int = 64,
                           gist_bins: int = 8) -> dict:
    """Reload a persisted A5 packet, verify its source and produce bounded views.

    The caller may pass these views to an explicitly shadow-only B/C observer.
    It must never interpret them as permission to act or train.
    """
    if not isinstance(packet_id, str) or not packet_id or len(packet_id) > 128:
        raise ValueError("bounded packet_id required")
    row = store.one("SELECT kind,event_id,generation_id,payload FROM packets WHERE id=?",
                    (packet_id,))
    if row is None or row["kind"] != "PerceptPacket":
        raise ValueError("persisted A5 packet required")
    try:
        percept = json.loads(row["payload"])
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid persisted packet JSON") from exc
    if not isinstance(percept, dict) or percept.get("packet_id") != packet_id:
        raise ValueError("packet identity mismatch")
    if percept.get("event_id") != row["event_id"] or percept.get("brain_generation_id") != row["generation_id"]:
        raise ValueError("persisted event/generation mismatch")
    ref = percept.get("source_ref")
    if not isinstance(ref, dict):
        raise ValueError("missing source reference")
    # Real Store.read_source revalidates the content hash and source revocation.
    descriptor = store.read_source(ref)
    raw = percept.get("raw_ear")
    if not isinstance(raw, dict):
        raise ValueError("missing RAW EAR")
    if descriptor != "v13.audio_pcm_sha256:" + str(raw.get("source_sha256")) + "\\n":
        raise ValueError("persisted A0 descriptor / RAW EAR hash mismatch")
    if percept.get("training_authority") != 0 or percept.get("native_receiver_authority") != 0:
        raise ValueError("unexpected learning/receiver authority")
    return acoustic_views(percept, max_detail=max_detail, gist_bins=gist_bins)
