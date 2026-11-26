import pytest

from v13.native_tap_contract import (
    NativeTapContractError,
    SENDER_ACTIVATION_SPACE,
    SENDER_CAPTURE_METHOD,
    validate_latent_tap_packet,
    validate_native_final_rmsnorm_output,
)


class Runner:
    tap_id = "lfm2.result_norm.final.v1"
    tap_dim = 2


def native_output():
    return {
        "tap_id": Runner.tap_id,
        "token_ids": [1, 11, 12],
        "vectors": [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]],
        "metrics": {
            "operation": "PREFILL_TAP",
            "normalization": "native_final_RMSNorm_only",
            "pooling": "none",
            "whole_sequence_prefill": True,
            "CAN_LATENT_TAP": True,
            "CAN_LATENT_INJECT": False,
            "CAN_TRAIN_BODY": False,
            "role": "B1_DETAIL",
            "tap_id": Runner.tap_id,
            "runner_revision": "b10964",
            "embedding_dim": 2,
            "prompt_tokens": 3,
        },
    }


def packet_and_data():
    output = native_output()
    contract = validate_native_final_rmsnorm_output(output, Runner(), "B1_DETAIL")
    packet = {
        "role": "B1_DETAIL",
        "tap_id": Runner.tap_id,
        "activation_space": contract["activation_space"],
        "capture_method": contract["capture_method"],
        "runner_revision": contract["runner_revision"],
        "token_ids": list(output["token_ids"]),
        "shape": [3, 2],
        "feature_path": "data/blobs/tap.json",
        "feature_sha256": "a" * 64,
        "role_state": "INDEPENDENT_READ_ONLY_PREFILL",
        "receiver_read_authority": 0,
        "receiver_injection_authority": 0,
        "body_learning_authority": 0,
        "metrics": dict(output["metrics"]),
    }
    data = {"token_ids": list(output["token_ids"]), "vectors": [list(row) for row in output["vectors"]]}
    return packet, data


def test_accepts_native_final_rmsnorm_prefill_and_readback():
    contract = validate_native_final_rmsnorm_output(native_output(), Runner(), "B1_DETAIL")
    assert contract["activation_space"] == SENDER_ACTIVATION_SPACE
    assert contract["capture_method"] == SENDER_CAPTURE_METHOD
    packet, data = packet_and_data()
    checked = validate_latent_tap_packet(
        packet, data, "B1_DETAIL", expected_tap_id=Runner.tap_id,
        expected_runner_revision="b10964",
    )
    assert checked["embedding_dim"] == 2


def test_rejects_static_input_embedding_rows_even_when_shape_matches():
    packet, data = packet_and_data()
    packet["activation_space"] = "INPUT_EMBEDDING_F32"
    with pytest.raises(NativeTapContractError, match="explicit final-RMSNorm"):
        validate_latent_tap_packet(packet, data, "B1_DETAIL")


def test_rejects_pooled_or_non_final_native_output():
    output = native_output()
    output["metrics"]["normalization"] = "input_embedding"
    with pytest.raises(NativeTapContractError, match="read-only native final-RMSNorm"):
        validate_native_final_rmsnorm_output(output, Runner(), "B1_DETAIL")
    output = native_output()
    output["metrics"]["pooling"] = "mean"
    with pytest.raises(NativeTapContractError):
        validate_native_final_rmsnorm_output(output, Runner(), "B1_DETAIL")


def test_rejects_writable_or_injection_capability():
    output = native_output()
    output["metrics"]["CAN_LATENT_INJECT"] = True
    with pytest.raises(NativeTapContractError):
        validate_native_final_rmsnorm_output(output, Runner(), "B1_DETAIL")
    output = native_output()
    output["metrics"]["CAN_TRAIN_BODY"] = True
    with pytest.raises(NativeTapContractError):
        validate_native_final_rmsnorm_output(output, Runner(), "B1_DETAIL")


def test_rejects_wrong_role_tap_and_runner_revision():
    with pytest.raises(NativeTapContractError, match="role is not bound"):
        validate_native_final_rmsnorm_output(native_output(), type("BadRunner", (), {"tap_id": "qwen35.result_norm.final.v1", "tap_dim": 2})(), "B1_DETAIL")
    packet, data = packet_and_data()
    with pytest.raises(NativeTapContractError, match="pinned runner"):
        validate_latent_tap_packet(packet, data, "B1_DETAIL", expected_runner_revision="other")


def test_rejects_nonfinite_or_mismatched_rows():
    output = native_output()
    output["vectors"][1][0] = float("nan")
    with pytest.raises(NativeTapContractError, match="geometry or values"):
        validate_native_final_rmsnorm_output(output, Runner(), "B1_DETAIL")
    packet, data = packet_and_data()
    data["vectors"][0] = [0.1]
    with pytest.raises(NativeTapContractError):
        validate_latent_tap_packet(packet, data, "B1_DETAIL")
