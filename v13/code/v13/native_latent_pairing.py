"""Source-bound paired native taps for a future JEPA-owned latent learner.

This records exact-token B1/B2 cross-body and B1/B2-to-C3 observations. It
does not train, inject, authorize B3, or promote a pair to a world fact.
"""
import hashlib
import math

from .common import dumps
from .contracts import FIELDS, packet, validate

MAX_TOKENS = 64
MAX_DIM = 8192
MAX_ELEMENTS = 262144
PAIR_ALLOWED = frozenset({
    ("B1_DETAIL", "B2_GIST"),
    ("B2_GIST", "B1_DETAIL"),
    ("B1_DETAIL", "C3_LANGUAGE"),
    ("B2_GIST", "C3_LANGUAGE"),
})
PAIR_FIELDS = {
    "sender_role": str,
    "receiver_role": str,
    "source_ref": dict,
    "sender_tap_packet_id": str,
    "receiver_tap_packet_id": str,
    "sender_tap_id": str,
    "receiver_tap_id": str,
    "tokenizer_revision": str,
    "sender_model_revision": str,
    "receiver_model_revision": str,
    "sender_model_sha256": str,
    "receiver_model_sha256": str,
    "sender_feature_sha256": str,
    "receiver_feature_sha256": str,
    "sender_shape": list,
    "receiver_shape": list,
    "token_ids_sha256": str,
    "token_count": int,
    "alignment": str,
    "pair_sha256": str,
    "status": str,
    "training_authority": int,
    "native_receiver_authority": int,
    "production_route": bool,
}


class NativeTapPairError(ValueError):
    """A pair is not safe or sufficiently aligned for a training candidate."""


def register_packet_contract():
    existing = FIELDS.get("LatentTapPairPacket")
    if existing is not None and existing != PAIR_FIELDS:
        raise NativeTapPairError("LatentTapPairPacket contract collision")
    FIELDS["LatentTapPairPacket"] = dict(PAIR_FIELDS)


def _digest(value, name):
    if (not isinstance(value, str) or len(value) != 64
            or any(ch not in "0123456789abcdef" for ch in value)):
        raise NativeTapPairError(name + " must be lowercase SHA-256")
    return value


def _tap_data(cognition, tap_packet, expected_role):
    validate("LatentTapPacket", tap_packet)
    if tap_packet.get("role") != expected_role:
        raise NativeTapPairError("tap role mismatch")
    metrics = tap_packet.get("metrics")
    if (not isinstance(metrics, dict)
            or metrics.get("whole_sequence_prefill") is not True
            or metrics.get("pooling") != "none"
            or metrics.get("prompt_tokens") != len(tap_packet.get("token_ids", []))):
        raise NativeTapPairError("tap is not a whole-sequence unpooled prefill")
    data = cognition.read_tap(tap_packet)
    token_ids = data.get("token_ids")
    vectors = data.get("vectors")
    if (not isinstance(token_ids, list) or not 1 <= len(token_ids) <= MAX_TOKENS
            or any(type(token_id) is not int or token_id < 0 for token_id in token_ids)):
        raise NativeTapPairError("tap token IDs are invalid")
    if not isinstance(vectors, list) or len(vectors) != len(token_ids):
        raise NativeTapPairError("tap token/vector count mismatch")
    if not isinstance(tap_packet.get("shape"), list) or len(tap_packet["shape"]) != 2:
        raise NativeTapPairError("tap shape is missing")
    rows, dim = tap_packet["shape"]
    if (type(rows) is not int or type(dim) is not int
            or rows != len(token_ids) or not 1 <= dim <= MAX_DIM
            or rows * dim > MAX_ELEMENTS):
        raise NativeTapPairError("tap shape is outside pairing bounds")
    for vector in vectors:
        if not isinstance(vector, list) or len(vector) != dim:
            raise NativeTapPairError("tap vector shape mismatch")
        for item in vector:
            if (not isinstance(item, (int, float)) or isinstance(item, bool)
                    or not math.isfinite(float(item)) or abs(float(item)) > 1.0e6):
                raise NativeTapPairError("tap contains non-finite or unbounded values")
    tokenizer_revision = tap_packet.get("tokenizer_revision")
    if not isinstance(tokenizer_revision, str) or not tokenizer_revision:
        raise NativeTapPairError("tap tokenizer revision is missing")
    _digest(tap_packet.get("feature_sha256"), "tap feature hash")
    if not isinstance(tap_packet.get("tap_id"), str) or not tap_packet["tap_id"]:
        raise NativeTapPairError("tap identity is missing")
    if not isinstance(tap_packet.get("model_revision"), str) or not tap_packet["model_revision"]:
        raise NativeTapPairError("tap model revision is missing")
    return data


def _binding(value):
    return {
        "event_id": value["event_id"],
        "brain_generation_id": value["brain_generation_id"],
        "source_ref": value["source_ref"],
        "sender_role": value["sender_role"],
        "receiver_role": value["receiver_role"],
        "sender_tap_packet_id": value["sender_tap_packet_id"],
        "receiver_tap_packet_id": value["receiver_tap_packet_id"],
        "sender_tap_id": value["sender_tap_id"],
        "receiver_tap_id": value["receiver_tap_id"],
        "tokenizer_revision": value["tokenizer_revision"],
        "sender_model_revision": value["sender_model_revision"],
        "receiver_model_revision": value["receiver_model_revision"],
        "sender_model_sha256": value["sender_model_sha256"],
        "receiver_model_sha256": value["receiver_model_sha256"],
        "sender_feature_sha256": value["sender_feature_sha256"],
        "receiver_feature_sha256": value["receiver_feature_sha256"],
        "sender_shape": value["sender_shape"],
        "receiver_shape": value["receiver_shape"],
        "token_ids_sha256": value["token_ids_sha256"],
        "token_count": value["token_count"],
        "alignment": value["alignment"],
    }


def validate_pair_packet(value):
    register_packet_contract()
    validate("LatentTapPairPacket", value)
    if ((value["sender_role"], value["receiver_role"]) not in PAIR_ALLOWED
            or value["status"] != "PAIRED_READ_ONLY"
            or value["alignment"] != "TOKEN_IDS_EXACT"):
        raise NativeTapPairError("tap-pair role/alignment/status")
    if (not isinstance(value["tokenizer_revision"], str)
            or not value["tokenizer_revision"]):
        raise NativeTapPairError("tap-pair tokenizer revision")
    for name in ("sender_tap_id", "receiver_tap_id",
                 "sender_model_revision", "receiver_model_revision"):
        if not isinstance(value[name], str) or not value[name]:
            raise NativeTapPairError("tap-pair " + name)
    if (value["training_authority"] != 0
            or value["native_receiver_authority"] != 0
            or value["production_route"] is not False):
        raise NativeTapPairError("tap pair cannot grant training or production authority")
    if (not isinstance(value["source_ref"].get("source_id"), str)
            or value["source_ref"] not in value.get("provenance", [])):
        raise NativeTapPairError("tap-pair source provenance")
    if type(value["token_count"]) is not int or not 1 <= value["token_count"] <= MAX_TOKENS:
        raise NativeTapPairError("tap-pair token count")
    for name in ("sender_shape", "receiver_shape"):
        shape = value[name]
        if (len(shape) != 2 or type(shape[0]) is not int or type(shape[1]) is not int
                or shape[0] != value["token_count"] or not 1 <= shape[1] <= MAX_DIM
                or shape[0] * shape[1] > MAX_ELEMENTS):
            raise NativeTapPairError("tap-pair " + name)
    for name in ("sender_model_sha256", "receiver_model_sha256",
                 "sender_feature_sha256", "receiver_feature_sha256",
                 "token_ids_sha256", "pair_sha256"):
        _digest(value[name], name)
    expected = hashlib.sha256(dumps(_binding(value)).encode("utf-8")).hexdigest()
    if value["pair_sha256"] != expected:
        raise NativeTapPairError("tap-pair binding hash mismatch")
    return value


def pair_taps(cognition, sender_packet, receiver_packet,
              sender_model_sha256, receiver_model_sha256):
    """Persist one exact-token B1/B2 cross-body or B1/B2->C3 pair."""
    register_packet_contract()
    sender_role = sender_packet.get("role")
    receiver_role = receiver_packet.get("role")
    if (sender_role, receiver_role) not in PAIR_ALLOWED:
        raise NativeTapPairError("unsupported native tap pair roles")
    if (sender_packet.get("event_id") != receiver_packet.get("event_id")
            or sender_packet.get("brain_generation_id") != receiver_packet.get("brain_generation_id")
            or sender_packet.get("source_ref") != receiver_packet.get("source_ref")):
        raise NativeTapPairError("tap event, generation or SourceRef mismatch")
    source_ref = sender_packet.get("source_ref")
    if (not isinstance(source_ref, dict) or not source_ref.get("source_id")
            or source_ref not in sender_packet.get("provenance", [])
            or source_ref not in receiver_packet.get("provenance", [])):
        raise NativeTapPairError("tap SourceRef is not provenance-bound")
    sender_tokenizer = sender_packet.get("tokenizer_revision")
    receiver_tokenizer = receiver_packet.get("tokenizer_revision")
    if (not isinstance(sender_tokenizer, str) or not sender_tokenizer
            or sender_tokenizer != receiver_tokenizer):
        raise NativeTapPairError("tokenizer revisions are missing or differ")
    # Tap IDs are model-specific extraction points; exact tokenizer identity
    # and token IDs, not identical layer names, define this read-only pairing.
    sender_data = _tap_data(cognition, sender_packet, sender_role)
    receiver_data = _tap_data(cognition, receiver_packet, receiver_role)
    if sender_data["token_ids"] != receiver_data["token_ids"]:
        raise NativeTapPairError("tokenizer output differs; no exact token alignment")
    sender_model_sha256 = _digest(sender_model_sha256, "sender model hash")
    receiver_model_sha256 = _digest(receiver_model_sha256, "receiver model hash")
    token_ids_sha256 = hashlib.sha256(dumps(sender_data["token_ids"]).encode("utf-8")).hexdigest()
    payload = {
        "sender_role": sender_role,
        "receiver_role": receiver_role,
        "source_ref": source_ref,
        "tokenizer_revision": sender_tokenizer,
        "sender_tap_packet_id": sender_packet["packet_id"],
        "receiver_tap_packet_id": receiver_packet["packet_id"],
        "sender_tap_id": sender_packet["tap_id"],
        "receiver_tap_id": receiver_packet["tap_id"],
        "sender_model_revision": sender_packet["model_revision"],
        "receiver_model_revision": receiver_packet["model_revision"],
        "sender_model_sha256": sender_model_sha256,
        "receiver_model_sha256": receiver_model_sha256,
        "sender_feature_sha256": sender_packet["feature_sha256"],
        "receiver_feature_sha256": receiver_packet["feature_sha256"],
        "sender_shape": list(sender_packet["shape"]),
        "receiver_shape": list(receiver_packet["shape"]),
        "token_ids_sha256": token_ids_sha256,
        "token_count": len(sender_data["token_ids"]),
        "alignment": "TOKEN_IDS_EXACT",
        "status": "PAIRED_READ_ONLY",
        "training_authority": 0,
        "native_receiver_authority": 0,
        "production_route": False,
    }
    binding_value = {
        "event_id": sender_packet["event_id"],
        "brain_generation_id": sender_packet["brain_generation_id"],
        **payload,
    }
    payload["pair_sha256"] = hashlib.sha256(dumps(_binding(binding_value)).encode("utf-8")).hexdigest()
    result = packet(
        "LatentTapPairPacket", "B3_NATIVE_TAP_PAIR",
        sender_packet["event_id"], sender_packet["brain_generation_id"],
        [source_ref], **payload,
    )
    validate_pair_packet(result)
    cognition.s.add_packet("LatentTapPairPacket", result)
    cognition.s.log("native_latent_tap_pair", sender_packet["event_id"], {
        "packet_id": result["packet_id"],
        "sender_role": result["sender_role"],
        "receiver_role": result["receiver_role"],
        "token_count": result["token_count"],
        "sender_shape": result["sender_shape"],
        "receiver_shape": result["receiver_shape"],
        "pair_sha256": result["pair_sha256"],
        "status": result["status"],
        "training_authority": 0,
        "native_receiver_authority": 0,
        "production_route": False,
    })
    return result
