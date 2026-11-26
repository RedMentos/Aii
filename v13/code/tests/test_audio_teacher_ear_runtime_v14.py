"""Runtime integration tests for the optional, transient RAW EAR teacher channel."""
import ast
import hashlib
import importlib.util
import json
import sys
import threading
import types
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from v13 import audio_voice_cues as audio_voice_cues_module
from v13.audio_teacher_ear import (
    append_teacher_hypothesis,
    teacher_ear_consent_lease,
    validate_teacher_ear_result,
)
from v13.audio_voice_cues import consume_pcm16_voice_window
from v13.common import dumps
from v13.store import Store


SOURCE_ID = "fixture:teacher-ear"
AUDIO_RECEIPT = "fixture:audio-consent"
TEACHER_RECEIPT = "fixture:teacher-consent"
TRANSCRIPT_RECEIPT = "fixture:transcript-consent"


def _tone(frequency=140, sample_rate=16000, seconds=1.0, amplitude=6000):
    import math
    import struct
    count = int(sample_rate * seconds)
    samples = [int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate))
               for i in range(count)]
    return struct.pack("<" + "h" * count, *samples)


@contextmanager
def _true_guard(*_args):
    yield True


def _teacher_result(pcm, generation_id, text="untrusted teacher phrase"):
    return {
        "schema": "v14.raw-ear-teacher-result/1",
        "source_id": SOURCE_ID,
        "generation_id": generation_id,
        "source_sha256": hashlib.sha256(pcm).hexdigest(),
        "start_ms": 0,
        "end_ms": 1000,
        "finality": "FINAL",
        "model_id": "fixture-teacher",
        "model_revision": "fixture-rev-1",
        "model_sha256": "1" * 64,
        "language": "en",
        "words": [{"start_ms": 100, "end_ms": 350, "text": text}],
        "network_used": False,
        "raw_audio_persisted": False,
    }


def _make_runtime(tmp_path):
    (tmp_path / "data" / "db").mkdir(parents=True)
    store = Store(tmp_path)
    store.ensure_generation_snapshot({}, {})
    session = store.new_session("RAW EAR teacher runtime test")
    event = store.event(session, "bounded synthetic audio fixture")
    return SimpleNamespace(home=tmp_path, store=store), event


def _load_candidate():
    code_dir = Path(__file__).resolve().parents[1]
    script = code_dir / "scripts" / "integrated_audio_context_candidate_20261121.py"
    spec = importlib.util.spec_from_file_location("teacher_audio_candidate_test", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    sources = {
        relative: (code_dir / relative).read_bytes()
        for relative in ("v13/runtime.py", "v13/cognition.py", "v13/arithmetic_reflex.py")
    }
    return module, module.apply_sources(code_dir, sources)


def _load_candidate_audio_context_store(candidate, monkeypatch):
    module = types.ModuleType("v13.audio_context_store")
    module.__package__ = "v13"
    exec(compile(candidate["v13/audio_context_store.py"], "v13/audio_context_store.py", "exec"),
         module.__dict__)
    monkeypatch.setitem(sys.modules, "v13.audio_context_store", module)
    return module


def _load_audio_window_validator(runtime_source):
    tree = ast.parse(runtime_source)
    names = {"_AUDIO_WINDOW_REQUIRED_FIELDS", "_AUDIO_WINDOW_OPTIONAL_FIELDS"}
    assignments = [
        node for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id in names for target in node.targets)
    ]
    validator = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_validate_audio_window"
    )
    namespace = {"dumps": dumps}
    exec(compile(ast.Module(body=assignments + [validator], type_ignores=[]),
                 "teacher_audio_window_validator.py", "exec"), namespace)
    return namespace["_validate_audio_window"]


def test_teacher_lease_binds_distinct_receipts_source_window_and_finality():
    pcm = _tone()
    generation = "generation-fixture"

    def check(source_id, teacher_receipt, transcript_receipt):
        return (source_id == SOURCE_ID and teacher_receipt == TEACHER_RECEIPT
                and transcript_receipt == TRANSCRIPT_RECEIPT)

    with teacher_ear_consent_lease(
        SOURCE_ID, generation, TEACHER_RECEIPT, TRANSCRIPT_RECEIPT,
        check, _true_guard,
    ) as lease:
        accepted = validate_teacher_ear_result(
            _teacher_result(pcm, generation),
            source_id=SOURCE_ID,
            generation_id=generation,
            source_sha256=hashlib.sha256(pcm).hexdigest(),
            start_ms=0,
            end_ms=1000,
            finality="FINAL",
            teacher_receipt=TEACHER_RECEIPT,
            transcript_receipt=TRANSCRIPT_RECEIPT,
            teacher_lease=lease,
        )
        assert accepted["status"] == "CALLER_SUPPLIED_UNVERIFIED"
        assert accepted["learning_authority"] is False
        assert accepted["action_authority"] is False
        assert accepted["persistence"] == "EPHEMERAL_ONLY"
        assert accepted["summary"] == "100-350ms:untrusted teacher phrase"
        with pytest.raises(ValueError, match="exact audio source/window"):
            validate_teacher_ear_result(
                _teacher_result(pcm, generation),
                source_id=SOURCE_ID,
                generation_id=generation,
                source_sha256="2" * 64,
                start_ms=0,
                end_ms=1000,
                finality="FINAL",
                teacher_receipt=TEACHER_RECEIPT,
                transcript_receipt=TRANSCRIPT_RECEIPT,
                teacher_lease=lease,
            )
    assert lease.active is False
    with pytest.raises(PermissionError, match="live separate teacher/transcript lease"):
        validate_teacher_ear_result(
            _teacher_result(pcm, generation),
            source_id=SOURCE_ID,
            generation_id=generation,
            source_sha256=hashlib.sha256(pcm).hexdigest(),
            start_ms=0,
            end_ms=1000,
            finality="FINAL",
            teacher_receipt=TEACHER_RECEIPT,
            transcript_receipt=TRANSCRIPT_RECEIPT,
            teacher_lease=lease,
        )


def test_teacher_hypothesis_is_added_to_a_copy_only():
    base = [
        {"role": "system", "content": "base system"},
        {"role": "user", "content": "What did I say?"},
    ]
    accepted = {
        "status": "CALLER_SUPPLIED_UNVERIFIED",
        "authority": "TEACHER_HYPOTHESIS",
        "persistence": "EPHEMERAL_ONLY",
        "learning_authority": False,
        "action_authority": False,
        "raw_audio_persisted": False,
        "network_used": False,
        "finality": "FINAL",
        "summary": "100-350ms:hello there",
    }
    dispatch = append_teacher_hypothesis(base, accepted)
    assert "hello there" in dispatch[0]["content"]
    assert "UNTRUSTED_RAW_EAR_TEACHER_HYPOTHESIS" in dispatch[0]["content"]
    assert base == [
        {"role": "system", "content": "base system"},
        {"role": "user", "content": "What did I say?"},
    ]
    assert "hello there" not in json.dumps(base)
    invalid = dict(accepted, learning_authority=True)
    with pytest.raises(ValueError, match="not eligible"):
        append_teacher_hypothesis(base, invalid)


def test_teacher_result_is_not_written_to_perceptpacket_or_audio_context(tmp_path, monkeypatch):
    runtime, event = _make_runtime(tmp_path)
    pcm = _tone()
    generation = event["brain_generation_id"]
    audio_check = lambda source_id, receipt: source_id == SOURCE_ID and receipt == AUDIO_RECEIPT

    @contextmanager
    def audio_guard(source_id, receipt):
        yield audio_check(source_id, receipt)

    def teacher_check(source_id, teacher_receipt, transcript_receipt):
        return (source_id == SOURCE_ID and teacher_receipt == TEACHER_RECEIPT
                and transcript_receipt == TRANSCRIPT_RECEIPT)

    try:
        with audio_voice_cues_module.audio_consent_lease(
            runtime, SOURCE_ID, generation, AUDIO_RECEIPT, audio_check, audio_guard,
        ) as audio_lease:
            with teacher_ear_consent_lease(
                SOURCE_ID, generation, TEACHER_RECEIPT, TRANSCRIPT_RECEIPT,
                teacher_check, _true_guard,
            ) as teacher_lease:
                result = consume_pcm16_voice_window(
                    runtime, pcm, sample_rate=16000, start_ms=0,
                    event_id=event["event_id"], generation_id=generation,
                    source_id=SOURCE_ID, consent_receipt=AUDIO_RECEIPT,
                    consent_check=None, consent_guard=None, consent_lease=audio_lease,
                    finality="FINAL", token_budget=256,
                    teacher_result=_teacher_result(pcm, generation),
                    teacher_lease=teacher_lease,
                    teacher_receipt=TEACHER_RECEIPT,
                    transcript_receipt=TRANSCRIPT_RECEIPT,
                )
                assert result["teacher_ear"]["summary"] == "100-350ms:untrusted teacher phrase"
                assert "teacher_ear" not in json.dumps(result["packet"])
                _module, candidate = _load_candidate()
                context_store = _load_candidate_audio_context_store(candidate, monkeypatch)
                audio_window = {
                    "source_id": SOURCE_ID,
                    "consent_receipt": AUDIO_RECEIPT,
                    "consent_check": audio_check,
                    "_consent_lease": audio_lease,
                }
                context = context_store.record(runtime, event["event_id"], result, audio_window)
                assert context is not None
                stored = runtime.store.read_source(context["summary_source_ref"])
                assert "untrusted teacher phrase" not in stored
                assert '"transcript":null' in stored.replace(" ", "")
                assert context_store.view(runtime, event["event_id"], "C3") is not None
        assert context_store.view(runtime, event["event_id"], "C3") is None
    finally:
        runtime.store.close()


def test_runtime_teacher_window_is_optional_separate_bounded_and_source_checked():
    _module, candidate = _load_candidate()
    runtime_source = candidate["v13/runtime.py"].decode("utf-8")
    validate = _load_audio_window_validator(runtime_source)

    def audio_guard(*_args):
        return _true_guard()

    def teacher_guard(*_args):
        return _true_guard()

    audio = {
        "pcm16": b"\x00\x00" * 160,
        "sample_rate": 16000,
        "start_ms": 0,
        "source_id": SOURCE_ID,
        "consent_receipt": AUDIO_RECEIPT,
        "consent_check": lambda *_: True,
        "consent_guard": audio_guard,
        "finality": "FINAL",
        "consent_revocation_subscribe": lambda *_: (lambda: None),
    }
    teacher = {
        "result": {"schema": "v14.raw-ear-teacher-result/1"},
        "teacher_receipt": TEACHER_RECEIPT,
        "transcript_receipt": TRANSCRIPT_RECEIPT,
        "consent_check": lambda *_: True,
        "consent_guard": teacher_guard,
        "consent_revocation_subscribe": lambda *_: (lambda: None),
    }
    accepted = validate(dict(audio, teacher_ear=teacher))
    assert accepted["teacher_ear"] == teacher
    assert "teacher_ear" not in validate(audio)

    same_receipt = dict(teacher, transcript_receipt=TEACHER_RECEIPT)
    with pytest.raises(ValueError, match="distinct receipts"):
        validate(dict(audio, teacher_ear=same_receipt))
    shared_guard = dict(teacher, consent_guard=audio_guard)
    with pytest.raises(ValueError, match="distinct provider guard"):
        validate(dict(audio, teacher_ear=shared_guard))
    missing_revoke = dict(teacher)
    missing_revoke.pop("consent_revocation_subscribe")
    with pytest.raises(ValueError, match="exact separate consent fields"):
        validate(dict(audio, teacher_ear=missing_revoke))
    oversized = dict(teacher, result={"text": "x" * 9000})
    with pytest.raises(ValueError, match="8192-byte queue bound"):
        validate(dict(audio, teacher_ear=oversized))


def test_runtime_dispatch_is_after_context_save_and_final_c3_selection():
    _module, candidate = _load_candidate()
    source = candidate["v13/runtime.py"].decode("utf-8")
    append_at = source.index("append_teacher_hypothesis(messages,teacher_ear)")
    save_at = source.rfind("save_context(self.store,self.session,eid,runner.role,messages)", 0, append_at)
    generate_at = source.index("runner.generate(messages,self.cancel_event,deadline", append_at)
    final_c3_at = source.rfind("runner=self.pool.get('C3_LANGUAGE')", 0, append_at)
    assert save_at >= 0 and save_at < final_c3_at < append_at < generate_at
    assert "runner.role=='C3_LANGUAGE' and audio_source_ref is not None" in source
    assert "teacher_ear_dispatch_only" in source
    assert "teacher_result=" in source and "teacher_lease=" in source
    assert "teacher_bytes=" in source


def test_teacher_revocation_cancels_active_c3_turn(monkeypatch):
    _module, candidate = _load_candidate()
    runtime_source = candidate["v13/runtime.py"].decode("utf-8")
    tree = ast.parse(runtime_source)
    wrapper = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_audio_lease_turn"
    )
    callbacks = {}
    unsubscribed = []
    teacher_guard_entered = []
    teacher_guard_exited = []

    def subscribe(source_id, receipt, generation_id, on_request, on_revoked):
        callbacks[receipt] = (on_request, on_revoked)
        def unsubscribe():
            unsubscribed.append(receipt)
            callbacks.pop(receipt, None)
        return unsubscribe

    @contextmanager
    def audio_lease(*_args):
        yield object()

    @contextmanager
    def teacher_guard(*_args):
        teacher_guard_entered.append(True)
        try:
            yield True
        finally:
            teacher_guard_exited.append(True)

    monkeypatch.setattr(audio_voice_cues_module, "audio_consent_lease", audio_lease)
    context_store = types.ModuleType("v13.audio_context_store")
    context_store.sweep_revoked = lambda *_args: None
    context_store.revoke_source = lambda *_args: 0
    context_store.has_context = lambda *_args: False
    monkeypatch.setitem(sys.modules, "v13.audio_context_store", context_store)

    def original_turn(_self, _event):
        callbacks[TEACHER_RECEIPT][0]()
        return "turn-finished"

    candidate_runtime = types.ModuleType("v13._candidate_teacher_runtime")
    candidate_runtime.__package__ = "v13"
    candidate_runtime.threading = threading
    candidate_runtime._AUDIO_ORIGINAL_TURN = original_turn
    exec(compile(ast.Module(body=[wrapper], type_ignores=[]),
                 "candidate_teacher_audio_runtime.py", "exec"),
         candidate_runtime.__dict__)

    class FakeStore:
        generation_id = "generation-fixture"
        def log(self, *_args):
            return None

    runtime = SimpleNamespace(
        store=FakeStore(),
        current="turn",
        turn_event=None,
        cancel_event=threading.Event(),
        notice=lambda *_args: None,
    )
    event = {
        "event_id": "teacher-revocation-event",
        "_audio_window": {
            "source_id": SOURCE_ID,
            "consent_receipt": AUDIO_RECEIPT,
            "consent_check": lambda *_args: True,
            "consent_guard": lambda *_args: _true_guard(),
            "consent_revocation_subscribe": subscribe,
            "teacher_ear": {
                "result": {"text": "must be dropped on revoke"},
                "teacher_receipt": TEACHER_RECEIPT,
                "transcript_receipt": TRANSCRIPT_RECEIPT,
                "consent_check": lambda *_args: True,
                "consent_guard": teacher_guard,
                "consent_revocation_subscribe": subscribe,
            },
        },
    }
    result = candidate_runtime._audio_lease_turn(runtime, event)
    assert result == "turn-finished"
    assert runtime.cancel_event.is_set()
    assert TEACHER_RECEIPT in unsubscribed and TRANSCRIPT_RECEIPT in unsubscribed
    assert teacher_guard_entered and teacher_guard_exited
    assert "teacher_ear" not in event["_audio_window"]
