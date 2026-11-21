"""B3 native-tap -> trained bridge candidate lab.

This is an explicit, local experiment. It trains only the small B3 adapter from
paired, source-bound native taps and C4 coalition outcomes. It never changes
B1/B2 model weights, activates LATENT, or injects into a live body.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np

from . import b3bridge
from .common import atomic_write, dumps, uid

MAX_EVENTS = 256
MAX_TOKENS = 64
MIN_SAMPLES = 10
MIN_TRAIN = 6
MIN_HOLDOUT = 2
K = 4
R = 8
EPOCHS = 60
BATCH = 8
RUNNER_REVISION = "b10964"


def _packet(store, kind, event_id, role=None):
    if role is None:
        row = store.one(
            "SELECT payload FROM packets WHERE kind=? AND event_id=? ORDER BY rowid DESC LIMIT 1",
            (kind, event_id),
        )
    else:
        row = store.one(
            "SELECT payload FROM packets WHERE kind=? AND event_id=? "
            "AND json_extract(payload,'$.role')=? ORDER BY rowid DESC LIMIT 1",
            (kind, event_id, role),
        )
    return json.loads(row["payload"]) if row else None


def _event(runtime, event_id):
    row = runtime.store.one(
        "SELECT session_id,generation_id,packet FROM events WHERE id=?", (event_id,)
    )
    if not row or row["session_id"] != runtime.session:
        return None
    event = json.loads(row["packet"])
    if row["generation_id"] != runtime.store.generation_id():
        return None
    return event, row["generation_id"]


def _roles(direction):
    if direction not in b3bridge.DIRECTIONS:
        raise ValueError("direction must be B1_TO_B2 or B2_TO_B1")
    sender, receiver = direction.split("_TO_")
    return (
        "B1_DETAIL" if sender == "B1" else "B2_GIST",
        "B1_DETAIL" if receiver == "B1" else "B2_GIST",
    )


def _read_vectors(runtime, tap):
    data = runtime.cognition.read_tap(tap)
    vectors = np.asarray(data["vectors"], dtype=np.float32)
    if vectors.ndim != 2 or vectors.shape[0] < 1 or vectors.shape[1] < 1:
        raise ValueError("native tap vectors must be a nonempty T x D matrix")
    if not np.isfinite(vectors).all():
        raise ValueError("native tap contains non-finite values")
    if len(data["token_ids"]) != vectors.shape[0]:
        raise ValueError("native tap token/vector count mismatch")
    if vectors.shape[0] > MAX_TOKENS:
        vectors = vectors[-MAX_TOKENS:]
    return vectors


def _pair_for_event(runtime, event_id, direction, require_outcome=True):
    sender_role, receiver_role = _roles(direction)
    loaded = _event(runtime, event_id)
    if loaded is None:
        return None
    event, generation = loaded
    source_ref = event.get("source_ref")
    if not isinstance(source_ref, dict) or not isinstance(source_ref.get("sha256"), str):
        return None

    sender_tap = _packet(runtime.store, "LatentTapPacket", event_id, sender_role)
    receiver_tap = _packet(runtime.store, "LatentTapPacket", event_id, receiver_role)
    if not sender_tap or not receiver_tap:
        return None
    for tap, role in ((sender_tap, sender_role), (receiver_tap, receiver_role)):
        if (
            tap.get("event_id") != event_id
            or tap.get("brain_generation_id") != generation
            or tap.get("role") != role
            or tap.get("source_ref") != source_ref
            or tap.get("runner_revision") != RUNNER_REVISION
            or not isinstance(tap.get("tap_id"), str)
            or not tap.get("tap_id")
            or tap.get("model_revision") != runtime.models.revision(role)
        ):
            return None
        ref = tap.get("source_ref") or {}
        if ref.get("char_start") != 0 or ref.get("char_end") != source_ref.get("char_end"):
            return None

    sender_offer = _packet(runtime.store, "OfferPacket", event_id, sender_role)
    receiver_offer = _packet(runtime.store, "OfferPacket", event_id, receiver_role)
    if not sender_offer or not receiver_offer:
        return None
    if (
        sender_offer.get("brain_generation_id") != generation
        or receiver_offer.get("brain_generation_id") != generation
        or sender_offer.get("model_revision") != runtime.models.revision(sender_role)
        or receiver_offer.get("model_revision") != runtime.models.revision(receiver_role)
    ):
        return None

    label = None
    if require_outcome:
        focal = _packet(runtime.store, "FocalCycle", event_id)
        if not focal or not isinstance(focal.get("coalition"), list):
            return None
        label = int(receiver_offer["packet_id"] in focal["coalition"])

    sender_vectors = _read_vectors(runtime, sender_tap)
    receiver_vectors = _read_vectors(runtime, receiver_tap)
    return {
        "event_id": event_id,
        "source_hash": source_ref["sha256"],
        "generation_id": generation,
        "sender_role": sender_role,
        "receiver_role": receiver_role,
        "sender_revision": sender_tap["model_revision"],
        "receiver_revision": receiver_tap["model_revision"],
        "sender_tap_id": sender_tap["tap_id"],
        "receiver_tap_id": receiver_tap["tap_id"],
        "sender_tap_packet_id": sender_tap["packet_id"],
        "receiver_tap_packet_id": receiver_tap["packet_id"],
        "sender_offer_packet_id": sender_offer["packet_id"],
        "receiver_offer_packet_id": receiver_offer["packet_id"],
        "H": sender_vectors,
        "Xr": receiver_vectors[-1],
        "label": label,
    }


def collect_pairs(runtime, direction, max_events=MAX_EVENTS):
    _roles(direction)
    rows = runtime.store.rows(
        "SELECT event_id FROM packets WHERE kind='LatentTapPacket' "
        "ORDER BY rowid DESC LIMIT ?",
        (max_events * 4,),
    )
    seen_events = set()
    seen_sources = set()
    pairs = []
    skipped = {"duplicate_event": 0, "duplicate_source": 0, "invalid_or_incomplete": 0}
    for row in rows:
        event_id = row["event_id"]
        if event_id in seen_events:
            skipped["duplicate_event"] += 1
            continue
        seen_events.add(event_id)
        try:
            pair = _pair_for_event(runtime, event_id, direction, require_outcome=True)
        except (ValueError, OSError, KeyError, TypeError):
            pair = None
        if pair is None:
            skipped["invalid_or_incomplete"] += 1
            continue
        if pair["source_hash"] in seen_sources:
            skipped["duplicate_source"] += 1
            continue
        seen_sources.add(pair["source_hash"])
        pairs.append(pair)
        if len(pairs) >= max_events:
            break
    return pairs, skipped


def _batch(pairs):
    if not pairs:
        raise ValueError("empty paired native-tap dataset")
    d = int(pairs[0]["H"].shape[1])
    h = int(pairs[0]["Xr"].shape[0])
    if any(p["H"].shape[1] != d or p["Xr"].shape[0] != h for p in pairs):
        raise ValueError("native tap dimensions changed within the paired dataset")
    width = min(MAX_TOKENS, max(int(p["H"].shape[0]) for p in pairs))
    H = np.zeros((len(pairs), width, d), dtype=np.float32)
    mask = np.zeros((len(pairs), width), dtype=np.float32)
    Xr = np.zeros((len(pairs), h), dtype=np.float32)
    y = np.zeros(len(pairs), dtype=np.int64)
    for i, pair in enumerate(pairs):
        tokens = pair["H"][-width:]
        H[i, : len(tokens)] = tokens
        mask[i, : len(tokens)] = 1.0
        Xr[i] = pair["Xr"]
        y[i] = int(pair["label"])
    return H, mask, Xr, y


def _accuracy(logits, labels):
    return [int(int(np.argmax(row)) == int(label)) for row, label in zip(logits, labels)]


def _split(pairs, direction):
    sources = sorted({p["source_hash"] for p in pairs})
    if len(sources) < 8:
        return None, None
    ordered = sorted(
        sources,
        key=lambda value: hashlib.sha256((direction + ":" + value).encode()).hexdigest(),
    )
    holdout_count = max(MIN_HOLDOUT, int(math.ceil(len(ordered) * 0.2)))
    holdout_sources = set(ordered[-holdout_count:])
    train = [p for p in pairs if p["source_hash"] not in holdout_sources]
    holdout = [p for p in pairs if p["source_hash"] in holdout_sources]
    if len(train) < MIN_TRAIN or len(holdout) < MIN_HOLDOUT:
        return None, None
    if set(p["source_hash"] for p in train) & set(p["source_hash"] for p in holdout):
        raise ValueError("source-disjoint split invariant failed")
    if set(p["label"] for p in train) != {0, 1} or set(p["label"] for p in holdout) != {0, 1}:
        return None, None
    return train, holdout


def _candidate_root(runtime):
    root = Path(runtime.home) / "b3"
    if root.is_symlink():
        raise ValueError("B3 directory cannot be a symlink")
    candidates = root / "candidates"
    if candidates.is_symlink():
        raise ValueError("B3 candidate directory cannot be a symlink")
    candidates.mkdir(parents=True, exist_ok=True)
    return candidates


def train_candidate(runtime, direction, max_events=MAX_EVENTS):
    """Train a versioned B3 adapter candidate from real paired taps and C4 labels.

    Only adapter parameters are updated. The candidate is never activated and
    the full L1 gate remains fail-closed until all canonical controls exist.
    """
    sender_role, receiver_role = _roles(direction)
    pairs, skipped = collect_pairs(runtime, direction, max_events=max_events)
    if len(pairs) < MIN_SAMPLES:
        return {
            "status": "INSUFFICIENT_PAIRED_NATIVE_TAPS",
            "direction": direction,
            "pairs": len(pairs),
            "required": MIN_SAMPLES,
            "skipped": skipped,
            "next": "Run :tap B1_DETAIL and :tap B2_GIST on more distinct completed turns",
            "adapter_weight_updates": 0,
            "body_weight_updates": 0,
            "latent_authority": 0,
        }
    train, holdout = _split(pairs, direction)
    if train is None:
        return {
            "status": "SOURCE_DISJOINT_OR_CLASS_BALANCE_INSUFFICIENT",
            "direction": direction,
            "pairs": len(pairs),
            "unique_sources": len({p["source_hash"] for p in pairs}),
            "skipped": skipped,
            "adapter_weight_updates": 0,
            "body_weight_updates": 0,
            "latent_authority": 0,
        }

    Htr, Mtr, Xtr, ytr = _batch(train)
    Hho, Mho, Xho, yho = _batch(holdout)
    d, h = int(Htr.shape[2]), int(Xtr.shape[1])
    budget = b3bridge.budget(d, K, R, h, classes=2, slots_buffer=MAX_TOKENS)
    if not budget["age0_ok"]:
        return {
            "status": "B3_AGE0_ADAPTER_BUDGET_EXCEEDED",
            "direction": direction,
            "budget": budget,
            "adapter_weight_updates": 0,
            "body_weight_updates": 0,
            "latent_authority": 0,
        }

    sender_revision = runtime.models.revision(sender_role)
    receiver_revision = runtime.models.revision(receiver_role)
    bridge = b3bridge.Bridge(
        d, K=K, r=R, h=h, classes=2, seed=0, direction=direction
    )
    before_digest = bridge.digest()
    bridge.fit_head(Xtr, ytr)
    history = bridge.fit(
        Htr, Mtr, Xtr, ytr, epochs=EPOCHS, batch=min(BATCH, len(ytr)), lr=3e-3, seed=0
    )
    bridge.calibrate(Htr, Mtr)
    after_digest = bridge.digest()
    if before_digest == after_digest:
        return {
            "status": "NO_ADAPTER_WEIGHT_CHANGE",
            "direction": direction,
            "adapter_weight_updates": 0,
            "body_weight_updates": 0,
            "latent_authority": 0,
        }

    Zho = b3bridge.to_bf16(bridge.encode(Hho, Mho))
    base_logits = bridge.receive(Zho, Xho, gate_open=False)
    candidate_logits = bridge.receive(Zho, Xho, gate_open=True)
    base_correct = _accuracy(base_logits, yho)
    candidate_correct = _accuracy(candidate_logits, yho)
    ood_rate = float(np.mean(bridge.ood(Zho) > bridge.cal["ood_tau"]))
    candidate_id = uid("b3")
    base_path = _candidate_root(runtime) / candidate_id
    evidence = {
        "label": "C4_FINAL_COALITION_MEMBERSHIP",
        "train_count": len(train),
        "holdout_count": len(holdout),
        "unique_source_count": len({p["source_hash"] for p in pairs}),
        "train_source_hashes": sorted({p["source_hash"] for p in train}),
        "holdout_source_hashes": sorted({p["source_hash"] for p in holdout}),
        "source_disjoint": not bool(
            {p["source_hash"] for p in train} & {p["source_hash"] for p in holdout}
        ),
        "event_id_hashes": sorted(
            hashlib.sha256(p["event_id"].encode()).hexdigest() for p in pairs
        ),
        "sender_role": sender_role,
        "receiver_role": receiver_role,
        "sender_revision": sender_revision,
        "receiver_revision": receiver_revision,
        "sender_tap_ids": sorted({p["sender_tap_id"] for p in pairs}),
        "receiver_tap_ids": sorted({p["receiver_tap_id"] for p in pairs}),
        "runner_revision": RUNNER_REVISION,
        "receiver_pooling": "last_token",
        "train_label_counts": {str(v): int(np.sum(ytr == v)) for v in (0, 1)},
        "holdout_label_counts": {str(v): int(np.sum(yho == v)) for v in (0, 1)},
        "training_seed": 0,
        "epochs": EPOCHS,
        "learning_rate": 3e-3,
        "first_loss": history[0] if history else None,
        "last_loss": history[-1] if history else None,
        "initial_adapter_digest": before_digest,
        "trained_adapter_digest": after_digest,
        "skipped": skipped,
        "authority": "EXPERIMENTAL_ADAPTER_ONLY",
        "base_model_weights_changed": False,
    }
    holdout_metrics = {
        "no_message_accuracy": float(np.mean(base_correct)),
        "latent_candidate_accuracy": float(np.mean(candidate_correct)),
        "candidate_delta_l2": float(np.linalg.norm(candidate_logits - base_logits)),
        "receiver_ood_rate": ood_rate,
        "no_message_correct": base_correct,
        "latent_candidate_correct": candidate_correct,
    }
    bridge.save(
        base_path,
        sender_revision,
        receiver_revision,
        extra={
            "candidate_id": candidate_id,
            "training_evidence": evidence,
            "holdout_metrics": holdout_metrics,
            "l1_gate": None,
            "claim_limit": (
                "Native tap-backed adapter candidate only; no active receiver effect, "
                "no B1/B2 weight change, no LATENT authority."
            ),
        },
    )
    loaded = b3bridge.Bridge.load(base_path, sender_revision, receiver_revision)
    reloaded_logits = loaded.logits(Hho, Mho, Xho)
    reload_identical = bool(np.array_equal(reloaded_logits, bridge.logits(Hho, Mho, Xho)))
    partial_gate = b3bridge.l1_gate(
        {
            "acc": {
                "NO_MESSAGE": base_correct,
                "LATENT": candidate_correct,
            },
            "bytes": {
                "NO_MESSAGE": 0,
                "LATENT": int(K * R * 2),
            },
            "seed_ids": {
                "NO_MESSAGE": [hashlib.sha256(p["event_id"].encode()).hexdigest()[:16] for p in holdout],
                "LATENT": [hashlib.sha256(p["event_id"].encode()).hexdigest()[:16] for p in holdout],
            },
            "role_drop": None,
            "ood_rate": ood_rate,
            "reload_identical": reload_identical,
        }
    )
    manifest_path = base_path.with_suffix(".json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["reload_identical"] = reload_identical
    manifest["l1_gate"] = partial_gate
    manifest["holdout_metrics"]["reload_identical"] = reload_identical
    manifest["candidate_files"] = {
        "weights_sha256": hashlib.sha256(base_path.with_suffix(".npz").read_bytes()).hexdigest(),
    }
    atomic_write(manifest_path, dumps(manifest))
    checked = b3bridge.Bridge.load(base_path, sender_revision, receiver_revision)
    if checked.digest() != after_digest or not reload_identical:
        raise RuntimeError("B3 candidate restart/readback mismatch")

    return {
        "status": "CANDIDATE_SAVED_NOT_ACTIVATED",
        "direction": direction,
        "candidate_id": candidate_id,
        "candidate_digest": after_digest,
        "weights_file_sha256": manifest["candidate_files"]["weights_sha256"],
        "train_count": len(train),
        "holdout_count": len(holdout),
        "holdout_metrics": holdout_metrics,
        "l1_gate": {
            "verdict": partial_gate["verdict"],
            "missing_baselines": partial_gate["missing_baselines"],
            "invalid_evidence": partial_gate["invalid_evidence"],
        },
        "reload_identical": reload_identical,
        "adapter_weight_updates": len(bridge.p),
        "body_weight_updates": 0,
        "latent_authority": 0,
        "active_bridge_changed": False,
        "budget": budget,
        "claim_limit": "Adapter candidate only; no live receiver effect or Redmi proof.",
    }


def probe_candidate(runtime, direction, candidate_id, event_id):
    """Counterfactual readout probe; never changes a live receiver or output."""
    sender_role, receiver_role = _roles(direction)
    if not re.fullmatch(r"b3_[A-Za-z0-9_-]{8,64}", str(candidate_id)):
        raise ValueError("invalid B3 candidate id")
    root = _candidate_root(runtime).resolve(strict=True)
    base_path = root / candidate_id
    manifest_path = base_path.with_suffix(".json")
    weights_path = base_path.with_suffix(".npz")
    if (not manifest_path.is_file() or not weights_path.is_file()
            or manifest_path.is_symlink() or weights_path.is_symlink()
            or manifest_path.resolve().parent != root or weights_path.resolve().parent != root):
        raise ValueError("B3 candidate path is missing or escapes candidate directory")
    pair = _pair_for_event(runtime, event_id, direction, require_outcome=True)
    if pair is None:
        return {
            "status": "NO_MATCHING_PAIRED_NATIVE_TAPS_AND_C4_OUTCOME",
            "direction": direction,
            "event_id": event_id,
            "applied": False,
            "latent_authority": 0,
        }
    bridge = b3bridge.Bridge.load(
        base_path,
        runtime.models.revision(sender_role),
        runtime.models.revision(receiver_role),
    )
    manifest = json.loads(base_path.with_suffix(".json").read_text(encoding="utf-8"))
    if manifest.get("direction") != direction or manifest.get("candidate_id") != candidate_id:
        raise ValueError("B3 candidate direction/id mismatch")
    H, mask, Xr, labels = _batch([pair])
    Z = b3bridge.to_bf16(bridge.encode(H, mask))
    base_logits = bridge.receive(Z, Xr, gate_open=False)
    candidate_logits = bridge.receive(Z, Xr, gate_open=True)
    delta = candidate_logits - base_logits
    ood_score = float(bridge.ood(Z)[0])
    ood_tau = float(bridge.cal["ood_tau"]) if bridge.cal is not None else None
    l1_pass = b3bridge.l1_report_valid(manifest.get("l1_gate"))
    probe_id = uid("b3p")
    report = {
        "schema": "v14.b3.readout-counterfactual/1",
        "probe_id": probe_id,
        "candidate_id": candidate_id,
        "direction": direction,
        "event_id_hash": hashlib.sha256(event_id.encode()).hexdigest(),
        "source_hash": pair["source_hash"],
        "sender_tap_packet_id": pair["sender_tap_packet_id"],
        "receiver_tap_packet_id": pair["receiver_tap_packet_id"],
        "sender_revision": pair["sender_revision"],
        "receiver_revision": pair["receiver_revision"],
        "receiver_pooling": "last_token",
        "base_logits": [float(x) for x in base_logits[0]],
        "candidate_logits": [float(x) for x in candidate_logits[0]],
        "candidate_delta_l2": float(np.linalg.norm(delta)),
        "ood_score": ood_score,
        "ood_tau": ood_tau,
        "bridge_gate_probability": bridge.gate(),
        "l1_gate_pass": bool(l1_pass),
        "c4_selected_receiver_offer": int(pair["label"]),
        "base_correct": bool(int(np.argmax(base_logits[0])) == int(pair["label"])),
        "candidate_correct": bool(int(np.argmax(candidate_logits[0])) == int(pair["label"])),
        "status": "COUNTERFACTUAL_READOUT_ONLY",
        "applied": False,
        "receiver_effect_proven": False,
        "latent_authority": 0,
        "body_learning_authority": 0,
        "semantic_truth_authority": False,
        "hardware_proof_id": None,
        "claim_limit": "Numeric readout counterfactual only; no live B2/B1 generation effect.",
    }
    probes = Path(runtime.home) / "b3" / "probes"
    if probes.is_symlink():
        raise ValueError("B3 probe directory cannot be a symlink")
    probes.mkdir(parents=True, exist_ok=True)
    atomic_write(probes / (probe_id + ".json"), dumps(report))
    return report


def list_candidates(runtime, direction=None, limit=20):
    if direction is not None:
        _roles(direction)
    root = Path(runtime.home) / "b3" / "candidates"
    if not root.exists():
        return {"candidates": [], "count": 0}
    if root.is_symlink():
        raise ValueError("B3 candidate directory cannot be a symlink")
    candidates = []
    for path in sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        if path.is_symlink():
            continue
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
        if direction is not None and manifest.get("direction") != direction:
            continue
        candidates.append(
            {
                "candidate_id": manifest.get("candidate_id"),
                "direction": manifest.get("direction"),
                "created_wall_time": manifest.get("created_wall_time"),
                "train_count": (manifest.get("training_evidence") or {}).get("train_count"),
                "holdout_count": (manifest.get("training_evidence") or {}).get("holdout_count"),
                "l1_verdict": (manifest.get("l1_gate") or {}).get("verdict"),
                "reload_identical": manifest.get("reload_identical"),
                "sender_revision": manifest.get("sender_revision"),
                "receiver_revision": manifest.get("receiver_revision"),
            }
        )
        if len(candidates) >= limit:
            break
    return {"candidates": candidates, "count": len(candidates), "active_bridge_changed": False}


def status(runtime):
    candidates = list_candidates(runtime)
    probes_root = Path(runtime.home) / "b3" / "probes"
    last_probe = None
    if probes_root.exists() and not probes_root.is_symlink():
        paths = sorted(probes_root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if paths and not paths[0].is_symlink():
            try:
                last_probe = json.loads(paths[0].read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                last_probe = {"status": "UNREADABLE"}
    return {
        "candidate_count": candidates["count"],
        "candidates": candidates["candidates"],
        "last_probe": last_probe,
        "active_bridge_authority": 0,
        "claim_limit": (
            "Training uses source-disjoint native tap pairs and C4 coalition labels. "
            "Candidates are never activated; probe is counterfactual readout only."
        ),
    }
