"""Low-rank, source-paired native latent alignment for V14.

This is an experimental adapter between real model tap spaces. It does not
modify GGUF masters, grant B3 routing authority, or establish semantic utility.
Only committed, locally admitted tap pairs can train it; native consumption
still requires the separate one-shot Callosum probe approval.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import tempfile

import numpy as np

SCHEMA = "v14.native-latent-adapter/1"
SENDER_ROLES = frozenset({"B1_DETAIL", "B2_GIST"})
RECEIVER_ROLES = frozenset({"B1_DETAIL", "B2_GIST", "C3_LANGUAGE"})
MAX_ROWS = 64
MAX_DIM = 8192
MAX_ELEMENTS = 262144
MAX_RANK = 64
MIN_PAIRS = 8
MAX_PAIRS = 256
MAX_STEPS = 2000
MAX_CHECKPOINT_BYTES = 64 * 1024 * 1024
FILE_RE = re.compile(r"adapter-[0-9a-f]{16}\.npz\Z")


def _roles(sender_role, receiver_role):
    if sender_role not in SENDER_ROLES or receiver_role not in RECEIVER_ROLES or sender_role == receiver_role:
        raise ValueError("native latent adapter requires distinct B1/B2 sender and B1/B2/C3 receiver roles")


def _revision(value):
    if type(value) is not str or not value or len(value) > 160:
        raise ValueError("model revision is missing or malformed")
    return value


def _matrix(value, *, rows=None, dim=None):
    try:
        result = np.asarray(value, dtype=np.float32)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("latent matrix is not numeric") from exc
    if result.ndim != 2 or not 1 <= result.shape[0] <= MAX_ROWS or not 1 <= result.shape[1] <= MAX_DIM:
        raise ValueError("latent matrix geometry outside bounds")
    if result.shape[0] * result.shape[1] > MAX_ELEMENTS:
        raise ValueError("latent matrix exceeds element budget")
    if rows is not None and result.shape[0] != rows:
        raise ValueError("latent row count mismatch")
    if dim is not None and result.shape[1] != dim:
        raise ValueError("latent dimension mismatch")
    if not bool(np.isfinite(result).all()) or (result.size and float(np.abs(result).max()) > 1.0e6):
        raise ValueError("latent matrix contains non-finite or unbounded values")
    return np.ascontiguousarray(result, dtype=np.float32)


def resample_rows(value, slots):
    """Deterministically align sequence lengths without exchanging text or token IDs."""
    matrix = _matrix(value)
    if type(slots) is not int or not 1 <= slots <= MAX_ROWS:
        raise ValueError("latent slot count outside bounds")
    if slots == matrix.shape[0]:
        return matrix.copy()
    if slots == 1:
        return matrix.mean(axis=0, keepdims=True, dtype=np.float64).astype(np.float32)
    positions = np.linspace(0.0, float(matrix.shape[0] - 1), slots, dtype=np.float64)
    lower = np.floor(positions).astype(np.int64)
    upper = np.minimum(lower + 1, matrix.shape[0] - 1)
    fraction = (positions - lower).astype(np.float32)[:, None]
    return np.ascontiguousarray(matrix[lower] * (1.0 - fraction) + matrix[upper] * fraction, dtype=np.float32)


def _mse_cosine(prediction, target):
    error = prediction - target
    loss = float(np.mean(error * error, dtype=np.float64))
    pn = np.linalg.norm(prediction, axis=1)
    tn = np.linalg.norm(target, axis=1)
    cosine = float(np.mean(np.sum(prediction * target, axis=1) / np.maximum(pn * tn, 1.0e-8)))
    if not math.isfinite(loss) or not math.isfinite(cosine):
        raise ValueError("latent alignment metric is non-finite")
    return loss, cosine


def _atomic_bytes(path, raw):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("adapter target cannot be a symlink")
    fd, temporary = tempfile.mkstemp(prefix=".adapter-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _atomic_json(path, value):
    _atomic_bytes(path, (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8"))


def adapter_directory(home, sender_role, receiver_role, sender_revision, receiver_revision):
    _roles(sender_role, receiver_role)
    sender_revision = _revision(sender_revision)
    receiver_revision = _revision(receiver_revision)
    return (Path(home) / "data" / "latent_adapters" /
            (sender_role + "__to__" + receiver_role) /
            (hashlib.sha256(sender_revision.encode()).hexdigest()[:12] + "_" +
             hashlib.sha256(receiver_revision.encode()).hexdigest()[:12]))


def _packet_source(packet):
    source_ref = packet.get("source_ref")
    if not isinstance(source_ref, dict) or type(source_ref.get("source_id")) is not str or not source_ref["source_id"]:
        raise ValueError("tap packet lacks a source-bound SourceRef")
    return source_ref


def pairs_from_packets(packets, read_tap, sender_role, receiver_role):
    """Build pairs only from committed tap packets on the exact same event/source/generation."""
    _roles(sender_role, receiver_role)
    if not callable(read_tap):
        raise ValueError("read_tap callback is required")
    grouped = {}
    for packet in packets:
        if not isinstance(packet, dict) or packet.get("kind") != "LatentTapPacket":
            continue
        role = packet.get("role")
        if role not in (sender_role, receiver_role):
            continue
        event_id = packet.get("event_id")
        generation = packet.get("brain_generation_id")
        if type(event_id) is not str or not event_id or type(generation) is not str or not generation:
            continue
        source_ref = _packet_source(packet)
        if packet.get("source_ref") != source_ref or packet.get("tap_id") is None:
            continue
        group = grouped.setdefault((event_id, generation, source_ref["source_id"]), {})
        group.setdefault(role, packet)
    pairs = []
    for (event_id, generation, source_id), group in grouped.items():
        sender = group.get(sender_role)
        receiver = group.get(receiver_role)
        if not sender or not receiver:
            continue
        if (sender.get("source_ref") != receiver.get("source_ref")
                or sender.get("event_id") != receiver.get("event_id")
                or sender.get("brain_generation_id") != receiver.get("brain_generation_id")):
            continue
        sender_revision = sender.get("model_revision")
        receiver_revision = receiver.get("model_revision")
        sender_tap = sender.get("tap_id")
        receiver_tap = receiver.get("tap_id")
        if not all(type(x) is str and x for x in (sender_revision, receiver_revision, sender_tap, receiver_tap)):
            continue
        sender_data = read_tap(sender)
        receiver_data = read_tap(receiver)
        sender_vectors = _matrix(sender_data.get("vectors"))
        receiver_vectors = _matrix(receiver_data.get("vectors"))
        if (len(sender_data.get("token_ids", [])) != sender_vectors.shape[0]
                or len(receiver_data.get("token_ids", [])) != receiver_vectors.shape[0]):
            raise ValueError("tap token/vector row count mismatch")
        pairs.append({
            "source_id": source_id,
            "event_id": event_id,
            "generation_id": generation,
            "source_ref": dict(sender["source_ref"]),
            "sender_role": sender_role,
            "receiver_role": receiver_role,
            "sender_model_revision": sender_revision,
            "receiver_model_revision": receiver_revision,
            "sender_tap_id": sender_tap,
            "receiver_tap_id": receiver_tap,
            "sender_vectors": sender_vectors,
            "receiver_vectors": receiver_vectors,
            "committed": True,
        })
    pairs.sort(key=lambda item: hashlib.sha256((item["source_id"] + item["event_id"]).encode()).hexdigest())
    return pairs[:MAX_PAIRS]


def collect_pairs(store, read_tap, session, sender_role, receiver_role, limit=256):
    if type(session) is not str or not session:
        raise ValueError("current session is required for latent adapter training")
    if type(limit) is not int or not 1 <= limit <= MAX_PAIRS:
        raise ValueError("tap packet limit outside bounds")
    rows = store.rows(
        "SELECT p.payload FROM packets p JOIN events e ON e.id=p.event_id "
        "WHERE p.kind='LatentTapPacket' AND e.session_id=? ORDER BY p.rowid DESC LIMIT ?",
        (session, limit * 2),
    )
    packets = []
    for row in rows:
        try:
            packets.append(json.loads(row["payload"]))
        except (TypeError, ValueError):
            continue
    return pairs_from_packets(packets, read_tap, sender_role, receiver_role)


class LowRankAdapter:
    """Trainable low-rank nonlinear map from one native tap space to another."""

    def __init__(self, sender_role, receiver_role, sender_revision, receiver_revision,
                 input_dim, output_dim, *, rank=16, learning_rate=0.01, weight_decay=1.0e-5, seed=17):
        _roles(sender_role, receiver_role)
        self.sender_role = sender_role
        self.receiver_role = receiver_role
        self.sender_revision = _revision(sender_revision)
        self.receiver_revision = _revision(receiver_revision)
        if (type(input_dim) is not int or type(output_dim) is not int
                or not 1 <= input_dim <= MAX_DIM or not 1 <= output_dim <= MAX_DIM):
            raise ValueError("adapter dimensions outside bounds")
        if type(rank) is not int or not 1 <= rank <= min(MAX_RANK, input_dim, output_dim):
            raise ValueError("adapter rank outside bounds")
        if (type(learning_rate) not in (int, float) or not 0 < learning_rate <= 0.05
                or type(weight_decay) not in (int, float) or not 0 <= weight_decay <= 0.1):
            raise ValueError("adapter optimizer parameters outside bounds")
        if type(seed) is not int or not 0 <= seed <= 2**31 - 1:
            raise ValueError("adapter seed outside bounds")
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.rank = rank
        self.learning_rate = float(learning_rate)
        self.weight_decay = float(weight_decay)
        self.seed = seed
        rng = np.random.default_rng(seed)
        self.a = rng.normal(0.0, math.sqrt(2.0 / input_dim), (rank, input_dim)).astype(np.float32)
        self.b = rng.normal(0.0, 0.01 / math.sqrt(rank), (output_dim, rank)).astype(np.float32)
        self.bias = np.zeros(output_dim, dtype=np.float32)
        self.ma = np.zeros_like(self.a)
        self.va = np.zeros_like(self.a)
        self.mb = np.zeros_like(self.b)
        self.vb = np.zeros_like(self.b)
        self.mbias = np.zeros_like(self.bias)
        self.vbias = np.zeros_like(self.bias)
        self.steps = 0
        self.status = "UNTRAINED"
        self.metrics = {}
        self.dataset_sha256 = None
        self.train_source_ids = []
        self.holdout_source_ids = []

    def _metadata(self):
        return {
            "schema": SCHEMA,
            "sender_role": self.sender_role,
            "receiver_role": self.receiver_role,
            "sender_model_revision": self.sender_revision,
            "receiver_model_revision": self.receiver_revision,
            "input_dim": self.input_dim,
            "output_dim": self.output_dim,
            "rank": self.rank,
            "learning_rate": self.learning_rate,
            "weight_decay": self.weight_decay,
            "seed": self.seed,
            "steps": self.steps,
            "status": self.status,
            "metrics": self.metrics,
            "dataset_sha256": self.dataset_sha256,
            "train_source_ids": self.train_source_ids,
            "holdout_source_ids": self.holdout_source_ids,
            "adapter_revision": self.revision(),
        }

    def revision(self):
        digest = hashlib.sha256()
        binding = {
            "schema": SCHEMA,
            "sender_role": self.sender_role,
            "receiver_role": self.receiver_role,
            "sender_model_revision": self.sender_revision,
            "receiver_model_revision": self.receiver_revision,
            "input_dim": self.input_dim,
            "output_dim": self.output_dim,
            "rank": self.rank,
            "steps": self.steps,
        }
        digest.update(json.dumps(binding, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        for value in (self.a, self.b, self.bias):
            digest.update(np.ascontiguousarray(value, dtype=np.float32).tobytes())
        return digest.hexdigest()

    def update(self, x, y, *, admitted=False, committed=False):
        if admitted is not True or committed is not True:
            raise PermissionError("native latent adapter updates require local admission and committed source pairs")
        x = _matrix(x, dim=self.input_dim)
        y = _matrix(y, rows=x.shape[0], dim=self.output_dim)
        hidden = np.tanh(x @ self.a.T)
        prediction = hidden @ self.b.T + self.bias
        error = prediction - y
        loss = float(np.mean(error * error, dtype=np.float64))
        if not math.isfinite(loss):
            raise ValueError("adapter loss is non-finite")
        scale = 2.0 / float(x.shape[0] * self.output_dim)
        grad_prediction = error * scale
        grad_b = grad_prediction.T @ hidden + self.weight_decay * self.b
        grad_bias = grad_prediction.sum(axis=0)
        grad_hidden = grad_prediction @ self.b
        grad_pre = grad_hidden * (1.0 - hidden * hidden)
        grad_a = grad_pre.T @ x + self.weight_decay * self.a
        norm = math.sqrt(float(np.sum(grad_a * grad_a) + np.sum(grad_b * grad_b) + np.sum(grad_bias * grad_bias)))
        if not math.isfinite(norm):
            raise ValueError("adapter gradient is non-finite")
        if norm > 1.0:
            factor = 1.0 / norm
            grad_a *= factor
            grad_b *= factor
            grad_bias *= factor
        self.steps += 1
        beta1, beta2, epsilon = 0.9, 0.999, 1.0e-8
        self.ma = beta1 * self.ma + (1.0 - beta1) * grad_a
        self.va = beta2 * self.va + (1.0 - beta2) * (grad_a * grad_a)
        self.mb = beta1 * self.mb + (1.0 - beta1) * grad_b
        self.vb = beta2 * self.vb + (1.0 - beta2) * (grad_b * grad_b)
        self.mbias = beta1 * self.mbias + (1.0 - beta1) * grad_bias
        self.vbias = beta2 * self.vbias + (1.0 - beta2) * (grad_bias * grad_bias)
        correction1 = 1.0 - beta1 ** self.steps
        correction2 = 1.0 - beta2 ** self.steps
        self.a -= self.learning_rate * (self.ma / correction1) / (np.sqrt(self.va / correction2) + epsilon)
        self.b -= self.learning_rate * (self.mb / correction1) / (np.sqrt(self.vb / correction2) + epsilon)
        self.bias -= self.learning_rate * (self.mbias / correction1) / (np.sqrt(self.vbias / correction2) + epsilon)
        if not all(bool(np.isfinite(value).all()) for value in (self.a, self.b, self.bias)):
            raise ValueError("adapter update produced non-finite weights")
        return loss

    def _predict(self, x):
        return np.tanh(x @ self.a.T) @ self.b.T + self.bias

    def fit(self, pairs, *, admitted=False, committed=False, epochs=20, batch_size=8,
            max_steps=200, slots=16):
        if admitted is not True or committed is not True:
            raise PermissionError("adapter fit requires explicit local admission and committed Store tap pairs")
        if type(pairs) is not list or not MIN_PAIRS <= len(pairs) <= MAX_PAIRS:
            raise ValueError("adapter fit requires 8..256 committed source pairs")
        if (type(epochs) is not int or not 1 <= epochs <= 100
                or type(batch_size) is not int or not 1 <= batch_size <= 32
                or type(max_steps) is not int or not 1 <= max_steps <= MAX_STEPS
                or type(slots) is not int or not 1 <= slots <= MAX_ROWS):
            raise ValueError("adapter fit bounds")
        source_ids = []
        prepared = []
        min_slots = slots
        for pair in pairs:
            if type(pair) is not dict or pair.get("committed") is not True:
                raise PermissionError("every adapter pair must be a committed Store observation")
            if (pair.get("sender_role") != self.sender_role or pair.get("receiver_role") != self.receiver_role
                    or pair.get("sender_model_revision") != self.sender_revision
                    or pair.get("receiver_model_revision") != self.receiver_revision):
                raise ValueError("adapter pair role/model revision binding mismatch")
            source_id = pair.get("source_id")
            if type(source_id) is not str or not source_id:
                raise ValueError("adapter pair source ID missing")
            source_ids.append(source_id)
            sender = _matrix(pair.get("sender_vectors"), dim=self.input_dim)
            receiver = _matrix(pair.get("receiver_vectors"), dim=self.output_dim)
            min_slots = min(min_slots, sender.shape[0], receiver.shape[0])
            prepared.append((pair, sender, receiver))
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("adapter training source IDs must be unique")
        slots = max(1, min_slots)
        prepared = [(pair, resample_rows(sender, slots), resample_rows(receiver, slots))
                    for pair, sender, receiver in prepared]
        order = sorted(range(len(prepared)), key=lambda index:
                       hashlib.sha256((prepared[index][0]["source_id"] + prepared[index][0].get("event_id", "")).encode()).hexdigest())
        holdout_count = max(2, int(math.ceil(len(order) * 0.2)))
        holdout_indices = order[:holdout_count]
        train_indices = order[holdout_count:]
        if len(train_indices) < 4:
            raise ValueError("adapter fit needs at least four source-disjoint training pairs")
        train_source_ids = [prepared[index][0]["source_id"] for index in train_indices]
        holdout_source_ids = [prepared[index][0]["source_id"] for index in holdout_indices]
        if set(train_source_ids) & set(holdout_source_ids):
            raise ValueError("adapter train/holdout source leakage")
        digest = hashlib.sha256()
        for index in order:
            pair, sender, receiver = prepared[index]
            digest.update(pair["source_id"].encode())
            digest.update(pair.get("event_id", "").encode())
            digest.update(pair.get("generation_id", "").encode())
            digest.update(sender.tobytes())
            digest.update(receiver.tobytes())
        self.dataset_sha256 = digest.hexdigest()
        self.train_source_ids = train_source_ids
        self.holdout_source_ids = holdout_source_ids

        def evaluate(indices):
            xs = np.concatenate([prepared[index][1] for index in indices], axis=0)
            ys = np.concatenate([prepared[index][2] for index in indices], axis=0)
            return _mse_cosine(self._predict(xs), ys)

        before_loss, before_cosine = evaluate(holdout_indices)
        rng = np.random.default_rng(self.seed + 1)
        step_start = self.steps
        for _ in range(epochs):
            shuffled = rng.permutation(train_indices)
            for offset in range(0, len(shuffled), batch_size):
                batch_indices = shuffled[offset:offset + batch_size]
                x = np.concatenate([prepared[index][1] for index in batch_indices], axis=0)
                y = np.concatenate([prepared[index][2] for index in batch_indices], axis=0)
                self.update(x, y, admitted=True, committed=True)
                if self.steps - step_start >= max_steps:
                    break
            if self.steps - step_start >= max_steps:
                break
        after_loss, after_cosine = evaluate(holdout_indices)
        holdout_order = list(holdout_indices)
        if len(holdout_order) > 1:
            target_order = holdout_order[1:] + holdout_order[:1]
            shuffled_x = np.concatenate([prepared[index][1] for index in holdout_order], axis=0)
            shuffled_y = np.concatenate([prepared[index][2] for index in target_order], axis=0)
            shuffled_loss, _ = _mse_cosine(self._predict(shuffled_x), shuffled_y)
        else:
            shuffled_loss = after_loss
        improved = after_loss < before_loss * 0.98 and after_cosine > before_cosine + 0.02
        negative_control = shuffled_loss > after_loss + 1.0e-6
        self.status = "SHADOW_CANDIDATE" if improved and negative_control else "REJECTED"
        self.metrics = {
            "slots": slots,
            "source_pairs": len(prepared),
            "train_pairs": len(train_indices),
            "holdout_pairs": len(holdout_indices),
            "train_source_ids": train_source_ids,
            "holdout_source_ids": holdout_source_ids,
            "steps_added": self.steps - step_start,
            "holdout_mse_before": before_loss,
            "holdout_mse_after": after_loss,
            "holdout_cosine_before": before_cosine,
            "holdout_cosine_after": after_cosine,
            "shuffled_target_mse_after": shuffled_loss,
            "heldout_improved": improved,
            "negative_control_passed": negative_control,
            "production_route": False,
            "semantic_use_proven": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
        }
        return dict(self.metrics, status=self.status, adapter_revision=self.revision(),
                    dataset_sha256=self.dataset_sha256)

    def project(self, vectors, *, source_id, generation_id, sender_revision, receiver_revision):
        if self.status != "SHADOW_CANDIDATE":
            raise PermissionError("only a held-out-passing SHADOW_CANDIDATE adapter may be applied")
        if (sender_revision != self.sender_revision or receiver_revision != self.receiver_revision):
            raise PermissionError("adapter model revisions differ from the installed sender/receiver")
        if type(source_id) is not str or not source_id or type(generation_id) is not str or not generation_id:
            raise ValueError("adapter projection requires source and generation provenance")
        matrix = _matrix(vectors, dim=self.input_dim)
        projected = self._predict(matrix)
        if not bool(np.isfinite(projected).all()) or projected.shape[1] != self.output_dim:
            raise ValueError("adapter projection output is invalid")
        return np.ascontiguousarray(projected, dtype=np.float32)

    def save(self, directory):
        if self.status != "SHADOW_CANDIDATE" or self.steps < 1 or not self.dataset_sha256:
            raise PermissionError("only a held-out-passing trained adapter can be checkpointed")
        directory = Path(directory)
        if directory.is_symlink():
            raise ValueError("adapter directory cannot be a symlink")
        directory.mkdir(parents=True, exist_ok=True)
        if not directory.is_dir():
            raise ValueError("adapter checkpoint path is not a directory")
        metadata = self._metadata()
        buffer = io.BytesIO()
        np.savez_compressed(
            buffer,
            metadata=np.frombuffer(json.dumps(metadata, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(), dtype=np.uint8),
            a=self.a, b=self.b, bias=self.bias,
            ma=self.ma, va=self.va, mb=self.mb, vb=self.vb,
            mbias=self.mbias, vbias=self.vbias,
        )
        raw = buffer.getvalue()
        if not 0 < len(raw) <= MAX_CHECKPOINT_BYTES:
            raise ValueError("adapter checkpoint size outside bounds")
        file_sha = hashlib.sha256(raw).hexdigest()
        revision = self.revision()
        filename = "adapter-" + revision[:16] + ".npz"
        final = directory / filename
        if final.exists():
            if final.is_symlink() or hashlib.sha256(final.read_bytes()).hexdigest() != file_sha:
                raise ValueError("immutable adapter checkpoint collision")
        else:
            fd, temporary = tempfile.mkstemp(prefix=".adapter-", dir=directory)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.link(temporary, final)
                dir_fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        pointer = {
            "schema": SCHEMA,
            "file": filename,
            "sha256": file_sha,
            "adapter_revision": revision,
            "sender_role": self.sender_role,
            "receiver_role": self.receiver_role,
            "sender_model_revision": self.sender_revision,
            "receiver_model_revision": self.receiver_revision,
            "status": self.status,
        }
        current_path = directory / "CURRENT.json"
        previous_path = directory / "PREVIOUS.json"
        if current_path.exists():
            if current_path.is_symlink() or current_path.stat().st_size > 4096:
                raise ValueError("untrusted current adapter pointer")
            old = json.loads(current_path.read_text(encoding="utf-8"))
            if old.get("adapter_revision") != revision:
                _atomic_json(previous_path, old)
        _atomic_json(current_path, pointer)
        return pointer

    @classmethod
    def load_current(cls, directory, *, expected_sender_revision=None, expected_receiver_revision=None):
        directory = Path(directory)
        pointer_path = directory / "CURRENT.json"
        if directory.is_symlink() or pointer_path.is_symlink() or not pointer_path.is_file():
            raise FileNotFoundError("no safe current native latent adapter")
        if pointer_path.stat().st_size > 4096:
            raise ValueError("oversized native latent adapter pointer")
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
        if (type(pointer) is not dict or pointer.get("schema") != SCHEMA
                or type(pointer.get("file")) is not str or not FILE_RE.fullmatch(pointer["file"])
                or type(pointer.get("sha256")) is not str or len(pointer["sha256"]) != 64
                or pointer.get("status") != "SHADOW_CANDIDATE"):
            raise ValueError("untrusted native latent adapter pointer")
        path = directory / pointer["file"]
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_CHECKPOINT_BYTES:
            raise ValueError("native latent adapter file missing or unsafe")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != pointer["sha256"]:
            raise ValueError("native latent adapter file hash mismatch")
        with np.load(io.BytesIO(raw), allow_pickle=False) as archive:
            metadata = json.loads(archive["metadata"].tobytes().decode("utf-8"))
            arrays = {name: np.ascontiguousarray(archive[name], dtype=np.float32)
                      for name in ("a", "b", "bias", "ma", "va", "mb", "vb", "mbias", "vbias")}
        if metadata.get("schema") != SCHEMA or metadata.get("status") != "SHADOW_CANDIDATE":
            raise ValueError("native latent adapter checkpoint schema/status")
        if expected_sender_revision is not None and metadata.get("sender_model_revision") != expected_sender_revision:
            raise ValueError("native latent adapter sender revision is stale")
        if expected_receiver_revision is not None and metadata.get("receiver_model_revision") != expected_receiver_revision:
            raise ValueError("native latent adapter receiver revision is stale")
        adapter = cls(
            metadata["sender_role"], metadata["receiver_role"],
            metadata["sender_model_revision"], metadata["receiver_model_revision"],
            metadata["input_dim"], metadata["output_dim"],
            rank=metadata["rank"], learning_rate=metadata["learning_rate"],
            weight_decay=metadata["weight_decay"], seed=metadata["seed"],
        )
        expected_shapes = {
            "a": (adapter.rank, adapter.input_dim),
            "b": (adapter.output_dim, adapter.rank),
            "bias": (adapter.output_dim,),
            "ma": (adapter.rank, adapter.input_dim),
            "va": (adapter.rank, adapter.input_dim),
            "mb": (adapter.output_dim, adapter.rank),
            "vb": (adapter.output_dim, adapter.rank),
            "mbias": (adapter.output_dim,),
            "vbias": (adapter.output_dim,),
        }
        for name, shape in expected_shapes.items():
            if arrays[name].shape != shape or not bool(np.isfinite(arrays[name]).all()):
                raise ValueError("native latent adapter tensor shape/value mismatch: " + name)
            setattr(adapter, name, arrays[name])
        if type(metadata.get("steps")) is not int or metadata["steps"] < 1:
            raise ValueError("native latent adapter step count")
        adapter.steps = metadata["steps"]
        adapter.status = metadata["status"]
        adapter.metrics = metadata.get("metrics") or {}
        adapter.dataset_sha256 = metadata.get("dataset_sha256")
        adapter.train_source_ids = metadata.get("train_source_ids") or []
        adapter.holdout_source_ids = metadata.get("holdout_source_ids") or []
        if adapter.revision() != metadata.get("adapter_revision") or adapter.revision() != pointer.get("adapter_revision"):
            raise ValueError("native latent adapter revision mismatch")
        if (pointer.get("sender_role") != adapter.sender_role
                or pointer.get("receiver_role") != adapter.receiver_role
                or pointer.get("sender_model_revision") != adapter.sender_revision
                or pointer.get("receiver_model_revision") != adapter.receiver_revision):
            raise ValueError("native latent adapter pointer binding mismatch")
        return adapter, pointer

    @classmethod
    def rollback(cls, directory):
        directory = Path(directory)
        current_path = directory / "CURRENT.json"
        previous_path = directory / "PREVIOUS.json"
        if (directory.is_symlink() or current_path.is_symlink() or previous_path.is_symlink()
                or not current_path.is_file() or not previous_path.is_file()):
            raise FileNotFoundError("no safe previous native latent adapter")
        current = json.loads(current_path.read_text(encoding="utf-8"))
        previous = json.loads(previous_path.read_text(encoding="utf-8"))
        # Validate the previous immutable file before changing either pointer.
        cls.load_pointer(directory, previous)
        cls.load_pointer(directory, current)
        _atomic_json(previous_path, current)
        _atomic_json(current_path, previous)
        return previous

    @classmethod
    def load_pointer(cls, directory, pointer):
        directory = Path(directory)
        if (type(pointer) is not dict or pointer.get("schema") != SCHEMA
                or type(pointer.get("file")) is not str or not FILE_RE.fullmatch(pointer["file"])):
            raise ValueError("invalid native latent adapter pointer")
        path = directory / pointer["file"]
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_CHECKPOINT_BYTES:
            raise ValueError("native latent adapter rollback file missing or unsafe")
        if hashlib.sha256(path.read_bytes()).hexdigest() != pointer.get("sha256"):
            raise ValueError("native latent adapter rollback hash mismatch")
        return pointer


def adapter_status(directory):
    try:
        adapter, pointer = LowRankAdapter.load_current(directory)
    except FileNotFoundError:
        return {"status": "MISSING", "production_route": False, "training_authority": 0}
    except (ValueError, OSError, KeyError, TypeError):
        return {"status": "INVALID", "production_route": False, "training_authority": 0}
    return {
        "status": adapter.status,
        "adapter_revision": adapter.revision(),
        "sha256": pointer["sha256"],
        "sender_role": adapter.sender_role,
        "receiver_role": adapter.receiver_role,
        "sender_model_revision": adapter.sender_revision,
        "receiver_model_revision": adapter.receiver_revision,
        "rank": adapter.rank,
        "training_pairs": adapter.metrics.get("source_pairs"),
        "holdout_mse": adapter.metrics.get("holdout_mse_after"),
        "holdout_cosine": adapter.metrics.get("holdout_cosine_after"),
        "dataset_sha256": adapter.dataset_sha256,
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }
