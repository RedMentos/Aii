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

TASK_SCHEMA = "v14.native-receiver-task-score/1"
NATIVE_SCHEMA = "v14.native-receiver-target-score/1"
RESULT_SCHEMA = "v14.native-receiver-task-utility/1"
SCORE_METHOD = "TEACHER_FORCED_TARGET_LOGPROB_V1"
CONDITIONS = ("NO_MESSAGE", "EXACT_MESSAGE", "LATENT_CANDIDATE", "ZERO", "SHUFFLE", "REPEAT", "OOD", "ENTITY_SUBSTITUTION")
LATENT_CONDITIONS = frozenset({"LATENT_CANDIDATE", "ZERO", "SHUFFLE", "REPEAT", "OOD", "ENTITY_SUBSTITUTION"})
TASK_FAMILIES = frozenset({"ARITHMETIC", "ENTITY_RECALL", "RELATION", "MULTI_STEP", "OTHER"})
ROLES = frozenset({"B1_DETAIL", "B2_GIST", "C3_LANGUAGE"})


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


def _native_score(value, receiver_sha, input_sha, target_sha, target_count):
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
    native = _native_score(native_receipt, receiver_data["model_sha256"], input_hash, target_sha, target_token_count)
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
    kind, env = native_binding[:2]
    # A synthetic fixture must not hide missing holdout coverage.
    # FIXTURE_ONLY is valid only after the session/family minima are met.
    if not enough:
        status, evidence = "COLLECTING", "SYNTHETIC" if kind == "SYNTHETIC_FIXTURE" else env
    elif kind == "SYNTHETIC_FIXTURE":
        status, evidence = "FIXTURE_ONLY", "SYNTHETIC"
    elif not all_pass:
        status, evidence = "UTILITY_NOT_ESTABLISHED", env
    else:
        status = {"LOCAL_LINUX": "NATIVE_LINUX_TARGET_LOGPROB_PASS",
            "TERMUX_ANDROID": "ANDROID_NATIVE_TARGET_LOGPROB_PASS", "REDMI": "REDMI_TARGET_LOGPROB_PASS"}[env]
        evidence = env
    return {"schema": RESULT_SCHEMA, "status": status, "evidence_class": evidence,
        "task_group_count": len(groups),
        "complete_task_group_count": len(groups),
        "incomplete_task_group_count": 0,
        "minimum_task_groups": min_task_groups,
        "minimum_sessions": min_sessions,
        "minimum_task_families": min_task_families,
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
        "score_method": SCORE_METHOD, "semantic_use_proven": False,
        "generated_answer_correctness_proven": False, "production_route": False,
        "training_authority": 0, "native_receiver_authority": 0, "persisted": False}
