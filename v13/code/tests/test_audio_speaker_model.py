"""Local synthetic contract tests for the optional RAW EAR speaker model adapter.

The fake extractor verifies the sherpa-onnx call contract; it is not native model
inference, speaker accuracy, Android performance, or a calibrated identity test.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import struct

import numpy as np
import pytest

from v13.audio_speaker_evidence import SCHEMA, SpeakerChangeEvidenceRegistry, SpeakerEvidenceError
from v13.audio_speaker_model import (
    SherpaSpeakerEmbeddingEncoder,
    SpeakerModelError,
    SpeakerModelManifest,
)
from v13.audio_voice_cues import audio_consent_lease, consume_pcm16_voice_window
from v13.runtime import Runtime


SOURCE = "fixture:speaker-model"
RECEIPT = "fixture:speaker-model-consent"


def tone(sample_rate=16000, frequency=140, seconds=1.0, amplitude=6000):
    count = int(sample_rate * seconds)
    samples = [
        int(amplitude * np.sin(2 * np.pi * frequency * index / sample_rate))
        for index in range(count)
    ]
    return struct.pack("<" + "h" * len(samples), *samples)


class FakeStream:
    def __init__(self):
        self.sample_rate = None
        self.waveform = None
        self.finished = False

    def accept_waveform(self, *, sample_rate, waveform):
        self.sample_rate = sample_rate
        self.waveform = np.asarray(waveform, dtype=np.float32).copy()

    def input_finished(self):
        self.finished = True

    def release(self):
        self.waveform = None


class FakeExtractor:
    dim = 3

    def __init__(self):
        self.create_stream_calls = 0
        self.compute_calls = 0
        self.last_stream = None

    def create_stream(self):
        self.create_stream_calls += 1
        self.last_stream = FakeStream()
        return self.last_stream

    def is_ready(self, stream):
        return stream.finished is True

    def compute(self, stream):
        assert stream.sample_rate == 16000
        assert stream.waveform is not None
        assert stream.waveform.dtype == np.float32
        self.compute_calls += 1
        return np.asarray([3.0, 4.0, 0.0], dtype=np.float32)


class FakeConfig:
    def __init__(self, *, model, num_threads, debug, provider):
        self.model = model
        self.num_threads = num_threads
        self.debug = debug
        self.provider = provider

    def validate(self):
        return (
            Path(self.model).is_file()
            and self.num_threads == 1
            and self.debug is False
            and self.provider == "cpu"
        )


class FakeSherpa:
    __version__ = "fixture-sherpa-1"

    SpeakerEmbeddingExtractorConfig = FakeConfig

    @staticmethod
    def SpeakerEmbeddingExtractor(config):
        assert config.validate()
        return FakeExtractor()


class FakeLease:
    def __init__(self, active=True):
        self.active = active

    def matches(self, *args, **kwargs):
        return self.active is True


def manifest_for(root, model_bytes=b"fixture-onnx-model", **overrides):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "speaker.onnx").write_bytes(model_bytes)
    values = {
        "model_id": "fixture/speaker-encoder",
        "model_revision": "fixture-rev-1",
        "model_language": "fixture",
        "model_license_id": "SYNTHETIC-NO-WEIGHTS",
        "model_root": str(root),
        "model_file": "speaker.onnx",
        "model_sha256": hashlib.sha256(model_bytes).hexdigest(),
        "sample_rate": 16000,
        "num_threads": 1,
    }
    values.update(overrides)
    return SpeakerModelManifest(**values)


def make_encoder(root, *, extractor=None):
    manifest = manifest_for(root)
    return SherpaSpeakerEmbeddingEncoder(
        manifest,
        extractor or FakeExtractor(),
        np,
        encoder_revision="fixture-sherpa-1",
    )


def consent_check(source_id, receipt):
    return source_id == SOURCE and receipt == RECEIPT


@contextmanager
def consent_guard(source_id, receipt):
    yield consent_check(source_id, receipt)


def window_batch(source_id, generation_id, start_ms, end_ms, pcm_sha, vector=(1.0, 0.0, 0.0)):
    return {
        "schema": SCHEMA,
        "source_id": source_id,
        "generation_id": generation_id,
        "consent_receipt_ref": RECEIPT,
        "current_chunk_sha256": pcm_sha,
        "model_id": "fixture/window-encoder",
        "model_revision": "fixture-rev-1",
        "model_sha256": "a" * 64,
        "model_license_id": "SYNTHETIC-NO-WEIGHTS",
        "model_language": "fixture",
        "encoder_id": "fixture-encoder",
        "encoder_revision": "fixture-v1",
        "embedding_unit": "WINDOW",
        "embedding_dim": 3,
        "frame_step_ms": 1000,
        "lookback_frames": 1,
        "confidence_threshold": None,
        "calibration_id": None,
        "frames": [{"end_ms": end_ms, "vector": list(vector)}],
    }


def test_manifest_rejects_parent_path_and_invalid_hash(tmp_path):
    with pytest.raises(SpeakerModelError, match="contained relative path"):
        SpeakerModelManifest(
            model_id="fixture/model", model_revision="r1", model_language="en",
            model_license_id="Apache-2.0", model_root=str(tmp_path),
            model_file="../speaker.onnx", model_sha256="a" * 64,
        )
    with pytest.raises(SpeakerModelError, match="model_sha256"):
        SpeakerModelManifest(
            model_id="fixture/model", model_revision="r1", model_language="en",
            model_license_id="Apache-2.0", model_root=str(tmp_path),
            model_file="speaker.onnx", model_sha256="not-a-digest",
        )


def test_hash_pinned_loader_uses_stable_open_inode_and_closes(tmp_path):
    manifest = manifest_for(tmp_path)
    encoder = SherpaSpeakerEmbeddingEncoder.load(
        manifest, sherpa_module=FakeSherpa, numpy_module=np,
    )
    try:
        assert encoder.encoder_revision == "fixture-sherpa-1"
        assert encoder._verified_model is not None
        assert str(encoder._verified_model.path).startswith("/proc/self/fd/")
        assert encoder._verified_model.path.is_file()
    finally:
        verified = encoder._verified_model
        encoder.close()
    assert verified.closed is True


def test_hash_mismatch_and_symlink_model_are_rejected(tmp_path):
    manifest = manifest_for(tmp_path)
    bad = SpeakerModelManifest(
        model_id=manifest.model_id, model_revision=manifest.model_revision,
        model_language=manifest.model_language, model_license_id=manifest.model_license_id,
        model_root=manifest.model_root, model_file=manifest.model_file,
        model_sha256="b" * 64,
    )
    with pytest.raises(SpeakerModelError, match="SHA-256 mismatch"):
        bad.open_verified_model()

    (tmp_path / "speaker.onnx").unlink()
    (tmp_path / "real.onnx").write_bytes(b"fixture-onnx-model")
    (tmp_path / "speaker.onnx").symlink_to(tmp_path / "real.onnx")
    with pytest.raises(SpeakerModelError, match="cannot safely open speaker model"):
        manifest.open_verified_model()


def test_encoder_emits_one_normalized_source_bound_window_embedding(tmp_path):
    pcm = tone()
    encoder = make_encoder(tmp_path)
    try:
        batch = encoder.encode_window(
            pcm,
            sample_rate=16000,
            runtime=object(),
            source_id=SOURCE,
            generation_id="generation-a",
            consent_receipt_ref=RECEIPT,
            consent_lease=FakeLease(),
            start_ms=100,
            end_ms=1100,
            expected_pcm_sha256=hashlib.sha256(pcm).hexdigest(),
        )
    finally:
        encoder.close()

    assert batch["schema"] == "v14.raw-ear-speaker-embeddings/4"
    assert batch["embedding_unit"] == "WINDOW"
    assert batch["frame_step_ms"] == 1000
    assert batch["lookback_frames"] == 1
    assert batch["current_chunk_sha256"] == hashlib.sha256(pcm).hexdigest()
    assert batch["model_license_id"] == "Apache-2.0"
    assert batch["encoder_id"] == "sherpa-onnx"
    assert batch["encoder_revision"] == "fixture-sherpa-1"
    assert batch["frames"] == [{"end_ms": 1100, "vector": pytest.approx([0.6, 0.8, 0.0])}]


def test_encoder_rejects_wrong_lease_hash_and_short_window_before_native_call(tmp_path):
    extractor = FakeExtractor()
    encoder = make_encoder(tmp_path, extractor=extractor)
    pcm = tone()
    try:
        with pytest.raises(PermissionError, match="live matching AudioConsentLease"):
            encoder.encode_window(
                pcm, sample_rate=16000, runtime=object(), source_id=SOURCE,
                generation_id="generation-a", consent_receipt_ref=RECEIPT,
                consent_lease=FakeLease(False), start_ms=100, end_ms=1100,
            )
        assert extractor.create_stream_calls == 0

        with pytest.raises(PermissionError, match="PCM hash differs"):
            encoder.encode_window(
                pcm, sample_rate=16000, runtime=object(), source_id=SOURCE,
                generation_id="generation-a", consent_receipt_ref=RECEIPT,
                consent_lease=FakeLease(), start_ms=100, end_ms=1100,
                expected_pcm_sha256="b" * 64,
            )
        assert extractor.create_stream_calls == 0

        with pytest.raises(SpeakerModelError, match="exactly one second"):
            encoder.encode_window(
                tone(seconds=0.5), sample_rate=16000, runtime=object(), source_id=SOURCE,
                generation_id="generation-a", consent_receipt_ref=RECEIPT,
                consent_lease=FakeLease(), start_ms=100, end_ms=600,
            )
        assert extractor.create_stream_calls == 0
    finally:
        encoder.close()


def test_window_schema_compares_only_cross_window_embeddings():
    registry = SpeakerChangeEvidenceRegistry()
    first_pcm = b"first-window"
    second_pcm = b"second-window"
    first = window_batch(
        SOURCE, "generation-window", 100, 1100, hashlib.sha256(first_pcm).hexdigest(),
    )
    warmup = registry.update(
        source_id=SOURCE, generation_id="generation-window",
        start_ms=100, end_ms=1100, activity_hint="VOICED",
        current_chunk_sha256=first["current_chunk_sha256"],
        consent_receipt_ref=RECEIPT, embeddings=first,
    )
    assert warmup["status"] == "WARMUP"
    assert warmup["embedding_unit"] == "WINDOW"

    second = window_batch(
        SOURCE, "generation-window", 1100, 2100, hashlib.sha256(second_pcm).hexdigest(),
    )
    measured = registry.update(
        source_id=SOURCE, generation_id="generation-window",
        start_ms=1100, end_ms=2100, activity_hint="VOICED",
        current_chunk_sha256=second["current_chunk_sha256"],
        consent_receipt_ref=RECEIPT, embeddings=second,
    )
    assert measured["status"] == "MEASURED"
    assert measured["lookback_ms"] == 1000
    assert measured["reference_frame_end_ms"] == 1100
    assert measured["cosine_similarity"] == 1.0
    assert measured["threshold_status"] == "NOT_CONFIGURED"
    assert measured["speaker_change_candidate"] is None
    assert measured["identity_authority"] is False
    assert measured["learning_authority"] is False
    assert measured["action_authority"] is False

    invalid = dict(second)
    invalid["frames"] = second["frames"] * 2
    with pytest.raises(SpeakerEvidenceError, match="exactly one vector"):
        registry.update(
            source_id=SOURCE, generation_id="generation-window",
            start_ms=1100, end_ms=2100, activity_hint="VOICED",
            current_chunk_sha256=invalid["current_chunk_sha256"],
            consent_receipt_ref=RECEIPT, embeddings=invalid,
        )


def test_opt_in_speaker_encoder_reaches_a5_a4_c3_consumer_without_persisting_vectors(tmp_path):
    runtime = Runtime(Path(tmp_path))
    runtime.sleep.cycle.set_policy("enabled", "off")
    encoder = make_encoder(tmp_path / "models")
    try:
        first_event = runtime.store.event(runtime.session, "synthetic audio window one")
        second_event = runtime.store.event(runtime.session, "synthetic audio window two")
        generation = first_event["brain_generation_id"]
        assert second_event["brain_generation_id"] == generation
        with audio_consent_lease(
            runtime, SOURCE, generation, RECEIPT, consent_check, consent_guard,
        ) as lease:
            first = consume_pcm16_voice_window(
                runtime, tone(), sample_rate=16000, start_ms=100,
                event_id=first_event["event_id"], generation_id=generation,
                source_id=SOURCE, consent_receipt=RECEIPT,
                consent_check=consent_check, consent_guard=consent_guard,
                finality="FINAL", consent_lease=lease,
                speaker_encoder=encoder, speaker_model_opt_in=True,
            )
            second = consume_pcm16_voice_window(
                runtime, tone(), sample_rate=16000, start_ms=1100,
                event_id=second_event["event_id"], generation_id=generation,
                source_id=SOURCE, consent_receipt=RECEIPT,
                consent_check=consent_check, consent_guard=consent_guard,
                finality="FINAL", consent_lease=lease,
                speaker_encoder=encoder, speaker_model_opt_in=True,
            )

        assert first["speaker_change_evidence"]["status"] == "WARMUP"
        evidence = second["speaker_change_evidence"]
        assert evidence["status"] == "MEASURED"
        assert evidence["embedding_unit"] == "WINDOW"
        assert evidence["frame_step_ms"] == 1000
        assert evidence["model_sha256"] == encoder.manifest.model_sha256
        assert evidence["model_license_id"] == "Apache-2.0"
        assert evidence["encoder_id"] == "sherpa-onnx"
        assert evidence["source_binding_status"] == "CURRENT_PCM_SHA256_MATCH_ENCODER_UNATTESTED"
        assert second["a4"]["speaker_change_decision"] == "DEFER"
        assert second["a4"]["identity_authority"] is False
        assert second["a4"]["learning_authority"] is False
        assert second["a4"]["action_authority"] is False
        stored = runtime.store.one(
            "SELECT payload FROM packets WHERE id=? AND kind='PerceptPacket'",
            (second["packet"]["packet_id"],),
        )
        assert stored is not None
        stored_packet = json.loads(stored["payload"])
        serialized = json.dumps(stored_packet, sort_keys=True)
        assert '"vector"' not in serialized
        assert "speaker_model" not in serialized
        assert evidence["model_id"] in serialized
    finally:
        encoder.close()
        runtime.close()


def test_speaker_encoder_requires_explicit_opt_in_and_caller_held_lease(tmp_path):
    runtime = Runtime(Path(tmp_path))
    runtime.sleep.cycle.set_policy("enabled", "off")
    encoder = make_encoder(tmp_path / "models")
    try:
        event = runtime.store.event(runtime.session, "speaker model opt-in negative test")
        generation = event["brain_generation_id"]
        with pytest.raises(PermissionError, match="explicit opt-in"):
            consume_pcm16_voice_window(
                runtime, tone(), sample_rate=16000, start_ms=100,
                event_id=event["event_id"], generation_id=generation,
                source_id=SOURCE, consent_receipt=RECEIPT,
                consent_check=consent_check, consent_guard=consent_guard,
                finality="FINAL", speaker_encoder=encoder,
            )
        with pytest.raises(PermissionError, match="explicit caller-held AudioConsentLease"):
            consume_pcm16_voice_window(
                runtime, tone(), sample_rate=16000, start_ms=100,
                event_id=event["event_id"], generation_id=generation,
                source_id=SOURCE, consent_receipt=RECEIPT,
                consent_check=consent_check, consent_guard=consent_guard,
                finality="FINAL", speaker_encoder=encoder, speaker_model_opt_in=True,
            )
        count = runtime.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind='PerceptPacket'"
        )["n"]
        assert count == 0
    finally:
        encoder.close()
        runtime.close()
