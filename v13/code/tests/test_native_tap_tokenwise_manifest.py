import hashlib
import threading
import time
from types import SimpleNamespace

from v13 import runners
from v13.latent_adapter import build_tokenwise_tap_manifest
from v13.runners import LlamaRunner
from v13.runtime import Runtime

SOURCE = "A\\u00e1\\U0001f9e0e\\u0301"
PIECES = [
    {"id": 10, "piece": "A"}, {"id": 11, "piece": [0xC3]},
    {"id": 12, "piece": [0xA1, 0xF0]}, {"id": 13, "piece": [0x9F, 0xA7]},
    {"id": 14, "piece": [0xA0]}, {"id": 15, "piece": "e"},
    {"id": 16, "piece": [0xCC]}, {"id": 17, "piece": [0x81]},
]
CONTENT_IDS = [piece["id"] for piece in PIECES]
PREFILL_IDS = [1] + CONTENT_IDS


def rows(count):
    return [[float(i + 1)] * 1024 for i in range(count)]


def test_native_runner_emits_exact_tokenwise_manifest(tmp_path, monkeypatch):
    vectors = rows(len(PREFILL_IDS))
    runner = LlamaRunner(tmp_path, "B2_GIST", SimpleNamespace(), {"threads": 1}, purpose="tap")
    runner.tap_id = "qwen35.result_norm.final.v1"
    runner.tap_dim = 1024
    runner.proc = SimpleNamespace(pid=4321)
    runner.load = lambda cancel, deadline: None
    runner.unload = lambda: None

    def fake_json(method, path, payload, deadline, timeout_cap=3.0):
        if path == "/tokenize" and payload.get("with_pieces"):
            return {"tokens": PIECES}
        if path == "/tokenize":
            return {"tokens": PREFILL_IDS}
        if path == "/embeddings":
            return [{"embedding": vectors}]
        raise AssertionError((method, path, payload))

    runner._json = fake_json
    monkeypatch.setattr(runners, "process_memory", lambda pid: {"rss_bytes": 4096, "pss_bytes": 2048})
    result = runner.tap(SOURCE, threading.Event(), time.monotonic() + 10)
    manifest = result["tokenwise_manifest"]
    assert manifest["schema"] == "v14.source-bound-tokenwise-tap/1"
    assert manifest["source_sha256"] == hashlib.sha256(SOURCE.encode("utf-8")).hexdigest()
    assert manifest["source_length"] == len(SOURCE.encode("utf-8"))
    assert manifest["token_ids"] == CONTENT_IDS
    assert manifest["prefill_positions"] == list(range(1, 9))
    assert manifest["token_spans"][1:3] == [[1, 2], [2, 4]]
    assert "vectors" not in manifest
    assert result["metrics"]["tokenwise_manifest_status"] == "VALID"
    assert result["vectors"] == vectors


def test_cognition_persists_and_revalidates_manifest_without_raw_source(tmp_path):
    runtime = Runtime(tmp_path)
    runtime.sleep.cycle.set_policy("enabled", "off")
    event = runtime.store.event(runtime.session, SOURCE)
    vectors = rows(len(PREFILL_IDS))
    built = build_tokenwise_tap_manifest(SOURCE, CONTENT_IDS, PIECES, PREFILL_IDS, vectors)
    metadata = {key: value for key, value in built.items() if key != "vectors"}

    class TapRunner:
        tap_id = "qwen35.result_norm.final.v1"

        def tap(self, text, cancel, deadline):
            assert text == SOURCE
            return {
                "tap_id": self.tap_id, "token_ids": PREFILL_IDS, "vectors": vectors,
                "tokenwise_manifest": metadata,
                "metrics": {"tap_id": self.tap_id, "whole_sequence_prefill": True,
                            "pooling": "none", "prompt_tokens": len(PREFILL_IDS)},
            }

    runtime.pool.get_tap = lambda role: TapRunner()
    runtime.models.revision = lambda role: "qwen35-r1"
    runtime.learner.predict_states = lambda role, values: None
    try:
        packet = runtime.cognition.tap("B2_GIST", event, event["source_ref"], time.monotonic() + 10)
        assert packet["tokenwise_manifest_sha256"] == packet["tokenwise_manifest"]["manifest_sha256"]
        blob_path = runtime.home / packet["feature_path"]
        assert SOURCE.encode("utf-8") not in blob_path.read_bytes()
        stored = runtime.cognition.read_tap(packet)
        assert stored["tokenwise_manifest"]["vectors"] == vectors[1:]
        original = runtime.store.read_source
        runtime.store.read_source = lambda ref: SOURCE + "tampered"
        try:
            import pytest
            with pytest.raises(ValueError, match="source bytes"):
                runtime.cognition.read_tap(packet)
        finally:
            runtime.store.read_source = original
    finally:
        runtime.close()
