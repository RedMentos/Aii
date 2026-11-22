"""Experimental numeric B3 sidecar coupled to real Enlightened Space event identity.

No GGUF hidden-state/KV injection. Source vectors MUST come from an explicitly
versioned encoder; symbolic bag-of-words is not a native latent.
"""
from __future__ import annotations
import hashlib
import json
import math
from .latent_bridge import Projector, receive

SCHEMA = "v13.numeric-sidecar/1"

def _id(value):
    return isinstance(value, str) and 0 < len(value) <= 128 and all(
        c.isalnum() or c in "._:-" for c in value)

class NumericSidecar:
    """Event-scoped numeric transport, not a permission or evidence authority."""
    def __init__(self, projector: Projector, *, encoder_revision: str, receiver_revision: str):
        if not _id(encoder_revision) or not _id(receiver_revision):
            raise ValueError("versioned encoder and receiver required")
        self.projector = projector
        self.encoder_revision = encoder_revision
        self.receiver_revision = receiver_revision
        self._pending = {}

    def send(self, event, *, source_id, source_vector, sender_revision,
             consent_active=False):
        if consent_active is not True:
            raise PermissionError("external current consent required")
        if not isinstance(event, dict) or not _id(event.get("event_id")) or not _id(event.get("brain_generation_id")):
            raise ValueError("event identity required")
        if not _id(source_id) or sender_revision != self.encoder_revision:
            raise ValueError("source/encoder mismatch")
        packet = self.projector.project(source_vector, source_id, event["brain_generation_id"])
        if not all(math.isfinite(v) for v in packet["values"]):
            raise ValueError("nonfinite projection")
        if math.sqrt(sum(v*v for v in packet["values"])) > 100:
            raise ValueError("unbounded projection")
        identity = (event["brain_generation_id"], event["event_id"], source_id)
        # No cross-event replay; latest packet overwrites only the same identity.
        self._pending[identity] = packet
        return {"schema": SCHEMA, "event_id": event["event_id"],
                "generation": event["brain_generation_id"], "source_id": source_id,
                "projector_revision": packet["revision"],
                "encoder_revision": self.encoder_revision,
                "receiver_revision": self.receiver_revision,
                "authority": "EXPERIMENTAL_NUMERIC_ONLY"}

    def take(self, event, receipt, *, receiver_revision, admitted_source_ids,
             consent_active=False):
        if consent_active is not True:
            raise PermissionError("external current consent required")
        if not isinstance(receipt, dict) or receipt.get("schema") != SCHEMA or receipt.get("authority") != "EXPERIMENTAL_NUMERIC_ONLY":
            raise ValueError("invalid receipt")
        if not isinstance(event, dict) or receipt.get("event_id") != event.get("event_id") or receipt.get("generation") != event.get("brain_generation_id"):
            raise PermissionError("event/generation mismatch")
        if receiver_revision != self.receiver_revision or receipt.get("receiver_revision") != receiver_revision or receipt.get("encoder_revision") != self.encoder_revision:
            raise ValueError("model revision mismatch")
        source_id = receipt.get("source_id")
        if not isinstance(admitted_source_ids, (tuple, list, set)) or source_id not in admitted_source_ids:
            raise PermissionError("unadmitted source")
        key = (receipt["generation"], receipt["event_id"], source_id)
        packet = self._pending.get(key)
        if packet is None or packet["revision"] != receipt.get("projector_revision"):
            raise ValueError("missing/stale numeric packet")
        values = receive(packet, self.projector.target, receipt["generation"],
                         admitted_source_ids, self.projector.revision())
        del self._pending[key]  # one-shot; prevents stale/replayed conditioning
        return tuple(values)

    def discard_event(self, event):
        if not isinstance(event, dict):
            raise ValueError("event")
        generation, event_id = event.get("brain_generation_id"), event.get("event_id")
        for key in tuple(self._pending):
            if key[:2] == (generation, event_id):
                del self._pending[key]
