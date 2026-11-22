import threading

import pytest

from v13 import vision
from v13 import vision_runtime_bridge as bridge


SOURCE_REF = {
    "source_id": "image-1",
    "sha256": "a" * 64,
    "char_start": 0,
    "char_end": 0,
    "modality": "image",
}
RECORD = {
    "ref": SOURCE_REF,
    "regions": [
        {"region_id": "r00", "box": [0, 0, 10, 10]},
        {"region_id": "r01", "box": [10, 0, 20, 10]},
        {"region_id": "r10", "box": [0, 10, 10, 20]},
    ],
}


class StoreStub:
    generation_id = "generation-1"

    def __init__(self, lock, *, fail_add=False):
        self.lock = lock
        self.fail_add = fail_add
        self.packets = []
        self.logs = []

    def add_packet(self, kind, packet_value):
        assert self.lock._is_owned()
        if self.fail_add:
            raise OSError("synthetic store failure")
        self.packets.append((kind, packet_value))

    def log(self, kind, event_id, data):
        self.logs.append((kind, event_id, data))


class RuntimeStub:
    def __init__(self, *, fail_add=False):
        self.lock = threading.RLock()
        self.store = StoreStub(self.lock, fail_add=fail_add)
        self.cfg = {"input_bytes": 8192}
        self.submitted = []

    def submit(self, text):
        assert self.lock._is_owned()
        self.submitted.append(text)
        return "event-1"


class AttentionStub:
    def __init__(self):
        self.calls = []

    def modulate(self, event_id, sal=None):
        self.calls.append((event_id, sal))
        return {"captured": True, "salience": sal}


def patch_vision(monkeypatch, *, caption_source=None):
    monkeypatch.setattr(vision, "read_image", lambda *args, **kwargs: object())
    monkeypatch.setattr(vision, "describe", lambda runtime, rec, region="g": {
        "text": "A red car near a tree.",
        "authority": vision.AUTHORITY,
        "teacher": "LFM2.5-VL-450M",
        "revision": "installed-revision",
        "source_ref": caption_source or {
            "source_id": SOURCE_REF["source_id"],
            "sha256": SOURCE_REF["sha256"],
        },
    })
    monkeypatch.setattr(vision, "background", lambda image: object())
    monkeypatch.setattr(
        vision, "saliency",
        lambda image, box, bg: {0: 0.2, 10: 0.7}.get(box[0], 0.1),
    )
    monkeypatch.setattr(vision, "region_ref", lambda source, region: {
        "source_id": source["source_id"],
        "sha256": source["sha256"],
        "char_start": 0,
        "char_end": 0,
        "modality": "image",
        "region_id": region["region_id"],
        "box": region["box"],
    })


def test_source_bound_a5_packet_a4_and_runtime_submit(monkeypatch):
    patch_vision(monkeypatch)
    runtime = RuntimeStub()
    attention = AttentionStub()
    monkeypatch.setattr(bridge.attctl, "controller", lambda _runtime: attention)

    result = bridge.submit_question(runtime, RECORD, "What is in this picture?")

    assert result["status"] == "IMAGE_CONTEXT_SUBMITTED"
    assert result["packet_persisted"] is True
    assert result["native_visual_activation"] is False
    assert len(runtime.submitted) == 1
    assert len(runtime.store.packets) == 1
    kind, percept = runtime.store.packets[0]
    assert kind == "PerceptPacket"
    assert percept["event_id"] == "event-1"
    assert percept["brain_generation_id"] == "generation-1"
    assert percept["modality"] == "image"
    assert percept["source_ref"]["sha256"] == "a" * 64
    assert percept["segments"][0]["teacher_authority"] == "REFERENCE_NOT_FACT"
    assert percept["segments"][0]["action_authority"] is False
    assert percept["segments"][0]["learning_authority"] is False
    assert "UNTRUSTED_IMAGE_EVIDENCE_JSON" in runtime.submitted[0]
    assert "What is in this picture?" in runtime.submitted[0]
    assert "native image pixels" in runtime.submitted[0]
    assert result["a4_attention"] == {"captured": True, "salience": {"novelty": 0.7}}
    assert attention.calls == [("event-1", {"novelty": 0.7})]


def test_oversized_question_and_invalid_source_fail_before_submit(monkeypatch):
    patch_vision(monkeypatch)
    runtime = RuntimeStub()
    with pytest.raises(ValueError, match="512 UTF-8 bytes"):
        bridge.submit_question(runtime, RECORD, "x" * 513)
    invalid = {"ref": dict(SOURCE_REF, sha256="bad"), "regions": []}
    with pytest.raises(ValueError, match="source digest"):
        bridge.submit_question(runtime, invalid, "Question?")
    assert runtime.submitted == []
    assert runtime.store.packets == []


def test_caption_from_different_source_is_rejected(monkeypatch):
    patch_vision(monkeypatch, caption_source={
        "source_id": SOURCE_REF["source_id"],
        "sha256": "b" * 64,
    })
    runtime = RuntimeStub()
    with pytest.raises(ValueError, match="not bound"):
        bridge.submit_question(runtime, RECORD, "Question?")
    assert runtime.submitted == []


def test_packet_persistence_failure_is_reported_not_claimed(monkeypatch):
    patch_vision(monkeypatch)
    runtime = RuntimeStub(fail_add=True)
    attention = AttentionStub()
    monkeypatch.setattr(bridge.attctl, "controller", lambda _runtime: attention)

    result = bridge.submit_question(runtime, RECORD, "Question?")

    assert result["status"] == "IMAGE_TEXT_CONTEXT_SUBMITTED_PACKET_PERSIST_FAILED"
    assert result["packet_persisted"] is False
    assert result["packet_id"] is None
    assert result["a4_attention"] is None
    assert attention.calls == []
    assert runtime.submitted
    assert runtime.store.logs[0][0] == "vision_packet_persist_failed"


def test_operator_command_exposes_image_ask(monkeypatch):
    from v13 import vision_runtime_bridge

    monkeypatch.setattr(vision, "load", lambda store: {"images": {}})
    monkeypatch.setattr(vision, "_find", lambda state, arg: RECORD)
    monkeypatch.setattr(
        vision_runtime_bridge, "submit_question",
        lambda runtime, rec, question: {"submitted": question, "source": rec["ref"]["source_id"]},
    )

    result = vision.operator_command(object(), ["ask", "last", "What", "is", "visible?"])

    assert result == {"submitted": "What is visible?", "source": "image-1"}
