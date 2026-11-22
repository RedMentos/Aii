import hashlib
import json
import os
import struct
import sys
import threading
import time
from pathlib import Path

import pytest

from v13.native_latent_receiver import (
    NativeReceiverError,
    NativeReceiverUnavailable,
    PINNED_LLAMA_REVISION,
    POSITION_MODE,
    SCHEMA,
    probe,
)


def fake_binary(path: Path, *, status="DECODED", receiver_input_dim=None, effect=0.5, sleep=0.0):
    source = f'''#!/usr/bin/env python3
import json, struct, sys, time
from pathlib import Path
REV = {PINNED_LLAMA_REVISION!r}
SCHEMA = {SCHEMA!r}
if len(sys.argv) == 2 and sys.argv[1] == "--version":
    print(json.dumps({{"schema": SCHEMA, "runner_revision": REV, "llama_version": "b10964"}}))
    raise SystemExit(0)
if {sleep!r}:
    time.sleep({sleep!r})
args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
rows = int(args["--rows"])
dim = int(args["--input-dim"])
positions = [int(value) for value in args["--positions"].split(",")]
raw = sys.stdin.buffer.read()
assert len(raw) == rows * dim * 4
status = {status!r}
receiver_dim = {receiver_input_dim if receiver_input_dim is not None else 0}
if receiver_dim == 0:
    receiver_dim = dim
if status == "DIMENSION_MISMATCH":
    receipt = {{
        "schema": SCHEMA, "runner_revision": REV, "llama_version": "b10964",
        "status": status, "input_rows": rows, "input_dim": dim,
        "receiver_input_dim": receiver_dim, "output_dim": 8,
        "decode_status": -100, "finite_output": False,
        "position_ids": positions,
        "position_mode": "ZERO_BASED_CONTIGUOUS_FROM_TOKENIZER_PREFILL",
        "row_shuffle_control_applicable": False,
        "row_shuffle_control_cosine": None
    }}
else:
    receipt = {{
        "schema": SCHEMA, "runner_revision": REV, "llama_version": "b10964",
        "status": status, "input_rows": rows, "input_dim": dim,
        "receiver_input_dim": receiver_dim, "output_dim": 8,
        "decode_status": 0, "output_norm": 2.0,
        "input_effect_rms": {effect!r}, "zero_control_cosine": 0.2,
        "shuffle_control_cosine": 0.1,
        "row_shuffle_control_applicable": rows >= 2,
        "row_shuffle_control_cosine": 0.05 if rows >= 2 else None,
        "repeat_cosine": 1.0,
        "position_ids": positions,
        "position_mode": "ZERO_BASED_CONTIGUOUS_FROM_TOKENIZER_PREFILL",
        "finite_output": True
    }}
print(json.dumps(receipt))
'''
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)
    return path


def fixture(tmp_path, **binary_options):
    home = tmp_path / "v13"
    model_dir = home / "models"
    binary_dir = home / "bin"
    model_dir.mkdir(parents=True)
    binary_dir.mkdir(parents=True)
    model = model_dir / "receiver.gguf"
    model.write_bytes(b"pinned-test-model-bytes")
    binary = fake_binary(binary_dir / "native_latent_receiver", **binary_options)
    digest = hashlib.sha256(model.read_bytes()).hexdigest()
    return home, model, binary, digest


def run_probe(home, model, binary, digest, *, deadline=None, vectors=None, position_ids=None):
    vectors = vectors or [[0.25, -0.5], [1.0, 0.75]]
    positions = list(range(len(vectors))) if position_ids is None else position_ids
    return probe(
        home=home,
        model_path=model,
        expected_model_sha256=digest,
        sender_role="B2_GIST",
        receiver_role="C3_LANGUAGE",
        sender_tap_id="qwen35.result_norm.final.v1",
        sender_model_revision="qwen35-r1",
        sender_model_sha256="b" * 64, tokenizer_revision=None,
        receiver_model_revision="lfm2-r1",
        source_id="source-1",
        generation_id="generation-1",
        vectors=vectors,
        position_ids=positions,
        position_mode=POSITION_MODE,
        deadline=deadline or (time.monotonic() + 10),
        threads=2,
        binary_path=binary,
    )


def test_probe_reports_native_decode_and_input_effect(tmp_path):
    home, model, binary, digest = fixture(tmp_path)
    receipt = run_probe(home, model, binary, digest)
    assert receipt["status"] == "NATIVE_INPUT_EFFECT"
    assert receipt["native_input_consumed"] is True
    assert receipt["input_effect_detected"] is True
    assert receipt["runner_revision"] == PINNED_LLAMA_REVISION
    assert receipt["input_rows"] == 2
    assert receipt["input_dim"] == receipt["receiver_input_dim"] == 2
    assert receipt["sender_model_sha256"] == "b" * 64
    assert receipt["position_ids"] == [0, 1]
    assert receipt["position_mode"] == POSITION_MODE
    assert receipt["row_shuffle_control_applicable"] is True
    assert receipt["row_shuffle_control_cosine"] == 0.05
    assert receipt["input_sha256"] == hashlib.sha256(
        struct.pack("<4f", 0.25, -0.5, 1.0, 0.75)
    ).hexdigest()
    assert model.read_bytes() == b"pinned-test-model-bytes"


def test_dimension_mismatch_is_explicit_and_never_consumed(tmp_path):
    home, model, binary, digest = fixture(tmp_path, status="DIMENSION_MISMATCH", receiver_input_dim=3)
    receipt = run_probe(home, model, binary, digest)
    assert receipt["status"] == "DIMENSION_MISMATCH"
    assert receipt["native_input_consumed"] is False
    assert receipt["input_effect_detected"] is False
    assert receipt["decode_status"] == -100
    assert receipt["input_dim"] == 2
    assert receipt["receiver_input_dim"] == 3


def test_zero_input_effect_does_not_claim_input_effect(tmp_path):
    home, model, binary, digest = fixture(tmp_path, effect=0.0)
    receipt = run_probe(home, model, binary, digest)
    assert receipt["status"] == "NATIVE_DECODE_NO_EFFECT"
    assert receipt["native_input_consumed"] is True
    assert receipt["input_effect_detected"] is False


def test_stale_model_hash_is_rejected_before_execution(tmp_path):
    home, model, binary, digest = fixture(tmp_path)
    model.write_bytes(b"changed-model")
    with pytest.raises(NativeReceiverError, match="hash"):
        run_probe(home, model, binary, digest)


def test_model_path_outside_models_root_is_rejected(tmp_path):
    home, model, binary, digest = fixture(tmp_path)
    outside = tmp_path / "outside.gguf"
    outside.write_bytes(model.read_bytes())
    with pytest.raises(NativeReceiverError, match="under home/models"):
        run_probe(home, outside, binary, digest)


def test_model_symlink_is_rejected(tmp_path):
    home, model, binary, digest = fixture(tmp_path)
    link = home / "models" / "linked.gguf"
    link.symlink_to(model)
    with pytest.raises(NativeReceiverError, match="symlink"):
        run_probe(home, link, binary, digest)


def test_bad_vectors_and_role_binding_are_rejected(tmp_path):
    home, model, binary, digest = fixture(tmp_path)
    with pytest.raises(NativeReceiverError, match="non-finite"):
        run_probe(home, model, binary, digest, vectors=[[float("nan"), 0.0]])
    with pytest.raises(NativeReceiverError, match="identical"):
        probe(
            home=home, model_path=model, expected_model_sha256=digest,
            sender_role="B2_GIST", receiver_role="B2_GIST",
            sender_tap_id="tap", sender_model_revision="r1", receiver_model_revision="r1",
            sender_model_sha256="b" * 64, tokenizer_revision=None,
            source_id="source-1", generation_id="generation-1",
            vectors=[[1.0, 2.0]], deadline=time.monotonic() + 5,
            position_ids=[0], position_mode=POSITION_MODE,
            binary_path=binary,
        )


def test_unpinned_binary_and_missing_binary_fail_closed(tmp_path):
    home, model, binary, digest = fixture(tmp_path)
    script = binary.read_text(encoding="utf-8").replace(PINNED_LLAMA_REVISION, "0" * 40)
    binary.write_text(script, encoding="utf-8")
    binary.chmod(0o755)
    with pytest.raises(NativeReceiverError, match="pinned"):
        run_probe(home, model, binary, digest)
    binary.unlink()
    with pytest.raises(NativeReceiverUnavailable):
        probe(
            home=home, model_path=model, expected_model_sha256=digest,
            sender_role="B2_GIST", receiver_role="C3_LANGUAGE",
            sender_tap_id="tap", sender_model_revision="r1", receiver_model_revision="r2",
            sender_model_sha256="b" * 64, tokenizer_revision=None,
            source_id="source-1", generation_id="generation-1",
            vectors=[[1.0, 2.0]], deadline=time.monotonic() + 5,
            position_ids=[0], position_mode=POSITION_MODE,
        )


def test_deadline_is_enforced(tmp_path):
    home, model, binary, digest = fixture(tmp_path, sleep=0.2)
    with pytest.raises(TimeoutError):
        run_probe(home, model, binary, digest, deadline=time.monotonic() + 0.05)


def test_position_ids_are_explicit_unique_monotonic_and_bounded(tmp_path):
    home, model, binary, digest = fixture(tmp_path)
    for invalid in ([1, 0], [0, 0], [0, 131072], [0], [False, 1]):
        with pytest.raises(NativeReceiverError, match="position"):
            run_probe(home, model, binary, digest, position_ids=invalid)


def test_row_shuffle_control_is_marked_not_applicable_for_single_token(tmp_path):
    home, model, binary, digest = fixture(tmp_path)
    receipt = run_probe(home, model, binary, digest, vectors=[[1.0, 2.0]])
    assert receipt["row_shuffle_control_applicable"] is False
    assert receipt["row_shuffle_control_cosine"] is None


def test_sender_checkpoint_hash_is_required(tmp_path):
    home, model, binary, digest = fixture(tmp_path)
    with pytest.raises(NativeReceiverError, match="sender model hash"):
        probe(
            home=home, model_path=model, expected_model_sha256=digest,
            sender_role="B2_GIST", receiver_role="C3_LANGUAGE",
            sender_tap_id="tap", sender_model_revision="r1", sender_model_sha256="bad",
            tokenizer_revision=None, receiver_model_revision="r2",
            source_id="source-1", generation_id="generation-1",
            vectors=[[1.0, 2.0]], position_ids=[0], position_mode=POSITION_MODE,
            deadline=time.monotonic() + 5, binary_path=binary,
        )


def test_cancel_event_terminates_native_receiver_process(tmp_path):
    home, model, binary, digest = fixture(tmp_path, sleep=0.5)
    cancelled = threading.Event()
    thread = threading.Thread(
        target=lambda: (time.sleep(0.1), cancelled.set()), daemon=True
    )
    thread.start()
    with pytest.raises(InterruptedError, match="cancelled"):
        probe(
            home=home,
            model_path=model,
            expected_model_sha256=digest,
            sender_role="B2_GIST",
            receiver_role="C3_LANGUAGE",
            sender_tap_id="qwen35.result_norm.final.v1",
            sender_model_revision="qwen35-r1",
            sender_model_sha256="b" * 64, tokenizer_revision=None,
            receiver_model_revision="lfm2-r1",
            source_id="source-1",
            generation_id="generation-1",
            vectors=[[1.0, 2.0]],
            position_ids=[0], position_mode=POSITION_MODE,
            deadline=time.monotonic() + 5,
            binary_path=binary,
            cancel_event=cancelled,
        )
