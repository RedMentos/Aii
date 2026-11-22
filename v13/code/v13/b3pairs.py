"""B3 paired native-state capture.

A paired example is two independent, read-only native prefill taps of the
*same exact source span and event*: B1_DETAIL + B2_GIST. It is not a text
message, does not inject foreign state, and grants no learning authority.
The returned arrays are suitable inputs to an offline/L1 bridge experiment;
task supervision and the L1 ablations remain separate requirements.
"""
from __future__ import annotations

import hashlib
import json
import math

from .contracts import packet

ROLES = ("B1_DETAIL", "B2_GIST")
SCHEMA = "v13.b3-paired-native-taps/1"


def _matrix(value, name):
    if not isinstance(value, list) or not value:
        raise ValueError(name + ": empty native state")
    width = None
    out = []
    for row in value:
        if not isinstance(row, list) or not row:
            raise ValueError(name + ": malformed row")
        if width is None:
            width = len(row)
        if len(row) != width:
            raise ValueError(name + ": ragged native state")
        clean = []
        for item in row:
            if type(item) not in (int, float) or not math.isfinite(item):
                raise ValueError(name + ": non-finite native state")
            clean.append(float(item))
        out.append(clean)
    return out, width


def _mean_pool(rows):
    n = len(rows)
    d = len(rows[0])
    return [sum(row[j] for row in rows) / n for j in range(d)]


def capture_pair(cognition, event, deadline):
    """Capture B1 and B2 native states for one event, sequentially on mobile.

    The pair packet binds both immutable LatentTapPackets to the same source,
    event, generation, and pinned model revisions. The actual feature tensors
    stay in the existing hash-verified data/blobs files.
    """
    if not isinstance(event, dict):
        raise ValueError("event required")
    event_id = event.get("event_id")
    generation = event.get("brain_generation_id")
    source = event.get("source_ref")
    if not event_id or not generation or not isinstance(source, dict):
        raise ValueError("event/source binding missing")

    taps = {}
    features = {}
    for role in ROLES:
        tap = cognition.tap(role, event, source, deadline)
        if not isinstance(tap, dict) or tap.get("role") != role:
            raise ValueError("tap role mismatch: " + role)
        if tap.get("event_id") != event_id or tap.get("brain_generation_id") != generation:
            raise ValueError("tap event/generation mismatch: " + role)
        if tap.get("source_ref") != source:
            raise ValueError("tap source span mismatch: " + role)
        if not tap.get("model_revision") or not tap.get("tap_id"):
            raise ValueError("tap identity/revision missing: " + role)
        data = cognition.read_tap(tap)
        if data.get("token_ids") != tap.get("token_ids"):
            raise ValueError("tap token lineage mismatch: " + role)
        rows, width = _matrix(data.get("vectors"), role)
        shape = tap.get("shape")
        if shape != [len(rows), width]:
            raise ValueError("tap shape mismatch: " + role)
        taps[role] = tap
        features[role] = rows

    # Each body keeps its own tokenizer and token sequence. Pairing is by the
    # exact source span, never by assuming token index equivalence.
    pair_key = hashlib.sha256(json.dumps(
        [event_id, generation, source, taps["B1_DETAIL"]["model_revision"],
         taps["B2_GIST"]["model_revision"], taps["B1_DETAIL"]["tap_id"],
         taps["B2_GIST"]["tap_id"]],
        sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()).hexdigest()
    body_pair_id = "B1_DETAIL<->B2_GIST:" + pair_key[:24]
    record = packet(
        "B3PairedTapPacket", "B3_CALLOSUM", event_id, generation, [source],
        packet_schema=SCHEMA, body_pair_id=body_pair_id, source_ref=source,
        sender_roles=list(ROLES),
        tap_packet_ids={role: taps[role]["packet_id"] for role in ROLES},
        tap_ids={role: taps[role]["tap_id"] for role in ROLES},
        model_revisions={role: taps[role]["model_revision"] for role in ROLES},
        feature_bindings={role: {
            "feature_path": taps[role]["feature_path"],
            "feature_sha256": taps[role]["feature_sha256"],
            "shape": taps[role]["shape"],
        } for role in ROLES},
        token_counts={role: len(features[role]) for role in ROLES},
        dimensions={role: len(features[role][0]) for role in ROLES},
        token_alignment="NOT_ASSUMED_DIFFERENT_NATIVE_TOKENIZERS",
        receiver_pooling="MEAN_OF_RECEIVER_NATIVE_TAP_TOKENS",
        injection_authority=0, learning_authority=0,
    )
    cognition.s.add_packet("B3PairedTapPacket", record)
    return {
        "packet": record,
        "body_pair_id": body_pair_id,
        "source_ref": source,
        "sender": {"role": "B1_DETAIL", "states": features["B1_DETAIL"]},
        "receiver": {"role": "B2_GIST", "states": features["B2_GIST"],
                     "pooled": _mean_pool(features["B2_GIST"])},
        "reverse_sender": {"role": "B2_GIST", "states": features["B2_GIST"]},
        "reverse_receiver": {"role": "B1_DETAIL", "states": features["B1_DETAIL"],
                             "pooled": _mean_pool(features["B1_DETAIL"])},
        "authority": {"native_read_only": True, "latent_injection": False,
                      "body_learning": False},
    }



def load_pair(cognition, pair_packet):
    """Reload a persisted pair after restart and revalidate every tap/source hash."""
    stored = cognition.s.one(
        "SELECT payload FROM packets WHERE kind='B3PairedTapPacket' AND id=?",
        (pair_packet.get("packet_id"),))
    if not stored or json.loads(stored["payload"]) != pair_packet:
        raise ValueError("B3 pair packet is not the stored immutable record")
    if pair_packet.get("schema") != SCHEMA:
        raise ValueError("B3 pair schema mismatch")
    source = pair_packet["source_ref"]
    taps, features = {}, {}
    for role in ROLES:
        tap_id = pair_packet["tap_packet_ids"][role]
        row = cognition.s.one(
            "SELECT payload FROM packets WHERE kind='LatentTapPacket' AND id=?",
            (tap_id,))
        if not row:
            raise ValueError("B3 pair tap packet missing: " + role)
        tap = json.loads(row["payload"])
        binding = pair_packet["feature_bindings"][role]
        if (tap.get("role") != role or tap.get("event_id") != pair_packet["event_id"]
                or tap.get("brain_generation_id") != pair_packet["brain_generation_id"]
                or tap.get("source_ref") != source
                or tap.get("tap_id") != pair_packet["tap_ids"][role]
                or tap.get("model_revision") != pair_packet["model_revisions"][role]
                or tap.get("feature_path") != binding.get("feature_path")
                or tap.get("feature_sha256") != binding.get("feature_sha256")
                or tap.get("shape") != binding.get("shape")):
            raise ValueError("B3 pair tap lineage changed: " + role)
        data = cognition.read_tap(tap)
        if data.get("token_ids") != tap.get("token_ids"):
            raise ValueError("B3 pair token lineage changed: " + role)
        rows, width = _matrix(data.get("vectors"), role)
        if tap["shape"] != [len(rows), width]:
            raise ValueError("B3 pair native feature shape changed: " + role)
        taps[role], features[role] = tap, rows
    return {
        "packet": pair_packet,
        "body_pair_id": pair_packet["body_pair_id"],
        "source_ref": source,
        "sender": {"role": "B1_DETAIL", "states": features["B1_DETAIL"]},
        "receiver": {"role": "B2_GIST", "states": features["B2_GIST"],
                     "pooled": _mean_pool(features["B2_GIST"])},
        "reverse_sender": {"role": "B2_GIST", "states": features["B2_GIST"]},
        "reverse_receiver": {"role": "B1_DETAIL", "states": features["B1_DETAIL"],
                             "pooled": _mean_pool(features["B1_DETAIL"])},
        "authority": {"native_read_only": True, "latent_injection": False,
                      "body_learning": False},
    }


def training_batch(cognition, pair_packets, labels, direction="B1_TO_B2"):
    """Build actual Bridge.fit inputs from persisted native pairs and explicit labels.

    No label is inferred from generated body text. Labels must be externally
    supplied, aligned to the pair order, and the same model revisions/dimensions
    must hold across the batch. Sender sequences are right-padded with a mask;
    receiver states are mean-pooled independently under their native tokenizer.
    """
    if direction not in ("B1_TO_B2", "B2_TO_B1"):
        raise ValueError("direction must be B1_TO_B2 or B2_TO_B1")
    if not isinstance(pair_packets, (list, tuple)) or not pair_packets:
        raise ValueError("at least one persisted B3 pair is required")
    if not isinstance(labels, (list, tuple)) or len(labels) != len(pair_packets):
        raise ValueError("explicit labels must align one-to-one with B3 pairs")
    pairs = [load_pair(cognition, p) for p in pair_packets]
    sender_role, receiver_role = (("B1_DETAIL", "B2_GIST") if direction == "B1_TO_B2"
                                   else ("B2_GIST", "B1_DETAIL"))
    sender_rev = pairs[0]["packet"]["model_revisions"][sender_role]
    receiver_rev = pairs[0]["packet"]["model_revisions"][receiver_role]
    sender_dim = pairs[0]["packet"]["dimensions"][sender_role]
    receiver_dim = pairs[0]["packet"]["dimensions"][receiver_role]
    if any(p["packet"]["model_revisions"] != pairs[0]["packet"]["model_revisions"]
           or p["packet"]["dimensions"] != pairs[0]["packet"]["dimensions"]
           for p in pairs):
        raise ValueError("B3 batch mixes body revisions or native dimensions")
    if any(type(y) is not int or y < 0 for y in labels):
        raise ValueError("labels must be nonnegative integers supplied by the task")
    sender_key = "sender" if direction == "B1_TO_B2" else "reverse_sender"
    receiver_key = "receiver" if direction == "B1_TO_B2" else "reverse_receiver"
    max_tokens = max(len(p[sender_key]["states"]) for p in pairs)
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("NumPy is required by the B3 training bridge") from exc
    H = np.zeros((len(pairs), max_tokens, sender_dim), dtype=np.float32)
    mask = np.zeros((len(pairs), max_tokens), dtype=np.float32)
    Xr = np.zeros((len(pairs), receiver_dim), dtype=np.float32)
    for i, p in enumerate(pairs):
        rows = p[sender_key]["states"]
        H[i, :len(rows), :] = np.asarray(rows, dtype=np.float32)
        mask[i, :len(rows)] = 1.
        Xr[i, :] = np.asarray(p[receiver_key]["pooled"], dtype=np.float32)
    y = np.asarray(labels, dtype=np.int64)
    return {"H": H, "mask": mask, "Xr": Xr, "y": y,
            "direction": direction, "sender_role": sender_role, "receiver_role": receiver_role,
            "body_pair_id": [p["body_pair_id"] for p in pairs],
            "source_refs": [p["source_ref"] for p in pairs],
            "sender_revision": sender_rev, "receiver_revision": receiver_rev,
            "claim_limit": "paired native read-only taps + explicit task labels; no receiver injection"}
