"""Source-bound tokenwise sender taps for the local native receiver diagnostic.

This module joins llama-server's no-special-token /tokenize-with-pieces result
to the exact whole-sequence prefill rows produced by LlamaRunner.tap. It stores
byte spans and selected numeric rows only; raw token pieces and source text are
never copied into the tap artifact. The receiver remains diagnostic-only.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
from pathlib import Path

from .common import atomic_write, dumps, file_hash, uid
from .contracts import FIELDS, packet, validate
from .models import model_key
from .latent_adapter import LatentAdapterError, build_tokenwise_tap_manifest

POSITION_MODE = "ZERO_BASED_CONTIGUOUS_SOURCE_CONTENT_TOKENS"
TOKENWISE_SCHEMA = "v14.source-bound-tokenwise-tap/1"
MAX_TOKENS = 64
MAX_DIM = 8192
MAX_ELEMENTS = 262144


class TokenwiseTapError(ValueError):
    pass


def _hex_digest(value):
    return (isinstance(value, str) and len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value))


def _json_sha256(value):
    return hashlib.sha256(dumps(value).encode("utf-8")).hexdigest()


def _register_packet_contract():
    schema = {
        "role": str,
        "source_ref": dict,
        "sender_tap_packet_id": str,
        "sender_tap_id": str,
        "model_revision": str,
        "model_sha256": str,
        "model_manifest_sha256": str,
        "tokenizer_revision": str,
        "token_ids": list,
        "token_spans": list,
        "prefill_positions": list,
        "prefill_token_count": int,
        "special_prefix_tokens": int,
        "special_suffix_tokens": int,
        "source_sha256": str,
        "source_length": int,
        "feature_path": str,
        "feature_sha256": str,
        "vectors_sha256": str,
        "manifest_sha256": str,
        "shape": list,
        "position_mode": str,
        "production_route": bool,
        "training_authority": int,
    }
    existing = FIELDS.get("TokenwiseTapPacket")
    if existing is not None and existing != schema:
        raise RuntimeError("TokenwiseTapPacket contract registration conflict")
    FIELDS["TokenwiseTapPacket"] = schema


def validate_tokenwise_packet(value):
    _register_packet_contract()
    validate("TokenwiseTapPacket", value)
    if value["role"] not in {"B1_DETAIL", "B2_GIST"}:
        raise TokenwiseTapError("tokenwise sender role")
    source_ref = value["source_ref"]
    if not isinstance(source_ref.get("source_id"), str) or source_ref not in value["provenance"]:
        raise TokenwiseTapError("tokenwise source provenance")
    for name in ("model_sha256", "model_manifest_sha256", "source_sha256",
                 "feature_sha256", "vectors_sha256", "manifest_sha256"):
        if not _hex_digest(value[name]):
            raise TokenwiseTapError("tokenwise " + name)
    if not all(isinstance(value[name], str) and value[name] for name in
               ("sender_tap_packet_id", "sender_tap_id", "model_revision", "tokenizer_revision")):
        raise TokenwiseTapError("tokenwise model/tap identity")
    ids = value["token_ids"]
    spans = value["token_spans"]
    positions = value["prefill_positions"]
    if not isinstance(ids, list) or not 2 <= len(ids) <= MAX_TOKENS:
        raise TokenwiseTapError("tokenwise content token count")
    if any(type(token_id) is not int or token_id < 0 or token_id > 2147483647 for token_id in ids):
        raise TokenwiseTapError("tokenwise token ID")
    if not isinstance(spans, list) or len(spans) != len(ids):
        raise TokenwiseTapError("tokenwise source span count")
    if type(value["source_length"]) is not int or value["source_length"] < 1:
        raise TokenwiseTapError("tokenwise source byte length")
    cursor = 0
    for span in spans:
        if (not isinstance(span, list) or len(span) != 2
                or type(span[0]) is not int or type(span[1]) is not int
                or span[0] != cursor or span[1] <= span[0]
                or span[1] > value["source_length"]):
            raise TokenwiseTapError("tokenwise source byte span")
        cursor = span[1]
    if cursor != value["source_length"]:
        raise TokenwiseTapError("tokenwise spans do not cover exact source bytes")
    if not isinstance(positions, list) or len(positions) != len(ids):
        raise TokenwiseTapError("tokenwise prefill position count")
    previous = -1
    for position in positions:
        if (type(position) is not int or position <= previous
                or position < 0 or position >= value["prefill_token_count"]):
            raise TokenwiseTapError("tokenwise prefill position")
        previous = position
    if positions != list(range(positions[0], positions[0] + len(positions))):
        raise TokenwiseTapError("tokenwise content rows are not contiguous")
    if (type(value["prefill_token_count"]) is not int
            or value["prefill_token_count"] < len(ids)
            or value["prefill_token_count"] > len(ids) + 2):
        raise TokenwiseTapError("tokenwise prefill token count")
    if (value["special_prefix_tokens"] != positions[0]
            or value["special_suffix_tokens"] != value["prefill_token_count"] - positions[-1] - 1
            or value["special_prefix_tokens"] + value["special_suffix_tokens"]
               != value["prefill_token_count"] - len(ids)):
        raise TokenwiseTapError("tokenwise special-token offset")
    shape = value["shape"]
    if (not isinstance(shape, list) or len(shape) != 2
            or type(shape[0]) is not int or type(shape[1]) is not int
            or shape[0] != len(ids) or not 1 <= shape[1] <= MAX_DIM
            or shape[0] * shape[1] > MAX_ELEMENTS):
        raise TokenwiseTapError("tokenwise vector shape")
    if value["position_mode"] != POSITION_MODE:
        raise TokenwiseTapError("tokenwise position mode")
    if value["production_route"] is not False or value["training_authority"] != 0:
        raise TokenwiseTapError("tokenwise packet cannot grant production or learning authority")
    return value


def _installed_model_binding(runtime, role, expected_revision):
    key = model_key(role, runtime.models.b2_control)
    installed = runtime.models.installed.get(key)
    if not isinstance(installed, dict) or installed.get("download_complete") is not True:
        raise TokenwiseTapError("sender model is not installed")
    revision = installed.get("exact_revision")
    if not isinstance(revision, str) or revision != expected_revision:
        raise TokenwiseTapError("sender model revision differs from installed manifest")
    if runtime.models.revision(role) != revision:
        raise TokenwiseTapError("sender model is routed/swapped")
    files = installed.get("files")
    main_name = installed.get("main_file")
    if not isinstance(files, dict) or not isinstance(main_name, str):
        raise TokenwiseTapError("sender model file manifest is missing")
    main = files.get(main_name)
    if not isinstance(main, dict) or not _hex_digest(main.get("sha256")):
        raise TokenwiseTapError("sender main model hash is missing")
    normalized_files = {}
    for name, item in sorted(files.items()):
        if (not isinstance(name, str) or not isinstance(item, dict)
                or not _hex_digest(item.get("sha256"))
                or type(item.get("size")) is not int or item["size"] < 1):
            raise TokenwiseTapError("sender model manifest entry is invalid")
        normalized_files[name] = {"sha256": item["sha256"], "size": item["size"]}
    manifest_sha = _json_sha256({
        "model_id": installed.get("model_id"),
        "exact_revision": revision,
        "files": normalized_files,
    })
    model_path = Path(runtime.models.path_for(role))
    if model_path.is_symlink():
        raise TokenwiseTapError("sender model symlink refused")
    model_path = model_path.resolve(strict=True)
    models_root = (Path(runtime.home) / "models").resolve()
    if not model_path.is_relative_to(models_root) or not model_path.is_file():
        raise TokenwiseTapError("sender model escaped installed models root")
    if file_hash(model_path) != main["sha256"]:
        raise TokenwiseTapError("sender model bytes differ from installed manifest")
    return main["sha256"], manifest_sha


def _runner_binary(runtime, runner=None):
    raw = getattr(runner, "binary", None) if runner is not None else None
    if not raw:
        raw = os.environ.get("V13_LLAMA_SERVER", str(Path(runtime.home) / "bin" / "llama-server"))
    path = Path(raw)
    if path.is_symlink() or not path.is_file():
        raise TokenwiseTapError("pinned llama-server binary is unavailable or unsafe")
    return path.resolve(strict=True)


def _tokenizer_revision(runtime, model_manifest_sha256, runner=None):
    binary = _runner_binary(runtime, runner)
    return "llama-server-sha256:" + file_hash(binary) + ";model-manifest-sha256:" + model_manifest_sha256


def _validate_vectors(vectors, expected_rows):
    if not isinstance(vectors, list) or len(vectors) != expected_rows:
        raise TokenwiseTapError("tokenwise selected vector row count")
    if not isinstance(vectors[0], list) or not 1 <= len(vectors[0]) <= MAX_DIM:
        raise TokenwiseTapError("tokenwise selected vector dimension")
    dimension = len(vectors[0])
    if expected_rows * dimension > MAX_ELEMENTS:
        raise TokenwiseTapError("tokenwise selected vector element bound")
    for row in vectors:
        if not isinstance(row, list) or len(row) != dimension:
            raise TokenwiseTapError("tokenwise selected vectors are ragged")
        for value in row:
            if type(value) not in (int, float) or not math.isfinite(float(value)) or abs(float(value)) > 1.0e6:
                raise TokenwiseTapError("tokenwise selected vector is non-finite or unbounded")
    return [expected_rows, dimension]


def capture_tokenwise_tap(cognition, tap_packet, deadline):
    """Create a source/tokenizer/model-bound content-only tap from a live sender runner."""
    _register_packet_contract()
    if not isinstance(tap_packet, dict):
        raise TokenwiseTapError("sender tap packet is missing")
    role = tap_packet.get("role")
    if role not in {"B1_DETAIL", "B2_GIST"}:
        raise TokenwiseTapError("sender tap role")
    if (not isinstance(tap_packet.get("source_ref"), dict)
            or tap_packet["source_ref"] not in tap_packet.get("provenance", [])
            or not isinstance(tap_packet.get("event_id"), str)
            or not isinstance(tap_packet.get("brain_generation_id"), str)):
        raise TokenwiseTapError("sender tap source/event/generation binding")
    runtime = cognition.r
    if runtime.cancel_event.is_set():
        raise InterruptedError("tokenwise tap cancelled")
    if type(deadline) not in (int, float) or not math.isfinite(float(deadline)) or float(deadline) <= time.monotonic():
        raise TimeoutError("tokenwise tap deadline expired")
    tap_data = cognition.read_tap(tap_packet)
    source_text = cognition.s.read_source(tap_packet["source_ref"])
    if not isinstance(source_text, str) or not source_text:
        raise TokenwiseTapError("source text is unavailable")
    runner = runtime.pool.get_tap(role)
    if runner.proc is None or runner.proc.poll() is not None:
        raise TokenwiseTapError("sender tap runner is not alive for tokenizer receipt")
    response = runner._json(
        "POST", "/tokenize",
        {"content": source_text, "add_special": False, "with_pieces": True},
        float(deadline),
    )
    rows = response.get("tokens") if isinstance(response, dict) else None
    if not isinstance(rows, list) or not rows:
        raise TokenwiseTapError("llama-server /tokenize did not return token pieces")
    if any(not isinstance(row, dict) or "id" not in row or "piece" not in row for row in rows):
        raise TokenwiseTapError("llama-server token-piece receipt is malformed")
    content_ids = [row["id"] for row in rows]
    try:
        manifest = build_tokenwise_tap_manifest(
            source_text, content_ids, rows, tap_data["token_ids"], tap_data["vectors"]
        )
    except (LatentAdapterError, KeyError, TypeError, ValueError) as exc:
        raise TokenwiseTapError("source/token/prefill alignment rejected: " + type(exc).__name__) from exc
    vectors = manifest["vectors"]
    shape = _validate_vectors(vectors, len(manifest["token_ids"]))
    manifest_payload = {key: value for key, value in manifest.items() if key != "vectors"}
    vectors_sha = _json_sha256(vectors)
    manifest_sha = _json_sha256(manifest_payload)
    model_sha, model_manifest_sha = _installed_model_binding(runtime, role, tap_packet["model_revision"])
    tokenizer_revision = _tokenizer_revision(runtime, model_manifest_sha, runner)
    if runtime.cancel_event.is_set():
        raise InterruptedError("tokenwise tap cancelled")
    if time.monotonic() >= float(deadline):
        raise TimeoutError("tokenwise tap deadline expired")
    blob = {
        "manifest": manifest_payload,
        "vectors": vectors,
        "manifest_sha256": manifest_sha,
        "vectors_sha256": vectors_sha,
    }
    path = Path(runtime.home) / "data" / "blobs" / (uid("tokenwise-tap") + ".json")
    atomic_write(path, dumps(blob))
    relative = str(path.relative_to(Path(runtime.home)))
    packet_value = packet(
        "TokenwiseTapPacket", "B3_TOKENWISE_TAP",
        tap_packet["event_id"], tap_packet["brain_generation_id"],
        [tap_packet["source_ref"]],
        role=role,
        source_ref=tap_packet["source_ref"],
        sender_tap_packet_id=tap_packet["packet_id"],
        sender_tap_id=tap_packet["tap_id"],
        model_revision=tap_packet["model_revision"],
        model_sha256=model_sha,
        model_manifest_sha256=model_manifest_sha,
        tokenizer_revision=tokenizer_revision,
        token_ids=manifest_payload["token_ids"],
        token_spans=manifest_payload["token_spans"],
        prefill_positions=manifest_payload["prefill_positions"],
        prefill_token_count=len(tap_data["token_ids"]),
        special_prefix_tokens=manifest_payload["special_prefix_tokens"],
        special_suffix_tokens=manifest_payload["special_suffix_tokens"],
        source_sha256=manifest_payload["source_sha256"],
        source_length=manifest_payload["source_length"],
        feature_path=relative,
        feature_sha256=file_hash(path),
        vectors_sha256=vectors_sha,
        manifest_sha256=manifest_sha,
        shape=shape,
        position_mode=POSITION_MODE,
        production_route=False,
        training_authority=0,
    )
    validate_tokenwise_packet(packet_value)
    try:
        cognition.s.add_packet("TokenwiseTapPacket", packet_value)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    cognition.s.log("tokenwise_tap", tap_packet["event_id"], {
        "role": role,
        "sender_tap_packet_id": tap_packet["packet_id"],
        "token_count": len(manifest_payload["token_ids"]),
        "prefill_token_count": len(tap_data["token_ids"]),
        "special_prefix_tokens": manifest_payload["special_prefix_tokens"],
        "special_suffix_tokens": manifest_payload["special_suffix_tokens"],
        "manifest_sha256": manifest_sha,
        "tokenizer_revision_sha256": hashlib.sha256(tokenizer_revision.encode("utf-8")).hexdigest(),
        "production_route": False,
        "training_authority": 0,
    })
    return packet_value


def read_tokenwise_tap(cognition, packet_value):
    """Read and revalidate the persisted tokenwise artifact before native consumption."""
    validate_tokenwise_packet(packet_value)
    row = cognition.s.one(
        "SELECT payload FROM packets WHERE kind='TokenwiseTapPacket' AND packet_id=?",
        (packet_value["packet_id"],),
    )
    if not row or json.loads(row["payload"]) != packet_value:
        raise TokenwiseTapError("tokenwise packet is not the stored observation")
    relative = Path(packet_value["feature_path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise TokenwiseTapError("tokenwise feature path is unsafe")
    path = Path(cognition.r.home) / relative
    if path.is_symlink() or not path.is_file():
        raise TokenwiseTapError("tokenwise feature blob is missing or symlinked")
    resolved = path.resolve(strict=True)
    blob_root = (Path(cognition.r.home) / "data" / "blobs").resolve()
    if not resolved.is_relative_to(blob_root) or file_hash(resolved) != packet_value["feature_sha256"]:
        raise TokenwiseTapError("tokenwise feature blob/source binding invalid")
    try:
        blob = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TokenwiseTapError("tokenwise feature blob is invalid") from exc
    manifest = blob.get("manifest")
    vectors = blob.get("vectors")
    if not isinstance(manifest, dict) or manifest.get("schema") != TOKENWISE_SCHEMA:
        raise TokenwiseTapError("tokenwise manifest schema")
    if blob.get("manifest_sha256") != packet_value["manifest_sha256"] or _json_sha256(manifest) != packet_value["manifest_sha256"]:
        raise TokenwiseTapError("tokenwise manifest hash mismatch")
    if blob.get("vectors_sha256") != packet_value["vectors_sha256"] or _json_sha256(vectors) != packet_value["vectors_sha256"]:
        raise TokenwiseTapError("tokenwise vector hash mismatch")
    source_text = cognition.s.read_source(packet_value["source_ref"])
    source_bytes = source_text.encode("utf-8")
    if (hashlib.sha256(source_bytes).hexdigest() != packet_value["source_sha256"]
            or len(source_bytes) != packet_value["source_length"]
            or manifest.get("source_sha256") != packet_value["source_sha256"]
            or manifest.get("source_length") != packet_value["source_length"]):
        raise TokenwiseTapError("tokenwise source bytes changed")
    for name in ("token_ids", "token_spans", "prefill_positions",
                 "special_prefix_tokens", "special_suffix_tokens"):
        if manifest.get(name) != packet_value[name]:
            raise TokenwiseTapError("tokenwise manifest metadata differs from packet: " + name)
    shape = _validate_vectors(vectors, len(packet_value["token_ids"]))
    if shape != packet_value["shape"]:
        raise TokenwiseTapError("tokenwise vector shape differs from packet")
    model_sha, model_manifest_sha = _installed_model_binding(
        cognition.r, packet_value["role"], packet_value["model_revision"]
    )
    if (model_sha != packet_value["model_sha256"]
            or model_manifest_sha != packet_value["model_manifest_sha256"]):
        raise TokenwiseTapError("tokenwise sender model binding changed")
    if _tokenizer_revision(cognition.r, model_manifest_sha) != packet_value["tokenizer_revision"]:
        raise TokenwiseTapError("tokenizer binary/model binding changed")
    return {
        "role": packet_value["role"],
        "source_ref": packet_value["source_ref"],
        "sender_tap_packet_id": packet_value["sender_tap_packet_id"],
        "sender_tap_id": packet_value["sender_tap_id"],
        "model_revision": packet_value["model_revision"],
        "model_sha256": packet_value["model_sha256"],
        "tokenizer_revision": packet_value["tokenizer_revision"],
        "token_ids": packet_value["token_ids"],
        "token_spans": packet_value["token_spans"],
        "prefill_positions": packet_value["prefill_positions"],
        "prefill_token_count": packet_value["prefill_token_count"],
        "special_prefix_tokens": packet_value["special_prefix_tokens"],
        "special_suffix_tokens": packet_value["special_suffix_tokens"],
        "vectors": vectors,
        "manifest_sha256": packet_value["manifest_sha256"],
        "position_mode": POSITION_MODE,
        "production_route": False,
        "training_authority": 0,
    }
