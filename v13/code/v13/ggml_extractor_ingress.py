"""Bounded numeric ingress for ggml-extractor HiddenStates NPY output.

This adapter consumes float32 activation rows, not text/JSON messages. It does
not capture model states itself, attest the producer, inject receiver KV state,
or grant training/action authority. The current upstream extractor is only
reported tested on Linux/macOS; Android and the repository's current llama.cpp
revision remain unverified.
"""
from __future__ import annotations

import ast
import hashlib
import math
import os
import re
import stat
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .latent_bridge import receive

SCHEMA = "v14.ggml-extractor-capture/1"
PACKET_SCHEMA = "v14.ggml-extractor-activation-packet/1"
EXTRACTOR_NAME = "ggml-extractor"
EXTRACTOR_VERSION = "0.2.0"
EXTRACTOR_REVISION = "0449f6335ce99f009c204e8c844a78eca6e9289d"
UPSTREAM_REPORTED_LLAMA_CPP_REVISION = "5ecbe1ac1"
MAX_CAPTURE_BYTES = 16 * 1024 * 1024
MAX_FRAMES = 64
MAX_REQUESTS = 16
MAX_WIDTH = 8192
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_HEX7_40 = re.compile(r"[0-9a-f]{7,40}\Z")
_ROLES = {"A3", "B1_DETAIL", "B2_GIST", "B3", "C3", "OTHER"}
_REQUIRED_METADATA = {
    "schema", "extractor", "extractor_version", "extractor_revision",
    "llama_cpp_revision", "model_role", "model_id", "model_revision",
    "model_sha256", "architecture", "n_layers", "layer_index",
    "model_n_embd", "tensor_name", "token_selector", "frame_index",
    "request_index", "source_id", "source_sha256", "generation_id",
    "capture_sha256",
}


@dataclass(frozen=True)
class ActivationFrame:
    """One selected hidden-state row plus non-text provenance."""

    values: tuple[float, ...]
    model_role: str
    model_id: str
    model_revision: str
    model_sha256: str
    architecture: str
    layer_index: int
    tensor_name: str
    token_selector: str
    llama_cpp_revision: str
    extractor_revision: str
    source_id: str
    source_sha256: str
    generation_id: str
    capture_sha256: str
    shape: tuple[int, int, int]
    compatibility_status: str

    @property
    def width(self) -> int:
        return len(self.values)

    def project(self, projector: Any) -> dict:
        """Create a numeric B3 candidate packet; never authorizes learning."""
        if getattr(projector, "ni", None) != self.width:
            raise ValueError("projector input width does not match captured activation")
        if getattr(projector, "source", None) != self.model_role:
            raise ValueError("projector source role does not match captured model role")
        if not callable(getattr(projector, "project", None)):
            raise TypeError("projector must expose project()")
        packet = projector.project(list(self.values), self.source_id, self.generation_id)
        packet["activation_ref"] = {
            "schema": PACKET_SCHEMA,
            "model_role": self.model_role,
            "model_id": self.model_id,
            "model_revision": self.model_revision,
            "model_sha256": self.model_sha256,
            "architecture": self.architecture,
            "layer_index": self.layer_index,
            "tensor_name": self.tensor_name,
            "token_selector": self.token_selector,
            "llama_cpp_revision": self.llama_cpp_revision,
            "extractor": EXTRACTOR_NAME,
            "extractor_version": EXTRACTOR_VERSION,
            "extractor_revision": self.extractor_revision,
            "capture_sha256": self.capture_sha256,
            "source_sha256": self.source_sha256,
            "npy_shape": list(self.shape),
            "compatibility_status": self.compatibility_status,
            "native_capture_status": "UNATTESTED",
        }
        packet["activation_capture_status"] = "UNVERIFIED"
        packet["authority"] = "EXPERIMENTAL_NUMERIC_ONLY"
        packet["training_authority"] = False
        packet["action_authority"] = False
        return packet


def _bounded_string(value: Any, name: str, maximum: int = 256) -> str:
    if type(value) is not str or not value.strip() or len(value) > maximum:
        raise ValueError("invalid " + name)
    return value


def _validate_metadata(metadata: Any) -> dict:
    if type(metadata) is not dict or set(metadata) != _REQUIRED_METADATA:
        raise ValueError("capture metadata fields do not match the exact schema")
    if metadata["schema"] != SCHEMA:
        raise ValueError("capture metadata schema mismatch")
    if metadata["extractor"] != EXTRACTOR_NAME or metadata["extractor_version"] != EXTRACTOR_VERSION:
        raise ValueError("unsupported ggml-extractor version")
    if metadata["extractor_revision"] != EXTRACTOR_REVISION:
        raise ValueError("ggml-extractor source revision is not pinned")
    if type(metadata["llama_cpp_revision"]) is not str or not _HEX7_40.fullmatch(metadata["llama_cpp_revision"]):
        raise ValueError("invalid llama.cpp source revision")
    if type(metadata["model_role"]) is not str or metadata["model_role"] not in _ROLES:
        raise ValueError("invalid model role")
    _bounded_string(metadata["model_id"], "model_id")
    _bounded_string(metadata["architecture"], "architecture", 64)
    _bounded_string(metadata["source_id"], "source_id", 128)
    _bounded_string(metadata["generation_id"], "generation_id", 128)
    if type(metadata["model_revision"]) is not str or not _HEX40.fullmatch(metadata["model_revision"]):
        raise ValueError("invalid model_revision")
    for key in ("model_sha256", "source_sha256", "capture_sha256"):
        if type(metadata[key]) is not str or not _HEX64.fullmatch(metadata[key]):
            raise ValueError("invalid " + key)
    for key, low, high in (
        ("n_layers", 1, 256), ("model_n_embd", 1, MAX_WIDTH),
        ("layer_index", 0, 255), ("frame_index", 0, MAX_FRAMES - 1),
        ("request_index", 0, MAX_REQUESTS - 1),
    ):
        value = metadata[key]
        if type(value) is not int or not low <= value <= high:
            raise ValueError("invalid " + key)
    if metadata["layer_index"] >= metadata["n_layers"]:
        raise ValueError("layer index exceeds model layer count")
    if metadata["tensor_name"] != "l_out-" + str(metadata["layer_index"]):
        raise ValueError("tensor name does not match selected transformer layer")
    selector = metadata["token_selector"]
    if type(selector) is not str or not (
        selector in {"last", "generated"}
        or re.fullmatch(r"from_end:(?:0|[1-9][0-9]?)", selector)
    ):
        raise ValueError("invalid token selector")
    return dict(metadata)


def _read_npy_header(handle) -> tuple[tuple[int, int, int], int]:
    if handle.read(6) != b"\x93NUMPY":
        raise ValueError("not a NumPy NPY file")
    version = handle.read(2)
    if version != b"\x01\x00":
        raise ValueError("only NPY v1.0 captures are supported")
    length_bytes = handle.read(2)
    if len(length_bytes) != 2:
        raise ValueError("truncated NPY header length")
    header_length = struct.unpack("<H", length_bytes)[0]
    if not 1 <= header_length <= 4096:
        raise ValueError("NPY header length is outside the bound")
    header_bytes = handle.read(header_length)
    if len(header_bytes) != header_length:
        raise ValueError("truncated NPY header")
    try:
        header = ast.literal_eval(header_bytes.decode("latin1").strip())
    except Exception:
        raise ValueError("invalid NPY header") from None
    if type(header) is not dict or set(header) != {"descr", "fortran_order", "shape"}:
        raise ValueError("unexpected NPY header fields")
    if header["descr"] != "<f4" or header["fortran_order"] is not False:
        raise ValueError("capture must be little-endian float32 C-order")
    shape = header["shape"]
    if type(shape) is not tuple or len(shape) != 3:
        raise ValueError("capture shape must be (frames, requests, embedding_width)")
    frames, requests, width = shape
    if any(type(x) is not int for x in shape):
        raise ValueError("capture dimensions must be integers")
    if not 1 <= frames <= MAX_FRAMES or not 1 <= requests <= MAX_REQUESTS or not 1 <= width <= MAX_WIDTH:
        raise ValueError("capture dimensions exceed bounded limits")
    return (frames, requests, width), 10 + header_length


def load_activation_frame(
    npy_path: str | os.PathLike[str],
    metadata: dict,
    *,
    max_capture_bytes: int = MAX_CAPTURE_BYTES,
) -> ActivationFrame:
    """Read one row from ggml-extractor's (frames, requests, n_embd) NPY.

    The NPY file is streamed for hashing and only the selected float32 row is
    allocated. metadata is a local sidecar supplied by the native wrapper;
    it is validated but cannot cryptographically attest that wrapper.
    """
    meta = _validate_metadata(metadata)
    if type(max_capture_bytes) is not int or not 1024 <= max_capture_bytes <= MAX_CAPTURE_BYTES:
        raise ValueError("invalid capture byte budget")
    path = Path(npy_path)
    if path.is_symlink():
        raise ValueError("capture file cannot be opened safely: symlink")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ValueError("capture file cannot be opened safely: " + type(exc).__name__) from None
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > max_capture_bytes:
            raise ValueError("capture file is not regular or exceeds byte budget")
        shape, data_offset = _read_npy_header(handle)
        frames, requests, width = shape
        expected_size = data_offset + frames * requests * width * 4
        if info.st_size != expected_size:
            raise ValueError("NPY payload size does not match declared shape")
        if width != meta["model_n_embd"]:
            raise ValueError("NPY embedding width does not match model metadata")
        if meta["frame_index"] >= frames or meta["request_index"] >= requests:
            raise ValueError("selected frame/request index is outside the capture")
        handle.seek(0)
        digest = hashlib.sha256()
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
        actual_sha = digest.hexdigest()
        if actual_sha != meta["capture_sha256"]:
            raise ValueError("capture SHA-256 mismatch")
        row_index = meta["frame_index"] * requests + meta["request_index"]
        handle.seek(data_offset + row_index * width * 4)
        raw = handle.read(width * 4)
        if len(raw) != width * 4:
            raise ValueError("truncated activation row")
        values = struct.unpack("<" + "f" * width, raw)
    if any(not math.isfinite(value) or abs(value) >= 1e6 for value in values):
        raise ValueError("activation contains nonfinite or unbounded values")
    compatibility = (
        "UPSTREAM_REPORTED_LINUX_MACOS_ONLY"
        if meta["llama_cpp_revision"].startswith(UPSTREAM_REPORTED_LLAMA_CPP_REVISION)
        else "UNVERIFIED"
    )
    return ActivationFrame(
        values=tuple(float(value) for value in values),
        model_role=meta["model_role"], model_id=meta["model_id"],
        model_revision=meta["model_revision"], model_sha256=meta["model_sha256"],
        architecture=meta["architecture"], layer_index=meta["layer_index"],
        tensor_name=meta["tensor_name"], token_selector=meta["token_selector"],
        llama_cpp_revision=meta["llama_cpp_revision"],
        extractor_revision=meta["extractor_revision"], source_id=meta["source_id"],
        source_sha256=meta["source_sha256"], generation_id=meta["generation_id"],
        capture_sha256=actual_sha, shape=shape,
        compatibility_status=compatibility,
    )


def _validate_activation_ref(ref: Any) -> None:
    required = {
        "schema", "model_role", "model_id", "model_revision", "model_sha256",
        "architecture", "layer_index", "tensor_name", "token_selector",
        "llama_cpp_revision", "extractor", "extractor_version",
        "extractor_revision", "capture_sha256", "source_sha256",
        "npy_shape", "compatibility_status", "native_capture_status",
    }
    if type(ref) is not dict or set(ref) != required or ref.get("schema") != PACKET_SCHEMA:
        raise ValueError("activation provenance fields do not match the exact schema")
    if type(ref.get("model_role")) is not str or ref["model_role"] not in _ROLES:
        raise ValueError("activation model role is invalid")
    _bounded_string(ref.get("model_id"), "activation model_id")
    _bounded_string(ref.get("architecture"), "activation architecture", 64)
    if type(ref.get("model_revision")) is not str or not _HEX40.fullmatch(ref["model_revision"]):
        raise ValueError("activation model revision is invalid")
    for key in ("model_sha256", "capture_sha256", "source_sha256"):
        if type(ref.get(key)) is not str or not _HEX64.fullmatch(ref[key]):
            raise ValueError("activation digest is invalid: " + key)
    layer = ref.get("layer_index")
    if type(layer) is not int or not 0 <= layer < 256 or ref.get("tensor_name") != "l_out-" + str(layer):
        raise ValueError("activation tensor/layer binding is invalid")
    selector = ref.get("token_selector")
    if type(selector) is not str or not (
        selector in {"last", "generated"}
        or re.fullmatch(r"from_end:(?:0|[1-9][0-9]?)", selector)
    ):
        raise ValueError("activation token selector is invalid")
    if type(ref.get("llama_cpp_revision")) is not str or not _HEX7_40.fullmatch(ref["llama_cpp_revision"]):
        raise ValueError("activation llama.cpp revision is invalid")
    if (ref.get("extractor") != EXTRACTOR_NAME or ref.get("extractor_version") != EXTRACTOR_VERSION
            or ref.get("extractor_revision") != EXTRACTOR_REVISION):
        raise ValueError("activation extractor provenance is invalid")
    shape = ref.get("npy_shape")
    if type(shape) is not list or len(shape) != 3 or any(type(x) is not int for x in shape):
        raise ValueError("activation NPY shape is invalid")
    if not (1 <= shape[0] <= MAX_FRAMES and 1 <= shape[1] <= MAX_REQUESTS and 1 <= shape[2] <= MAX_WIDTH):
        raise ValueError("activation NPY shape exceeds bounds")
    if ref.get("compatibility_status") not in {"UNVERIFIED", "UPSTREAM_REPORTED_LINUX_MACOS_ONLY"}:
        raise ValueError("activation compatibility status is invalid")
    if ref.get("native_capture_status") != "UNATTESTED":
        raise PermissionError("native capture attestation is not implemented")


def receive_activation_packet(packet: dict, target: str, generation: str,
                              source_ids: set[str], projector_revision: str) -> dict:
    """Validate and deliver numeric activation values to the existing receiver port.

    The result is always SHADOW_UNVERIFIED until a real local native capture,
    model/runner compatibility, and target-device receipt exist.
    """
    if type(packet) is not dict or packet.get("activation_capture_status") != "UNVERIFIED":
        raise PermissionError("only explicitly unverified activation packets are accepted in shadow")
    ref = packet.get("activation_ref")
    _validate_activation_ref(ref)
    if packet.get("authority") != "EXPERIMENTAL_NUMERIC_ONLY":
        raise PermissionError("activation packet authority is invalid")
    if packet.get("training_authority") is not False or packet.get("action_authority") is not False:
        raise PermissionError("activation packet cannot grant authority")
    values = receive(packet, target, generation, source_ids, projector_revision)
    return {
        "schema": "v14.ggml-extractor-receive/1",
        "target": target,
        "source_id": packet.get("source_id"),
        "generation": generation,
        "values": values,
        "status": "SHADOW_UNVERIFIED",
        "native_capture_status": "UNATTESTED",
        "training_authority": False,
        "action_authority": False,
    }
