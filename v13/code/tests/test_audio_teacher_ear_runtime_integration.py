import json
import math
import struct
from contextlib import contextmanager
from pathlib import Path

import pytest

from v13.audio_teacher_ear import TeacherEarManifest, SherpaOnlineTeacher
from v13.audio_voice_cues import audio_consent_lease, consume_pcm16_voice_window
from v13.audio_temporal_evidence import TemporalVoiceEvidence
from v13.runtime import Runtime

SOURCE = "fixture:teacher-ear"
RECEIPT = "fixture:teacher-ear-consent"


class FloatArray:
    def __init__(self, values):
        self.values = list(values)
    def astype(self, _dtype):
        return self
    def __itruediv__(self, divisor):
        self.values = [value / divisor for value in self.values]
        return self
    def copy(self):
        return FloatArray(self.values)


class FakeNumpy:
    float32 = "float32"
    @staticmethod
    def frombuffer(data, dtype):
        assert dtype == "<i2"
        return FloatArray(value[0] for value in struct.iter_unpack("<h", data))
    @staticmethod
    def zeros(count, dtype):
        assert dtype == "float32"
        return FloatArray([0.0] * count)


class FakeStream:
    def __init__(self):
        self.waveforms = []
        self.pending = False
        self.finished = False
        self.input_finished_calls = 0
    def accept_waveform(self, sample_rate, waveform):
        assert sample_rate == 16000
        assert isinstance(waveform, FloatArray)
        self.waveforms.append(waveform.copy())
        self.pending = True
    def input_finished(self):
        self.finished = True
        self.input_finished_calls += 1
        self.pending = True


class FakeRecognizer:
    def __init__(self):
        self.stream = FakeStream()
        self.text = "hello from the optional teacher"
        self.create_stream_calls = 0
    def create_stream(self):
        self.create_stream_calls += 1
        return self.stream
    def is_ready(self, stream):
        return stream.pending
    def decode_stream(self, stream):
        stream.pending = False
    def get_result(self, _stream):
        return self.text


def teacher():
    manifest = TeacherEarManifest(
        model_id="fixture/sherpa-small", model_revision="fixture-rev",
        language="en", license_id="Apache-2.0", model_root="/unused-in-test",
        encoder="encoder.onnx", decoder="decoder.onnx", joiner="joiner.onnx", tokens="tokens.txt",
        file_sha256={name: "a" * 64 for name in ("encoder", "decoder", "joiner", "tokens")},
    )
    return SherpaOnlineTeacher(manifest, recognizer=FakeRecognizer(), numpy_module=FakeNumpy())


def tone(sample_rate=16000, frequency=140, seconds=1.0, amplitude=6000):
    count = int(sample_rate * seconds)
    samples = [int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate)) for i in range(count)]
    return struct.pack("<" + "h" * len(samples), *samples)


def consent_ok(source_id, receipt):
    return source_id == SOURCE and receipt == RECEIPT


@contextmanager
def consent_guard(source_id, receipt):
    yield consent_ok(source_id, receipt)


def run_consumer(tmp_path, *, persist):
    runtime = Runtime(Path(tmp_path))
    runtime.sleep.cycle.set_policy("enabled", "off")
    try:
        event = runtime.store.event(runtime.session, "synthetic caller-supplied audio input")
        generation = event["brain_generation_id"]
        with audio_consent_lease(
            runtime, SOURCE, generation, RECEIPT, consent_ok, consent_guard,
        ) as lease:
            result = consume_pcm16_voice_window(
                runtime, tone(), sample_rate=16000, start_ms=100,
                event_id=event["event_id"], generation_id=generation,
                source_id=SOURCE, consent_receipt=RECEIPT,
                consent_check=consent_ok, consent_guard=consent_guard,
                finality="FINAL", consent_lease=lease, token_budget=512,
                teacher_ear=teacher(), teacher_asr_opt_in=True,
                transcript_persist_opt_in=persist,
            )
        stored = runtime.store.one(
            "SELECT payload FROM packets WHERE id=? AND kind='PerceptPacket'",
            (result["packet"]["packet_id"],),
        )
        assert stored is not None
        return result, json.loads(stored["payload"])
    finally:
        runtime.close()


def test_teacher_transcript_is_ephemeral_without_separate_persistence_opt_in(tmp_path):
    result, stored_packet = run_consumer(tmp_path, persist=False)
    acoustic = result["packet"]["segments"][0]["acoustic"]
    assert result["teacher_ear"]["segments"][0]["text"] == "hello from the optional teacher"
    assert "teacher_ear" not in acoustic
    assert "teacher_ear" not in stored_packet["segments"][0]["acoustic"]
    assert result["packet"]["segments"][0]["asr_transcript"] is None
    assert "hello from the optional teacher" not in result["c3_admission"].selected[0].summary


def test_teacher_transcript_reaches_packet_and_c3_only_after_separate_persistence_opt_in(tmp_path):
    result, stored_packet = run_consumer(tmp_path, persist=True)
    acoustic = result["packet"]["segments"][0]["acoustic"]
    teacher_record = acoustic["teacher_ear"]
    assert teacher_record["source_ref"]["source_sha256"] == result["packet"]["source_ref"]["sha256"]
    assert stored_packet["segments"][0]["acoustic"]["teacher_ear"] == teacher_record
    assert result["packet"]["segments"][0]["asr_transcript"] is None
    assert "hello from the optional teacher" in result["c3_admission"].selected[0].summary


def test_teacher_object_without_asr_opt_in_fails_before_packet_persistence(tmp_path):
    runtime = Runtime(Path(tmp_path))
    runtime.sleep.cycle.set_policy("enabled", "off")
    try:
        event = runtime.store.event(runtime.session, "synthetic caller-supplied audio input")
        generation = event["brain_generation_id"]
        with audio_consent_lease(
            runtime, SOURCE, generation, RECEIPT, consent_ok, consent_guard,
        ) as lease:
            with pytest.raises(PermissionError, match="explicit opt-in"):
                consume_pcm16_voice_window(
                    runtime, tone(), sample_rate=16000, start_ms=100,
                    event_id=event["event_id"], generation_id=generation,
                    source_id=SOURCE, consent_receipt=RECEIPT,
                    consent_check=consent_ok, consent_guard=consent_guard,
                    finality="FINAL", consent_lease=lease, token_budget=512,
                    teacher_ear=teacher(), teacher_asr_opt_in=False,
                )
        count = runtime.store.one("SELECT COUNT(*) AS n FROM packets WHERE kind='PerceptPacket'")["n"]
        assert count == 0
    finally:
        runtime.close()



def test_streaming_teacher_session_reaches_real_audio_packet_and_c3_delta_consumer(tmp_path):
    runtime = Runtime(Path(tmp_path))
    runtime.sleep.cycle.set_policy("enabled", "off")
    temporal_state = TemporalVoiceEvidence()
    ear = teacher()
    recognizer = ear._recognizer
    try:
        first_event = runtime.store.event(runtime.session, "synthetic audio window one")
        second_event = runtime.store.event(runtime.session, "synthetic audio window two")
        third_event = runtime.store.event(runtime.session, "synthetic audio window three")
        generation = first_event["brain_generation_id"]
        assert second_event["brain_generation_id"] == generation
        assert third_event["brain_generation_id"] == generation
        with audio_consent_lease(
            runtime, SOURCE, generation, RECEIPT, consent_ok, consent_guard,
            temporal_state=temporal_state,
        ) as lease:
            session = ear.open_stream(
                runtime=runtime, source_id=SOURCE, generation_id=generation,
                consent_receipt_ref=RECEIPT, consent_lease=lease,
                temporal_state=temporal_state, teacher_asr_opt_in=True,
            )
            recognizer.text = "hello"
            first = consume_pcm16_voice_window(
                runtime, tone(seconds=0.5), sample_rate=16000, start_ms=100,
                event_id=first_event["event_id"], generation_id=generation,
                source_id=SOURCE, consent_receipt=RECEIPT,
                consent_check=consent_ok, consent_guard=consent_guard,
                finality="PROVISIONAL", consent_lease=lease,
                temporal_state=temporal_state, token_budget=512,
                teacher_ear=session, teacher_asr_opt_in=True,
                transcript_persist_opt_in=True,
            )
            recognizer.text = "hello world"
            second = consume_pcm16_voice_window(
                runtime, tone(seconds=0.5), sample_rate=16000, start_ms=600,
                event_id=second_event["event_id"], generation_id=generation,
                source_id=SOURCE, consent_receipt=RECEIPT,
                consent_check=consent_ok, consent_guard=consent_guard,
                finality="PROVISIONAL", consent_lease=lease,
                temporal_state=temporal_state, token_budget=512,
                teacher_ear=session, teacher_asr_opt_in=True,
                transcript_persist_opt_in=True,
            )
            # A streaming recognizer may revise already emitted words. The
            # replacement must reach C3 as an explicit untrusted revision,
            # not disappear because its delta is empty.
            recognizer.text = "hello there"
            third = consume_pcm16_voice_window(
                runtime, tone(seconds=0.5), sample_rate=16000, start_ms=1100,
                event_id=third_event["event_id"], generation_id=generation,
                source_id=SOURCE, consent_receipt=RECEIPT,
                consent_check=consent_ok, consent_guard=consent_guard,
                finality="FINAL", consent_lease=lease,
                temporal_state=temporal_state, token_budget=512,
                teacher_ear=session, teacher_asr_opt_in=True,
                transcript_persist_opt_in=True,
            )

        assert first["teacher_ear"]["processing_mode"] == "CONTIGUOUS_STREAM"
        assert first["teacher_ear"]["segments"][0]["text"] == "hello"
        assert first["teacher_ear"]["stream_ref"]["chunk_count"] == 1
        assert second["teacher_ear"]["segments"][0]["text"] == "world"
        assert second["teacher_ear"]["stream_ref"]["chunk_count"] == 2
        assert second["teacher_ear"]["stream_ref"]["start_ms"] == 100
        assert second["teacher_ear"]["stream_ref"]["end_ms"] == 1100
        assert third["teacher_ear"]["segments"][0]["text"] == ""
        assert third["teacher_ear"]["segments"][0]["revision"] is True
        assert third["teacher_ear"]["cumulative_hypothesis"] == "hello there"
        assert third["teacher_ear"]["stream_ref"]["chunk_count"] == 3
        assert third["teacher_ear"]["stream_ref"]["end_ms"] == 1600
        assert first["teacher_ear"]["source_ref"]["source_sha256"] == first["packet"]["source_ref"]["sha256"]
        assert second["teacher_ear"]["source_ref"]["source_sha256"] == second["packet"]["source_ref"]["sha256"]
        assert third["teacher_ear"]["source_ref"]["source_sha256"] == third["packet"]["source_ref"]["sha256"]
        assert "asr_hypothesis_untrusted=hello" in first["c3_admission"].selected[0].summary
        assert "asr_hypothesis_untrusted=world" in second["c3_admission"].selected[0].summary
        assert "hello world" not in second["c3_admission"].selected[0].summary
        assert "asr_revision_untrusted=hello there" in third["c3_admission"].selected[0].summary
        assert "hello there" not in third["teacher_ear"]["segments"][0]["text"]
        assert session.closed
        assert ear._active_streams == 0
        assert recognizer.create_stream_calls == 1
        assert len(recognizer.stream.waveforms) == 4  # three chunks + one final-only tail
        assert recognizer.stream.input_finished_calls == 1
    finally:
        runtime.close()
