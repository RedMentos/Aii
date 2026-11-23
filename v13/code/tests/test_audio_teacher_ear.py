import hashlib
import struct
import threading
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
    def accept_waveform(self, sample_rate, waveform):
        self.waveforms.append((sample_rate, waveform.copy()))


class Recognizer:
    def __init__(self, text="hello world"):
        self.text = text
        self.stream = Stream()
        self.decoded = 0
    def create_stream(self):
        return self.stream
    def is_ready(self, stream):
        return self.decoded == 0
    def decode_stream(self, stream):
        self.decoded += 1
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
    with pytest.raises(TeacherEarError, match="symlinks"):
        manifest.verified_files()
    other = tmp_path / "other"
    other.mkdir()
    too_small = make_manifest(other, max_total_bytes=2)
    with pytest.raises(TeacherEarError, match="size ceiling"):
        too_small.verified_files()


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
