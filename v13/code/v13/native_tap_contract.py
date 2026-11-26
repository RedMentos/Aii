"""Typed guard for contextual sender activations used by the tokenwise latent adapter.

The sender space is the model's final-RMSNorm prefill output, not the static
input-embedding table, pooled sentence embeddings, or a writable training tap.
"""
from __future__ import annotations

from collections.abc import Mapping
import math

SENDER_ACTIVATION_SPACE = "FINAL_RMSNORM_PREFILL_F32"
SENDER_CAPTURE_METHOD = "LLAMA_SERVER_EMBEDDINGS_FINAL_RMSNORM_ONLY"
SENDER_TAP_IDS = {
    "B1_DETAIL": frozenset({"lfm2.result_norm.final.v1"}),
    "B2_GIST": frozenset({"qwen35.result_norm.final.v1", "lfm2.result_norm.final.v1"}),
}


class NativeTapContractError(ValueError):
    pass


def _validate_vectors(token_ids, vectors, dimension):
    if (not isinstance(token_ids, (list, tuple)) or not token_ids
            or any(type(token_id) is not int or token_id < 0 for token_id in token_ids)):
        raise NativeTapContractError("final-RMSNorm tap token IDs are invalid")
    if not isinstance(vectors, (list, tuple)) or len(vectors) != len(token_ids):
        raise NativeTapContractError("final-RMSNorm tap token/vector row count differs")
    for row in vectors:
        if (not isinstance(row, (list, tuple)) or len(row) != dimension
                or any(type(value) not in (int, float) or not math.isfinite(float(value)) for value in row)):
            raise NativeTapContractError("final-RMSNorm tap vector geometry or values are invalid")
    return len(token_ids)


def _validate_metrics(metrics, role, tap_id, runner_revision, dimension, token_count):
    if (not isinstance(metrics, Mapping)
            or metrics.get("operation") != "PREFILL_TAP"
            or metrics.get("normalization") != "native_final_RMSNorm_only"
            or metrics.get("pooling") != "none"
            or metrics.get("whole_sequence_prefill") is not True
            or metrics.get("CAN_LATENT_TAP") is not True
            or metrics.get("CAN_LATENT_INJECT") is not False
            or metrics.get("CAN_TRAIN_BODY") is not False
            or metrics.get("role") != role
            or metrics.get("tap_id") != tap_id
            or metrics.get("runner_revision") != runner_revision
            or metrics.get("embedding_dim") != dimension
            or metrics.get("prompt_tokens") != token_count):
        raise NativeTapContractError("sender tap is not a read-only native final-RMSNorm prefill")


def validate_native_final_rmsnorm_output(native, tap_runner, role):
    """Validate the native runner output before Cognition persists a local tap."""
    if not isinstance(native, Mapping):
        raise NativeTapContractError("native tap output is not a mapping")
    tap_id = getattr(tap_runner, "tap_id", None)
    dimension = getattr(tap_runner, "tap_dim", None)
    if role not in SENDER_TAP_IDS or tap_id not in SENDER_TAP_IDS[role]:
        raise NativeTapContractError("sender role is not bound to a supported final-RMSNorm tap")
    if native.get("tap_id") != tap_id:
        raise NativeTapContractError("native tap identity differs from the validated runner")
    if type(dimension) is not int or not 1 <= dimension <= 8192:
        raise NativeTapContractError("native final-RMSNorm dimension is invalid")
    token_ids = native.get("token_ids")
    vectors = native.get("vectors")
    token_count = _validate_vectors(token_ids, vectors, dimension)
    metrics = native.get("metrics")
    runner_revision = metrics.get("runner_revision") if isinstance(metrics, Mapping) else None
    if type(runner_revision) is not str or not runner_revision:
        raise NativeTapContractError("native final-RMSNorm runner revision is missing")
    _validate_metrics(metrics, role, tap_id, runner_revision, dimension, token_count)
    return {
        "tap_id": tap_id,
        "activation_space": SENDER_ACTIVATION_SPACE,
        "capture_method": SENDER_CAPTURE_METHOD,
        "embedding_dim": dimension,
        "runner_revision": runner_revision,
    }


def validate_latent_tap_packet(
    packet,
    tap_data,
    role,
    *,
    expected_tap_id=None,
    expected_runner_revision=None,
):
    """Validate the persisted packet and its read-back vectors before pairing."""
    if not isinstance(packet, Mapping) or not isinstance(tap_data, Mapping):
        raise NativeTapContractError("sender LatentTapPacket and read-back data are required")
    tap_id = packet.get("tap_id")
    if role not in SENDER_TAP_IDS or tap_id not in SENDER_TAP_IDS[role]:
        raise NativeTapContractError("sender LatentTapPacket role/tap binding is unsupported")
    if expected_tap_id is not None and tap_id != expected_tap_id:
        raise NativeTapContractError("sender LatentTapPacket tap ID differs from the requested binding")
    if (packet.get("activation_space") != SENDER_ACTIVATION_SPACE
            or packet.get("capture_method") != SENDER_CAPTURE_METHOD):
        raise NativeTapContractError("sender LatentTapPacket is not explicit final-RMSNorm prefill")
    if (packet.get("role") != role
            or packet.get("role_state") != "INDEPENDENT_READ_ONLY_PREFILL"
            or packet.get("receiver_read_authority") != 0
            or packet.get("receiver_injection_authority") != 0
            or packet.get("body_learning_authority") != 0):
        raise NativeTapContractError("sender LatentTapPacket carries the wrong role or authority")
    feature_path = packet.get("feature_path")
    feature_sha = packet.get("feature_sha256")
    if (type(feature_path) is not str or not feature_path.startswith("data/blobs/")
            or type(feature_sha) is not str or len(feature_sha) != 64
            or any(ch not in "0123456789abcdef" for ch in feature_sha)):
        raise NativeTapContractError("sender LatentTapPacket feature blob binding is invalid")
    runner_revision = packet.get("runner_revision")
    if type(runner_revision) is not str or not runner_revision:
        raise NativeTapContractError("sender LatentTapPacket runner revision is missing")
    if expected_runner_revision is not None and runner_revision != expected_runner_revision:
        raise NativeTapContractError("sender LatentTapPacket runner revision differs from the pinned runner")
    shape = packet.get("shape")
    dimension = shape[1] if isinstance(shape, (list, tuple)) and len(shape) == 2 else None
    if type(dimension) is not int or not 1 <= dimension <= 8192:
        raise NativeTapContractError("sender LatentTapPacket embedding dimension is invalid")
    token_ids = packet.get("token_ids")
    readback_ids = tap_data.get("token_ids")
    vectors = tap_data.get("vectors")
    token_count = _validate_vectors(readback_ids, vectors, dimension)
    if (list(token_ids) if isinstance(token_ids, (list, tuple)) else None) != list(readback_ids):
        raise NativeTapContractError("sender LatentTapPacket token IDs differ from read-back data")
    if list(shape) != [token_count, dimension]:
        raise NativeTapContractError("sender LatentTapPacket shape differs from read-back vectors")
    _validate_metrics(packet.get("metrics"), role, tap_id, runner_revision, dimension, token_count)
    return {
        "tap_id": tap_id,
        "activation_space": SENDER_ACTIVATION_SPACE,
        "capture_method": SENDER_CAPTURE_METHOD,
        "embedding_dim": dimension,
        "runner_revision": runner_revision,
    }
