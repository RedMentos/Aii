from __future__ import annotations

import hashlib
import sys
from pathlib import Path
import time

import pytest

from v13.native_latent_receiver import (
    NativeReceiverError,
    PINNED_LLAMA_REVISION,
    SCHEMA,
    TOKEN_ROW_SCHEMA,
    extract_token_rows,
)


def _fixture(tmp_path: Path, mode: str = "ok"):
    home = tmp_path / "home"
    models = home / "models"
    models.mkdir(parents=True)
    model = models / "receiver.gguf"
    model.write_bytes(b"pinned receiver model bytes")
    binary = tmp_path / "native_latent_receiver"
    script = f"""#!/usr/bin/env python3
import json
import sys

model = {str(model)!r}
mode = {mode!r}
if sys.argv[1:] == ["--version"]:
    revision = "wrong-revision" if mode == "bad_revision" else {PINNED_LLAMA_REVISION!r}
    print(json.dumps({{"schema": {SCHEMA!r}, "runner_revision": revision, "llama_version": "fake-pinned-llama"}}))
    raise SystemExit(0)

args = sys.argv[1:]
if "--token-rows" not in args or "--model" not in args or "--token-ids" not in args:
    raise SystemExit(64)
token_ids = [int(value) for value in args[args.index("--token-ids") + 1].split(",")]
rows = [{{"token_id": token_id, "values": [float(token_id), 1.0, -1.0]}} for token_id in token_ids]
payload = {{
    "schema": {TOKEN_ROW_SCHEMA!r},
    "runner_revision": {PINNED_LLAMA_REVISION!r},
    "llama_version": "fake-pinned-llama",
    "status": "ROWS_READ",
    "source": "RECEIVER_INPUT_TOKEN_EMBEDDING_TABLE",
    "model_vocab": 128,
    "embedding_dim": 3,
    "tensor_type": "F16",
    "row_bytes": 6,
    "tensor_row_stride_bytes": 6,
    "requested_token_ids": token_ids,
    "rows": rows,
    "full_table_copied": False,
    "read_only": True,
    "max_rows": 32,
}}
if mode == "bad_source":
    payload["source"] = "FINAL_LAYER_OUTPUT"
if mode == "bad_shape":
    payload["rows"][0]["values"] = [1.0, 2.0]
if mode == "bad_full_table":
    payload["full_table_copied"] = True
if mode == "bad_requested_ids":
    payload["requested_token_ids"][0] = True
if mode == "bad_row_id":
    payload["rows"][0]["token_id"] = True
if mode == "mutate_model":
    with open(model, "ab") as stream:
        stream.write(b"changed")
print(json.dumps(payload, allow_nan=True))
"""
    binary.write_text(script, encoding="utf-8")
    binary.chmod(0o755)
    return home, model, binary


class _TTY:
    def isatty(self):
        return True


def _extract(home, model, binary, token_ids=(2, 7)):
    previous_stdin, previous_stdout = sys.stdin, sys.stdout
    sys.stdin, sys.stdout = _TTY(), _TTY()
    try:
        return extract_token_rows(
            home=home,
            model_path=model,
            expected_model_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),
            model_revision="receiver-revision-1",
            tokenizer_revision="receiver-tokenizer-1",
            token_ids=list(token_ids),
            deadline=time.monotonic() + 10.0,
            local_confirmed=True,
            binary_path=binary,
        )
    finally:
        sys.stdin, sys.stdout = previous_stdin, previous_stdout


def test_extract_token_rows_verifies_model_bytes_and_preserves_revision_metadata(tmp_path):
    home, model, binary = _fixture(tmp_path)
    result = _extract(home, model, binary)
    assert result["schema"] == TOKEN_ROW_SCHEMA
    assert result["status"] == "NATIVE_TOKEN_ROWS_READ_ONLY"
    assert result["source"] == "RECEIVER_INPUT_TOKEN_EMBEDDING_TABLE"
    assert result["model_revision"] == "receiver-revision-1"
    assert result["tokenizer_revision"] == "receiver-tokenizer-1"
    assert result["revision_binding_source"] == "caller_supplied_unverified"
    assert result["model_sha256"] == hashlib.sha256(model.read_bytes()).hexdigest()
    assert result["requested_token_ids"] == [2, 7]
    assert [row["token_id"] for row in result["rows"]] == [2, 7]
    assert result["rows"][0]["values"] == [2.0, 1.0, -1.0]
    assert result["full_table_copied"] is False
    assert result["read_only"] is True
    assert result["training_authority"] == 0
    assert result["production_route"] is False
    assert result["semantic_use_proven"] is False
    assert result["local_tty_gate_passed"] is True
    assert result["caller_confirmation_flag"] is True


@pytest.mark.parametrize("token_ids", [
    [],
    [True],
    [-1],
    [1.5],
    [1, 1],
    list(range(33)),
])
def test_extract_token_rows_rejects_invalid_or_unbounded_token_id_requests(tmp_path, token_ids):
    home, model, binary = _fixture(tmp_path)
    with pytest.raises(NativeReceiverError):
        _extract(home, model, binary, token_ids=token_ids)


@pytest.mark.parametrize("mode", ["bad_source", "bad_shape", "bad_full_table", "bad_requested_ids", "bad_row_id"])
def test_extract_token_rows_rejects_untrusted_native_receipts(tmp_path, mode):
    home, model, binary = _fixture(tmp_path, mode)
    with pytest.raises(NativeReceiverError):
        _extract(home, model, binary)


def test_extract_token_rows_requires_explicit_local_confirmation(tmp_path):
    home, model, binary = _fixture(tmp_path)
    with pytest.raises(PermissionError, match="explicit local confirmation"):
        extract_token_rows(
            home=home,
            model_path=model,
            expected_model_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),
            model_revision="receiver-revision-1",
            tokenizer_revision="receiver-tokenizer-1",
            token_ids=[2],
            deadline=time.monotonic() + 10.0,
            binary_path=binary,
        )


def test_extract_token_rows_requires_interactive_local_tty(tmp_path, monkeypatch):
    home, model, binary = _fixture(tmp_path)

    class _NotTTY:
        def isatty(self):
            return False

    monkeypatch.setattr(sys, "stdin", _NotTTY())
    monkeypatch.setattr(sys, "stdout", _NotTTY())
    with pytest.raises(PermissionError, match="interactive local TTY"):
        extract_token_rows(
            home=home,
            model_path=model,
            expected_model_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),
            model_revision="receiver-revision-1",
            tokenizer_revision="receiver-tokenizer-1",
            token_ids=[2],
            deadline=time.monotonic() + 10.0,
            local_confirmed=True,
            binary_path=binary,
        )


def test_extract_token_rows_rechecks_model_bytes_after_native_read(tmp_path):
    home, model, binary = _fixture(tmp_path, "mutate_model")
    with pytest.raises(NativeReceiverError, match="changed during"):
        _extract(home, model, binary)


def test_extract_token_rows_rejects_model_outside_installed_models_root(tmp_path):
    home, model, binary = _fixture(tmp_path)
    outside = tmp_path / "outside.gguf"
    outside.write_bytes(b"outside")
    with pytest.raises(NativeReceiverError, match="under home/models"):
        _extract(home, outside, binary)


def test_extract_token_rows_rejects_symlinked_model(tmp_path):
    home, model, binary = _fixture(tmp_path)
    outside = tmp_path / "outside.gguf"
    outside.write_bytes(b"outside")
    link = home / "models" / "linked.gguf"
    link.symlink_to(outside)
    with pytest.raises(NativeReceiverError, match="symlink"):
        _extract(home, link, binary)


def test_extract_token_rows_rejects_wrong_pinned_runner_revision(tmp_path):
    home, model, binary = _fixture(tmp_path, "bad_revision")
    with pytest.raises(NativeReceiverError, match="pinned llama.cpp"):
        _extract(home, model, binary)
