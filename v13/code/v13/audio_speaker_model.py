"""Optional, local sherpa-onnx speaker-window encoder for RAW EAR.

This module never downloads weights, opens a microphone, or stores PCM/embeddings.
The caller must supply a hash-pinned local model and a live AudioConsentLease.
It emits one whole-window embedding per one-second PCM16 chunk; this is not a
streaming frame encoder, speaker identity system, or calibrated diarizer.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_HAS_OPEN_DIR_FD = os.open in getattr(os, "supports_dir_fd", set())
_MAX_WINDOW_MS = 1000


class SpeakerModelError(ValueError):
    """Invalid model manifest, unavailable runtime, or unusable embedding."""


@dataclass(frozen=True)
class SpeakerModelManifest:
    model_id: str
    model_revision: str
    model_language: str
    model_license_id: str
    model_root: str
    model_file: str
    model_sha256: str
    sample_rate: int = 16000
    num_threads: int = 1
    max_model_bytes: int = 64 * 1024 * 1024

    def __post_init__(self) -> None:
        for name, limit in (
            ("model_id", 128),
            ("model_revision", 128),
            ("model_language", 64),
            ("model_license_id", 64),
            ("model_root", 1024),
            ("model_file", 512),
        ):
            value = getattr(self, name)
            if type(value) is not str or not value.strip() or len(value) > limit:
                raise SpeakerModelError(f"{name} is invalid")
        if "\\" in self.model_file:
            raise SpeakerModelError("model_file must use POSIX relative path separators")
        relative = PurePosixPath(self.model_file)
        if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
            raise SpeakerModelError("model_file must be a contained relative path")
        if type(self.model_sha256) is not str or not _SHA256.fullmatch(self.model_sha256.lower()):
            raise SpeakerModelError("model_sha256 is invalid")
        object.__setattr__(self, "model_sha256", self.model_sha256.lower())
        if type(self.sample_rate) is not int or not 8000 <= self.sample_rate <= 48000:
            raise SpeakerModelError("sample_rate must be in 8000..48000")
        if type(self.num_threads) is not int or not 1 <= self.num_threads <= 2:
            raise SpeakerModelError("num_threads must be 1 or 2")
        if (type(self.max_model_bytes) is not int
                or not 1 <= self.max_model_bytes <= 128 * 1024 * 1024):
            raise SpeakerModelError("max_model_bytes is invalid")

    def open_verified_model(self) -> "VerifiedSpeakerModelFile":
        raw_root = Path(self.model_root).expanduser()
        if raw_root.is_symlink():
            raise SpeakerModelError("model root must not be a symlink")
        try:
            root = raw_root.resolve(strict=True)
        except OSError as exc:
            raise SpeakerModelError("model root is unavailable") from exc
        if not root.is_dir():
            raise SpeakerModelError("model root must be a directory")
        if (not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW")
                or not _HAS_OPEN_DIR_FD):
            raise SpeakerModelError(
                "secure model loading requires O_DIRECTORY, O_NOFOLLOW and dir_fd support"
            )
        if not Path("/proc/self/fd").is_dir():
            raise SpeakerModelError("stable model loading requires /proc/self/fd")

        directory_flags = (
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            | getattr(os, "O_CLOEXEC", 0)
        )
        file_flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        root_anchor = None
        root_handle = None
        model_fd = None
        try:
            root_anchor = os.open("/", directory_flags)
            root_handle = root_anchor
            for part in root.parts[1:]:
                next_handle = os.open(part, directory_flags, dir_fd=root_handle)
                if root_handle != root_anchor:
                    os.close(root_handle)
                root_handle = next_handle

            parts = PurePosixPath(self.model_file).parts
            parent_fd = os.dup(root_handle)
            try:
                for part in parts[:-1]:
                    next_fd = os.open(part, directory_flags, dir_fd=parent_fd)
                    os.close(parent_fd)
                    parent_fd = next_fd
                model_fd = os.open(parts[-1], file_flags, dir_fd=parent_fd)
            finally:
                os.close(parent_fd)

            opened = os.fstat(model_fd)
            if not stat.S_ISREG(opened.st_mode):
                raise SpeakerModelError("speaker model must be a regular file")
            if opened.st_size <= 0 or opened.st_size > self.max_model_bytes:
                raise SpeakerModelError("speaker model exceeds configured size bounds")
            digest = hashlib.sha256()
            with os.fdopen(os.dup(model_fd), "rb") as handle:
                while True:
                    chunk = handle.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
            if digest.hexdigest() != self.model_sha256:
                raise SpeakerModelError("speaker model SHA-256 mismatch")

            fd_path = Path(f"/proc/self/fd/{model_fd}")
            pinned = os.stat(fd_path)
            if (pinned.st_dev, pinned.st_ino) != (opened.st_dev, opened.st_ino):
                raise SpeakerModelError("descriptor path does not identify the verified model")
            verified = VerifiedSpeakerModelFile(fd_path, model_fd)
            model_fd = None
            return verified
        except SpeakerModelError:
            raise
        except OSError as exc:
            raise SpeakerModelError("cannot safely open speaker model") from exc
        finally:
            if model_fd is not None:
                os.close(model_fd)
            if root_handle is not None and root_handle != root_anchor:
                os.close(root_handle)
            if root_anchor is not None:
                os.close(root_anchor)


class VerifiedSpeakerModelFile:
    """Keep a hash-checked model inode open for the native sherpa loader."""

    def __init__(self, path: Path, descriptor: int):
        self.path = Path(path)
        self._descriptor = descriptor
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            os.close(self._descriptor)
        except OSError:
            pass
        self._descriptor = -1

    def __enter__(self):
        if self._closed:
            raise SpeakerModelError("verified speaker model handle is closed")
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


class SherpaSpeakerEmbeddingEncoder:
    """Lazy CPU-only wrapper around sherpa_onnx.SpeakerEmbeddingExtractor."""

    def __init__(
        self,
        manifest: SpeakerModelManifest,
        extractor,
        numpy_module,
        *,
        encoder_revision: str = "unknown",
        verified_model: VerifiedSpeakerModelFile | None = None,
    ):
        if not isinstance(manifest, SpeakerModelManifest):
            raise TypeError("manifest must be a SpeakerModelManifest")
        if not callable(getattr(extractor, "create_stream", None)):
            raise SpeakerModelError("speaker extractor has no create_stream()")
        dimension = getattr(extractor, "dim", None)
        if type(dimension) is not int or not 2 <= dimension <= 512:
            raise SpeakerModelError("speaker extractor dimension is invalid")
        if (not all(callable(getattr(numpy_module, name, None))
                    for name in ("frombuffer", "asarray", "ascontiguousarray", "isfinite"))
                or not callable(getattr(getattr(numpy_module, "linalg", None), "norm", None))):
            raise SpeakerModelError("NumPy-compatible array module is required")
        if type(encoder_revision) is not str or not encoder_revision.strip() or len(encoder_revision) > 128:
            raise SpeakerModelError("encoder_revision is invalid")
        self.manifest = manifest
        self.embedding_dim = dimension
        self.encoder_revision = encoder_revision
        self._extractor = extractor
        self._numpy = numpy_module
        self._verified_model = verified_model
        self._closed = False

    @classmethod
    def load(
        cls,
        manifest: SpeakerModelManifest,
        *,
        sherpa_module=None,
        numpy_module=None,
    ) -> "SherpaSpeakerEmbeddingEncoder":
        verified = manifest.open_verified_model()
        try:
            if sherpa_module is None:
                try:
                    import sherpa_onnx as sherpa_module
                except ImportError as exc:
                    raise SpeakerModelError("optional sherpa-onnx runtime is not installed") from exc
            if numpy_module is None:
                try:
                    import numpy as numpy_module
                except ImportError as exc:
                    raise SpeakerModelError("optional NumPy runtime is not installed") from exc
            config = sherpa_module.SpeakerEmbeddingExtractorConfig(
                model=str(verified.path),
                num_threads=manifest.num_threads,
                debug=False,
                provider="cpu",
            )
            if not config.validate():
                raise SpeakerModelError("sherpa-onnx rejected the speaker model configuration")
            extractor = sherpa_module.SpeakerEmbeddingExtractor(config)
            revision = getattr(sherpa_module, "__version__", None)
            if not revision:
                revision = getattr(sherpa_module, "version", "unknown")
            if callable(revision):
                revision = revision()
            return cls(
                manifest,
                extractor,
                numpy_module,
                encoder_revision=revision,
                verified_model=verified,
            )
        except SpeakerModelError:
            verified.close()
            raise
        except Exception as exc:
            verified.close()
            raise SpeakerModelError("sherpa-onnx speaker extractor could not be loaded") from exc

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        # Destroy the native object before releasing its pinned model descriptor.
        self._extractor = None
        if self._verified_model is not None:
            self._verified_model.close()
            self._verified_model = None

    def __enter__(self):
        if self._closed:
            raise SpeakerModelError("speaker encoder is closed")
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def encode_window(
        self,
        pcm: bytes,
        *,
        sample_rate: int,
        runtime,
        source_id: str,
        generation_id: str,
        consent_receipt_ref: str,
        consent_lease,
        start_ms: int,
        end_ms: int,
        expected_pcm_sha256: str | None = None,
        temporal_state=None,
        vad_stream=None,
    ) -> dict:
        """Encode exactly one consented 1-second mono PCM16 window into one vector."""
        if self._closed or self._extractor is None:
            raise SpeakerModelError("speaker encoder is closed")
        matches = getattr(consent_lease, "matches", None)
        if not callable(matches) or matches(
            runtime,
            source_id,
            generation_id,
            consent_receipt_ref,
            temporal_state=temporal_state,
            vad_stream=vad_stream,
            require_state=True,
        ) is not True:
            raise PermissionError("a live matching AudioConsentLease is required for speaker inference")
        if type(pcm) is not bytes or not pcm or len(pcm) % 2:
            raise SpeakerModelError("speaker input must be complete mono PCM16 bytes")
        if sample_rate != self.manifest.sample_rate:
            raise SpeakerModelError("speaker PCM sample rate does not match the pinned model manifest")
        if (type(start_ms) is not int or type(end_ms) is not int
                or start_ms < 0 or end_ms <= start_ms):
            raise SpeakerModelError("speaker window timestamps are invalid")
        if len(pcm) != sample_rate * 2 or end_ms - start_ms != _MAX_WINDOW_MS:
            raise SpeakerModelError("speaker encoder requires exactly one second of PCM16")

        pcm_sha256 = hashlib.sha256(pcm).hexdigest()
        if expected_pcm_sha256 is not None and expected_pcm_sha256 != pcm_sha256:
            raise PermissionError("speaker encoder PCM hash differs from the admitted audio source")
        if (type(source_id) is not str or not source_id.strip()
                or type(generation_id) is not str or not generation_id.strip()
                or type(consent_receipt_ref) is not str or not consent_receipt_ref.strip()):
            raise PermissionError("speaker inference source/consent binding is invalid")

        np = self._numpy
        stream = None
        try:
            samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32)
            samples = np.ascontiguousarray(samples / np.float32(32768.0))
            stream = self._extractor.create_stream()
            stream.accept_waveform(sample_rate=sample_rate, waveform=samples)
            stream.input_finished()
            if self._extractor.is_ready(stream) is not True:
                raise SpeakerModelError("sherpa-onnx speaker stream is not ready")
            embedding = np.asarray(self._extractor.compute(stream), dtype=np.float32).reshape(-1)
            if embedding.size != self.embedding_dim:
                raise SpeakerModelError("sherpa-onnx returned an unexpected embedding dimension")
            if not bool(np.isfinite(embedding).all()):
                raise SpeakerModelError("sherpa-onnx returned non-finite embedding values")
            norm = float(np.linalg.norm(embedding))
            if not math.isfinite(norm) or norm <= 1e-12:
                raise SpeakerModelError("sherpa-onnx returned a zero or invalid embedding")
            vector = (embedding / norm).astype(np.float32).tolist()
        except SpeakerModelError:
            raise
        except Exception as exc:
            raise SpeakerModelError("sherpa-onnx speaker inference failed") from exc
        finally:
            release = getattr(stream, "release", None)
            if callable(release):
                release()

        return {
            "schema": "v14.raw-ear-speaker-embeddings/4",
            "source_id": source_id,
            "generation_id": generation_id,
            "consent_receipt_ref": consent_receipt_ref,
            "current_chunk_sha256": pcm_sha256,
            "model_id": self.manifest.model_id,
            "model_revision": self.manifest.model_revision,
            "model_sha256": self.manifest.model_sha256,
            "model_license_id": self.manifest.model_license_id,
            "model_language": self.manifest.model_language,
            "encoder_id": "sherpa-onnx",
            "encoder_revision": self.encoder_revision,
            "embedding_unit": "WINDOW",
            "embedding_dim": self.embedding_dim,
            "frame_step_ms": 1000,
            "lookback_frames": 1,
            "confidence_threshold": None,
            "calibration_id": None,
            "frames": [{"end_ms": end_ms, "vector": vector}],
        }
