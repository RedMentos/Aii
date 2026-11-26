"""Strict, privacy-minimized receipts for same-model hybrid sequence-state restore.

This validates a native producer's read-only diagnostic output. It does not
capture state itself, authorize injection, or establish cross-model transfer.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
import statistics

HYBRID_STATE_SCHEMA = "v14.native-hybrid-state-roundtrip/2"
HYBRID_STATE_API = "LLAMA_STATE_SEQ_GET_SIZE_GET_DATA_SET_DATA"
HYBRID_STATE_SCOPE = "FULL_HYBRID_SEQUENCE"
HYBRID_STATE_COMPONENTS = ("ATTENTION_KV", "RECURRENT_SHORTCONV")
MAX_HYBRID_STATE_BYTES = 16 * 1024 * 1024
MAX_DURATION_US = 120_000_000
MAX_ABS_LOGIT_DIFF = 1.0e-4
MAX_RMS_LOGIT_DIFF = 1.0e-5


class NativeHybridStateReceiptError(ValueError):
    pass


def _sha(value, name):
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise NativeHybridStateReceiptError(name + " must be a lowercase SHA-256")
    return value


def _id(value, name):
    if type(value) is not str or not value or len(value) > 256:
        raise NativeHybridStateReceiptError(name + " must be a non-empty bounded string")
    return value


def _revision(value, name):
    if type(value) is not str or len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
        raise NativeHybridStateReceiptError(name + " must be a lowercase 40-character Git revision")
    return value


def _count(value, name, *, minimum=0, maximum=MAX_DURATION_US):
    if type(value) is not int or not minimum <= value <= maximum:
        raise NativeHybridStateReceiptError(name + " is outside its integer bounds")
    return value


def _metric(value, name):
    if type(value) not in (int, float) or not math.isfinite(float(value)) or float(value) < 0:
        raise NativeHybridStateReceiptError(name + " must be finite and non-negative")
    return float(value)


def _same_sha(value, source, destination, expected, name):
    source_sha = _sha(value.get(source), "hybrid_state." + source)
    destination_sha = _sha(value.get(destination), "hybrid_state." + destination)
    expected_sha = _sha(expected, "expected." + name)
    if source_sha != destination_sha or source_sha != expected_sha:
        raise NativeHybridStateReceiptError(name + " changed across same-model state roundtrip")
    return source_sha


def validate_native_hybrid_state_roundtrip(
    value, *, expected_model_sha256, expected_model_revision,
    expected_tokenizer_revision, expected_llama_cpp_revision,
    expected_binary_sha256, expected_context_sha256, expected_input_sha256,
    expected_target_token_ids_sha256, expected_target_token_count,
    expected_sequence_id=0,
):
    """Validate a sanitized same-model full-hybrid sequence-state roundtrip.

    The schema intentionally accepts only hashes, dimensions, byte counts and
    timings. Raw serialized state, prompt/token/logit arrays and persisted
    buffers are rejected. A failed fidelity result is retained as a negative
    diagnostic rather than converted into a successful receipt.
    """
    if not isinstance(value, Mapping) or value.get("schema") != HYBRID_STATE_SCHEMA:
        raise NativeHybridStateReceiptError("hybrid-state roundtrip schema mismatch")

    required = {
        "schema", "status", "state_api", "state_scope", "state_components",
        "prefill_decode_status", "source_sequence_id", "destination_sequence_id",
        "source_model_sha256", "destination_model_sha256",
        "source_model_revision", "destination_model_revision",
        "source_tokenizer_revision", "destination_tokenizer_revision",
        "source_llama_cpp_revision", "destination_llama_cpp_revision",
        "source_binary_sha256", "destination_binary_sha256",
        "source_context_sha256", "destination_context_sha256",
        "source_input_sha256", "prefill_condition", "prefill_rows",
        "continuation_token_ids_sha256",
        "source_context_params_sha256", "destination_context_params_sha256",
        "state_bytes", "get_size_bytes", "get_data_bytes", "set_data_bytes",
        "state_sha256", "capture_duration_us", "restore_duration_us",
        "baseline_logits_sha256", "restored_logits_sha256",
        "continuation_token_count", "top1_match_count",
        "max_abs_logit_diff", "rms_logit_diff", "roundtrip_passed", "truncated_restore_rejected",
        "attention_kv_included", "recurrent_shortconv_included",
        "raw_state_exported", "state_persisted", "state_buffer_zeroized",
        "installed_runtime_touched", "production_route",
        "training_authority", "native_receiver_authority",
    }
    keys = set(value)
    if keys != required:
        missing, extra = sorted(required - keys), sorted(keys - required)
        raise NativeHybridStateReceiptError(
            "hybrid-state receipt fields mismatch; missing=" + ",".join(missing)
            + "; extra=" + ",".join(extra)
        )
    if value.get("status") != "READ_ONLY_ROUNDTRIP" or value.get("state_api") != HYBRID_STATE_API:
        raise NativeHybridStateReceiptError("hybrid-state roundtrip API/status unsupported")
    if value.get("state_scope") != HYBRID_STATE_SCOPE:
        raise NativeHybridStateReceiptError("hybrid-state roundtrip is not full sequence scope")
    components = value.get("state_components")
    if not isinstance(components, (list, tuple)) or tuple(components) != HYBRID_STATE_COMPONENTS:
        raise NativeHybridStateReceiptError("hybrid-state component coverage is incomplete")
    if value.get("prefill_condition") != "LATENT_CANDIDATE":
        raise NativeHybridStateReceiptError("hybrid-state prefill must be LATENT_CANDIDATE")
    prefill_rows = _count(value.get("prefill_rows"), "prefill_rows", minimum=1, maximum=64)
    prefill_decode_status = value.get("prefill_decode_status")
    if type(prefill_decode_status) is not int or prefill_decode_status != 0:
        raise NativeHybridStateReceiptError("hybrid-state latent prefill decode did not pass")

    sequence_id = _count(value.get("source_sequence_id"), "source_sequence_id", maximum=255)
    destination_sequence_id = _count(value.get("destination_sequence_id"), "destination_sequence_id", maximum=255)
    if sequence_id != expected_sequence_id or destination_sequence_id != expected_sequence_id:
        raise NativeHybridStateReceiptError("hybrid-state sequence binding mismatch")

    model_sha = _same_sha(value, "source_model_sha256", "destination_model_sha256", expected_model_sha256, "model SHA")
    binary_sha = _same_sha(value, "source_binary_sha256", "destination_binary_sha256", expected_binary_sha256, "native binary SHA")
    context_sha = _same_sha(value, "source_context_sha256", "destination_context_sha256", expected_context_sha256, "context SHA")
    context_params_sha = _same_sha(
        value, "source_context_params_sha256", "destination_context_params_sha256",
        value.get("source_context_params_sha256"), "context parameters SHA",
    )
    source_llama_revision = _revision(value.get("source_llama_cpp_revision"), "hybrid_state.source_llama_cpp_revision")
    destination_llama_revision = _revision(value.get("destination_llama_cpp_revision"), "hybrid_state.destination_llama_cpp_revision")
    expected_llama_revision = _revision(expected_llama_cpp_revision, "expected.llama_cpp_revision")
    if source_llama_revision != destination_llama_revision or source_llama_revision != expected_llama_revision:
        raise NativeHybridStateReceiptError("llama.cpp revision changed across same-model state roundtrip")
    llama_revision = source_llama_revision

    model_revision = _id(value.get("source_model_revision"), "hybrid_state.source_model_revision")
    if (model_revision != _id(value.get("destination_model_revision"), "hybrid_state.destination_model_revision")
            or model_revision != _id(expected_model_revision, "expected.model_revision")):
        raise NativeHybridStateReceiptError("model revision changed across same-model state roundtrip")
    tokenizer_revision = _id(value.get("source_tokenizer_revision"), "hybrid_state.source_tokenizer_revision")
    if (tokenizer_revision != _id(value.get("destination_tokenizer_revision"), "hybrid_state.destination_tokenizer_revision")
            or tokenizer_revision != _id(expected_tokenizer_revision, "expected.tokenizer_revision")):
        raise NativeHybridStateReceiptError("tokenizer revision changed across same-model state roundtrip")

    input_sha = _sha(value.get("source_input_sha256"), "hybrid_state.source_input_sha256")
    if input_sha != _sha(expected_input_sha256, "expected.input_sha256"):
        raise NativeHybridStateReceiptError("hybrid-state input binding mismatch")
    target_sha = _sha(value.get("continuation_token_ids_sha256"), "hybrid_state.continuation_token_ids_sha256")
    if target_sha != _sha(expected_target_token_ids_sha256, "expected.target_token_ids_sha256"):
        raise NativeHybridStateReceiptError("hybrid-state continuation-token binding mismatch")
    target_count = _count(expected_target_token_count, "expected.target_token_count", minimum=1, maximum=512)
    continuation_count = _count(value.get("continuation_token_count"), "continuation_token_count", minimum=1, maximum=512)
    if continuation_count != target_count:
        raise NativeHybridStateReceiptError("hybrid-state continuation length mismatch")

    state_bytes = _count(value.get("state_bytes"), "state_bytes", minimum=1, maximum=MAX_HYBRID_STATE_BYTES)
    size_bytes = _count(value.get("get_size_bytes"), "get_size_bytes", minimum=1, maximum=MAX_HYBRID_STATE_BYTES)
    data_bytes = _count(value.get("get_data_bytes"), "get_data_bytes", minimum=1, maximum=MAX_HYBRID_STATE_BYTES)
    restored_bytes = _count(value.get("set_data_bytes"), "set_data_bytes", minimum=1, maximum=MAX_HYBRID_STATE_BYTES)
    state_sha = _sha(value.get("state_sha256"), "hybrid_state.state_sha256")
    capture_us = _count(value.get("capture_duration_us"), "capture_duration_us")
    restore_us = _count(value.get("restore_duration_us"), "restore_duration_us")
    baseline_logits_sha = _sha(value.get("baseline_logits_sha256"), "hybrid_state.baseline_logits_sha256")
    restored_logits_sha = _sha(value.get("restored_logits_sha256"), "hybrid_state.restored_logits_sha256")
    top1_matches = _count(value.get("top1_match_count"), "top1_match_count", maximum=target_count)
    max_diff = _metric(value.get("max_abs_logit_diff"), "max_abs_logit_diff")
    rms_diff = _metric(value.get("rms_logit_diff"), "rms_logit_diff")

    if value.get("truncated_restore_rejected") is not True:
        raise NativeHybridStateReceiptError("hybrid-state truncated restore negative control was not rejected")
    if value.get("attention_kv_included") is not True or value.get("recurrent_shortconv_included") is not True:
        raise NativeHybridStateReceiptError("hybrid-state receipt omits attention or recurrent shortconv state")
    if (value.get("raw_state_exported") is not False
            or value.get("state_persisted") is not False
            or value.get("state_buffer_zeroized") is not True
            or value.get("installed_runtime_touched") is not False
            or value.get("production_route") is not False
            or type(value.get("training_authority")) is not int or value["training_authority"] != 0
            or type(value.get("native_receiver_authority")) is not int or value["native_receiver_authority"] != 0):
        raise NativeHybridStateReceiptError("hybrid-state receipt exceeds read-only diagnostic authority")

    fidelity_passed = (
        value.get("truncated_restore_rejected") is True
        and state_bytes == size_bytes == data_bytes == restored_bytes
        and top1_matches == target_count
        and max_diff <= MAX_ABS_LOGIT_DIFF
        and rms_diff <= MAX_RMS_LOGIT_DIFF
    )
    if type(value.get("roundtrip_passed")) is not bool or value["roundtrip_passed"] != fidelity_passed:
        raise NativeHybridStateReceiptError("hybrid-state roundtrip pass flag disagrees with measured fidelity")

    return {
        "schema": HYBRID_STATE_SCHEMA,
        "status": "READ_ONLY_ROUNDTRIP",
        "state_api": HYBRID_STATE_API,
        "state_scope": HYBRID_STATE_SCOPE,
        "state_components": list(HYBRID_STATE_COMPONENTS),
        "source_sequence_id": sequence_id,
        "destination_sequence_id": destination_sequence_id,
        "source_model_sha256": model_sha,
        "destination_model_sha256": model_sha,
        "source_model_revision": model_revision,
        "destination_model_revision": model_revision,
        "source_tokenizer_revision": tokenizer_revision,
        "destination_tokenizer_revision": tokenizer_revision,
        "source_llama_cpp_revision": llama_revision,
        "destination_llama_cpp_revision": llama_revision,
        "source_binary_sha256": binary_sha,
        "destination_binary_sha256": binary_sha,
        "source_context_sha256": context_sha,
        "destination_context_sha256": context_sha,
        "source_input_sha256": input_sha,
        "prefill_condition": "LATENT_CANDIDATE",
        "prefill_rows": prefill_rows,
        "prefill_decode_status": prefill_decode_status,
        "continuation_token_ids_sha256": target_sha,
        "source_context_params_sha256": context_params_sha,
        "destination_context_params_sha256": context_params_sha,
        "state_bytes": state_bytes,
        "get_size_bytes": size_bytes,
        "get_data_bytes": data_bytes,
        "set_data_bytes": restored_bytes,
        "state_sha256": state_sha,
        "capture_duration_us": capture_us,
        "restore_duration_us": restore_us,
        "baseline_logits_sha256": baseline_logits_sha,
        "restored_logits_sha256": restored_logits_sha,
        "continuation_token_count": continuation_count,
        "top1_match_count": top1_matches,
        "max_abs_logit_diff": max_diff,
        "rms_logit_diff": rms_diff,
        "roundtrip_passed": fidelity_passed,
        "truncated_restore_rejected": True,
        "attention_kv_included": True,
        "recurrent_shortconv_included": True,
        "raw_state_exported": False,
        "state_persisted": False,
        "state_buffer_zeroized": True,
        "installed_runtime_touched": False,
        "production_route": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }


def summarize_native_hybrid_state_roundtrips(receipts):
    """Summarize same-model roundtrip diagnostics without affecting task utility."""
    if not isinstance(receipts, Sequence) or isinstance(receipts, (str, bytes)):
        raise NativeHybridStateReceiptError("hybrid-state roundtrip receipts must be a sequence")
    if not receipts:
        return {
            "status": "UNAVAILABLE", "task_group_count": 0,
            "prefill_condition": None, "prefill_rows_min": None,
            "prefill_rows_median": None, "prefill_rows_max": None,
            "context_params_variant_count": 0,
            "all_roundtrips_passed": False, "same_model_only": True,
            "cross_model_transfer_proven": False, "trained_latent_coupling_proven": False,
            "semantic_use_proven": False, "generated_answer_correctness_proven": False,
            "production_route": False, "training_authority": 0,
            "native_receiver_authority": 0, "persisted": False,
            "influence_on_utility_gate": False,
        }
    identity_fields = (
        "state_api", "state_scope", "state_components", "source_sequence_id",
        "destination_sequence_id", "prefill_condition", "source_model_sha256", "source_model_revision",
        "source_tokenizer_revision", "source_llama_cpp_revision", "source_binary_sha256",
    )
    identity = tuple(receipts[0][field] for field in identity_fields)
    for receipt in receipts[1:]:
        if tuple(receipt[field] for field in identity_fields) != identity:
            raise NativeHybridStateReceiptError("hybrid-state geometry/model binding changed across task cohort")
    token_total = sum(receipt["continuation_token_count"] for receipt in receipts)
    matches = sum(receipt["top1_match_count"] for receipt in receipts)
    passed = all(receipt["roundtrip_passed"] for receipt in receipts)
    return {
        "status": "SAME_MODEL_ROUNDTRIP_PASS" if passed else "SAME_MODEL_ROUNDTRIP_FAIL",
        "task_group_count": len(receipts),
        "prefill_condition": receipts[0]["prefill_condition"],
        "prefill_rows_min": min(item["prefill_rows"] for item in receipts),
        "prefill_rows_median": statistics.median(item["prefill_rows"] for item in receipts),
        "prefill_rows_max": max(item["prefill_rows"] for item in receipts),
        "context_params_variant_count": len({
            item["source_context_params_sha256"] for item in receipts
        }),
        "state_scope": HYBRID_STATE_SCOPE,
        "state_components": list(HYBRID_STATE_COMPONENTS),
        "model_sha256": receipts[0]["source_model_sha256"],
        "model_revision": receipts[0]["source_model_revision"],
        "llama_cpp_revision": receipts[0]["source_llama_cpp_revision"],
        "state_bytes_min": min(item["state_bytes"] for item in receipts),
        "state_bytes_median": statistics.median(item["state_bytes"] for item in receipts),
        "state_bytes_max": max(item["state_bytes"] for item in receipts),
        "capture_duration_us_median": statistics.median(item["capture_duration_us"] for item in receipts),
        "restore_duration_us_median": statistics.median(item["restore_duration_us"] for item in receipts),
        "max_abs_logit_diff": max(item["max_abs_logit_diff"] for item in receipts),
        "max_rms_logit_diff": max(item["rms_logit_diff"] for item in receipts),
        "top1_match_rate": matches / token_total,
        "all_roundtrips_passed": passed,
        "truncated_restore_rejected_count": sum(1 for item in receipts if item["truncated_restore_rejected"]),
        "same_model_only": True,
        "cross_model_transfer_proven": False,
        "trained_latent_coupling_proven": False,
        "semantic_use_proven": False,
        "generated_answer_correctness_proven": False,
        "production_route": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
        "persisted": False,
        "influence_on_utility_gate": False,
    }
