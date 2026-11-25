import hashlib
import json
import threading
import time
from pathlib import Path

import pytest

from v13.models import model_key
from v13.tokenwise_tap_runtime import (
    POSITION_MODE,
    TokenwiseTapError,
    capture_tokenwise_tap,
    read_tokenwise_tap,
)


SOURCE = "A🌍 café"
PIECES = [
    {"id": 11, "piece": "A"},
    {"id": 12, "piece": "🌍"},
    {"id": 13, "piece": " café"},
]
PREFILL_IDS = [1, 11, 12, 13, 2]
PREFILL_VECTORS = [
    [99.0, 99.0],
    [0.1, 0.2],
    [0.3, 0.4],
    [0.5, 0.6],
    [88.0, 88.0],
]


class _Proc:
    def __init__(self, code=None):
        self.code = code

    def poll(self):
        return self.code


class _Runner:
    def __init__(self, binary):
        self.binary = str(binary)
        self.proc = _Proc()
        self.calls = []

    def _json(self, method, path, body, deadline, timeout_cap=None):
        self.calls.append((method, path, body, deadline, timeout_cap))
        assert method == "POST"
        assert path == "/tokenize"
        assert body == {"content": SOURCE, "add_special": False, "with_pieces": True}
        return {"tokens": PIECES}


class _Store:
    def __init__(self, source_ref, source_text):
        self.source_ref = source_ref
        self.source_text = source_text
        self.packets = {}
        self.logs = []

    def read_source(self, source_ref):
        assert source_ref == self.source_ref
        return self.source_text

    def add_packet(self, kind, packet):
        self.packets[(kind, packet["packet_id"])] = json.dumps(packet, sort_keys=True)

    def one(self, query, params):
        packet_id = params[0]
        payload = self.packets.get(("TokenwiseTapPacket", packet_id))
        return {"payload": payload} if payload is not None else None

    def log(self, kind, event_id, detail):
        self.logs.append((kind, event_id, detail))


class _Models:
    def __init__(self, model_path, model_sha):
        self.b2_control = False
        self.installed = {
            model_key("B2_GIST", False): {
                "download_complete": True,
                "model_id": "qwen35-gist",
                "exact_revision": "model-r1",
                "main_file": "sender.gguf",
                "files": {"sender.gguf": {"sha256": model_sha, "size": model_path.stat().st_size}},
            }
        }
        self._model_path = model_path

    def revision(self, role):
        assert role == "B2_GIST"
        return "model-r1"

    def path_for(self, role):
        assert role == "B2_GIST"
        return self._model_path


class _Pool:
    def __init__(self, runner):
        self.runner = runner

    def get_tap(self, role):
        assert role == "B2_GIST"
        return self.runner


class _Runtime:
    def __init__(self, home, model_path, model_sha, runner):
        self.home = home
        self.models = _Models(model_path, model_sha)
        self.pool = _Pool(runner)
        self.cancel_event = threading.Event()


class _Cognition:
    def __init__(self, runtime, store, tap_data):
        self.r = runtime
        self.s = store
        self.tap_data = tap_data

    def read_tap(self, tap_packet):
        assert tap_packet["packet_id"] == "tap-1"
        return self.tap_data


def _fixture(tmp_path, *, pieces=PIECES, prefill_ids=PREFILL_IDS, vectors=PREFILL_VECTORS):
    home = Path(tmp_path)
    (home / "models" / "gist").mkdir(parents=True)
    (home / "bin").mkdir()
    (home / "data" / "blobs").mkdir(parents=True)
    model_path = home / "models" / "gist" / "sender.gguf"
    model_path.write_bytes(b"installed sender model")
    model_sha = hashlib.sha256(model_path.read_bytes()).hexdigest()
    binary = home / "bin" / "llama-server"
    binary.write_bytes(b"pinned llama-server test binary")
    source_ref = {
        "source_id": "source-1",
        "sha256": hashlib.sha256(SOURCE.encode("utf-8")).hexdigest(),
        "char_start": 0,
        "char_end": len(SOURCE),
        "modality": "text",
    }
    store = _Store(source_ref, SOURCE)
    runner = _Runner(binary)
    runner._json = lambda method, path, body, deadline, timeout_cap=None: (
        runner.calls.append((method, path, body, deadline, timeout_cap))
        or {"tokens": pieces}
    )
    runtime = _Runtime(home, model_path, model_sha, runner)
    cognition = _Cognition(runtime, store, {
        "token_ids": list(prefill_ids),
        "vectors": [list(row) for row in vectors],
    })
    tap_packet = {
        "packet_id": "tap-1",
        "event_id": "event-1",
        "brain_generation_id": "generation-1",
        "source_ref": source_ref,
        "provenance": [source_ref],
        "role": "B2_GIST",
        "tap_id": "qwen35.result_norm.final.v1",
        "model_revision": "model-r1",
    }
    return cognition, tap_packet, runner, model_path, binary


def test_capture_maps_content_tokens_to_prefill_rows_and_roundtrips(tmp_path):
    cognition, tap_packet, runner, model_path, binary = _fixture(tmp_path)
    packet = capture_tokenwise_tap(cognition, tap_packet, time.monotonic() + 20)
    assert runner.calls[0][1] == "/tokenize"
    assert runner.calls[0][2]["add_special"] is False
    assert runner.calls[0][2]["with_pieces"] is True
    assert packet["role"] == "B2_GIST"
    assert packet["token_ids"] == [11, 12, 13]
    assert packet["token_spans"] == [[0, 1], [1, 5], [5, 11]]
    assert packet["prefill_positions"] == [1, 2, 3]
    assert packet["special_prefix_tokens"] == 1
    assert packet["special_suffix_tokens"] == 1
    assert packet["prefill_token_count"] == 5
    assert packet["position_mode"] == POSITION_MODE
    assert packet["shape"] == [3, 2]
    assert packet["production_route"] is False
    assert packet["training_authority"] == 0

    blob_path = cognition.r.home / packet["feature_path"]
    blob = json.loads(blob_path.read_text(encoding="utf-8"))
    assert blob["vectors"] == [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
    serialized = json.dumps(blob, ensure_ascii=False)
    assert "piece" not in serialized
    assert SOURCE not in serialized

    restored = read_tokenwise_tap(cognition, packet)
    assert restored["token_ids"] == [11, 12, 13]
    assert restored["token_spans"] == [[0, 1], [1, 5], [5, 11]]
    assert restored["vectors"] == blob["vectors"]
    assert restored["tokenizer_revision"].startswith("llama-server-sha256:")
    assert restored["position_mode"] == POSITION_MODE


def test_capture_rejects_ambiguous_content_sequence(tmp_path):
    ambiguous_prefill = [1, 11, 12, 13, 11, 12, 13, 2]
    ambiguous_vectors = [[float(i), float(i + 1)] for i in range(len(ambiguous_prefill))]
    cognition, tap_packet, runner, _, _ = _fixture(
        tmp_path, prefill_ids=ambiguous_prefill, vectors=ambiguous_vectors
    )
    with pytest.raises(TokenwiseTapError, match="alignment rejected"):
        capture_tokenwise_tap(cognition, tap_packet, time.monotonic() + 20)
    assert not cognition.s.packets


def test_capture_rejects_non_reconstructing_token_pieces(tmp_path):
    bad_pieces = [dict(PIECES[0]), dict(PIECES[1]), {"id": 13, "piece": " wrong"}]
    cognition, tap_packet, runner, _, _ = _fixture(tmp_path, pieces=bad_pieces)
    with pytest.raises(TokenwiseTapError, match="alignment rejected"):
        capture_tokenwise_tap(cognition, tap_packet, time.monotonic() + 20)
    assert not cognition.s.packets


def test_read_rejects_source_model_and_runner_drift(tmp_path):
    cognition, tap_packet, _, model_path, binary = _fixture(tmp_path)
    packet = capture_tokenwise_tap(cognition, tap_packet, time.monotonic() + 20)

    cognition.s.source_text = SOURCE + " changed"
    with pytest.raises(TokenwiseTapError, match="source bytes changed"):
        read_tokenwise_tap(cognition, packet)
    cognition.s.source_text = SOURCE

    model_path.write_bytes(b"changed model")
    with pytest.raises(TokenwiseTapError, match="model bytes differ"):
        read_tokenwise_tap(cognition, packet)
    model_path.write_bytes(b"installed sender model")

    binary.write_bytes(b"changed llama-server")
    with pytest.raises(TokenwiseTapError, match="tokenizer binary/model binding changed"):
        read_tokenwise_tap(cognition, packet)


def test_capture_requires_live_runner_and_valid_deadline(tmp_path):
    cognition, tap_packet, runner, _, _ = _fixture(tmp_path)
    runner.proc = _Proc(1)
    with pytest.raises(TokenwiseTapError, match="runner is not alive"):
        capture_tokenwise_tap(cognition, tap_packet, time.monotonic() + 20)
    runner.proc = _Proc()
    with pytest.raises(TimeoutError):
        capture_tokenwise_tap(cognition, tap_packet, time.monotonic() - 1)
