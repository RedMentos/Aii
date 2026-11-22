"""Source-bound T8 supervision for the B1/B2 paired-native receiver bridge.

The WorldJEPA Store consumer remains the persistent world predictor/EMA learner.
This additive bridge binds its already-verified T8 ActionOutcome receipts to
persisted B3PairedTapPacket records, then asks the separate B3 L1 trainer for
non-promoted receiver-adapter candidates. It never derives labels from text,
changes a foundation model, or grants latent-injection authority.

The paired-tap producer/trainer is optional until the Core B3 stack is present.
Without it this module fails closed with B3_PAIR_TRAINER_UNAVAILABLE.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
from pathlib import Path

from . import world_model
from .world_jepa_store_authority import verify_committed_transitions

REVISION = "v14-world-jepa-b3-t8-supervision-v1"
PAIR_KIND = "B3PairedTapPacket"
PAIR_SCHEMA = "v13.b3-paired-native-taps/3"
ROLES = ("B1_DETAIL", "B2_GIST")
OBSERVED_STATUSES = {"FINAL", "FAILED", "ERROR", "DEADLINE", "REJECTED"}
LABEL_SOURCE = "VERIFIED_T8_ACTION_OUTCOME_STATUS_V1"
TASK_ID = "t8_outcome_success_v1"
MIN_PAIRS = 64
MAX_PAIRS = 256
MAX_EPOCHS = 10
MAX_HEAD_STEPS = 200
STATE_KEY = "v14.world_jepa.b3_t8_supervision"
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def _mapping(row):
    if type(row) is dict:
        return row
    try:
        return {key: row[key] for key in row.keys()}
    except Exception as exc:
        raise ValueError("invalid Store row") from exc


def _object(value):
    if type(value) is dict:
        return value
    if type(value) is not str:
        raise ValueError("invalid packet payload")
    result = json.loads(value)
    if type(result) is not dict:
        raise ValueError("packet payload must be an object")
    return result


def _source_key(source):
    if type(source) is not dict:
        raise ValueError("missing SourceRef")
    source_id = source.get("source_id")
    digest = source.get("sha256")
    start, end = source.get("char_start"), source.get("char_end")
    modality = source.get("modality")
    if (type(source_id) is not str or not source_id or len(source_id) > 256
            or type(digest) is not str or not _HEX64.fullmatch(digest)
            or type(start) is not int or type(end) is not int
            or not 0 <= start < end
            or type(modality) is not str or not modality):
        raise ValueError("invalid SourceRef identity/span")
    return source_id, digest, start, end, modality


def _validate_pair(pair, stored_id):
    if (type(pair) is not dict or type(stored_id) is not str or not stored_id
            or pair.get("packet_id") != stored_id):
        raise ValueError("B3 pair is not its stored immutable packet")
    if pair.get("packet_schema") != PAIR_SCHEMA or pair.get("sender_roles") != list(ROLES):
        raise ValueError("B3 pair schema/roles mismatch")
    event_id = pair.get("event_id")
    generation = pair.get("brain_generation_id")
    if (type(event_id) is not str or not event_id or len(event_id) > 128
            or type(generation) is not str or not generation or len(generation) > 128):
        raise ValueError("B3 pair event/generation binding missing")
    source = pair.get("source_ref")
    source_key = _source_key(source)
    provenance = pair.get("provenance")
    if type(provenance) is not list or provenance != [source]:
        raise ValueError("B3 pair source provenance mismatch")
    if (pair.get("injection_authority") != 0 or pair.get("learning_authority") != 0
            or pair.get("token_alignment") != "NOT_ASSUMED_DIFFERENT_NATIVE_TOKENIZERS"
            or pair.get("receiver_pooling") !=
            "B2_ADAPTIVE_GIST_SLOTS;B1_SOURCE_ALIGNED_FINE_NATIVE_SLOTS"):
        raise ValueError("B3 pair authority/semantics mismatch")

    for field in ("tap_packet_ids", "tap_ids", "model_revisions",
                  "feature_bindings", "token_counts", "dimensions"):
        value = pair.get(field)
        if type(value) is not dict or set(value) != set(ROLES):
            raise ValueError("B3 pair " + field + " mismatch")
    for role in ROLES:
        for field in ("tap_packet_ids", "tap_ids", "model_revisions"):
            value = pair[field][role]
            if type(value) is not str or not value:
                raise ValueError("B3 pair " + field + " identity")
        for field in ("token_counts", "dimensions"):
            value = pair[field][role]
            if type(value) is not int or value < 1:
                raise ValueError("B3 pair " + field + " geometry")
        binding = pair["feature_bindings"][role]
        if (type(binding) is not dict
                or type(binding.get("feature_path")) is not str
                or not binding["feature_path"]
                or type(binding.get("feature_sha256")) is not str
                or not _HEX64.fullmatch(binding["feature_sha256"])
                or type(binding.get("shape")) is not list
                or len(binding["shape"]) != 2
                or any(type(value) is not int or value < 1 for value in binding["shape"])
                or binding["shape"] != [
                    pair["token_counts"][role], pair["dimensions"][role]
                ]):
            raise ValueError("B3 pair feature binding")
    if any(pair["token_counts"][role] > 64 for role in ROLES):
        raise ValueError("B3 pair native tap exceeds 64-token bound")

    gist = pair.get("gist_readout")
    fine = pair.get("fine_readout")
    if (type(gist) is not dict or type(gist.get("plan")) is not dict
            or gist.get("tap_packet_id") != pair["tap_packet_ids"]["B2_GIST"]
            or type(fine) is not dict or type(fine.get("plan")) is not dict
            or fine.get("tap_packet_id") != pair["tap_packet_ids"]["B1_DETAIL"]):
        raise ValueError("B3 pair readout binding")
    if (gist["plan"].get("tap_id") != pair["tap_ids"]["B2_GIST"]
            or gist["plan"].get("lossless") is not True
            or gist["plan"].get("receiver_injection_authority") != 0
            or fine["plan"].get("tap_id") != pair["tap_ids"]["B1_DETAIL"]
            or fine["plan"].get("lossless") is not True
            or fine["plan"].get("receiver_injection_authority") != 0
            or fine["plan"].get("body_learning_authority") != 0):
        raise ValueError("B3 pair readout authority/lineage")
    slots = gist["plan"].get("max_slots")
    if type(slots) is not int or slots < 1:
        raise ValueError("B3 pair Gist slot budget")
    return event_id, generation, source_key


def _receipt_key(receipt):
    return (
        receipt.event_id,
        receipt.generation_id,
        _source_key(receipt.source_ref),
    )


def _cohort_digest(pair_packets, labels, label_provenance, direction,
                   seeds, epochs, head_steps, split_seed):
    identity = {
        "revision": REVISION,
        "direction": direction,
        "body_pair_ids": [pair["body_pair_id"] for pair in pair_packets],
        "source_sha256": [pair["source_ref"]["sha256"] for pair in pair_packets],
        "labels": list(labels),
        "label_provenance": list(label_provenance),
        "model_revisions": pair_packets[0]["model_revisions"],
        "seeds": list(seeds),
        "epochs": epochs,
        "head_steps": head_steps,
        "split_seed": split_seed,
    }
    raw = json.dumps(identity, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def collect_t8_outcome_labels(store, *, limit=MAX_PAIRS):
    """Join stored paired native taps to exactly matching verified T8 outcomes.

    Labels are 1 for a committed FINAL outcome and 0 for an observed terminal
    failure. Event, generation, source ID, source digest, exact span and modality
    must all match. Censored or ambiguous outcomes are not training labels.
    """
    if type(limit) is not int or not 1 <= limit <= MAX_PAIRS:
        raise ValueError("pair limit outside bounded range")
    try:
        raw_pairs = store.rows(
            "SELECT id,payload FROM packets WHERE kind=? ORDER BY rowid DESC LIMIT ?",
            (PAIR_KIND, limit),
        )
        if type(raw_pairs) is not list:
            raise ValueError("paired packet query did not return a list")
        if not raw_pairs:
            return {
                "status": "NO_PAIRED_TAPS",
                "verified_transition_count": 0,
                "rejected_transition_count": 0,
                "pair_packet_count": 0,
                "pair_count": 0,
                "unmatched_pair_count": 0,
                "ambiguous_pair_count": 0,
                "invalid_pair_count": 0,
                "conflicting_source_count": 0,
                "label_counts": {"FINAL": 0, "NONFINAL_OBSERVED": 0},
                "source_group_counts": {"FINAL": 0, "NONFINAL_OBSERVED": 0},
                "cohort_sha256": None,
                "model_revisions": None,
                "pair_packets": [],
                "labels": [],
                "label_provenance": [],
            }
        verified, rejected_t8 = verify_committed_transitions(
            store, limit=world_model.MAX_ROWS
        )
    except (ValueError, TypeError, KeyError, OSError, OverflowError,
            ArithmeticError, AttributeError) as exc:
        return {
            "status": "T8_OR_PAIR_STORE_UNAVAILABLE",
            "error": type(exc).__name__,
            "pair_count": 0,
            "pair_packets": [],
            "labels": [],
            "label_provenance": [],
        }

    by_key = {}
    for receipt in verified:
        try:
            if receipt.status not in OBSERVED_STATUSES:
                continue
            by_key.setdefault(_receipt_key(receipt), []).append(receipt)
        except (ValueError, TypeError, KeyError, AttributeError):
            continue

    matched = []
    invalid_pairs = unmatched = ambiguous = 0
    seen_pair_ids, seen_spans = set(), set()
    for raw_row in raw_pairs:
        try:
            row = _mapping(raw_row)
            stored_id = row.get("id")
            pair = _object(row.get("payload"))
            event_id, generation, source_key = _validate_pair(pair, stored_id)
            body_pair_id = pair.get("body_pair_id")
            if (type(body_pair_id) is not str or not body_pair_id
                    or len(body_pair_id) > 128 or body_pair_id in seen_pair_ids
                    or source_key in seen_spans):
                raise ValueError("duplicate/invalid B3 pair identity")
            seen_pair_ids.add(body_pair_id)
            seen_spans.add(source_key)
            receipts = by_key.get((event_id, generation, source_key), [])
            if not receipts:
                unmatched += 1
                continue
            if len(receipts) != 1:
                ambiguous += 1
                continue
            receipt = receipts[0]
            evidence_ref = receipt.evidence_ref
            if type(evidence_ref) is not str or not evidence_ref.startswith("T8:"):
                raise ValueError("T8 evidence reference missing")
            label = 1 if receipt.status == "FINAL" else 0
            matched.append({
                "pair": pair,
                "label": label,
                "evidence_ref": evidence_ref,
                "source_key": source_key,
            })
        except (ValueError, TypeError, KeyError, OSError, OverflowError,
                AttributeError, json.JSONDecodeError):
            invalid_pairs += 1

    # A source digest is one indivisible holdout group. If one source has
    # conflicting outcomes, discard the entire source instead of leaking it.
    source_labels = {}
    for item in matched:
        digest = item["source_key"][1]
        source_labels.setdefault(digest, set()).add(item["label"])
    conflicting_sources = {
        digest for digest, values in source_labels.items() if len(values) != 1
    }
    matched = [
        item for item in matched
        if item["source_key"][1] not in conflicting_sources
    ]
    matched.sort(key=lambda item: item["pair"]["body_pair_id"])

    pair_packets = [item["pair"] for item in matched]
    labels = [item["label"] for item in matched]
    label_provenance = [item["evidence_ref"] for item in matched]
    label_counts = {
        "FINAL": sum(label == 1 for label in labels),
        "NONFINAL_OBSERVED": sum(label == 0 for label in labels),
    }
    source_groups = {"FINAL": set(), "NONFINAL_OBSERVED": set()}
    for item in matched:
        source_groups["FINAL" if item["label"] == 1 else "NONFINAL_OBSERVED"].add(
            item["source_key"][1]
        )
    source_group_counts = {key: len(value) for key, value in source_groups.items()}

    signatures = {
        (
            json.dumps(pair["model_revisions"], sort_keys=True),
            json.dumps(pair["dimensions"], sort_keys=True),
            pair["gist_readout"]["plan"]["max_slots"],
        )
        for pair in pair_packets
    }
    cohort_sha = (
        hashlib.sha256(
            json.dumps(
                {
                    "pairs": [pair["body_pair_id"] for pair in pair_packets],
                    "labels": labels,
                    "provenance": label_provenance,
                },
                sort_keys=True, separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        if pair_packets else None
    )

    if len(signatures) > 1:
        status = "INCOMPATIBLE_PAIR_BATCH"
    elif len(pair_packets) < MIN_PAIRS:
        status = "INSUFFICIENT_VERIFIED_PAIRS"
    elif len(set(labels)) < 2:
        status = "INSUFFICIENT_LABEL_DIVERSITY"
    elif any(count < 4 for count in source_group_counts.values()):
        status = "INSUFFICIENT_SOURCE_GROUPS"
    else:
        status = "READY"

    return {
        "status": status,
        "verified_transition_count": len(verified),
        "rejected_transition_count": rejected_t8,
        "pair_packet_count": len(raw_pairs),
        "pair_count": len(pair_packets),
        "unmatched_pair_count": unmatched,
        "ambiguous_pair_count": ambiguous,
        "invalid_pair_count": invalid_pairs,
        "conflicting_source_count": len(conflicting_sources),
        "label_counts": label_counts,
        "source_group_counts": source_group_counts,
        "cohort_sha256": cohort_sha,
        "model_revisions": pair_packets[0]["model_revisions"] if pair_packets else None,
        "pair_packets": pair_packets,
        "labels": labels,
        "label_provenance": label_provenance,
    }


def _safe_shadow_path(home, relative):
    root = Path(home).resolve()
    shadow_root = (root / "b3" / "shadow").resolve()
    if not shadow_root.is_relative_to(root):
        raise ValueError("B3 shadow directory escaped the local home")
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("B3 candidate path is not a safe relative path")
    path = root / rel
    if path.is_symlink() or not path.resolve().is_relative_to(shadow_root):
        raise ValueError("B3 candidate path escaped the shadow directory")
    return path


def _parameter_delta(report, home, direction, bridge_module):
    """Read back each candidate and compare numeric adapter weights to its seed init."""
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("NumPy unavailable for parameter readback") from exc
    results = []
    for seed_report in report.get("seed_reports", []):
        seed = seed_report.get("seed")
        weight_rel = seed_report.get("candidate_weights")
        if type(seed) is not int or type(weight_rel) is not str or not weight_rel.endswith(".npz"):
            raise ValueError("candidate weight receipt malformed")
        candidate_path = _safe_shadow_path(home, weight_rel)
        manifest_path = candidate_path.with_suffix(".json")
        if not candidate_path.is_file() or manifest_path.is_symlink() or not manifest_path.is_file():
            raise ValueError("candidate checkpoint files missing")
        prefix = candidate_path.with_suffix("")
        candidate = bridge_module.Bridge.load(
            prefix,
            sender_revision=report["sender_revision"],
            receiver_revision=report["receiver_revision"],
        )
        manifest = getattr(candidate, "manifest", {})
        manifest_sha = seed_report.get("manifest_sha256")
        if (type(manifest_sha) is not str or not _HEX64.fullmatch(manifest_sha)
                or manifest.get("sha256") != manifest_sha
                or manifest.get("direction") != direction
                or manifest.get("latent_authority") != 0
                or manifest.get("receiver_injection_authority") != 0
                or manifest.get("body_learning_authority") != 0
                or "NOT_PROMOTED" not in str(manifest.get("status", ""))):
            raise ValueError("candidate manifest authority/readback mismatch")
        baseline = bridge_module.Bridge(
            d=candidate.d, K=candidate.K, r=candidate.r, h=candidate.h,
            classes=candidate.classes, seed=seed, direction=direction,
            aux=candidate.aux,
        )
        if set(candidate.p) != set(baseline.p):
            raise ValueError("candidate parameter groups changed")
        groups = {}
        for key in sorted(baseline.p):
            delta = np.asarray(candidate.p[key]) - np.asarray(baseline.p[key])
            if delta.shape != np.asarray(baseline.p[key]).shape or not np.isfinite(delta).all():
                raise ValueError("candidate parameter delta invalid")
            groups[key] = float(np.linalg.norm(delta))
        for key in ("in_mu", "in_sd"):
            delta = np.asarray(getattr(candidate, key)) - np.asarray(getattr(baseline, key))
            if delta.shape != np.asarray(getattr(baseline, key)).shape or not np.isfinite(delta).all():
                raise ValueError("candidate normalization-buffer delta invalid")
            groups[key] = float(np.linalg.norm(delta))
        total = math.sqrt(sum(value * value for value in groups.values()))
        if not math.isfinite(total) or total <= 0:
            raise ValueError("candidate contains no measurable numeric parameter update")
        if seed_report.get("reload_identical") is not True:
            raise ValueError("candidate checkpoint reload was not bit-identical")
        head = getattr(candidate, "head", None)
        head_l2 = None
        if head is not None:
            head_l2 = math.sqrt(sum(float(np.linalg.norm(np.asarray(value))) ** 2 for value in head))
        results.append({
            "seed": seed,
            "parameter_delta_l2": total,
            "parameter_delta_by_group": groups,
            "receiver_no_message_head_l2": head_l2,
            "manifest_sha256": manifest_sha,
            "reload_identical": True,
        })
    if len(results) < 2 or len({item["seed"] for item in results}) != len(results):
        raise ValueError("trainer did not return two distinct seed checkpoint receipts")
    return results


def _train_direction(store, cognition, home, cohort, direction, *,
                     seeds, epochs, head_steps, split_seed):
    from . import b3bridge, b3train

    state_key = STATE_KEY + ":" + direction
    default_state = {
        "revision": REVISION,
        "last_cohort_sha256": None,
        "last_report_path": None,
        "last_manifest_sha256": None,
        "previous": None,
    }
    state, version = store.state(state_key, default_state)
    if type(state) is not dict or state.get("revision") != REVISION:
        return {"status": "STATE_INCOMPATIBLE", "direction": direction}
    cohort_sha = _cohort_digest(
        cohort["pair_packets"], cohort["labels"], cohort["label_provenance"],
        direction, seeds, epochs, head_steps, split_seed,
    )
    if state.get("last_cohort_sha256") == cohort_sha:
        return {
            "status": "ALREADY_TRAINED",
            "direction": direction,
            "cohort_sha256": cohort_sha,
            "report_path": state.get("last_report_path"),
            "manifest_sha256": state.get("last_manifest_sha256"),
        }

    report = b3train.train_l1_shadow(
        cognition,
        cohort["pair_packets"],
        cohort["labels"],
        cohort["label_provenance"],
        TASK_ID,
        LABEL_SOURCE,
        direction=direction,
        seeds=tuple(seeds),
        epochs=epochs,
        head_steps=head_steps,
        split_seed=split_seed,
        l0_evidence=None,
    )
    if type(report) is not dict:
        raise ValueError("B3 trainer returned a non-object report")
    report_path = report.get("report_path")
    if type(report_path) is not str or not report_path:
        raise ValueError("trainer report path missing")
    report_file = _safe_shadow_path(home, report_path)
    if report_file.is_symlink() or not report_file.is_file():
        raise ValueError("trainer report file missing or linked")
    persisted_report = json.loads(report_file.read_text(encoding="utf-8"))
    if persisted_report != report:
        raise ValueError("trainer report readback mismatch")
    if (report.get("status") != "L1_SHADOW_CANDIDATES_SAVED_NOT_PROMOTED"
            or report.get("l1_utility_gate") !=
            "NOT_RUN_MISSING_L0_CHANNEL_BASELINES_AND_ROLE_RETENTION"
            or report.get("latent_authority") != 0
            or report.get("receiver_injection_authority") != 0
            or report.get("body_learning_authority") != 0):
        raise ValueError("B3 trainer returned an unexpected promotion/authority state")

    deltas = _parameter_delta(report, home, direction, b3bridge)
    mean_delta = sum(item["parameter_delta_l2"] for item in deltas) / len(deltas)
    manifests = [item["manifest_sha256"] for item in deltas]
    previous = None
    if state.get("last_cohort_sha256"):
        previous = {
            "cohort_sha256": state.get("last_cohort_sha256"),
            "report_path": state.get("last_report_path"),
            "manifest_sha256": state.get("last_manifest_sha256"),
            "status": state.get("last_status"),
        }
    next_state = {
        "revision": REVISION,
        "last_cohort_sha256": cohort_sha,
        "last_report_path": report.get("report_path"),
        "last_manifest_sha256": manifests,
        "last_parameter_delta_l2": mean_delta,
        "last_parameter_delta_by_seed": deltas,
        "last_pair_count": cohort["pair_count"],
        "last_label_counts": cohort["label_counts"],
        "last_source_group_counts": cohort["source_group_counts"],
        "last_status": report["status"],
        "last_updated_wall": time.time(),
        "previous": previous,
    }
    store.set_state(state_key, next_state, expected=version)
    return {
        "status": report["status"],
        "direction": direction,
        "cohort_sha256": cohort_sha,
        "report_path": report.get("report_path"),
        "manifest_sha256": manifests,
        "parameter_delta_l2": mean_delta,
        "parameter_delta_by_seed": deltas,
        "pair_count": cohort["pair_count"],
        "label_counts": cohort["label_counts"],
        "source_group_counts": cohort["source_group_counts"],
        "l1_utility_gate": report["l1_utility_gate"],
        "latent_authority": 0,
        "receiver_injection_authority": 0,
        "body_learning_authority": 0,
    }


def train_l1_shadow_directions_from_t8(
    store, cognition, home=None, *,
    directions=("B1_TO_B2", "B2_TO_B1"),
    limit=MAX_PAIRS, seeds=(11, 17), epochs=1, head_steps=25,
    split_seed=20261122, cancel_check=None,
):
    """Run bounded bidirectional shadow receiver training from verified T8 labels.

    Both V14 learning permissions must already be enabled in the local Store.
    The candidates are saved separately per direction, remain NOT_PROMOTED, and
    require separate L0 channel baselines plus role-retention evidence before
    any L1 utility claim. This is not native receiver injection.
    """
    directions = tuple(directions)
    if (not directions or len(set(directions)) != len(directions)
            or any(direction not in {"B1_TO_B2", "B2_TO_B1"} for direction in directions)):
        return {"status": "INVALID_DIRECTION", "directions": {}}
    if (type(epochs) is not int or not 1 <= epochs <= MAX_EPOCHS
            or type(head_steps) is not int or not 1 <= head_steps <= MAX_HEAD_STEPS
            or type(split_seed) is not int
            or type(seeds) not in (tuple, list) or len(seeds) < 2
            or any(type(seed) is not int for seed in seeds)
            or len(set(seeds)) != len(seeds)):
        return {"status": "INVALID_TRAINING_BUDGET", "directions": {}}
    if cancel_check is not None and not callable(cancel_check):
        return {"status": "INVALID_CANCEL_CHECK", "directions": {}}

    from .world_jepa_runtime import permission_state
    gates = permission_state(store)
    if not gates["learning_enabled"]:
        return {
            "status": "OFF",
            "directions": {direction: {"status": "OFF"} for direction in directions},
        }
    if not gates["optimizer_permission"]:
        return {
            "status": "PENDING_OPTIMIZER_PERMISSION",
            "directions": {
                direction: {"status": "PENDING_OPTIMIZER_PERMISSION"}
                for direction in directions
            },
        }
    if cancel_check is not None and cancel_check():
        return {"status": "CANCELLED", "directions": {}}
    models = getattr(getattr(cognition, "r", None), "models", None)
    if cognition is None or not callable(getattr(models, "revision", None)):
        return {"status": "COGNITION_UNAVAILABLE", "directions": {}}

    cohort = collect_t8_outcome_labels(store, limit=limit)
    if cohort.get("status") != "READY":
        return {
            "status": cohort.get("status", "COHORT_UNAVAILABLE"),
            "cohort": {key: value for key, value in cohort.items()
                       if key not in {"pair_packets", "labels", "label_provenance"}},
            "directions": {
                direction: {"status": cohort.get("status", "COHORT_UNAVAILABLE")}
                for direction in directions
            },
        }
    current = {
        "B1_DETAIL": cognition.r.models.revision("B1_DETAIL"),
        "B2_GIST": cognition.r.models.revision("B2_GIST"),
    }
    if cohort.get("model_revisions") != current:
        return {"status": "STALE_MODEL_REVISION", "directions": {}}
    try:
        from . import b3pairs, b3train, b3bridge  # noqa: F401
    except ImportError:
        return {"status": "B3_PAIR_TRAINER_UNAVAILABLE", "directions": {}}

    root = Path(home if home is not None else cognition.r.home)
    results = {}
    for direction in directions:
        if cancel_check is not None and cancel_check():
            results[direction] = {"status": "CANCELLED", "direction": direction}
            break
        try:
            results[direction] = _train_direction(
                store, cognition, root, cohort, direction,
                seeds=tuple(seeds), epochs=epochs, head_steps=head_steps,
                split_seed=split_seed,
            )
        except (ValueError, TypeError, KeyError, OSError, OverflowError,
                ArithmeticError, AttributeError, RuntimeError) as exc:
            results[direction] = {
                "status": "TRAINING_REJECTED",
                "direction": direction,
                "error": type(exc).__name__,
                "pair_count": cohort["pair_count"],
            }
    statuses = {item.get("status") for item in results.values()}
    overall = "COMPLETED" if statuses and all(
        status in {"L1_SHADOW_CANDIDATES_SAVED_NOT_PROMOTED", "ALREADY_TRAINED"}
        for status in statuses
    ) else "PARTIAL"
    return {
        "status": overall,
        "cohort": {key: value for key, value in cohort.items()
                   if key not in {"pair_packets", "labels", "label_provenance"}},
        "directions": results,
    }


def train_l1_shadow_from_t8(store, cognition, home=None, *, direction="B1_TO_B2",
                            **kwargs):
    """Single-direction convenience wrapper for explicit research/diagnostic calls."""
    result = train_l1_shadow_directions_from_t8(
        store, cognition, home, directions=(direction,), **kwargs
    )
    return result.get("directions", {}).get(
        direction, {"status": result.get("status", "UNAVAILABLE")}
    ) | {"overall_status": result.get("status")}
