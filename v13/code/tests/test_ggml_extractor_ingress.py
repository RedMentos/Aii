import hashlib
import struct

import pytest

from v13.ggml_extractor_ingress import (
    EXTRACTOR_REVISION,
    SCHEMA,
    load_activation_frame,
    receive_activation_packet,
)
from v13.latent_bridge import Projector


def write_npy(path, shape, values, descr="<f4", fortran=False):
    header = repr({"descr": descr, "fortran_order": fortran, "shape": tuple(shape)}).encode("latin1")
    padding = (64 - ((10 + len(header) + 1) % 64)) % 64
    header += b" " * padding + b"\n"
    with open(path, "wb") as handle:
        handle.write(b"\x93NUMPY\x01\x00")
        handle.write(struct.pack("<H", len(header)))
        handle.write(header)
        if descr == "<f4":
            handle.write(struct.pack("<" + "f" * len(values), *values))
        else:
            handle.write(b"\x00" * (len(values) * 4))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metadata(path, **changes):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    value = {
        "schema": SCHEMA,
        "extractor": "ggml-extractor",
        "extractor_version": "0.2.0",
        "extractor_revision": EXTRACTOR_REVISION,
        "llama_cpp_revision": "b29c606e28a01b1bc8c1351026a0fa6e616bf6c4",
        "model_role": "B1_DETAIL",
        "model_id": "fixture/model",
        "model_revision": "a" * 40,
        "model_sha256": "b" * 64,
        "architecture": "fixture",
        "n_layers": 4,
        "layer_index": 2,
        "model_n_embd": 2,
        "tensor_name": "l_out-2",
        "token_selector": "last",
        "frame_index": 0,
        "request_index": 0,
        "source_id": "fixture:turn-1",
        "source_sha256": "c" * 64,
        "generation_id": "generation-1",
        "capture_sha256": digest,
    }
    value.update(changes)
    return value


def capture(tmp_path, values=(0.25, -0.5), shape=(1, 1, 2), **meta_changes):
    path = tmp_path / "hidden.npy"
    write_npy(path, shape, values)
    return path, metadata(path, **meta_changes)


def test_reads_numeric_activation_and_delivers_to_existing_receiver_port(tmp_path):
    path, meta = capture(tmp_path)
    frame = load_activation_frame(path, meta)
    assert frame.values == (0.25, -0.5)
    assert frame.width == 2
    assert frame.compatibility_status == "UNVERIFIED"

    projector = Projector("B1_DETAIL", "B3", 2, 2)
    projector.w = [[1.0, 0.0], [0.0, 1.0]]
    packet = frame.project(projector)
    receipt = receive_activation_packet(
        packet, "B3", "generation-1", {"fixture:turn-1"}, projector.revision()
    )
    assert receipt["values"] == [0.25, -0.5]
    assert receipt["status"] == "SHADOW_UNVERIFIED"
    assert receipt["training_authority"] is False
    assert receipt["action_authority"] is False
    assert "prompt" not in packet["activation_ref"]


def test_selects_requested_frame_and_request_without_loading_whole_array(tmp_path):
    path, meta = capture(
        tmp_path,
        values=(1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0),
        shape=(2, 2, 2), frame_index=1, request_index=0,
    )
    assert load_activation_frame(path, meta).values == (5.0, 6.0)


def test_current_registry_llama_revision_is_not_upstream_verified(tmp_path):
    path, meta = capture(tmp_path)
    frame = load_activation_frame(path, meta)
    assert frame.compatibility_status == "UNVERIFIED"


def test_upstream_reported_revision_is_not_android_verified(tmp_path):
    path, meta = capture(tmp_path, llama_cpp_revision="5ecbe1ac1")
    frame = load_activation_frame(path, meta)
    assert frame.compatibility_status == "UPSTREAM_REPORTED_LINUX_MACOS_ONLY"


@pytest.mark.parametrize("field,value", [
    ("model_sha256", "not-a-hash"),
    ("source_sha256", "f"),
    ("model_revision", "z" * 40),
    ("extractor_revision", "0" * 40),
    ("tensor_name", "l_out-3"),
    ("layer_index", 4),
    ("token_selector", "absolute:17"),
    ("model_n_embd", 3),
    ("source_id", ""),
])
def test_rejects_bad_metadata(tmp_path, field, value):
    path, meta = capture(tmp_path, **{field: value})
    with pytest.raises(ValueError):
        load_activation_frame(path, meta)


def test_rejects_unexpected_private_prompt_field(tmp_path):
    path, meta = capture(tmp_path)
    meta["prompt_text"] = "must not be persisted"
    with pytest.raises(ValueError, match="exact schema"):
        load_activation_frame(path, meta)


def test_rejects_wrong_capture_hash_and_truncated_payload(tmp_path):
    path, meta = capture(tmp_path)
    meta["capture_sha256"] = "d" * 64
    with pytest.raises(ValueError, match="SHA-256"):
        load_activation_frame(path, meta)
    path.write_bytes(path.read_bytes()[:-1])
    meta["capture_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="payload size"):
        load_activation_frame(path, meta)


def test_rejects_nonfinite_activation_values(tmp_path):
    path, _ = capture(tmp_path, values=(float("nan"), 1.0))
    meta = metadata(path)
    with pytest.raises(ValueError, match="nonfinite"):
        load_activation_frame(path, meta)


def test_rejects_fortran_order_or_non_float32(tmp_path):
    path = tmp_path / "hidden.npy"
    write_npy(path, (1, 1, 2), (1.0, 2.0), fortran=True)
    with pytest.raises(ValueError, match="float32 C-order"):
        load_activation_frame(path, metadata(path))
    write_npy(path, (1, 1, 2), (1.0, 2.0), descr="|i4")
    with pytest.raises(ValueError, match="float32 C-order"):
        load_activation_frame(path, metadata(path))


def test_rejects_symlink_and_excessive_size(tmp_path):
    real, meta = capture(tmp_path)
    link = tmp_path / "linked.npy"
    link.symlink_to(real)
    with pytest.raises(ValueError, match="cannot be opened safely"):
        load_activation_frame(link, meta)
    big = tmp_path / "big.npy"
    write_npy(big, (1, 1, 512), [0.0] * 512)
    big_meta = metadata(big, model_n_embd=512)
    with pytest.raises(ValueError, match="byte budget"):
        load_activation_frame(big, big_meta, max_capture_bytes=1024)


def test_projector_rejects_mismatched_source_role(tmp_path):
    path, meta = capture(tmp_path)
    frame = load_activation_frame(path, meta)
    with pytest.raises(ValueError, match="source role"):
        frame.project(Projector("C3", "B3", 2, 2))


def test_receiver_rejects_missing_capture_provenance_and_authority_escalation(tmp_path):
    path, meta = capture(tmp_path)
    frame = load_activation_frame(path, meta)
    projector = Projector("B1_DETAIL", "B3", 2, 2)
    packet = frame.project(projector)
    bad = dict(packet)
    bad.pop("activation_ref")
    with pytest.raises(ValueError, match="provenance"):
        receive_activation_packet(bad, "B3", "generation-1", {"fixture:turn-1"}, projector.revision())
    bad = dict(packet)
    bad["training_authority"] = True
    with pytest.raises(PermissionError, match="cannot grant authority"):
        receive_activation_packet(bad, "B3", "generation-1", {"fixture:turn-1"}, projector.revision())
    with pytest.raises(PermissionError):
        receive_activation_packet(packet, "B3", "generation-2", {"fixture:turn-1"}, projector.revision())
