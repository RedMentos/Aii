"""Source-bound target-logprob evaluation for the diagnostic native B3 receiver.

Decode/input-effect metrics are not task utility. This module validates paired
teacher-forced target scores and negative controls; it never grants production,
training, persistence, or B3 authority.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
import hashlib
import json
import math
import random
import statistics
import struct

TASK_SCHEMA = "v14.native-receiver-task-score/1"
NATIVE_SCHEMA = "v14.native-receiver-target-score/1"
RESULT_SCHEMA = "v14.native-receiver-task-utility/1"
SCORE_METHOD = "TEACHER_FORCED_TARGET_LOGPROB_V1"
CONDITIONS = ("NO_MESSAGE", "EXACT_MESSAGE", "LATENT_CANDIDATE", "ZERO", "SHUFFLE", "REPEAT", "OOD", "ENTITY_SUBSTITUTION")
LATENT_CONDITIONS = frozenset({"LATENT_CANDIDATE", "ZERO", "SHUFFLE", "REPEAT", "OOD", "ENTITY_SUBSTITUTION"})
TASK_FAMILIES = frozenset({"ARITHMETIC", "ENTITY_RECALL", "RELATION", "MULTI_STEP", "OTHER"})
ROLES = frozenset({"B1_DETAIL", "B2_GIST", "C3_LANGUAGE"})
KV_SNAPSHOT_SCHEMA = "v14.native-receiver-kv-snapshot/1"
MAX_KV_SNAPSHOT_BYTES = 32 * 1024 * 1024


class NativeReceiverUtilityError(ValueError):
    pass


def _validate_duplicate_input_digests(group):
    """Identical receiver inputs must have identical teacher-forced token scores.

    A collapsed control is a valid negative result (for example, an identity
    adapter or a candidate that ignores an entity change). Rejecting every
    duplicate digest would discard that evidence. Different scores for the
    same input digest, target and native runner indicate a corrupt receipt.
    """
    by_digest = defaultdict(list)
    for condition in CONDITIONS:
        item = group[condition]
        by_digest[item["input_sha256"]].append(item)
    for items in by_digest.values():
        if len(items) < 2:
            continue
        reference = items[0]["native"].get("token_logprobs")
        if not isinstance(reference, list):
            raise NativeReceiverUtilityError("identical input receipt lacks tokenwise scores")
        for item in items[1:]:
            scores = item["native"].get("token_logprobs")
            if (not isinstance(scores, list) or len(scores) != len(reference)
                    or any(type(a) not in (int, float) or type(b) not in (int, float)
                           or not math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=1.0e-6)
                           for a, b in zip(reference, scores))):
                raise NativeReceiverUtilityError(
                    "identical input digest produced different target scores"
                )


def _kv_snapshot_signature(snapshot):
    """Stable one-layer K/V identity; deliberately excludes capture duration."""
    return (
        snapshot["schema"], snapshot["cache_kind"], snapshot["snapshot_scope"],
        snapshot["sequence_id"], snapshot["layer_id"], snapshot["attention_layer_count"],
        snapshot["position_count"], snapshot["position_sha256"],
        tuple(snapshot["k_shape"]), tuple(snapshot["v_shape"]),
        snapshot["k_type"], snapshot["v_type"], snapshot["k_sha256"],
        snapshot["v_sha256"], snapshot["combined_sha256"],
        snapshot["stable_read_sha256"], snapshot["bytes_read_per_snapshot"],
        snapshot["double_read_bytes_read"],
    )


def _validate_duplicate_kv_snapshots(group):
    """Check sampled K/V state determinism without treating it as task utility.

    Identical receiver input bytes, model, target and runner must produce the
    same sampled K/V state. Different inputs may legitimately collapse to the
    same state (a negative result), so that case is reported rather than
    rejected. The snapshot covers one attention layer, not LFM2 recurrent state.
    """
    snapshots = {
        condition: group[condition]["native"].get("kv_snapshot")
        for condition in CONDITIONS
    }
    present = [snapshot is not None for snapshot in snapshots.values()]
    if not any(present):
        return None
    if not all(present):
        raise NativeReceiverUtilityError("partial native K/V snapshot coverage in task group")

    geometry = None
    by_input = defaultdict(list)
    for condition in CONDITIONS:
        item = group[condition]
        snapshot = snapshots[condition]
        if not isinstance(snapshot, Mapping):
            raise NativeReceiverUtilityError("native K/V snapshot is malformed")
        if (snapshot.get("condition") != condition
                or snapshot.get("input_sha256") != item["input_sha256"]
                or snapshot.get("receiver_model_sha256") != item["receiver"]["model_sha256"]):
            raise NativeReceiverUtilityError("native K/V snapshot lost its condition/model/input binding")
        current_geometry = (
            snapshot["schema"], snapshot["cache_kind"], snapshot["snapshot_scope"],
            snapshot["sequence_id"], snapshot["layer_id"], snapshot["attention_layer_count"],
            tuple(snapshot["k_shape"]), tuple(snapshot["v_shape"]),
            snapshot["k_type"], snapshot["v_type"],
        )
        if geometry is None:
            geometry = current_geometry
        elif current_geometry != geometry:
            raise NativeReceiverUtilityError("native K/V snapshot geometry changed across conditions")
        by_input[item["input_sha256"]].append(snapshot)

    duplicate_groups_checked = 0
    for same_input in by_input.values():
        if len(same_input) < 2:
            continue
        duplicate_groups_checked += 1
        if len({_kv_snapshot_signature(snapshot) for snapshot in same_input}) != 1:
            raise NativeReceiverUtilityError(
                "identical receiver input digest produced different native K/V snapshots"
            )

    baseline_sha = snapshots["NO_MESSAGE"]["combined_sha256"]
    distinct = {
        condition: snapshots[condition]["combined_sha256"] != baseline_sha
        for condition in CONDITIONS
    }
    return {
        "status": "READ_ONLY_SAMPLE_ONLY",
        "snapshot_count": len(CONDITIONS),
        "scope": snapshots["NO_MESSAGE"]["snapshot_scope"],
        "sampled_layer_id": snapshots["NO_MESSAGE"]["layer_id"],
        "attention_layer_count": snapshots["NO_MESSAGE"]["attention_layer_count"],
        "_geometry": geometry,
        "distinct_from_no_message_by_condition": distinct,
        "candidate_differs_from_no_message": distinct["LATENT_CANDIDATE"],
        "candidate_differs_from_exact_message": (
            snapshots["LATENT_CANDIDATE"]["combined_sha256"]
            != snapshots["EXACT_MESSAGE"]["combined_sha256"]
        ),
        "duplicate_input_groups_checked": duplicate_groups_checked,
        "same_input_consistency_passed": True,
        "semantic_use_proven": False,
        "generated_answer_correctness_proven": False,
        "production_route": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
        "persisted": False,
    }


def _digest(value: Mapping) -> str:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise NativeReceiverUtilityError("receipt is not canonical JSON") from exc
    return hashlib.sha256(raw).hexdigest()


def _sha(value, name):
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise NativeReceiverUtilityError(name + " must be a lowercase SHA-256")
    return value


def _id(value, name):
    if type(value) is not str or not value or len(value) > 256:
        raise NativeReceiverUtilityError(name + " must be a non-empty bounded string")
    return value


def _source(value, name):
    if not isinstance(value, Mapping):
        raise NativeReceiverUtilityError(name + " must be an object")
    return {"source_id": _id(value.get("source_id"), name + ".source_id"),
            "sha256": _sha(value.get("sha256"), name + ".sha256")}


def validate_native_receiver_kv_snapshot(value, *, expected_rows=None,
        expected_condition=None, expected_model_sha256=None,
        expected_input_sha256=None, allow_sanitized=False):
    """Validate and minimize a read-only native K/V snapshot receipt.

    Raw K/V bytes are never accepted here. Only shape/type metadata and
    cryptographic digests cross the Runtime boundary. A sanitized receipt may
    be revalidated by downstream consumers with allow_sanitized=True.
    """
    if not isinstance(value, Mapping) or value.get("schema") != KV_SNAPSHOT_SCHEMA:
        raise NativeReceiverUtilityError("native K/V snapshot schema mismatch")
    if (value.get("status") != "READ_ONLY_SNAPSHOT"
            or value.get("cache_kind") != "LLAMA_MEMORY_HYBRID_ATTENTION"
            or value.get("snapshot_scope") != "ONE_ATTENTION_LAYER_ONE_SEQUENCE"):
        raise NativeReceiverUtilityError("native K/V snapshot scope/status is unsupported")
    if type(value.get("sequence_id")) is not int or value["sequence_id"] != 0:
        raise NativeReceiverUtilityError("native K/V snapshot sequence is unsupported")
    if type(value.get("layer_id")) is not int or value["layer_id"] < 0:
        raise NativeReceiverUtilityError("native K/V snapshot layer ID is invalid")
    if (type(value.get("attention_layer_count")) is not int
            or value["attention_layer_count"] < 1):
        raise NativeReceiverUtilityError("native K/V snapshot attention-layer count is invalid")

    raw_positions = value.get("position_ids")
    if isinstance(raw_positions, (list, tuple)):
        if not 1 <= len(raw_positions) <= 64 or any(
                type(position) is not int or position < 0 or position > 131071
                for position in raw_positions):
            raise NativeReceiverUtilityError("native K/V snapshot positions are invalid")
        positions = list(raw_positions)
        if positions != list(range(len(positions))):
            raise NativeReceiverUtilityError("native K/V snapshot positions are not contiguous prefill positions")
        position_count = len(positions)
        expected_position_sha = hashlib.sha256(
            struct.pack("<" + "i" * position_count, *positions)
        ).hexdigest()
        position_sha = _sha(value.get("position_sha256"), "kv_snapshot.position_sha256")
        if position_sha != expected_position_sha:
            raise NativeReceiverUtilityError("native K/V snapshot position digest mismatch")
    elif allow_sanitized:
        position_count = value.get("position_count")
        if type(position_count) is not int or not 1 <= position_count <= 64:
            raise NativeReceiverUtilityError("sanitized native K/V snapshot position count is invalid")
        position_sha = _sha(value.get("position_sha256"), "kv_snapshot.position_sha256")
    else:
        raise NativeReceiverUtilityError("native K/V snapshot position list is missing")
    if expected_rows is not None and (
            type(expected_rows) is not int or expected_rows != position_count):
        raise NativeReceiverUtilityError("native K/V snapshot position count differs from receiver context")
    if type(value.get("active_cell_count")) is not int or value["active_cell_count"] != position_count:
        raise NativeReceiverUtilityError("native K/V snapshot active-cell count differs from positions")

    shapes = {}
    for name in ("k_shape", "v_shape"):
        shape = value.get(name)
        if (not isinstance(shape, (list, tuple)) or len(shape) != 4
                or any(type(dim) is not int or dim < 1 for dim in shape)):
            raise NativeReceiverUtilityError("native K/V snapshot " + name + " is invalid")
        shapes[name] = list(shape)
    types = {}
    for name in ("k_type", "v_type"):
        types[name] = _id(value.get(name), "kv_snapshot." + name)
        if types[name] == "unknown":
            raise NativeReceiverUtilityError("native K/V snapshot tensor type is unknown")
    digests = {}
    for name in ("k_sha256", "v_sha256", "combined_sha256", "stable_read_sha256"):
        digests[name] = _sha(value.get(name), "kv_snapshot." + name)
    if digests["stable_read_sha256"] != digests["combined_sha256"]:
        raise NativeReceiverUtilityError("native K/V snapshot stable read digest differs")
    byte_count = value.get("bytes_read_per_snapshot")
    double_bytes = value.get("double_read_bytes_read")
    if (type(byte_count) is not int or not 1 <= byte_count <= MAX_KV_SNAPSHOT_BYTES
            or type(double_bytes) is not int or double_bytes != 2 * byte_count
            or double_bytes > 2 * MAX_KV_SNAPSHOT_BYTES):
        raise NativeReceiverUtilityError("native K/V snapshot read-byte accounting is invalid")
    duration = value.get("duration_us")
    if type(duration) is not int or duration < 0:
        raise NativeReceiverUtilityError("native K/V snapshot duration is invalid")
    if (value.get("read_only") is not True
            or value.get("double_read_stable") is not True
            or value.get("raw_data_exported") is not False
            or value.get("recurrent_state_included") is not False):
        raise NativeReceiverUtilityError("native K/V snapshot is not stable/read-only or exposes raw/recurrent state")

    result = {
        "schema": KV_SNAPSHOT_SCHEMA,
        "status": "READ_ONLY_SNAPSHOT",
        "cache_kind": "LLAMA_MEMORY_HYBRID_ATTENTION",
        "snapshot_scope": "ONE_ATTENTION_LAYER_ONE_SEQUENCE",
        "sequence_id": 0,
        "layer_id": value["layer_id"],
        "attention_layer_count": value["attention_layer_count"],
        "active_cell_count": position_count,
        "position_count": position_count,
        "position_sha256": position_sha,
        "k_shape": shapes["k_shape"],
        "v_shape": shapes["v_shape"],
        "k_type": types["k_type"],
        "v_type": types["v_type"],
        "k_sha256": digests["k_sha256"],
        "v_sha256": digests["v_sha256"],
        "combined_sha256": digests["combined_sha256"],
        "stable_read_sha256": digests["stable_read_sha256"],
        "bytes_read_per_snapshot": byte_count,
        "double_read_bytes_read": double_bytes,
        "duration_us": duration,
        "read_only": True,
        "double_read_stable": True,
        "raw_data_exported": False,
        "recurrent_state_included": False,
    }
    condition = expected_condition if expected_condition is not None else value.get("condition")
    if condition is not None:
        if condition not in CONDITIONS or (expected_condition is not None and condition != expected_condition):
            raise NativeReceiverUtilityError("native K/V snapshot condition binding mismatch")
        result["condition"] = condition
    model_sha = expected_model_sha256 if expected_model_sha256 is not None else value.get("receiver_model_sha256")
    input_sha = expected_input_sha256 if expected_input_sha256 is not None else value.get("input_sha256")
    if model_sha is not None:
        model_sha = _sha(model_sha, "kv_snapshot.receiver_model_sha256")
        if value.get("receiver_model_sha256") is not None and _sha(
                value.get("receiver_model_sha256"), "kv_snapshot.receiver_model_sha256") != model_sha:
            raise NativeReceiverUtilityError("native K/V snapshot receiver-model binding mismatch")
        result["receiver_model_sha256"] = model_sha
    if input_sha is not None:
        input_sha = _sha(input_sha, "kv_snapshot.input_sha256")
        if value.get("input_sha256") is not None and _sha(
                value.get("input_sha256"), "kv_snapshot.input_sha256") != input_sha:
            raise NativeReceiverUtilityError("native K/V snapshot condition-input binding mismatch")
        result["input_sha256"] = input_sha
    return result


def _native_score(value, receiver_sha, input_sha, target_sha, target_count, condition):
    if not isinstance(value, Mapping) or value.get("schema") != NATIVE_SCHEMA:
        raise NativeReceiverUtilityError("native target-score schema mismatch")
    kind, env = value.get("execution_kind"), value.get("environment")
    if kind not in {"NATIVE_LLAMA_CPP_GGUF", "SYNTHETIC_FIXTURE"} or env not in {"LOCAL_LINUX", "TERMUX_ANDROID", "REDMI", "SYNTHETIC"}:
        raise NativeReceiverUtilityError("native execution kind/environment invalid")
    if (kind == "SYNTHETIC_FIXTURE") != (env == "SYNTHETIC"):
        raise NativeReceiverUtilityError("synthetic/native environment mismatch")
    model_sha = _sha(value.get("receiver_model_sha256"), "native.receiver_model_sha256")
    input_hash = _sha(value.get("input_sha256"), "native.input_sha256")
    target_hash = _sha(value.get("target_token_ids_sha256"), "native.target_token_ids_sha256")
    if (model_sha, input_hash, target_hash) != (receiver_sha, input_sha, target_sha):
        raise NativeReceiverUtilityError("native model/input/target binding mismatch")
    if value.get("score_method") != SCORE_METHOD or value.get("target_token_count") != target_count:
        raise NativeReceiverUtilityError("native score method or target length mismatch")
    if type(value.get("decode_status")) is not int or value["decode_status"] != 0 or value.get("native_input_consumed") is not True:
        raise NativeReceiverUtilityError("native receiver did not successfully consume the input")
    token_scores = value.get("token_logprobs")
    if (not isinstance(token_scores, list) or len(token_scores) != target_count
            or any(type(x) not in (int, float) or not math.isfinite(float(x)) or float(x) > 1e-7 for x in token_scores)):
        raise NativeReceiverUtilityError("target token log-probabilities are invalid")
    native_data = {
        "schema": NATIVE_SCHEMA, "execution_kind": kind, "environment": env,
        "llama_cpp_revision": _id(value.get("llama_cpp_revision"), "native.llama_cpp_revision"),
        "binary_sha256": _sha(value.get("binary_sha256"), "native.binary_sha256"),
        "receiver_model_sha256": model_sha, "input_sha256": input_hash,
        "target_token_ids_sha256": target_hash, "target_token_count": target_count,
        "score_method": SCORE_METHOD, "token_logprobs": [float(x) for x in token_scores],
        "decode_status": 0, "native_input_consumed": True,
        "llama_version": _id(value.get("llama_version"), "native.llama_version")[:120],
    }
    if env in {"TERMUX_ANDROID", "REDMI"}:
        native_data["device_execution_receipt_sha256"] = _sha(
            value.get("device_execution_receipt_sha256"), "native.device_execution_receipt_sha256")
        native_data["device_runtime_build_id"] = _id(
            value.get("device_runtime_build_id"), "native.device_runtime_build_id")
    if "kv_snapshot" in value:
        native_data["kv_snapshot"] = validate_native_receiver_kv_snapshot(
            value.get("kv_snapshot"),
            expected_condition=condition,
            expected_model_sha256=model_sha,
            expected_input_sha256=input_hash,
            allow_sanitized=True,
        )
    return native_data


def build_native_receiver_task_score_receipt(*, condition, task_group_id, task_family, session_id,
        source_ref, message_source_ref, receiver, target_token_ids_sha256, target_token_count,
        context_sha256, input_sha256, native_receipt, adapter_sha256=None):
    """Bind a native score to a held-out task without storing text, token IDs or vectors.

    native_receipt must come from the native score producer. Hashing it gives
    integrity, not cryptographic attestation of the producer's identity.
    """
    if condition not in CONDITIONS:
        raise NativeReceiverUtilityError("unknown task-score condition")
    task_id, session = _id(task_group_id, "task_group_id"), _id(session_id, "session_id")
    if task_family not in TASK_FAMILIES:
        raise NativeReceiverUtilityError("unsupported task family")
    source = _source(source_ref, "source_ref")
    message_source = None if message_source_ref is None else _source(message_source_ref, "message_source_ref")
    if not isinstance(receiver, Mapping) or receiver.get("role") not in ROLES:
        raise NativeReceiverUtilityError("unsupported receiver binding")
    receiver_data = {"role": receiver["role"],
        "model_revision": _id(receiver.get("model_revision"), "receiver.model_revision"),
        "model_sha256": _sha(receiver.get("model_sha256"), "receiver.model_sha256"),
        "tokenizer_revision": _id(receiver.get("tokenizer_revision"), "receiver.tokenizer_revision")}
    target_sha, context_sha, input_hash = (_sha(target_token_ids_sha256, "target_token_ids_sha256"),
        _sha(context_sha256, "context_sha256"), _sha(input_sha256, "input_sha256"))
    if type(target_token_count) is not int or not 1 <= target_token_count <= 512:
        raise NativeReceiverUtilityError("target_token_count must be in [1, 512]")
    if condition == "NO_MESSAGE":
        if message_source is not None or adapter_sha256 is not None:
            raise NativeReceiverUtilityError("NO_MESSAGE must not bind a sender source or adapter")
    elif condition == "EXACT_MESSAGE":
        if message_source != source or adapter_sha256 is not None:
            raise NativeReceiverUtilityError("EXACT_MESSAGE must use exact source text and no adapter")
    else:
        if message_source is None:
            raise NativeReceiverUtilityError("latent/control condition missing message source")
        if condition in {"OOD", "ENTITY_SUBSTITUTION"}:
            if message_source["sha256"] == source["sha256"]:
                raise NativeReceiverUtilityError("OOD/entity-substitution source must differ")
        elif message_source != source:
            raise NativeReceiverUtilityError("in-distribution latent control source mismatch")
        _sha(adapter_sha256, "adapter_sha256")
    native = _native_score(native_receipt, receiver_data["model_sha256"], input_hash, target_sha, target_token_count, condition)
    material = {
        "schema": TASK_SCHEMA, "status": "SCORED", "condition": condition,
        "task_group_id": task_id, "task_family": task_family, "session_id": session,
        "source_ref": source, "message_source_ref": message_source, "receiver": receiver_data,
        "target_token_ids_sha256": target_sha, "target_token_count": target_token_count,
        "score_method": SCORE_METHOD, "token_logprobs": native["token_logprobs"],
        "mean_target_logprob": sum(native["token_logprobs"]) / target_token_count,
        "context_sha256": context_sha, "input_sha256": input_hash,
        "adapter_sha256": adapter_sha256, "native": native,
        "native_receipt_sha256": _digest(native), "persisted": False,
        "training_authority": 0, "native_receiver_authority": 0,
    }
    return material | {"receipt_sha256": _digest(material)}


def _check_receipt(receipt):
    if not isinstance(receipt, Mapping) or receipt.get("schema") != TASK_SCHEMA:
        raise NativeReceiverUtilityError("task-score schema mismatch")
    material = dict(receipt)
    digest = _sha(material.pop("receipt_sha256", None), "receipt_sha256")
    if _digest(material) != digest:
        raise NativeReceiverUtilityError("task-score receipt digest mismatch")
    if receipt.get("status") != "SCORED" or receipt.get("persisted") is not False or receipt.get("training_authority") != 0 or receipt.get("native_receiver_authority") != 0:
        raise NativeReceiverUtilityError("task-score receipt is not ephemeral/authority-zero")
    rebuilt = build_native_receiver_task_score_receipt(
        condition=receipt.get("condition"), task_group_id=receipt.get("task_group_id"),
        task_family=receipt.get("task_family"), session_id=receipt.get("session_id"),
        source_ref=receipt.get("source_ref"), message_source_ref=receipt.get("message_source_ref"),
        receiver=receipt.get("receiver"), target_token_ids_sha256=receipt.get("target_token_ids_sha256"),
        target_token_count=receipt.get("target_token_count"), context_sha256=receipt.get("context_sha256"),
        input_sha256=receipt.get("input_sha256"), native_receipt=receipt.get("native"),
        adapter_sha256=receipt.get("adapter_sha256"))
    if rebuilt != dict(receipt) or receipt.get("native_receipt_sha256") != _digest(receipt["native"]):
        raise NativeReceiverUtilityError("task-score derived/native receipt digest mismatch")
    return rebuilt


def _bootstrap_ci(values, samples, seed):
    rng = random.Random(seed)
    n = len(values)
    draws = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(samples))
    return draws[int(.025 * (samples - 1))], draws[int(.975 * (samples - 1))]


def evaluate_native_receiver_task_utility(receipts, *, min_task_groups=20, min_sessions=2,
        min_task_families=2, min_tasks_per_session=5, min_tasks_per_family=4,
        min_tasks_per_session_family=2, min_mean_delta_nats=0.02, min_win_rate=0.70,
        bootstrap_samples=1000, seed=17):
    """Evaluate paired held-out target-logprob proxy on source-disjoint crossed cohorts.

    Distinct task_group IDs must not reuse identical source bytes: otherwise
    correlated questions from one message could inflate the bootstrap sample
    count. Every observed session must also contain every observed task family.
    This is still a likelihood proxy, never answer-correctness proof.
    Optional one-layer K/V differences are reported as read-only structural
    evidence and never contribute to the task-utility pass/fail decision.
    """
    if not isinstance(receipts, Sequence) or isinstance(receipts, (str, bytes)) or not receipts:
        raise NativeReceiverUtilityError("task-score receipts must be a non-empty sequence")
    if type(min_task_groups) is not int or min_task_groups < 1 or type(min_sessions) is not int or min_sessions < 2:
        raise NativeReceiverUtilityError("invalid minimum task/session cohort")
    if type(min_task_families) is not int or min_task_families < 1:
        raise NativeReceiverUtilityError("min_task_families must be positive")
    if type(min_tasks_per_session) is not int or min_tasks_per_session < 1:
        raise NativeReceiverUtilityError("min_tasks_per_session must be positive")
    if type(min_tasks_per_family) is not int or min_tasks_per_family < 1:
        raise NativeReceiverUtilityError("min_tasks_per_family must be positive")
    if type(min_tasks_per_session_family) is not int or min_tasks_per_session_family < 1:
        raise NativeReceiverUtilityError("min_tasks_per_session_family must be positive")
    if type(min_mean_delta_nats) not in (int, float) or not math.isfinite(float(min_mean_delta_nats)) or min_mean_delta_nats < 0:
        raise NativeReceiverUtilityError("invalid minimum score delta")
    if type(min_win_rate) not in (int, float) or not math.isfinite(float(min_win_rate)) or not .5 <= min_win_rate <= 1:
        raise NativeReceiverUtilityError("min_win_rate must be in [0.5, 1]")
    if type(bootstrap_samples) is not int or not 200 <= bootstrap_samples <= 20000:
        raise NativeReceiverUtilityError("bootstrap_samples must be in [200, 20000]")
    checked = [_check_receipt(item) for item in receipts]
    groups = defaultdict(dict)
    for item in checked:
        group = groups[item["task_group_id"]]
        if item["condition"] in group:
            raise NativeReceiverUtilityError("duplicate condition in task group")
        group[item["condition"]] = item
    if len(checked) != len(groups) * len(CONDITIONS):
        raise NativeReceiverUtilityError("task cohort has missing or extra conditions")
    sessions, families, receiver_binding, native_binding, cohort_adapter = set(), set(), None, None, None
    tasks_per_session, tasks_per_family = defaultdict(int), defaultdict(int)
    tasks_per_session_family = defaultdict(int)
    source_hashes = set()
    scores = defaultdict(list)
    deltas = {name: [] for name in CONDITIONS if name != "LATENT_CANDIDATE"}
    kv_snapshot_effects = []
    kv_snapshot_mode = None
    kv_cohort_geometry = None
    for group in groups.values():
        if set(group) != set(CONDITIONS):
            raise NativeReceiverUtilityError("task group lacks a required control")
        first = group["NO_MESSAGE"]
        common = (first["session_id"], first["task_family"], first["source_ref"],
            first["target_token_ids_sha256"], first["target_token_count"], first["context_sha256"], first["receiver"])
        source_hash = first["source_ref"]["sha256"]
        if source_hash in source_hashes:
            raise NativeReceiverUtilityError("duplicate source content across task groups")
        source_hashes.add(source_hash)
        sessions.add(first["session_id"]); families.add(first["task_family"])
        tasks_per_session[first["session_id"]] += 1
        tasks_per_family[first["task_family"]] += 1
        tasks_per_session_family[(first["session_id"], first["task_family"])] += 1
        if receiver_binding is None: receiver_binding = first["receiver"]
        elif receiver_binding != first["receiver"]: raise NativeReceiverUtilityError("receiver binding changed across cohort")
        for condition in CONDITIONS:
            item = group[condition]
            if (item["session_id"], item["task_family"], item["source_ref"], item["target_token_ids_sha256"],
                item["target_token_count"], item["context_sha256"], item["receiver"]) != common:
                raise NativeReceiverUtilityError("paired conditions differ in source/target/context/model")
            native = item["native"]
            key = (native["execution_kind"], native["environment"], native["llama_cpp_revision"],
                native["binary_sha256"], native["llama_version"], item["receiver"]["model_sha256"])
            if native_binding is None: native_binding = key
            elif native_binding != key: raise NativeReceiverUtilityError("native runner/model changed across cohort")
            if condition == "NO_MESSAGE":
                if item["message_source_ref"] is not None: raise NativeReceiverUtilityError("NO_MESSAGE contains sender data")
            elif condition in {"OOD", "ENTITY_SUBSTITUTION"}:
                if item["message_source_ref"]["sha256"] == item["source_ref"]["sha256"]:
                    raise NativeReceiverUtilityError("OOD/entity-substitution did not change sender source")
            elif item["message_source_ref"] != item["source_ref"]:
                raise NativeReceiverUtilityError("in-distribution message source mismatch")
            scores[condition].append(item["mean_target_logprob"])
        _validate_duplicate_input_digests(group)
        kv_effect = _validate_duplicate_kv_snapshots(group)
        has_kv_snapshot = kv_effect is not None
        if kv_snapshot_mode is None:
            kv_snapshot_mode = has_kv_snapshot
        elif kv_snapshot_mode != has_kv_snapshot:
            raise NativeReceiverUtilityError("K/V snapshot coverage changed across task cohort")
        if kv_effect is not None:
            current_geometry = kv_effect["_geometry"]
            if kv_cohort_geometry is None:
                kv_cohort_geometry = current_geometry
            elif current_geometry != kv_cohort_geometry:
                raise NativeReceiverUtilityError(
                    "native K/V snapshot geometry changed across task cohort"
                )
            kv_snapshot_effects.append(kv_effect)
        adapter_hashes = {group[name]["adapter_sha256"] for name in LATENT_CONDITIONS}
        if len(adapter_hashes) != 1:
            raise NativeReceiverUtilityError("latent controls use different adapter revisions")
        adapter_hash = next(iter(adapter_hashes))
        if cohort_adapter is None:
            cohort_adapter = adapter_hash
        elif cohort_adapter != adapter_hash:
            raise NativeReceiverUtilityError("adapter revision changed across task cohort")
        candidate = group["LATENT_CANDIDATE"]["mean_target_logprob"]
        for control in deltas: deltas[control].append(candidate - group[control]["mean_target_logprob"])
    balanced_session_family_coverage = all(
        tasks_per_session_family[(session, family)] >= min_tasks_per_session_family
        for session in sessions for family in families
    )
    session_family_report = {
        session: {
            family: tasks_per_session_family[(session, family)]
            for family in sorted(families)
        }
        for session in sorted(sessions)
    }
    enough = (len(groups) >= min_task_groups and len(sessions) >= min_sessions
        and len(families) >= min_task_families
        and min(tasks_per_session.values()) >= min_tasks_per_session
        and min(tasks_per_family.values()) >= min_tasks_per_family
        and balanced_session_family_coverage)
    delta_report, all_pass = {}, enough
    for i, (control, values) in enumerate(deltas.items()):
        mean = sum(values) / len(values); win = sum(x > 0 for x in values) / len(values)
        low, high = _bootstrap_ci(values, bootstrap_samples, seed + i)
        passed = mean >= min_mean_delta_nats and win >= min_win_rate and low > 0
        all_pass &= passed
        delta_report[control] = {"mean_delta_nats_per_token": mean,
            "median_delta_nats_per_token": statistics.median(values), "win_rate": win,
            "bootstrap_95pct_low": low, "bootstrap_95pct_high": high, "pass": passed}
    if kv_snapshot_effects:
        kv_snapshot_effect = {
            "status": "READ_ONLY_SAMPLE_ONLY",
            "task_group_count": len(kv_snapshot_effects),
            "snapshot_count": sum(item["snapshot_count"] for item in kv_snapshot_effects),
            "candidate_differs_from_no_message_count": sum(
                item["candidate_differs_from_no_message"] for item in kv_snapshot_effects
            ),
            "candidate_differs_from_exact_message_count": sum(
                item["candidate_differs_from_exact_message"] for item in kv_snapshot_effects
            ),
            "distinct_from_no_message_task_groups_by_condition": {
                condition: sum(
                    item["distinct_from_no_message_by_condition"][condition]
                    for item in kv_snapshot_effects
                )
                for condition in CONDITIONS
            },
            "duplicate_input_groups_checked": sum(
                item["duplicate_input_groups_checked"] for item in kv_snapshot_effects
            ),
            "same_input_consistency_passed": True,
            "scope": "ONE_ATTENTION_LAYER_ONE_SEQUENCE",
            "semantic_use_proven": False,
            "generated_answer_correctness_proven": False,
            "production_route": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
            "persisted": False,
        }
    else:
        kv_snapshot_effect = {
            "status": "UNAVAILABLE",
            "task_group_count": 0,
            "snapshot_count": 0,
            "same_input_consistency_passed": None,
            "semantic_use_proven": False,
            "generated_answer_correctness_proven": False,
            "production_route": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
            "persisted": False,
        }
    kind, env = native_binding[:2]
    if kind == "SYNTHETIC_FIXTURE": status, evidence = "FIXTURE_ONLY", "SYNTHETIC"
    elif not enough: status, evidence = "INSUFFICIENT_HOLDOUT", env
    elif not all_pass: status, evidence = "UTILITY_NOT_ESTABLISHED", env
    else:
        status = {"LOCAL_LINUX": "NATIVE_LINUX_TARGET_LOGPROB_PASS",
            "TERMUX_ANDROID": "ANDROID_NATIVE_TARGET_LOGPROB_PASS", "REDMI": "REDMI_TARGET_LOGPROB_PASS"}[env]
        evidence = env
    return {"schema": RESULT_SCHEMA, "status": status, "evidence_class": evidence,
        "task_group_count": len(groups), "complete_task_group_count": len(groups),
        "incomplete_task_group_count": 0, "minimum_task_groups": min_task_groups,
        "minimum_sessions": min_sessions, "minimum_task_families": min_task_families,
        "minimum_tasks_per_session": min_tasks_per_session,
        "minimum_tasks_per_family": min_tasks_per_family,
        "minimum_tasks_per_session_family": min_tasks_per_session_family,
        "session_count": len(sessions), "task_families": sorted(families),
        "tasks_per_session": dict(sorted(tasks_per_session.items())),
        "tasks_per_family": dict(sorted(tasks_per_family.items())),
        "tasks_per_session_family": session_family_report,
        "source_group_count": len(source_hashes),
        "balanced_session_family_coverage": balanced_session_family_coverage,
        "enough_holdout": enough,
        "holdout_status": "SUFFICIENT_HOLDOUT" if enough else "INSUFFICIENT_HOLDOUT",
        "mean_target_logprob_by_condition": {k: sum(v) / len(v) for k, v in sorted(scores.items())},
        "paired_candidate_deltas": delta_report, "candidate_beats_all_controls": bool(all_pass),
        "kv_snapshot_effect": kv_snapshot_effect,
        "score_method": SCORE_METHOD, "semantic_use_proven": False,
        "generated_answer_correctness_proven": False, "production_route": False,
        "training_authority": 0, "native_receiver_authority": 0, "persisted": False}
