"""Optional, source-bound sherpa-onnx Teacher Ear for RAW EAR.

The acoustic/prosodic path remains primary. This adapter is opt-in, uses only
caller-supplied PCM16, never opens a microphone or downloads a model, and emits
an untrusted window-timed ASR hypothesis. Transcript persistence is a separate
caller decision in the Runtime consumer.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat
import threading
import unicodedata
from types import MappingProxyType
from typing import Mapping

_REQUIRED_FILES = ("encoder", "decoder", "joiner", "tokens")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_MAX_WINDOW_MS = 1000
_MAX_PCM_BYTES = 96_000  # 48 kHz mono PCM16, one second
_MAX_TEXT_CHARS = 512


class TeacherEarError(ValueError):
    """Invalid teacher configuration, input, or model output."""


class VerifiedModelFiles(dict[str, Path]):
    """Keep hash-checked model inodes open while a native loader uses /proc/self/fd paths."""

    def __init__(self, values: Mapping[str, Path], file_descriptors: list[int]):
        super().__init__(values)
        self._file_descriptors = list(file_descriptors)
        self._closed = False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for descriptor in reversed(self._file_descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass
        self._file_descriptors.clear()

    def __enter__(self):
        if self._closed:
            raise TeacherEarError("verified model file handles are closed")
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


@dataclass(frozen=True)
class TeacherEarManifest:
    model_id: str
    model_revision: str
    language: str
    license_id: str
    model_root: str
    encoder: str
    decoder: str
    joiner: str
    tokens: str
    file_sha256: Mapping[str, str]
    num_threads: int = 1
    sample_rate: int = 16000
    max_total_bytes: int = 64 * 1024 * 1024

    def __post_init__(self) -> None:
        for name in ("model_id", "model_revision", "language", "license_id", "model_root"):
            value = getattr(self, name)
            if type(value) is not str or not value.strip() or len(value) > 512:
                raise TeacherEarError(f"{name} is invalid")
        if type(self.num_threads) is not int or not 1 <= self.num_threads <= 2:
            raise TeacherEarError("num_threads must be 1 or 2")
        if type(self.sample_rate) is not int or not 8000 <= self.sample_rate <= 48000:
            raise TeacherEarError("sample_rate must be in [8000, 48000]")
        if type(self.max_total_bytes) is not int or not 1 <= self.max_total_bytes <= 256 * 1024 * 1024:
            raise TeacherEarError("max_total_bytes is invalid")
        hashes = dict(self.file_sha256) if isinstance(self.file_sha256, Mapping) else None
        if hashes is None or set(hashes) != set(_REQUIRED_FILES):
            raise TeacherEarError("file_sha256 must pin encoder, decoder, joiner and tokens")
        for key, digest in hashes.items():
            if type(digest) is not str or not _SHA256.fullmatch(digest):
                raise TeacherEarError(f"invalid {key} SHA-256")
        object.__setattr__(self, "file_sha256", MappingProxyType(hashes))
        for key in _REQUIRED_FILES:
            rel = getattr(self, key)
            if type(rel) is not str or not rel or len(rel) > 512:
                raise TeacherEarError(f"{key} path is invalid")
            pure = PurePosixPath(rel)
            if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
                raise TeacherEarError(f"{key} path must be relative and contained")

    def verified_files(self) -> VerifiedModelFiles:
        """Hash files through directory FDs and pin their inodes for native loading.

        The returned paths are /proc/self/fd entries backed by still-open read-only
        descriptors. This prevents a rename/symlink swap between hash verification
        and sherpa-onnx opening the model paths. Call close() after the recognizer
        has been destroyed.
        """
        raw_root = Path(self.model_root).expanduser()
        if raw_root.is_symlink():
            raise TeacherEarError("model root must not be a symlink")
        try:
            root = raw_root.resolve(strict=True)
        except OSError as exc:
            raise TeacherEarError("model root is unavailable") from exc
        if not root.is_dir():
            raise TeacherEarError("model root must be a directory")
        if (not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW")
                or os.open not in getattr(os, "supports_dir_fd", set())):
            raise TeacherEarError("secure model loading requires O_DIRECTORY, O_NOFOLLOW and dir_fd support")
        proc_fd_root = Path("/proc/self/fd")
        if not proc_fd_root.is_dir():
            raise TeacherEarError("stable model loading requires /proc/self/fd")

        directory_flags = (
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            | getattr(os, "O_CLOEXEC", 0)
        )
        file_flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        root_anchor = None
        root_handle = None
        file_descriptors: list[int] = []
        try:
            # Walk the canonical absolute root without following a component
            # that was replaced by a symlink after Path.resolve().
            root_anchor = os.open("/", directory_flags)
            root_handle = root_anchor
            for part in root.parts[1:]:
                next_handle = os.open(part, directory_flags, dir_fd=root_handle)
                if root_handle != root_anchor:
                    os.close(root_handle)
                root_handle = next_handle

            verified: dict[str, Path] = {}
            total = 0
            for key in _REQUIRED_FILES:
                parts = PurePosixPath(getattr(self, key)).parts
                parent_fd = os.dup(root_handle)
                file_fd = None
                try:
                    for part in parts[:-1]:
                        try:
                            next_fd = os.open(part, directory_flags, dir_fd=parent_fd)
                        except OSError as exc:
                            raise TeacherEarError(
                                f"{key} parent path is unavailable or contains a symlink"
                            ) from exc
                        os.close(parent_fd)
                        parent_fd = next_fd
                    try:
                        file_fd = os.open(parts[-1], file_flags, dir_fd=parent_fd)
                    except OSError as exc:
                        raise TeacherEarError(
                            f"{key} file is unavailable or contains a symlink"
                        ) from exc
                finally:
                    os.close(parent_fd)

                try:
                    opened = os.fstat(file_fd)
                    if not stat.S_ISREG(opened.st_mode):
                        raise TeacherEarError(f"{key} must be a regular file")
                    total += opened.st_size
                    if total > self.max_total_bytes:
                        raise TeacherEarError("model bundle exceeds configured size ceiling")
                    digest = hashlib.sha256()
                    with os.fdopen(os.dup(file_fd), "rb") as handle:
                        while True:
                            chunk = handle.read(1024 * 1024)
                            if not chunk:
                                break
                            digest.update(chunk)
                    if digest.hexdigest() != self.file_sha256[key]:
                        raise TeacherEarError(f"{key} SHA-256 mismatch")

                    fd_path = Path(f"/proc/self/fd/{file_fd}")
                    pinned = os.stat(fd_path)
                    if (pinned.st_dev, pinned.st_ino) != (opened.st_dev, opened.st_ino):
                        raise TeacherEarError(f"{key} descriptor path does not identify the verified file")
                    file_descriptors.append(file_fd)
                    verified[key] = fd_path
                    file_fd = None
                finally:
                    if file_fd is not None:
                        os.close(file_fd)

            return VerifiedModelFiles(verified, file_descriptors)
        except TeacherEarError:
            for descriptor in reversed(file_descriptors):
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            raise
        except OSError as exc:
            for descriptor in reversed(file_descriptors):
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            raise TeacherEarError("cannot safely open model bundle") from exc
        finally:
            if root_handle is not None and root_handle != root_anchor:
                os.close(root_handle)
            if root_anchor is not None:
                os.close(root_anchor)


def _clean_hypothesis(value: str) -> str:
    if type(value) is not str:
        raise TeacherEarError("recognizer returned a non-text result")
    normalized = unicodedata.normalize("NFC", value)
    cleaned = "".join(
        ch for ch in normalized
        if unicodedata.category(ch) != "Cc" or ch in "\t\n\r"
    )
    cleaned = " ".join(cleaned.split())
    if len(cleaned) > _MAX_TEXT_CHARS:
        cleaned = cleaned[:_MAX_TEXT_CHARS]
    return cleaned


class SherpaOnlineTeacher:
    """Lazy, CPU-only wrapper around sherpa_onnx.OnlineRecognizer.from_transducer."""

    def __init__(self, manifest: TeacherEarManifest, *, recognizer=None, numpy_module=None):
        if not isinstance(manifest, TeacherEarManifest):
            raise TypeError("manifest must be a TeacherEarManifest")
        self.manifest = manifest
        self._recognizer = recognizer
        self._np = numpy_module
        self._lock = threading.RLock()
        self._verified = None
        self._active_streams = 0

    def _load(self):
        if self._recognizer is not None:
            if self._np is None:
                try:
                    import numpy as np
                except ImportError as exc:
                    raise RuntimeError("NumPy is required for sherpa-onnx audio input") from exc
                self._np = np
            return self._recognizer
        files = self.manifest.verified_files()
        try:
            import numpy as np
            import sherpa_onnx
        except ImportError as exc:
            files.close()
            raise RuntimeError("optional sherpa-onnx and NumPy are not installed") from exc
        try:
            recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
                encoder=str(files["encoder"]),
                decoder=str(files["decoder"]),
                joiner=str(files["joiner"]),
                tokens=str(files["tokens"]),
                num_threads=self.manifest.num_threads,
                sample_rate=self.manifest.sample_rate,
                feature_dim=80,
                decoding_method="greedy_search",
                provider="cpu",
                enable_endpoint_detection=False,
                debug=False,
            )
        except Exception:
            files.close()
            raise
        self._np = np
        self._verified = files
        self._recognizer = recognizer
        return self._recognizer

    def close(self) -> None:
        """Release the recognizer and its pinned model descriptors when idle."""
        with self._lock:
            if self._active_streams:
                raise TeacherEarError("cannot close Teacher Ear while a stream is active")
            self._recognizer = None
            verified = self._verified
            self._verified = None
            if verified is not None:
                verified.close()

    @staticmethod
    def _lease_matches(lease, runtime, source_id, generation_id, receipt,
                       temporal_state, vad_stream) -> bool:
        matches = getattr(lease, "matches", None)
        if not callable(matches):
            return False
        try:
            return matches(
                runtime, source_id, generation_id, receipt,
                temporal_state=temporal_state, vad_stream=vad_stream,
                require_state=True,
            ) is True
        except Exception:
            return False


    def open_stream(
        self, *, runtime, source_id: str, generation_id: str,
        consent_receipt_ref: str, consent_lease, temporal_state=None,
        vad_stream=None, teacher_asr_opt_in: bool = False,
    ):
        """Open one bounded contiguous stream; caller closes it on revoke/teardown."""
        if teacher_asr_opt_in is not True:
            raise PermissionError("separate Teacher Ear ASR opt-in is required")
        if type(source_id) is not str or not source_id.strip() or len(source_id) > 128:
            raise TeacherEarError("source_id is invalid")
        if type(generation_id) is not str or not generation_id.strip() or len(generation_id) > 128:
            raise TeacherEarError("generation_id is invalid")
        if type(consent_receipt_ref) is not str or not consent_receipt_ref.strip() or len(consent_receipt_ref) > 256:
            raise PermissionError("audio consent receipt is required")
        if not self._lease_matches(
            consent_lease, runtime, source_id, generation_id, consent_receipt_ref,
            temporal_state, vad_stream,
        ):
            raise PermissionError("live source-bound AudioConsentLease required")
        with self._lock:
            if self._active_streams:
                raise TeacherEarError("one active streaming Teacher Ear session per recognizer")
            recognizer = self._load()
            stream = recognizer.create_stream()
            session = SherpaOnlineTeacherStream(
                self, recognizer, stream, runtime=runtime, source_id=source_id,
                generation_id=generation_id, consent_receipt_ref=consent_receipt_ref,
                temporal_state=temporal_state, vad_stream=vad_stream,
            )
            self._active_streams += 1
            return session

    def _release_stream(self):
        with self._lock:
            if self._active_streams > 0:
                self._active_streams -= 1

    def transcribe_pcm16(
        self,
        pcm16,
        *,
        sample_rate: int,
        start_ms: int,
        end_ms: int,
        runtime,
        source_id: str,
        generation_id: str,
        consent_receipt_ref: str,
        consent_lease,
        temporal_state=None,
        vad_stream=None,
        finality: str = "PROVISIONAL",
        teacher_asr_opt_in: bool = False,
    ) -> dict:
        if teacher_asr_opt_in is not True:
            raise PermissionError("separate Teacher Ear ASR opt-in is required")
        if type(source_id) is not str or not source_id.strip() or len(source_id) > 128:
            raise TeacherEarError("source_id is invalid")
        if type(generation_id) is not str or not generation_id.strip() or len(generation_id) > 128:
            raise TeacherEarError("generation_id is invalid")
        if type(consent_receipt_ref) is not str or not consent_receipt_ref.strip() or len(consent_receipt_ref) > 256:
            raise PermissionError("audio consent receipt is required")
        if type(start_ms) is not int or type(end_ms) is not int or start_ms < 0 or end_ms <= start_ms or end_ms - start_ms > _MAX_WINDOW_MS:
            raise TeacherEarError("audio interval must be a positive window of at most 1000 ms")
        if type(sample_rate) is not int or not 8000 <= sample_rate <= 48000:
            raise TeacherEarError("sample_rate must be in [8000, 48000]")
        if finality not in {"FINAL", "PROVISIONAL"}:
            raise TeacherEarError("finality must be FINAL or PROVISIONAL")
        if type(pcm16) not in (bytes, bytearray) or not pcm16 or len(pcm16) % 2 or len(pcm16) > _MAX_PCM_BYTES:
            raise TeacherEarError("PCM16 must be a non-empty bounded mono byte buffer")
        measured_ms = (len(pcm16) // 2) * 1000.0 / sample_rate
        if abs(measured_ms - (end_ms - start_ms)) > 2.0:
            raise TeacherEarError("PCM16 duration does not match its source interval")
        if not self._lease_matches(
            consent_lease, runtime, source_id, generation_id, consent_receipt_ref,
            temporal_state, vad_stream,
        ):
            raise PermissionError("live source-bound AudioConsentLease required")

        with self._lock:
            recognizer = self._load()
            waveform = self._np.frombuffer(bytes(pcm16), dtype="<i2").astype(self._np.float32)
            waveform /= 32768.0
            stream = recognizer.create_stream()
            stream.accept_waveform(sample_rate, waveform)
            # sherpa-onnx's documented streaming example flushes a short zero tail.
            stream.accept_waveform(
                sample_rate,
                self._np.zeros(int(sample_rate * 0.5), dtype=self._np.float32),
            )
            decode_steps = 0
            while recognizer.is_ready(stream):
                recognizer.decode_stream(stream)
                decode_steps += 1
                if decode_steps > 4096:
                    raise TeacherEarError("recognizer exceeded bounded decode steps")
            hypothesis = _clean_hypothesis(recognizer.get_result(stream))

        if not self._lease_matches(
            consent_lease, runtime, source_id, generation_id, consent_receipt_ref,
            temporal_state, vad_stream,
        ):
            raise PermissionError("AudioConsentLease expired or changed during Teacher Ear inference")
        return {
            "method": "SHERPA_ONNX_ONLINE_TRANSDUCER",
            "processing_mode": "INDEPENDENT_WINDOW",
            "status": "MEASURED" if hypothesis else "EMPTY",
            "model_id": self.manifest.model_id,
            "model_revision": self.manifest.model_revision,
            "language": self.manifest.language,
            "license_id": self.manifest.license_id,
            "source_ref": {
                "source_id": source_id,
                "source_sha256": hashlib.sha256(bytes(pcm16)).hexdigest(),
                "generation_id": generation_id,
                "consent_receipt_ref": consent_receipt_ref,
            },
            "model_file_sha256": dict(self.manifest.file_sha256),
            "segments": ([{
                "start_ms": start_ms,
                "end_ms": end_ms,
                "timestamp_granularity": "WINDOW",
                "finality": finality,
                "text": hypothesis,
                "hypothesis_not_truth": True,
            }] if hypothesis else []),
            "truth_authority": 0,
            "learning_authority": False,
            "action_authority": False,
        }



class SherpaOnlineTeacherStream:
    """One source/consent-bound sherpa stream across contiguous timed PCM windows.

    Partial hypotheses are deltas; cumulative text and a rolling source hash
    remain available only in the returned, separately persistable Teacher Ear
    record. close() discards the native stream without finalizing it.
    """

    def __init__(
        self, teacher, recognizer, stream, *, runtime, source_id,
        generation_id, consent_receipt_ref, temporal_state=None, vad_stream=None,
    ):
        self._teacher = teacher
        self._recognizer = recognizer
        self._stream = stream
        self._runtime = runtime
        self._source_id = source_id
        self._generation_id = generation_id
        self._receipt = consent_receipt_ref
        self._temporal_state = temporal_state
        self._vad_stream = vad_stream
        self._thread_id = threading.get_ident()
        self._lock = threading.RLock()
        self._closed = False
        self._sample_rate = None
        self._first_start_ms = None
        self._next_start_ms = None
        self._total_ms = 0
        self._chunk_count = 0
        self._rolling_digest = hashlib.sha256(b"").digest()
        self._stream_id = None
        self._last_hypothesis = ""

    @property
    def closed(self):
        return self._closed is True

    def __enter__(self):
        if self.closed:
            raise TeacherEarError("Teacher Ear stream is closed")
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def __reduce__(self):
        raise TypeError("Teacher Ear stream sessions are ephemeral")

    def __copy__(self):
        raise TypeError("Teacher Ear stream sessions cannot be copied")

    def __deepcopy__(self, memo):
        raise TypeError("Teacher Ear stream sessions cannot be copied")

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._stream = None
            self._recognizer = None
            self._teacher._release_stream()

    def transcribe_pcm16(
        self, pcm16, *, sample_rate: int, start_ms: int, end_ms: int,
        runtime, source_id: str, generation_id: str,
        consent_receipt_ref: str, consent_lease, temporal_state=None,
        vad_stream=None, finality: str = "PROVISIONAL",
        teacher_asr_opt_in: bool = False,
    ) -> dict:
        with self._lock:
            try:
                if self.closed:
                    raise TeacherEarError("Teacher Ear stream is closed")
                if teacher_asr_opt_in is not True:
                    raise PermissionError("separate Teacher Ear ASR opt-in is required")
                if threading.get_ident() != self._thread_id:
                    raise PermissionError("Teacher Ear stream must stay on its owner thread")
                if (runtime is not self._runtime or source_id != self._source_id
                        or generation_id != self._generation_id
                        or consent_receipt_ref != self._receipt
                        or temporal_state is not self._temporal_state
                        or vad_stream is not self._vad_stream):
                    raise PermissionError("Teacher Ear stream source or consent scope changed")
                if type(start_ms) is not int or type(end_ms) is not int or start_ms < 0 or end_ms <= start_ms or end_ms - start_ms > _MAX_WINDOW_MS:
                    raise TeacherEarError("audio interval must be a positive window of at most 1000 ms")
                if type(sample_rate) is not int or not 8000 <= sample_rate <= 48000:
                    raise TeacherEarError("sample_rate must be in [8000, 48000]")
                if finality not in {"FINAL", "PROVISIONAL"}:
                    raise TeacherEarError("finality must be FINAL or PROVISIONAL")
                if type(pcm16) not in (bytes, bytearray) or not pcm16 or len(pcm16) % 2 or len(pcm16) > _MAX_PCM_BYTES:
                    raise TeacherEarError("PCM16 must be a non-empty bounded mono byte buffer")
                measured_ms = (len(pcm16) // 2) * 1000.0 / sample_rate
                if abs(measured_ms - (end_ms - start_ms)) > 2.0:
                    raise TeacherEarError("PCM16 duration does not match its source interval")
                if not self._teacher._lease_matches(
                    consent_lease, runtime, source_id, generation_id,
                    consent_receipt_ref, temporal_state, vad_stream,
                ):
                    raise PermissionError("live source-bound AudioConsentLease required")
                if self._sample_rate is not None and sample_rate != self._sample_rate:
                    raise TeacherEarError("sample rate cannot change inside a Teacher Ear stream")
                if self._next_start_ms is not None and start_ms != self._next_start_ms:
                    raise TeacherEarError("Teacher Ear stream windows must be contiguous")
                if self._total_ms + (end_ms - start_ms) > 120_000 or self._chunk_count >= 2400:
                    raise TeacherEarError("Teacher Ear stream exceeded its bounded duration or chunk count")

                stream = self._stream
                recognizer = self._recognizer
                if stream is None or recognizer is None:
                    raise TeacherEarError("Teacher Ear stream is unavailable")
                chunk_sha256 = hashlib.sha256(bytes(pcm16)).hexdigest()
                with self._teacher._lock:
                    waveform = self._teacher._np.frombuffer(
                        bytes(pcm16), dtype="<i2",
                    ).astype(self._teacher._np.float32)
                    waveform /= 32768.0
                    stream.accept_waveform(sample_rate, waveform)
                    if finality == "FINAL":
                        stream.accept_waveform(
                            sample_rate,
                            self._teacher._np.zeros(
                                int(sample_rate * 0.5), dtype=self._teacher._np.float32,
                            ),
                        )
                        finish = getattr(stream, "input_finished", None)
                        if not callable(finish):
                            raise TeacherEarError("sherpa stream lacks input_finished()")
                        finish()
                    decode_steps = 0
                    while recognizer.is_ready(stream):
                        recognizer.decode_stream(stream)
                        decode_steps += 1
                        if decode_steps > 4096:
                            raise TeacherEarError("recognizer exceeded bounded decode steps")
                    cumulative = _clean_hypothesis(recognizer.get_result(stream))

                if not self._teacher._lease_matches(
                    consent_lease, runtime, source_id, generation_id,
                    consent_receipt_ref, temporal_state, vad_stream,
                ):
                    raise PermissionError("AudioConsentLease expired or changed during Teacher Ear inference")

                if self._first_start_ms is None:
                    self._first_start_ms = start_ms
                    self._sample_rate = sample_rate
                    self._stream_id = hashlib.sha256(
                        f"{source_id}\\0{generation_id}\\0{consent_receipt_ref}\\0{start_ms}".encode("utf-8")
                    ).hexdigest()
                if cumulative.startswith(self._last_hypothesis):
                    delta = cumulative[len(self._last_hypothesis):].strip()
                    revision = False
                else:
                    delta = ""
                    revision = cumulative != self._last_hypothesis
                self._last_hypothesis = cumulative
                self._chunk_count += 1
                self._total_ms += end_ms - start_ms
                self._next_start_ms = end_ms
                self._rolling_digest = hashlib.sha256(
                    self._rolling_digest + bytes.fromhex(chunk_sha256)
                    + start_ms.to_bytes(8, "big") + end_ms.to_bytes(8, "big")
                ).digest()
                result = {
                    "method": "SHERPA_ONNX_ONLINE_TRANSDUCER",
                    "processing_mode": "CONTIGUOUS_STREAM",
                    "status": "MEASURED" if cumulative else "EMPTY",
                    "model_id": self._teacher.manifest.model_id,
                    "model_revision": self._teacher.manifest.model_revision,
                    "language": self._teacher.manifest.language,
                    "license_id": self._teacher.manifest.license_id,
                    "source_ref": {
                        "source_id": source_id,
                        "source_sha256": chunk_sha256,
                        "generation_id": generation_id,
                        "consent_receipt_ref": consent_receipt_ref,
                    },
                    "stream_ref": {
                        "stream_id": self._stream_id,
                        "source_id": source_id,
                        "generation_id": generation_id,
                        "consent_receipt_ref": consent_receipt_ref,
                        "start_ms": self._first_start_ms,
                        "end_ms": end_ms,
                        "chunk_index": self._chunk_count,
                        "chunk_count": self._chunk_count,
                        "rolling_sha256": self._rolling_digest.hex(),
                    },
                    "model_file_sha256": dict(self._teacher.manifest.file_sha256),
                    "cumulative_hypothesis": cumulative,
                    "segments": ([{
                        "start_ms": start_ms,
                        "end_ms": end_ms,
                        "timestamp_granularity": "WINDOW",
                        "finality": finality,
                        "text": delta,
                        "revision": revision,
                        "hypothesis_not_truth": True,
                    }] if cumulative else []),
                    "truth_authority": 0,
                    "learning_authority": False,
                    "action_authority": False,
                }
                if finality == "FINAL":
                    self.close()
                return result
            except Exception:
                self.close()
                raise
