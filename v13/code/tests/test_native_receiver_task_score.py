import hashlib
from pathlib import Path
import struct
import sys
import time
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from v13.native_receiver_task_score import NativeReceiverTaskScoreError, probe_native_receiver_task_score, probe_anchor_preserving_candidate, _target_payload

REV = "b29c606e28a01b1bc8c1351026a0fa6e616bf6c4"
MODEL_BYTES = b"fixture-model-no-weights"
MODEL_SHA = hashlib.sha256(MODEL_BYTES).hexdigest()
SOURCE = {"source_id": "task-source-1", "sha256": "a" * 64}
MESSAGE = SOURCE


def fake_binary(path: Path, *, scores=None, modify_model=False, bad_count=False, bad_finite=True):
    scores = scores if scores is not None else [-0.2, -0.4]
    mutate = 'model.write_bytes(b"tampered")' if modify_model else "pass"
    source = f'''#!/usr/bin/env python3
import json, pathlib, struct, sys
REV = {REV!r}
if sys.argv[1:] == ["--version"]:
    print(json.dumps(dict(schema="v14.native-receiver-target-score/1", runner_revision=REV, llama_version="fake-llama-1")))
    raise SystemExit(0)
args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
rows, dim, count = int(args["--rows"]), int(args["--input-dim"]), int(args["--target-count"])
payload = sys.stdin.buffer.read()
if len(payload) != rows * dim * 4 + count * 4: raise SystemExit(65)
values = struct.unpack("<" + "f" * (rows * dim), payload[:rows * dim * 4])
ids = struct.unpack("<" + "i" * count, payload[rows * dim * 4:])
if list(ids) != [5, 6][:count]: raise SystemExit(66)
if len(values) != rows * dim: raise SystemExit(67)
model = pathlib.Path(args["--model"])
{mutate}
out = dict(schema="v14.native-receiver-target-score/1", runner_revision=REV,
    llama_version="fake-llama-1", status="TARGET_SCORED", input_rows=rows, input_dim=dim,
    receiver_input_dim=dim, position_ids=[int(x) for x in args["--positions"].split(",")],
    position_mode="ZERO_BASED_CONTIGUOUS_FROM_TOKENIZER_PREFILL", decode_status=0,
    native_input_consumed=True, score_method="TEACHER_FORCED_TARGET_LOGPROB_V1",
    target_token_count=(count + 1 if {bad_count!r} else count),
    token_logprobs={scores!r}, finite_scores={bad_finite!r})
print(json.dumps(out))
'''
    path.write_text(source)
    path.chmod(0o755)
    return path


def setup(tmp_path, **fake_kwargs):
    home = tmp_path / "home"
    (home / "models").mkdir(parents=True)
    model = home / "models" / "receiver.gguf"
    model.write_bytes(MODEL_BYTES)
    binary = fake_binary(tmp_path / "fake-native-scorer", **fake_kwargs)
    return home, model, binary


def call(home, model, binary, **overrides):
    args = dict(
        home=home, model_path=model, expected_model_sha256=MODEL_SHA,
        receiver_role="C3_LANGUAGE", receiver_model_revision="receiver-r1",
        tokenizer_revision="llama-server:b10964;gguf:" + MODEL_SHA,
        vectors=[[0.1, 0.2], [0.3, 0.4]],
        expected_input_sha256=hashlib.sha256(struct.pack("<ffff", 0.1, 0.2, 0.3, 0.4)).hexdigest(),
        position_ids=[0, 1], position_mode="ZERO_BASED_CONTIGUOUS_FROM_TOKENIZER_PREFILL",
        target_token_ids=[5, 6], deadline=time.monotonic() + 10,
        environment="SYNTHETIC", condition="LATENT_CANDIDATE", task_group_id="task-1",
        task_family="ARITHMETIC", session_id="session-a", source_ref=SOURCE,
        message_source_ref=MESSAGE, context_sha256="c" * 64, adapter_sha256="d" * 64,
        binary_path=binary,
    )
    args.update(overrides)
    return probe_native_receiver_task_score(**args)


def test_synthetic_native_task_score_binds_payload_and_builds_authority_zero_receipt(tmp_path):
    home, model, binary = setup(tmp_path)
    result = call(home, model, binary)
    native = result["native_receipt"]
    task = result["task_score_receipt"]
    expected_input = hashlib.sha256(struct.pack("<ffff", 0.1, 0.2, 0.3, 0.4)).hexdigest()
    expected_target = hashlib.sha256(struct.pack("<ii", 5, 6)).hexdigest()
    assert native["execution_kind"] == "SYNTHETIC_FIXTURE"
    assert native["environment"] == "SYNTHETIC"
    assert native["llama_cpp_revision"] == REV
    assert native["input_sha256"] == expected_input
    assert native["target_token_ids_sha256"] == expected_target
    assert native["target_token_count"] == 2
    assert native["token_logprobs"] == [-0.2, -0.4]
    assert task["status"] == "SCORED"
    assert task["persisted"] is False
    assert task["training_authority"] == 0
    assert task["native_receiver_authority"] == 0
    assert result["persisted"] is False


def test_rejects_malformed_target_ids_before_native_execution():
    with pytest.raises(NativeReceiverTaskScoreError):
        _target_payload([5, True])
    with pytest.raises(NativeReceiverTaskScoreError):
        _target_payload([-1])
    with pytest.raises(NativeReceiverTaskScoreError):
        _target_payload([1] * 513)


def test_rejects_missing_android_receipt_metadata(tmp_path):
    home, model, _binary = setup(tmp_path)
    with pytest.raises(NativeReceiverTaskScoreError, match="Android/Redmi scoring requires"):
        call(home, model, None, binary_path=None, environment="REDMI")


def test_rejects_injected_binary_claiming_redmi(tmp_path):
    home, model, binary = setup(tmp_path)
    with pytest.raises(NativeReceiverTaskScoreError, match="injected native scorer binaries are SYNTHETIC"):
        call(home, model, binary, environment="REDMI")


def test_rejects_bad_native_target_count(tmp_path):
    home, model, binary = setup(tmp_path, bad_count=True)
    with pytest.raises(NativeReceiverTaskScoreError, match="receipt failed validation"):
        call(home, model, binary)


def test_rejects_model_mutation_during_scoring(tmp_path):
    home, model, binary = setup(tmp_path, modify_model=True)
    with pytest.raises(NativeReceiverTaskScoreError, match="model changed"):
        call(home, model, binary)


def test_rejects_nonfinite_or_positive_target_logprob(tmp_path):
    home, model, binary = setup(tmp_path, scores=[-0.1, 0.2])
    with pytest.raises(NativeReceiverTaskScoreError, match="log-probabilities"):
        call(home, model, binary)


def test_rejects_tokenizer_revision_not_bound_to_gguf(tmp_path):
    home, model, binary = setup(tmp_path)
    with pytest.raises(NativeReceiverTaskScoreError, match="tokenizer revision"):
        call(home, model, binary, tokenizer_revision="llama-server:b10964;gguf:" + "e" * 64)


def test_rejects_candidate_input_hash_mismatch(tmp_path):
    home, model, binary = setup(tmp_path)
    with pytest.raises(NativeReceiverTaskScoreError, match="differ from the bound candidate"):
        call(home, model, binary, expected_input_sha256="e" * 64)


def test_rejects_noncontiguous_positions(tmp_path):
    home, model, binary = setup(tmp_path)
    with pytest.raises(NativeReceiverTaskScoreError, match="contiguous"):
        call(home, model, binary, position_ids=[0, 2])


def test_rejects_expired_deadline(tmp_path):
    home, model, binary = setup(tmp_path)
    with pytest.raises(TimeoutError, match="deadline expired"):
        call(home, model, binary, deadline=time.monotonic() - 1)


def test_anchor_candidate_helper_consumes_exact_perception_output(tmp_path):
    home, model, binary = setup(tmp_path)
    input_sha = hashlib.sha256(struct.pack("<ffff", 0.1, 0.2, 0.3, 0.4)).hexdigest()
    candidate = {
        "schema": "v14.native-tokenwise-anchor-residual-input/1",
        "input_strategy": "ANCHOR_PLUS_CAPPED_RESIDUAL_V1",
        "vectors": [[0.1, 0.2], [0.3, 0.4]],
        "input_sha256": input_sha,
        "position_ids": [0, 1],
        "position_mode": "ZERO_BASED_CONTIGUOUS_FROM_TOKENIZER_PREFILL",
        "receiver_model_sha256": MODEL_SHA,
        "receiver_model_revision": "receiver-r1",
        "tokenizer_revision": "llama-server:b10964;gguf:" + MODEL_SHA,
        "receiver_role": "C3_LANGUAGE",
        "source_ref": SOURCE,
        "session_id": "session-a",
        "adapter_sha256": "d" * 64,
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
        "persisted": False,
        "anchor_rows_preserved_as_base": True,
    }
    result = probe_anchor_preserving_candidate(
        candidate, home=home, model_path=model, target_token_ids=[5, 6],
        task_group_id="task-anchor-1", task_family="ARITHMETIC",
        context_sha256=SOURCE["sha256"], deadline=time.monotonic() + 10,
        environment="SYNTHETIC", binary_path=binary,
    )
    assert result["task_score_receipt"]["status"] == "SCORED"
    assert result["task_score_receipt"]["arguments"]["condition"] == "LATENT_CANDIDATE"
    assert result["task_score_receipt"]["arguments"]["message_source_ref"] == SOURCE
    assert result["task_score_receipt"]["arguments"]["input_sha256"] == input_sha
