import hashlib
import os
import struct
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from v13.audio_teacher_ear import TeacherEarManifest, TeacherEarError, SherpaOnlineTeacher


class Lease:
    def __init__(self, allowed=True):
        self.allowed = allowed
        self.thread_id = threading.get_ident()
    def matches(self, runtime, source_id, generation_id, receipt, *, temporal_state=None, vad_stream=None, require_state=False):
        return self.allowed and threading.get_ident() == self.thread_id and source_id == "src" and generation_id == "gen" and receipt == "receipt" and require_state is True


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


class Stream:
    def __init__(self):
        self.waveforms = []
        self.pending = False
        self.finished = False
        self.input_finished_calls = 0
    def accept_waveform(self, sample_rate, waveform):
        self.waveforms.append((sample_rate, waveform.copy()))
        self.pending = True
    def input_finished(self):
        self.finished = True
        self.input_finished_calls += 1
        self.pending = True


class Recognizer:
    def __init__(self, text="hello world"):
        self.text = text
        self.stream = Stream()
        self.decoded = 0
        self.create_stream_calls = 0
    def create_stream(self):
        self.create_stream_calls += 1
        return self.stream
    def is_ready(self, stream):
        return stream.pending
    def decode_stream(self, stream):
        self.decoded += 1
        stream.pending = False
    def get_result(self, stream):
        return self.text


def make_manifest(tmp_path, *, max_total_bytes=1024):
    names = {"encoder": "encoder.onnx", "decoder": "decoder.onnx", "joiner": "joiner.onnx", "tokens": "tokens.txt"}
    hashes = {}
    for key, name in names.items():
        path = tmp_path / name
        path.write_bytes((key + "-fixture").encode())
        hashes[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    return TeacherEarManifest(
        model_id="fixture/sherpa-small", model_revision="rev-1", language="en",
        license_id="Apache-2.0", model_root=str(tmp_path),
        encoder=names["encoder"], decoder=names["decoder"], joiner=names["joiner"], tokens=names["tokens"],
        file_sha256=hashes, max_total_bytes=max_total_bytes,
    )


def pcm16_for(ms=1000, sample_rate=16000):
    return b"\x01\x00" * int(ms * sample_rate / 1000)


def test_manifest_hashes_and_no_symlink_paths(tmp_path):
    manifest = make_manifest(tmp_path)
    files = manifest.verified_files()
    assert set(files) == {"encoder", "decoder", "joiner", "tokens"}
    (tmp_path / "encoder.onnx").write_bytes(b"tampered")
    with pytest.raises(TeacherEarError, match="SHA-256 mismatch"):
        manifest.verified_files()


def test_manifest_rejects_path_traversal_and_bad_hash(tmp_path):
    manifest = make_manifest(tmp_path)
    with pytest.raises(TeacherEarError, match="relative and contained"):
        TeacherEarManifest(
            model_id="m", model_revision="r", language="en", license_id="Apache-2.0",
            model_root=str(tmp_path), encoder="../encoder", decoder="decoder.onnx",
            joiner="joiner.onnx", tokens="tokens.txt", file_sha256=manifest.file_sha256,
        )
    hashes = dict(manifest.file_sha256)
    hashes["encoder"] = "0" * 64
    bad = TeacherEarManifest(
        model_id="m", model_revision="r", language="en", license_id="Apache-2.0",
        model_root=str(tmp_path), encoder="encoder.onnx", decoder="decoder.onnx",
        joiner="joiner.onnx", tokens="tokens.txt", file_sha256=hashes,
    )
    with pytest.raises(TeacherEarError, match="SHA-256 mismatch"):
        bad.verified_files()


def test_manifest_rejects_symlink_and_size_overflow(tmp_path):
    manifest = make_manifest(tmp_path)
    target = tmp_path / "target.bin"
    target.write_bytes(b"x")
    (tmp_path / "encoder.onnx").unlink()
    (tmp_path / "encoder.onnx").symlink_to(target)
    with pytest.raises(TeacherEarError, match="symlink"):
        manifest.verified_files()
    other = tmp_path / "other"
    other.mkdir()
    too_small = make_manifest(other, max_total_bytes=2)
    with pytest.raises(TeacherEarError, match="size ceiling"):
        too_small.verified_files()


def test_verified_model_descriptor_survives_path_replacement(tmp_path):
    manifest = make_manifest(tmp_path)
    files = manifest.verified_files()
    try:
        original = tmp_path / "encoder.onnx"
        saved = tmp_path / "encoder.original"
        original.rename(saved)
        original.write_bytes(b"attacker-replacement")
        assert original.read_bytes() == b"attacker-replacement"
        assert files["encoder"].read_bytes() == b"encoder-fixture"
    finally:
        files.close()


def test_manifest_parent_directory_fd_survives_symlink_swap(tmp_path, monkeypatch):
    root = tmp_path / "models"
    root.mkdir()
    nested = root / "nested"
    nested.mkdir()
    names = {
        "encoder": "nested/encoder.onnx",
        "decoder": "decoder.onnx",
        "joiner": "joiner.onnx",
        "tokens": "tokens.txt",
    }
    hashes = {}
    for key, relative in names.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = (key + "-fixture").encode()
        path.write_bytes(payload)
        hashes[key] = hashlib.sha256(payload).hexdigest()
    manifest = TeacherEarManifest(
        model_id="fixture/sherpa-small",
        model_revision="rev-1",
        language="en",
        license_id="Apache-2.0",
        model_root=str(root),
        encoder=names["encoder"],
        decoder=names["decoder"],
        joiner=names["joiner"],
        tokens=names["tokens"],
        file_sha256=hashes,
    )
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "encoder.onnx").write_bytes(b"attacker-outside")
    real_open = os.open
    swapped = False

    def race_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal swapped
        descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
        if path == "nested" and dir_fd is not None and not swapped:
            nested.rename(root / "nested.original")
            nested.symlink_to(outside, target_is_directory=True)
            swapped = True
        return descriptor

    monkeypatch.setattr(os, "open", race_open)
    files = manifest.verified_files()
    try:
        assert swapped is True
        assert (nested / "encoder.onnx").read_bytes() == b"attacker-outside"
        assert files["encoder"].read_bytes() == b"encoder-fixture"
    finally:
        files.close()


def test_native_loader_receives_pinned_descriptor_paths(tmp_path, monkeypatch):
    manifest = make_manifest(tmp_path)
    captured = {}
    original = tmp_path / "encoder.onnx"

    class Loader:
        @staticmethod
        def from_transducer(**kwargs):
            original.rename(tmp_path / "encoder.original")
            original.write_bytes(b"attacker-replacement")
            for name in ("encoder", "decoder", "joiner", "tokens"):
                captured[name] = Path(kwargs[name]).read_bytes()
            return Recognizer()

    monkeypatch.setitem(sys.modules, "numpy", SimpleNamespace())
    monkeypatch.setitem(
        sys.modules, "sherpa_onnx", SimpleNamespace(OnlineRecognizer=Loader),
    )
    teacher = SherpaOnlineTeacher(manifest)
    try:
        teacher._load()
        assert captured == {
            "encoder": b"encoder-fixture",
            "decoder": b"decoder-fixture",
            "joiner": b"joiner-fixture",
            "tokens": b"tokens-fixture",
        }
        pinned_path = teacher._verified["encoder"]
    finally:
        teacher.close()
    with pytest.raises(FileNotFoundError):
        pinned_path.read_bytes()


def test_teacher_requires_opt_in_and_current_lease(tmp_path):
    manifest = make_manifest(tmp_path)
    teacher = SherpaOnlineTeacher(manifest, recognizer=Recognizer(), numpy_module=FakeNumpy())
    kwargs = dict(
        sample_rate=16000, start_ms=0, end_ms=1000, runtime=object(),
        source_id="src", generation_id="gen", consent_receipt_ref="receipt",
        consent_lease=Lease(),
    )
    with pytest.raises(PermissionError, match="opt-in"):
        teacher.transcribe_pcm16(pcm16_for(), **kwargs)
    with pytest.raises(PermissionError, match="AudioConsentLease"):
        teacher.transcribe_pcm16(pcm16_for(), **{**kwargs, "consent_lease": Lease(False)}, teacher_asr_opt_in=True)


def test_teacher_returns_source_bound_window_hypothesis_without_authority(tmp_path):
    manifest = make_manifest(tmp_path)
    recognizer = Recognizer(" hello\x00   world ")
    teacher = SherpaOnlineTeacher(manifest, recognizer=recognizer, numpy_module=FakeNumpy())
    pcm = pcm16_for()
    result = teacher.transcribe_pcm16(
        pcm, sample_rate=16000, start_ms=100, end_ms=1100,
        runtime=object(), source_id="src", generation_id="gen", consent_receipt_ref="receipt",
        consent_lease=Lease(), teacher_asr_opt_in=True,
    )
    assert result["status"] == "MEASURED"
    assert result["segments"] == [{
        "start_ms": 100, "end_ms": 1100, "timestamp_granularity": "WINDOW",
        "finality": "PROVISIONAL", "text": "hello world", "hypothesis_not_truth": True,
    }]
    assert result["source_ref"]["consent_receipt_ref"] == "receipt"
    assert result["source_ref"]["source_sha256"] == hashlib.sha256(pcm).hexdigest()
    assert result["model_file_sha256"] == dict(manifest.file_sha256)
    assert result["truth_authority"] == 0
    assert result["learning_authority"] is False
    assert result["action_authority"] is False
    assert len(recognizer.stream.waveforms) == 2
    assert recognizer.stream.waveforms[0][0] == 16000


def test_teacher_rejects_duration_mismatch_bad_pcm_and_invalid_finality(tmp_path):
    teacher = SherpaOnlineTeacher(make_manifest(tmp_path), recognizer=Recognizer(), numpy_module=FakeNumpy())
    common = dict(
        sample_rate=16000, start_ms=0, end_ms=1000, runtime=object(), source_id="src",
        generation_id="gen", consent_receipt_ref="receipt", consent_lease=Lease(),
        teacher_asr_opt_in=True,
    )
    with pytest.raises(TeacherEarError, match="duration"):
        teacher.transcribe_pcm16(pcm16_for(500), **common)
    with pytest.raises(TeacherEarError, match="PCM16"):
        teacher.transcribe_pcm16(b"\x01", **common)
    with pytest.raises(TeacherEarError, match="finality"):
        teacher.transcribe_pcm16(pcm16_for(), **{**common, "finality": "UNKNOWN"})


def test_teacher_rejects_cross_thread_lease(tmp_path):
    teacher = SherpaOnlineTeacher(make_manifest(tmp_path), recognizer=Recognizer(), numpy_module=FakeNumpy())
    lease = Lease()
    errors = []
    def run():
        try:
            teacher.transcribe_pcm16(
                pcm16_for(), sample_rate=16000, start_ms=0, end_ms=1000,
                runtime=object(), source_id="src", generation_id="gen", consent_receipt_ref="receipt",
                consent_lease=lease, teacher_asr_opt_in=True,
            )
        except Exception as exc:
            errors.append(exc)
    worker = threading.Thread(target=run)
    worker.start(); worker.join()
    assert len(errors) == 1 and isinstance(errors[0], PermissionError)


def test_empty_hypothesis_is_not_promoted_to_transcript(tmp_path):
    teacher = SherpaOnlineTeacher(make_manifest(tmp_path), recognizer=Recognizer(""), numpy_module=FakeNumpy())
    result = teacher.transcribe_pcm16(
        pcm16_for(), sample_rate=16000, start_ms=0, end_ms=1000,
        runtime=object(), source_id="src", generation_id="gen", consent_receipt_ref="receipt",
        consent_lease=Lease(), teacher_asr_opt_in=True,
    )
    assert result["status"] == "EMPTY"
    assert result["segments"] == []



def test_contiguous_teacher_stream_reuses_one_stream_and_finishes_once(tmp_path):
    teacher = SherpaOnlineTeacher(make_manifest(tmp_path), recognizer=Recognizer("hello"), numpy_module=FakeNumpy())
    runtime = object()
    lease = Lease()
    session = teacher.open_stream(
        runtime=runtime, source_id="src", generation_id="gen",
        consent_receipt_ref="receipt", consent_lease=lease,
        teacher_asr_opt_in=True,
    )
    first = session.transcribe_pcm16(
        pcm16_for(500), sample_rate=16000, start_ms=100, end_ms=600,
        runtime=runtime, source_id="src", generation_id="gen",
        consent_receipt_ref="receipt", consent_lease=lease,
        finality="PROVISIONAL", teacher_asr_opt_in=True,
    )
    assert first["processing_mode"] == "CONTIGUOUS_STREAM"
    assert first["segments"][0]["text"] == "hello"
    assert first["stream_ref"]["chunk_count"] == 1
    assert len(teacher._recognizer.stream.waveforms) == 1
    assert teacher._recognizer.stream.input_finished_calls == 0

    teacher._recognizer.text = "hello world"
    second = session.transcribe_pcm16(
        pcm16_for(500), sample_rate=16000, start_ms=600, end_ms=1100,
        runtime=runtime, source_id="src", generation_id="gen",
        consent_receipt_ref="receipt", consent_lease=lease,
        finality="PROVISIONAL", teacher_asr_opt_in=True,
    )
    assert second["segments"][0]["text"] == "world"
    assert second["stream_ref"]["chunk_count"] == 2
    assert second["stream_ref"]["rolling_sha256"] != first["stream_ref"]["rolling_sha256"]
    assert len(teacher._recognizer.stream.waveforms) == 2

    teacher._recognizer.text = "hello world."
    third = session.transcribe_pcm16(
        pcm16_for(500), sample_rate=16000, start_ms=1100, end_ms=1600,
        runtime=runtime, source_id="src", generation_id="gen",
        consent_receipt_ref="receipt", consent_lease=lease,
        finality="FINAL", teacher_asr_opt_in=True,
    )
    assert third["segments"][0]["text"] == "."
    assert third["stream_ref"]["chunk_count"] == 3
    assert third["stream_ref"]["start_ms"] == 100
    assert third["stream_ref"]["end_ms"] == 1600
    assert len(teacher._recognizer.stream.waveforms) == 4  # three chunks + one final-only tail
    assert teacher._recognizer.stream.input_finished_calls == 1
    assert session.closed
    assert teacher._active_streams == 0
    with pytest.raises(TeacherEarError, match="closed"):
        session.transcribe_pcm16(
            pcm16_for(500), sample_rate=16000, start_ms=1600, end_ms=2100,
            runtime=runtime, source_id="src", generation_id="gen",
            consent_receipt_ref="receipt", consent_lease=lease,
            finality="PROVISIONAL", teacher_asr_opt_in=True,
        )


def test_teacher_stream_rejects_gap_and_releases_native_stream(tmp_path):
    teacher = SherpaOnlineTeacher(make_manifest(tmp_path), recognizer=Recognizer(), numpy_module=FakeNumpy())
    runtime = object()
    lease = Lease()
    session = teacher.open_stream(
        runtime=runtime, source_id="src", generation_id="gen",
        consent_receipt_ref="receipt", consent_lease=lease,
        teacher_asr_opt_in=True,
    )
    session.transcribe_pcm16(
        pcm16_for(500), sample_rate=16000, start_ms=0, end_ms=500,
        runtime=runtime, source_id="src", generation_id="gen",
        consent_receipt_ref="receipt", consent_lease=lease,
        finality="PROVISIONAL", teacher_asr_opt_in=True,
    )
    with pytest.raises(TeacherEarError, match="contiguous"):
        session.transcribe_pcm16(
            pcm16_for(500), sample_rate=16000, start_ms=600, end_ms=1100,
            runtime=runtime, source_id="src", generation_id="gen",
            consent_receipt_ref="receipt", consent_lease=lease,
            finality="PROVISIONAL", teacher_asr_opt_in=True,
        )
    assert session.closed
    assert teacher._active_streams == 0


def test_teacher_stream_rejects_second_session_and_cross_thread_use(tmp_path):
    teacher = SherpaOnlineTeacher(make_manifest(tmp_path), recognizer=Recognizer(), numpy_module=FakeNumpy())
    runtime = object()
    lease = Lease()
    session = teacher.open_stream(
        runtime=runtime, source_id="src", generation_id="gen",
        consent_receipt_ref="receipt", consent_lease=lease,
        teacher_asr_opt_in=True,
    )
    with pytest.raises(TeacherEarError, match="one active"):
        teacher.open_stream(
            runtime=runtime, source_id="src", generation_id="gen",
            consent_receipt_ref="receipt", consent_lease=lease,
            teacher_asr_opt_in=True,
        )
    errors = []
    def wrong_thread():
        try:
            session.transcribe_pcm16(
                pcm16_for(500), sample_rate=16000, start_ms=0, end_ms=500,
                runtime=runtime, source_id="src", generation_id="gen",
                consent_receipt_ref="receipt", consent_lease=lease,
                finality="PROVISIONAL", teacher_asr_opt_in=True,
            )
        except Exception as exc:
            errors.append(exc)
    thread = threading.Thread(target=wrong_thread)
    thread.start()
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert errors and isinstance(errors[0], PermissionError)
    assert session.closed
    assert teacher._active_streams == 0

def test_teacher_close_waits_for_streams_then_releases_pinned_files(tmp_path):
    teacher = SherpaOnlineTeacher(
        make_manifest(tmp_path), recognizer=Recognizer(), numpy_module=FakeNumpy(),
    )
    pinned = teacher.manifest.verified_files()
    teacher._verified = pinned
    pinned_path = pinned["encoder"]
    teacher._active_streams = 1

    with pytest.raises(TeacherEarError, match="stream is active"):
        teacher.close()
    assert pinned_path.read_bytes() == b"encoder-fixture"

    teacher._active_streams = 0
    teacher.close()
    teacher.close()
    with pytest.raises(FileNotFoundError):
        pinned_path.read_bytes()
