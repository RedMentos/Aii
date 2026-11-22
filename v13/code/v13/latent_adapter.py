"""Low-rank cross-organ activation adapter for the native B3 diagnostic receiver.

The adapter maps paired sender activations into a receiver's input-embedding
width. Training is an opt-in offline operation (NumPy is optional); projection
uses only the Python standard library. Alignment metrics are NOT semantic
utility: every result remains diagnostic, non-promoted and authority-zero.
"""
from __future__ import annotations

from array import array
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys
import tempfile
from typing import Mapping, Sequence

SCHEMA = "v14.cross-organ-latent-adapter/1"
_MAGIC = b"V14LAT1\0"
_MAX_DIM = 8192
_MAX_RANK = 64
_MAX_PAIRS = 4096
_MAX_FILE_BYTES = 64 * 1024 * 1024
_ROLES = frozenset({"B1_DETAIL", "B2_GIST"})
_RECEIVERS = frozenset({"B1_DETAIL", "B2_GIST", "C3_LANGUAGE"})


class LatentAdapterError(ValueError):
    pass


class LatentAdapterUnavailable(RuntimeError):
    pass


def _sha256_text(value: str, name: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value.lower()):
        raise LatentAdapterError(name + " must be a SHA-256 hex digest")
    return value.lower()


def _finite_vector(value, name: str, expected_dim: int | None = None) -> list[float]:
    if not isinstance(value, (list, tuple)) or not value or len(value) > _MAX_DIM:
        raise LatentAdapterError(name + " has invalid vector geometry")
    if expected_dim is not None and len(value) != expected_dim:
        raise LatentAdapterError(name + " dimension mismatch")
    out = []
    for item in value:
        if type(item) not in (int, float) or not math.isfinite(float(item)):
            raise LatentAdapterError(name + " contains a non-finite or non-numeric value")
        out.append(float(item))
    return out


def _validate_pairs(pairs, name: str):
    if not isinstance(pairs, (list, tuple)) or not pairs or len(pairs) > _MAX_PAIRS:
        raise LatentAdapterError(name + " must contain a bounded non-empty pair list")
    pair_ids, source_ids, senders, receivers = set(), set(), [], []
    source_dim = receiver_dim = None
    for pair in pairs:
        if not isinstance(pair, Mapping):
            raise LatentAdapterError(name + " pair must be a mapping")
        pair_id, source_id = pair.get("pair_id"), pair.get("source_id")
        if type(pair_id) is not str or not pair_id or len(pair_id) > 128 or pair_id in pair_ids:
            raise LatentAdapterError(name + " pair IDs must be unique non-empty strings")
        if type(source_id) is not str or not source_id or len(source_id) > 128:
            raise LatentAdapterError(name + " source IDs must be non-empty strings")
        pair_ids.add(pair_id)
        source_ids.add(source_id)
        sender = _finite_vector(pair.get("sender_vector"), name + " sender_vector", source_dim)
        receiver = _finite_vector(pair.get("receiver_vector"), name + " receiver_vector", receiver_dim)
        source_dim = len(sender) if source_dim is None else source_dim
        receiver_dim = len(receiver) if receiver_dim is None else receiver_dim
        senders.append(sender)
        receivers.append(receiver)
    return pair_ids, source_ids, senders, receivers


def _weight_values(adapter: Mapping) -> list[float]:
    values = list(adapter["sender_mean"]) + list(adapter["receiver_mean"])
    values.extend(value for row in adapter["sender_factor"] for value in row)
    values.extend(value for row in adapter["receiver_factor"] for value in row)
    return values


def _serialize(adapter: Mapping) -> bytes:
    values = _weight_values(adapter)
    if not values or any(type(v) not in (int, float) or not math.isfinite(float(v)) for v in values):
        raise LatentAdapterError("adapter weights are malformed")
    packed = array("f", (float(v) for v in values))
    if sys.byteorder != "little":
        packed.byteswap()
    weight_bytes = packed.tobytes()
    header = {key: adapter[key] for key in (
        "schema", "status", "sender_role", "receiver_role", "sender_tap_id", "receiver_tap_id",
        "sender_model_revision", "receiver_model_revision", "sender_model_sha256",
        "receiver_model_sha256", "sender_dim", "receiver_dim", "rank", "metrics",
        "train_pairs", "holdout_pairs", "train_source_count", "holdout_source_count",
        "training_method", "holdout_policy",
        "production_route", "semantic_use_proven", "training_authority", "native_receiver_authority",
    )}
    header["weight_count"] = len(values)
    header["weights_sha256"] = hashlib.sha256(weight_bytes).hexdigest()
    header_bytes = json.dumps(header, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return _MAGIC + struct.pack("<I", len(header_bytes)) + header_bytes + weight_bytes


def _validate_adapter(adapter: Mapping, *, require_candidate: bool = True) -> None:
    if not isinstance(adapter, Mapping) or adapter.get("schema") != SCHEMA:
        raise LatentAdapterError("unsupported latent adapter schema")
    if adapter.get("status") not in {"ALIGNMENT_CANDIDATE", "REJECTED"}:
        raise LatentAdapterError("invalid adapter status")
    if require_candidate and adapter.get("status") != "ALIGNMENT_CANDIDATE":
        raise LatentAdapterError("adapter did not pass its source-disjoint alignment gate")
    if adapter.get("sender_role") not in _ROLES or adapter.get("receiver_role") not in _RECEIVERS or adapter.get("sender_role") == adapter.get("receiver_role"):
        raise LatentAdapterError("invalid sender/receiver role binding")
    _sha256_text(adapter.get("sender_model_sha256"), "sender_model_sha256")
    _sha256_text(adapter.get("receiver_model_sha256"), "receiver_model_sha256")
    for key in ("sender_tap_id", "receiver_tap_id", "sender_model_revision", "receiver_model_revision"):
        if type(adapter.get(key)) is not str or not adapter[key] or len(adapter[key]) > 160:
            raise LatentAdapterError("invalid adapter binding: " + key)
    source_dim, receiver_dim, rank = adapter.get("sender_dim"), adapter.get("receiver_dim"), adapter.get("rank")
    if type(source_dim) is not int or type(receiver_dim) is not int or type(rank) is not int:
        raise LatentAdapterError("adapter dimensions must be integers")
    if not (1 <= source_dim <= _MAX_DIM and 1 <= receiver_dim <= _MAX_DIM and 1 <= rank <= min(_MAX_RANK, source_dim, receiver_dim)):
        raise LatentAdapterError("adapter dimensions are outside bounds")
    if len(adapter.get("sender_mean", ())) != source_dim or len(adapter.get("receiver_mean", ())) != receiver_dim:
        raise LatentAdapterError("adapter mean dimensions do not match metadata")
    if len(adapter.get("sender_factor", ())) != source_dim or any(len(row) != rank for row in adapter["sender_factor"]):
        raise LatentAdapterError("sender factor dimensions do not match metadata")
    if len(adapter.get("receiver_factor", ())) != rank or any(len(row) != receiver_dim for row in adapter["receiver_factor"]):
        raise LatentAdapterError("receiver factor dimensions do not match metadata")
    if (adapter.get("production_route") is not False or adapter.get("semantic_use_proven") is not False
            or adapter.get("training_authority") != 0 or adapter.get("native_receiver_authority") != 0):
        raise LatentAdapterError("latent adapter cannot grant production or learning authority")
    digest = hashlib.sha256(_serialize(adapter)).hexdigest()
    if adapter.get("adapter_sha256") is not None and adapter["adapter_sha256"] != digest:
        raise LatentAdapterError("adapter checkpoint digest mismatch")


def fit_adapter(train_pairs: Sequence[Mapping], holdout_pairs: Sequence[Mapping], *,
                sender_role: str, receiver_role: str, sender_tap_id: str, receiver_tap_id: str,
                sender_model_revision: str, receiver_model_revision: str,
                sender_model_sha256: str, receiver_model_sha256: str,
                rank: int = 16, ridge: float = 1e-4,
                min_relative_improvement: float = 0.02, seed: int = 7) -> dict:
    """Fit a low-rank affine map on paired activations with source-disjoint holdout.

    This is an alignment candidate only. The held-out MSE and shuffled control
    are necessary diagnostics, not semantic/task-utility evidence.
    """
    if sender_role not in _ROLES or receiver_role not in _RECEIVERS or sender_role == receiver_role:
        raise LatentAdapterError("unsupported or identical sender/receiver roles")
    for key, value in (("sender_tap_id", sender_tap_id), ("receiver_tap_id", receiver_tap_id),
                       ("sender_model_revision", sender_model_revision), ("receiver_model_revision", receiver_model_revision)):
        if type(value) is not str or not value or len(value) > 160:
            raise LatentAdapterError("invalid adapter binding: " + key)
    sender_model_sha256 = _sha256_text(sender_model_sha256, "sender_model_sha256")
    receiver_model_sha256 = _sha256_text(receiver_model_sha256, "receiver_model_sha256")
    if type(rank) is not int or not 1 <= rank <= _MAX_RANK:
        raise LatentAdapterError("rank must be between 1 and 64")
    if type(ridge) not in (int, float) or not math.isfinite(float(ridge)) or not 0.0 < float(ridge) <= 1.0:
        raise LatentAdapterError("ridge must be finite and in (0, 1]")
    if type(min_relative_improvement) not in (int, float) or not math.isfinite(float(min_relative_improvement)) or not 0.0 <= float(min_relative_improvement) < 1.0:
        raise LatentAdapterError("invalid minimum holdout improvement")
    if type(seed) is not int:
        raise LatentAdapterError("seed must be an integer")
    train_ids, train_sources, x_train, y_train = _validate_pairs(train_pairs, "train_pairs")
    holdout_ids, holdout_sources, x_holdout, y_holdout = _validate_pairs(holdout_pairs, "holdout_pairs")
    if train_ids & holdout_ids:
        raise LatentAdapterError("paired activation IDs cross train/holdout")
    if train_sources & holdout_sources:
        raise LatentAdapterError("source leakage: a source appears in train and holdout")
    if len(train_pairs) < 8 or len(holdout_pairs) < 4 or len(train_sources) < 4 or len(holdout_sources) < 2:
        raise LatentAdapterError("insufficient independent source groups for alignment holdout")
    sender_dim, receiver_dim = len(x_train[0]), len(y_train[0])
    if len(x_holdout[0]) != sender_dim or len(y_holdout[0]) != receiver_dim:
        raise LatentAdapterError("train/holdout activation dimensions differ")
    if rank > min(_MAX_RANK, sender_dim, receiver_dim, len(train_pairs) - 1):
        raise LatentAdapterError("rank exceeds available geometry or training rows")
    try:
        import numpy as np
    except ImportError as exc:
        raise LatentAdapterUnavailable("NumPy is required only for offline adapter fitting") from exc

    x = np.asarray(x_train, dtype=np.float64)
    y = np.asarray(y_train, dtype=np.float64)
    xh = np.asarray(x_holdout, dtype=np.float64)
    yh = np.asarray(y_holdout, dtype=np.float64)
    x_mean = x.mean(axis=0)
    y_mean = y.mean(axis=0)
    xc = x - x_mean
    yc = y - y_mean
    _, singular, vt = np.linalg.svd(xc, full_matrices=False)
    tolerance = max(xc.shape) * (singular[0] if singular.size else 0.0) * np.finfo(np.float64).eps
    effective_rank = min(rank, int(np.count_nonzero(singular > tolerance)))
    if effective_rank < 1:
        raise LatentAdapterError("sender activations have no trainable variance")
    sender_factor = vt[:effective_rank].T.copy()
    z = xc @ sender_factor
    gram = z.T @ z + float(ridge) * np.eye(effective_rank, dtype=np.float64)
    receiver_factor = np.linalg.solve(gram, z.T @ yc)

    holdout_z = (xh - x_mean) @ sender_factor
    prediction = holdout_z @ receiver_factor + y_mean
    holdout_mse = float(np.mean((prediction - yh) ** 2))
    baseline_mse = float(np.mean((yh - y_mean) ** 2))

    rng = np.random.default_rng(seed)
    shuffled_y = yc[rng.permutation(len(yc))]
    shuffled_factor = np.linalg.solve(gram, z.T @ shuffled_y)
    shuffled_prediction = holdout_z @ shuffled_factor + y_mean
    shuffled_mse = float(np.mean((shuffled_prediction - yh) ** 2))
    relative_improvement = 0.0 if baseline_mse <= 1e-12 else (baseline_mse - holdout_mse) / baseline_mse
    shuffle_advantage = 0.0 if shuffled_mse <= 1e-12 else (shuffled_mse - holdout_mse) / shuffled_mse
    candidate = (
        relative_improvement >= float(min_relative_improvement)
        and holdout_mse + 1e-12 < baseline_mse
        and holdout_mse + 1e-12 < shuffled_mse
    )
    adapter = {
        "schema": SCHEMA,
        "status": "ALIGNMENT_CANDIDATE" if candidate else "REJECTED",
        "sender_role": sender_role,
        "receiver_role": receiver_role,
        "sender_tap_id": sender_tap_id,
        "receiver_tap_id": receiver_tap_id,
        "sender_model_revision": sender_model_revision,
        "receiver_model_revision": receiver_model_revision,
        "sender_model_sha256": sender_model_sha256,
        "receiver_model_sha256": receiver_model_sha256,
        "sender_dim": sender_dim,
        "receiver_dim": receiver_dim,
        "rank": effective_rank,
        "sender_mean": x_mean.tolist(),
        "receiver_mean": y_mean.tolist(),
        "sender_factor": sender_factor.tolist(),
        "receiver_factor": receiver_factor.tolist(),
        "metrics": {
            "holdout_mse": holdout_mse,
            "mean_baseline_mse": baseline_mse,
            "shuffled_train_mse": shuffled_mse,
            "relative_improvement": relative_improvement,
            "shuffle_advantage": shuffle_advantage,
            "min_relative_improvement": float(min_relative_improvement),
        },
        "train_pairs": len(train_pairs),
        "holdout_pairs": len(holdout_pairs),
        "train_source_count": len(train_sources),
        "holdout_source_count": len(holdout_sources),
        "training_method": "SOURCE_PCA_RIDGE_LOW_RANK_AFFINE",
        "holdout_policy": "SOURCE_ID_DISJOINT",
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }
    adapter["adapter_sha256"] = hashlib.sha256(_serialize(adapter)).hexdigest()
    _validate_adapter(adapter, require_candidate=False)
    return adapter


def project_vector(adapter: Mapping, sender_vector, *, sender_model_sha256: str,
                   receiver_model_sha256: str, sender_tap_id: str, receiver_tap_id: str) -> list[float]:
    """Apply the trained adapter without NumPy or other runtime dependencies."""
    _validate_adapter(adapter)
    if (_sha256_text(sender_model_sha256, "sender_model_sha256") != adapter["sender_model_sha256"]
            or _sha256_text(receiver_model_sha256, "receiver_model_sha256") != adapter["receiver_model_sha256"]
            or sender_tap_id != adapter["sender_tap_id"] or receiver_tap_id != adapter["receiver_tap_id"]):
        raise LatentAdapterError("adapter model revision/hash or tap binding mismatch")
    vector = _finite_vector(sender_vector, "sender_vector", adapter["sender_dim"])
    centered = [value - mean for value, mean in zip(vector, adapter["sender_mean"])]
    latent = [sum(centered[i] * adapter["sender_factor"][i][j] for i in range(adapter["sender_dim"]))
              for j in range(adapter["rank"])]
    projected = [adapter["receiver_mean"][j] + sum(latent[k] * adapter["receiver_factor"][k][j]
                 for k in range(adapter["rank"])) for j in range(adapter["receiver_dim"])]
    if any(not math.isfinite(value) for value in projected):
        raise LatentAdapterError("projected activation is non-finite")
    return projected


def project_rows(adapter: Mapping, sender_vectors, **bindings) -> list[list[float]]:
    if not isinstance(sender_vectors, (list, tuple)) or not sender_vectors or len(sender_vectors) > 64:
        raise LatentAdapterError("sender tap must contain 1..64 activation rows")
    return [project_vector(adapter, row, **bindings) for row in sender_vectors]


def save_adapter(adapter: Mapping, path: str | os.PathLike) -> str:
    """Atomically persist adapter parameters; returns the exact checkpoint SHA-256."""
    _validate_adapter(adapter, require_candidate=False)
    data = _serialize(adapter)
    target = Path(path)
    if target.exists() and target.is_symlink():
        raise LatentAdapterError("adapter checkpoint symlink refused")
    parent = target.parent.resolve(strict=True)
    if target.parent.is_symlink() or not parent.is_dir():
        raise LatentAdapterError("adapter checkpoint parent must be a real directory")
    fd, temporary = tempfile.mkstemp(prefix="." + target.name + ".", dir=str(parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return hashlib.sha256(data).hexdigest()


def load_adapter(path: str | os.PathLike) -> dict:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise LatentAdapterError("adapter checkpoint must be a regular non-symlink file")
    if target.stat().st_size > _MAX_FILE_BYTES:
        raise LatentAdapterError("adapter checkpoint exceeds size limit")
    data = target.read_bytes()
    if len(data) < len(_MAGIC) + 4 or data[:len(_MAGIC)] != _MAGIC:
        raise LatentAdapterError("adapter checkpoint magic mismatch")
    header_size = struct.unpack("<I", data[len(_MAGIC):len(_MAGIC) + 4])[0]
    header_start = len(_MAGIC) + 4
    header_end = header_start + header_size
    if header_size > 65536 or header_end > len(data):
        raise LatentAdapterError("adapter checkpoint header is invalid")
    try:
        header = json.loads(data[header_start:header_end].decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise LatentAdapterError("adapter checkpoint header cannot be decoded") from exc
    payload = data[header_end:]
    if hashlib.sha256(payload).hexdigest() != header.get("weights_sha256"):
        raise LatentAdapterError("adapter checkpoint weight digest mismatch")
    count = header.get("weight_count")
    if type(count) is not int or count < 1 or count * 4 != len(payload):
        raise LatentAdapterError("adapter checkpoint weight count mismatch")
    weights = array("f")
    weights.frombytes(payload)
    if sys.byteorder != "little":
        weights.byteswap()
    if any(not math.isfinite(value) for value in weights):
        raise LatentAdapterError("adapter checkpoint contains non-finite weights")
    source_dim, receiver_dim, rank = header.get("sender_dim"), header.get("receiver_dim"), header.get("rank")
    if (type(source_dim) is not int or type(receiver_dim) is not int or type(rank) is not int
            or not 1 <= source_dim <= _MAX_DIM or not 1 <= receiver_dim <= _MAX_DIM
            or not 1 <= rank <= min(_MAX_RANK, source_dim, receiver_dim)):
        raise LatentAdapterError("adapter checkpoint dimensions are invalid")
    expected_count = source_dim + receiver_dim + source_dim * rank + rank * receiver_dim
    if expected_count != count:
        raise LatentAdapterError("adapter checkpoint tensor geometry mismatch")
    cursor = 0
    sender_mean = list(weights[cursor:cursor + source_dim]); cursor += source_dim
    receiver_mean = list(weights[cursor:cursor + receiver_dim]); cursor += receiver_dim
    sender_flat = list(weights[cursor:cursor + source_dim * rank]); cursor += source_dim * rank
    receiver_flat = list(weights[cursor:cursor + rank * receiver_dim])
    header.pop("weight_count", None)
    header.pop("weights_sha256", None)
    adapter = dict(header)
    adapter.update({
        "sender_mean": sender_mean,
        "receiver_mean": receiver_mean,
        "sender_factor": [sender_flat[i * rank:(i + 1) * rank] for i in range(source_dim)],
        "receiver_factor": [receiver_flat[i * receiver_dim:(i + 1) * receiver_dim] for i in range(rank)],
        "adapter_sha256": hashlib.sha256(data).hexdigest(),
    })
    _validate_adapter(adapter, require_candidate=False)
    return adapter


def probe_native_receiver(adapter: Mapping, sender_vectors, *, home, model_path,
                          source_id: str, generation_id: str, position_ids,
                          position_mode: str, deadline: float, confirm: bool = False,
                          runtime_idle: bool = False, threads: int = 1,
                          binary_path=None, cancel_event=None) -> dict:
    """Feed projected rows to the existing opt-in llama.cpp receiver probe.

    A native input-effect receipt proves only that llama.cpp consumed a tensor.
    It does not prove semantic transfer, useful B3 communication or production
    authority; task-level held-out utility remains a separate mandatory gate.
    """
    _validate_adapter(adapter)
    if confirm is not True or runtime_idle is not True:
        raise PermissionError("native latent adapter probe requires explicit confirmation while Runtime is idle")
    mapped = project_rows(
        adapter, sender_vectors,
        sender_model_sha256=adapter["sender_model_sha256"],
        receiver_model_sha256=adapter["receiver_model_sha256"],
        sender_tap_id=adapter["sender_tap_id"],
        receiver_tap_id=adapter["receiver_tap_id"],
    )
    from . import native_latent_receiver
    receipt = native_latent_receiver.probe(
        home=home, model_path=model_path,
        expected_model_sha256=adapter["receiver_model_sha256"],
        sender_role=adapter["sender_role"], receiver_role=adapter["receiver_role"],
        sender_tap_id=adapter["sender_tap_id"],
        sender_model_revision=adapter["sender_model_revision"],
        sender_model_sha256=adapter["sender_model_sha256"], tokenizer_revision=None,
        receiver_model_revision=adapter["receiver_model_revision"],
        source_id=source_id, generation_id=generation_id,
        vectors=mapped, position_ids=position_ids, position_mode=position_mode,
        deadline=deadline, threads=threads, binary_path=binary_path, cancel_event=cancel_event,
    )
    return {
        "schema": "v14.cross-organ-latent-probe/1",
        "status": "DIAGNOSTIC_ONLY",
        "adapter_sha256": adapter["adapter_sha256"],
        "adapter_status": adapter["status"],
        "adapter_rank": adapter["rank"],
        "training_method": adapter["training_method"],
        "holdout_policy": adapter["holdout_policy"],
        "sender_dim": adapter["sender_dim"],
        "receiver_dim": adapter["receiver_dim"],
        "projected_rows": len(mapped),
        "projected_input_sha256": receipt["input_sha256"],
        "receiver_probe": receipt,
        "semantic_use_proven": False,
        "production_route": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }
