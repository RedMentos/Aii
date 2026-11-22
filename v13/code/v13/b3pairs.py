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

from .contracts import packet, validate
from .common import atomic_write, dumps, file_hash

ROLES = ("B1_DETAIL", "B2_GIST")
SCHEMA = "v13.b3-paired-native-taps/2"
B1_FINE_SLOTS = 64


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

    # B2's receiver representation must be its adaptive Gist readout, not a
    # global mean over all native tokens. Verify pieces against this exact tap.
    from .age import controller as age_controller
    from .gist import resolve as resolve_gist
    from .gist_readout import consume as consume_gist, DEFAULT_MODE
    runtime = cognition.r
    source_text = cognition.s.read_source(source)
    runner = runtime.pool.get_tap("B2_GIST")
    try:
        runner.load(runtime.cancel_event, deadline)
        token_rows = runner._json("POST", "/tokenize", {
            "content": source_text, "add_special": True, "with_pieces": True
        }, deadline)["tokens"]
    finally:
        runtime.pool.unload()
    gist_ids = [row["id"] for row in token_rows]
    if gist_ids != taps["B2_GIST"]["token_ids"]:
        raise ValueError("B2 Gist tokenizer pieces do not belong to this native tap")
    resolution = resolve_gist(age_controller(runtime), source_text)
    gist_plan, gist_vectors = consume_gist(
        source_text, source, gist_ids, [row["piece"] for row in token_rows],
        features["B2_GIST"], size=resolution["tokens_per_group"],
        slots=resolution["slots"], mode=DEFAULT_MODE,
        tap_id=taps["B2_GIST"]["tap_id"])
    if not gist_plan.get("lossless") or gist_plan.get("receiver_injection_authority") != 0:
        raise ValueError("B2 Gist readout failed its lossless/read-only gate")

    # B1 keeps one fine slot per native token. Persist exact source spans so
    # the receiver side does not collapse Detail into a pooled summary either.
    from .gist_readout import token_spans
    runner = runtime.pool.get_tap("B1_DETAIL")
    try:
        runner.load(runtime.cancel_event, deadline)
        fine_rows = runner._json("POST", "/tokenize", {
            "content": source_text, "add_special": True, "with_pieces": True
        }, deadline)["tokens"]
    finally:
        runtime.pool.unload()
    fine_ids = [row["id"] for row in fine_rows]
    if fine_ids != taps["B1_DETAIL"]["token_ids"]:
        raise ValueError("B1 Fine tokenizer pieces do not belong to this native tap")
    spans = token_spans(source_text, [row["piece"] for row in fine_rows])
    fine_slots = []
    for index, (token_id, span) in enumerate(zip(fine_ids, spans)):
        start, end = span
        fine_slots.append({
            "slot": index, "token_id": token_id,
            "source_ref": source | {
                "char_start": source["char_start"] + start,
                "char_end": source["char_start"] + end,
            },
        })
    fine_plan = {
        "revision": "b1-native-fine-slots-v1", "tap_id": taps["B1_DETAIL"]["tap_id"],
        "source_ref": source, "token_ids": fine_ids, "native_tokens": len(fine_ids),
        "dim": taps["B1_DETAIL"]["shape"][1], "max_slots": B1_FINE_SLOTS,
        "slots": fine_slots, "lossless": True,
        "receiver_injection_authority": 0, "body_learning_authority": 0,
    }

    # Each body keeps its own tokenizer and token sequence. Pairing is by the
    # exact source span, never by assuming token index equivalence.
    pair_key = hashlib.sha256(json.dumps(
        [event_id, generation, source, taps["B1_DETAIL"]["model_revision"],
         taps["B2_GIST"]["model_revision"], taps["B1_DETAIL"]["tap_id"],
         taps["B2_GIST"]["tap_id"], gist_plan["revision"], gist_plan["mode"],
         gist_plan["tokens_per_group"], gist_plan["max_slots"]],
        sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()).hexdigest()
    body_pair_id = "B1_DETAIL<->B2_GIST:" + pair_key[:24]
    artifact_key = hashlib.sha256((pair_key + taps["B2_GIST"]["packet_id"] + taps["B1_DETAIL"]["packet_id"]).encode()).hexdigest()
    gist_path = runtime.home / "data/blobs" / ("b3pair-" + artifact_key + "-gist.json")
    gist_artifact = {"body_pair_id": body_pair_id,
                     "tap_packet_id": taps["B2_GIST"]["packet_id"],
                     "source_ref": source, "revision": gist_plan["revision"],
                     "vectors": gist_vectors.tolist()}
    atomic_write(gist_path, dumps(gist_artifact))
    gist_binding = {
        "plan": gist_plan,
        "tap_packet_id": taps["B2_GIST"]["packet_id"],
        "feature_path": str(gist_path.relative_to(runtime.home)),
        "feature_sha256": file_hash(gist_path),
        "shape": [int(gist_vectors.shape[0]), int(gist_vectors.shape[1])],
    }
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
        gist_readout=gist_binding,
        fine_readout={"tap_packet_id": taps["B1_DETAIL"]["packet_id"], "plan": fine_plan},
        token_counts={role: len(features[role]) for role in ROLES},
        dimensions={role: len(features[role][0]) for role in ROLES},
        token_alignment="NOT_ASSUMED_DIFFERENT_NATIVE_TOKENIZERS",
        receiver_pooling="B2_ADAPTIVE_GIST_SLOTS;B1_NATIVE_FINE_TOKEN_SLOTS",
        injection_authority=0, learning_authority=0,
    )
    cognition.s.add_packet("B3PairedTapPacket", record)
    return {
        "packet": record,
        "body_pair_id": body_pair_id,
        "source_ref": source,
        "sender": {"role": "B1_DETAIL", "states": features["B1_DETAIL"]},
        "receiver": {"role": "B2_GIST", "states": features["B2_GIST"],
                     "gist_states": gist_vectors.tolist(), "gist_plan": gist_plan},
        "reverse_sender": {"role": "B2_GIST", "states": features["B2_GIST"]},
        "reverse_receiver": {"role": "B1_DETAIL", "states": features["B1_DETAIL"],
                             "fine_states": features["B1_DETAIL"], "fine_plan": fine_plan},
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
    validate("B3PairedTapPacket", pair_packet)
    if pair_packet.get("packet_schema") != SCHEMA:
        raise ValueError("B3 pair schema mismatch")
    source = pair_packet["source_ref"]
    gist_binding = pair_packet.get("gist_readout")
    if (not isinstance(gist_binding, dict) or not isinstance(gist_binding.get("plan"), dict)
            or gist_binding.get("tap_packet_id") != pair_packet["tap_packet_ids"]["B2_GIST"]):
        raise ValueError("B3 pair has no correctly bound adaptive Gist readout")
    fine_binding = pair_packet.get("fine_readout")
    if (not isinstance(fine_binding, dict) or not isinstance(fine_binding.get("plan"), dict)
            or fine_binding.get("tap_packet_id") != pair_packet["tap_packet_ids"]["B1_DETAIL"]):
        raise ValueError("B3 pair has no correctly bound B1 fine-slot readout")
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
    fine_plan = fine_binding["plan"]
    b1_tap = taps["B1_DETAIL"]
    if (fine_plan.get("tap_id") != b1_tap.get("tap_id")
            or fine_plan.get("token_ids") != b1_tap.get("token_ids")
            or fine_plan.get("source_ref") != source
            or fine_plan.get("native_tokens") != len(features["B1_DETAIL"])
            or fine_plan.get("dim") != pair_packet["dimensions"]["B1_DETAIL"]
            or fine_plan.get("max_slots") != B1_FINE_SLOTS
            or len(fine_plan.get("slots", [])) != len(features["B1_DETAIL"])
            or not fine_plan.get("lossless")
            or fine_plan.get("receiver_injection_authority") != 0
            or fine_plan.get("body_learning_authority") != 0):
        raise ValueError("B1 fine readout lineage/geometry mismatch")
    gist_path = cognition.r.home / gist_binding["feature_path"]
    root = (cognition.r.home / "data/blobs").resolve()
    if gist_path.is_symlink() or not gist_path.resolve().is_relative_to(root):
        raise ValueError("B3 Gist artifact path escaped data/blobs")
    if not gist_path.is_file() or file_hash(gist_path) != gist_binding["feature_sha256"]:
        raise ValueError("B3 Gist artifact hash mismatch")
    gist_artifact = json.loads(gist_path.read_text())
    if (gist_binding.get("tap_packet_id") != pair_packet["tap_packet_ids"]["B2_GIST"]
            or gist_binding["plan"].get("tap_id") != pair_packet["tap_ids"]["B2_GIST"]
            or gist_artifact.get("body_pair_id") != pair_packet["body_pair_id"]
            or gist_artifact.get("tap_packet_id") != pair_packet["tap_packet_ids"]["B2_GIST"]
            or gist_artifact.get("source_ref") != source
            or gist_artifact.get("revision") != gist_binding["plan"].get("revision")):
        raise ValueError("B3 Gist artifact lineage mismatch")
    gist_rows, gist_dim = _matrix(gist_artifact.get("vectors"), "B2_GIST_GIST")
    if [len(gist_rows), gist_dim] != gist_binding["shape"] or gist_dim != pair_packet["dimensions"]["B2_GIST"]:
        raise ValueError("B3 Gist artifact shape mismatch")
    return {
        "packet": pair_packet,
        "body_pair_id": pair_packet["body_pair_id"],
        "source_ref": source,
        "sender": {"role": "B1_DETAIL", "states": features["B1_DETAIL"]},
        "receiver": {"role": "B2_GIST", "states": features["B2_GIST"],
                     "gist_states": gist_rows, "gist_plan": gist_binding["plan"]},
        "reverse_sender": {"role": "B2_GIST", "states": features["B2_GIST"]},
        "reverse_receiver": {"role": "B1_DETAIL", "states": features["B1_DETAIL"],
                             "fine_states": features["B1_DETAIL"], "fine_plan": fine_plan},
        "authority": {"native_read_only": True, "latent_injection": False,
                      "body_learning": False},
    }


def training_batch(cognition, pair_packets, labels, direction="B1_TO_B2"):
    """Build actual Bridge.fit inputs from persisted native pairs and explicit labels.

    No label is inferred from generated body text. Labels must be externally
    supplied, aligned to the pair order, and the same model revisions/dimensions
    must hold across the batch. Sender sequences are right-padded with a mask;
    B1->B2 uses fixed-budget adaptive Gist slots; B2->B1 preserves the
    receiver's native fine token slots (up to the tap's 64-token bound).
    """
    if direction not in ("B1_TO_B2", "B2_TO_B1"):
        raise ValueError("direction must be B1_TO_B2 or B2_TO_B1")
    if not isinstance(pair_packets, (list, tuple)) or not pair_packets:
        raise ValueError("at least one persisted B3 pair is required")
    if not isinstance(labels, (list, tuple)) or len(labels) != len(pair_packets):
        raise ValueError("explicit labels must align one-to-one with B3 pairs")
    pair_ids = [p.get("body_pair_id") for p in pair_packets]
    if len(set(pair_ids)) != len(pair_ids):
        raise ValueError("B3 training batch contains duplicate body_pair_id experiences")
    source_keys = [(p.get("source_ref", {}).get("source_id"),
                    p.get("source_ref", {}).get("char_start"),
                    p.get("source_ref", {}).get("char_end")) for p in pair_packets]
    if len(set(source_keys)) != len(source_keys):
        raise ValueError("B3 training batch repeats the same exact source span")
    pairs = [load_pair(cognition, p) for p in pair_packets]
    sender_role, receiver_role = (("B1_DETAIL", "B2_GIST") if direction == "B1_TO_B2"
                                   else ("B2_GIST", "B1_DETAIL"))
    sender_rev = pairs[0]["packet"]["model_revisions"][sender_role]
    receiver_rev = pairs[0]["packet"]["model_revisions"][receiver_role]
    sender_dim = pairs[0]["packet"]["dimensions"][sender_role]
    receiver_dim = (pairs[0]["packet"]["gist_readout"]["shape"][1] *
                    pairs[0]["packet"]["gist_readout"]["plan"]["max_slots"]
                    if direction == "B1_TO_B2"
                    else pairs[0]["packet"]["dimensions"][receiver_role] * B1_FINE_SLOTS)
    if any(p["packet"]["model_revisions"] != pairs[0]["packet"]["model_revisions"]
           or p["packet"]["dimensions"] != pairs[0]["packet"]["dimensions"]
           or p["packet"]["gist_readout"]["plan"]["max_slots"] != pairs[0]["packet"]["gist_readout"]["plan"]["max_slots"]
           for p in pairs):
        raise ValueError("B3 batch mixes body revisions, native dimensions, or Gist slot budgets")
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
        if direction == "B1_TO_B2":
            slots = np.asarray(p[receiver_key]["gist_states"], dtype=np.float32)
            max_slots = p["packet"]["gist_readout"]["plan"]["max_slots"]
            slot_dim = p["packet"]["gist_readout"]["shape"][1]
            if slots.shape[0] > max_slots or slots.shape[1] != slot_dim:
                raise ValueError("B2 Gist slot geometry mismatch")
            flat = np.zeros((max_slots, slot_dim), dtype=np.float32)
            flat[:slots.shape[0], :] = slots
            Xr[i, :] = flat.reshape(-1)
        else:
            fine = np.asarray(p[receiver_key]["fine_states"], dtype=np.float32)
            if fine.shape[0] > B1_FINE_SLOTS or fine.shape[1] != receiver_dim // B1_FINE_SLOTS:
                raise ValueError("B1 Detail fine-slot geometry mismatch")
            flat = np.zeros((B1_FINE_SLOTS, fine.shape[1]), dtype=np.float32)
            flat[:fine.shape[0], :] = fine
            Xr[i, :] = flat.reshape(-1)
    y = np.asarray(labels, dtype=np.int64)
    return {"H": H, "mask": mask, "Xr": Xr, "y": y,
            "direction": direction, "sender_role": sender_role, "receiver_role": receiver_role,
            "body_pair_id": [p["body_pair_id"] for p in pairs],
            "source_refs": [p["source_ref"] for p in pairs],
            "sender_revision": sender_rev, "receiver_revision": receiver_rev,
            "receiver_max_slots": (pairs[0]["packet"]["gist_readout"]["plan"]["max_slots"] if direction == "B1_TO_B2" else B1_FINE_SLOTS),
            "receiver_slot_counts": ([len(p["receiver"]["gist_states"]) for p in pairs] if direction == "B1_TO_B2" else [len(p["reverse_receiver"]["fine_states"]) for p in pairs]),
            "receiver_feature_mode": ("B2_GIST_ADAPTIVE_SLOTS_FLATTENED" if direction == "B1_TO_B2" else "B1_DETAIL_FINE_NATIVE_SLOTS_FLATTENED"),
            "claim_limit": ("paired native read-only taps + adaptive B2 Gist readout + explicit task labels; no receiver injection"
                            if direction == "B1_TO_B2" else
                            "paired native read-only taps + B1 native fine token slots + explicit task labels; no receiver injection")}
