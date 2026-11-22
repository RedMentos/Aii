#!/usr/bin/env python3
"""Compare RAW EAR V3 activity hints with a WebRTC/libfvad VAD baseline.

The tool is offline and read-only. It consumes caller-selected mono PCM16 WAV
files plus local speech-interval annotations. It never records, uploads,
transcribes, persists, or prints audio samples. WebRTC 20 ms decisions are
OR-aligned into the same overlapping 40 ms / 20 ms windows used by RAW EAR V3;
both then pass through the same TemporalVoiceEvidence V1 smoother.

This is an evaluation harness, not a VAD replacement or a production consumer.
"""
from __future__ import annotations

import argparse
import ast
import ctypes
import ctypes.util
import hashlib
import importlib.util
from functools import lru_cache
import json
import math
import platform
try:
    import resource
except ImportError:  # pragma: no cover - non-POSIX host
    resource = None
import statistics
import struct
import sys
import time
import wave
from pathlib import Path
from typing import Callable

SUPPORTED_RATES = (8000, 16000, 32000, 48000)
FRAME_MS = 20
WINDOW_MS = 40
HOP_MS = 20


class WebRtcVadBackend:
    def __init__(self, mode: int = 2) -> None:
        import webrtcvad
        self._vad = webrtcvad.Vad(mode)
        try:
            from importlib.metadata import version
            self.version = version("webrtcvad-wheels")
        except Exception:
            self.version = getattr(webrtcvad, "__version__", "unknown")
        self.name = "WEBRTCVAD_PYTHON_WHEELS"

    def is_speech(self, frame: bytes, sample_rate: int) -> bool:
        return bool(self._vad.is_speech(frame, sample_rate))


class LibFvadBackend:
    """Small ctypes binding for the public dpirch/libfvad C API."""
    def __init__(self, library_path: str, mode: int = 2, sample_rate: int = 16000, version: str = "library-path-pinned-by-caller") -> None:
        self._lib = ctypes.CDLL(library_path)
        self._lib.fvad_new.restype = ctypes.c_void_p
        self._lib.fvad_free.argtypes = [ctypes.c_void_p]
        self._lib.fvad_free.restype = None
        self._lib.fvad_set_mode.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self._lib.fvad_set_mode.restype = ctypes.c_int
        self._lib.fvad_set_sample_rate.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self._lib.fvad_set_sample_rate.restype = ctypes.c_int
        self._lib.fvad_process.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_int16), ctypes.c_size_t
        ]
        self._lib.fvad_process.restype = ctypes.c_int
        self._instance = self._lib.fvad_new()
        if not self._instance:
            raise RuntimeError("fvad_new returned NULL")
        if self._lib.fvad_set_mode(self._instance, mode) != 0:
            self.close()
            raise ValueError("libfvad rejected aggressiveness mode")
        if self._lib.fvad_set_sample_rate(self._instance, sample_rate) != 0:
            self.close()
            raise ValueError("libfvad rejected sample rate")
        self.name = "LIBFVAD_C_API"
        self.version = version
        self._sample_rate = sample_rate

    def is_speech(self, frame: bytes, sample_rate: int) -> bool:
        if sample_rate not in SUPPORTED_RATES or len(frame) % 2:
            raise ValueError("invalid libfvad frame")
        sample_count = len(frame) // 2
        valid_counts = {
            sample_rate // 100,
            sample_rate // 50,
            sample_rate * 3 // 100,
        }
        if sample_count not in valid_counts:
            raise ValueError("libfvad frame must be 10, 20 or 30 ms")
        if sample_rate != self._sample_rate:
            if self._lib.fvad_set_sample_rate(self._instance, sample_rate) != 0:
                raise ValueError("libfvad rejected sample rate")
            self._sample_rate = sample_rate
        samples = (ctypes.c_int16 * sample_count).from_buffer_copy(frame)
        result = self._lib.fvad_process(self._instance, samples, sample_count)
        if result < 0:
            raise ValueError("libfvad rejected frame length")
        return result == 1

    def close(self) -> None:
        instance = getattr(self, "_instance", None)
        if instance:
            self._lib.fvad_free(instance)
            self._instance = None

    def __del__(self) -> None:
        self.close()


def _load_temporal_class(source_path: Path):
    spec = importlib.util.spec_from_file_location("_v14_temporal_voice_evidence", source_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load TemporalVoiceEvidence source")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cls = getattr(module, "TemporalVoiceEvidence", None)
    if cls is None:
        raise RuntimeError("TemporalVoiceEvidence is missing from source")
    return cls


def _load_v3_extractor(source_path: Path):
    raw = source_path.read_bytes()
    tree = ast.parse(raw, filename=str(source_path))
    wanted_functions = {"_estimate_pitch", "_voice_decimator_coefficients", "_anti_alias_decimate", "_percentile", "validate_voice_cues", "extract_voice_cues"}
    selected = []
    found = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "_ACTIVITY_HINTS"
            for target in node.targets
        ):
            selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected.append(node)
            found.add(node.name)
    missing = wanted_functions - found
    if missing:
        raise RuntimeError("V3 source is missing functions: " + ", ".join(sorted(missing)))
    namespace = {"math": math, "struct": struct, "median": statistics.median, "lru_cache": lru_cache}
    isolated = ast.Module(body=selected, type_ignores=[])
    exec(compile(isolated, str(source_path), "exec"), namespace)
    extractor = namespace["extract_voice_cues"]
    probe = extractor(struct.pack("<" + "h" * 640, *([3000] * 640)), 16000)
    if probe.get("method") != "RAW_EAR_AUTOCORR_V3":
        raise RuntimeError("source is not the expected RAW EAR V3 producer")
    git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    return extractor, hashlib.sha256(raw).hexdigest(), git_blob


def _validate_intervals(intervals, duration_ms: int) -> list[tuple[int, int]]:
    if not isinstance(intervals, list):
        raise ValueError("speech_intervals_ms must be a list")
    clean = []
    previous_end = -1
    for pair in intervals:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("each speech interval must be [start_ms, end_ms]")
        start, end = pair
        if type(start) is not int or type(end) is not int or start < 0 or end <= start or end > duration_ms:
            raise ValueError("speech interval bounds are invalid")
        if start < previous_end:
            raise ValueError("speech intervals must be sorted and non-overlapping")
        clean.append((start, end))
        previous_end = end
    return clean


def _state_transitions(predictions: list[dict]) -> list[tuple[str, int]]:
    """Return state changes at the end of the window that first observed them."""
    transitions = []
    previous = False
    for item in predictions:
        current = bool(item["positive"])
        if current != previous:
            transitions.append(("onset" if current else "offset", int(item["end_ms"])))
        previous = current
    return transitions


def _metrics(predictions: list[dict], intervals: list[tuple[int, int]], duration_ms: int) -> dict:
    tp = fp = tn = fn = 0
    for item in predictions:
        reference = any(item["start_ms"] < end and item["end_ms"] > start for start, end in intervals)
        predicted = bool(item["positive"])
        if predicted and reference:
            tp += 1
        elif predicted:
            fp += 1
        elif reference:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    speech_ms = sum(end - start for start, end in intervals)
    nonspeech_ms = max(0, duration_ms - speech_ms)
    fpr = fp / (fp + tn) if fp + tn else 0.0
    fnr = fn / (fn + tp) if fn + tp else 0.0
    fp_per_minute = fp * 60000 / max(nonspeech_ms, HOP_MS)
    transitions = _state_transitions(predictions)
    used_onsets, used_offsets = set(), set()
    onset_delays, offset_delays = [], []
    missing_onsets = missing_offsets = 0
    tolerance_ms = 500
    for start, end in intervals:
        onset_candidates = [
            (abs(time_ms - start), time_ms, index)
            for index, (kind, time_ms) in enumerate(transitions)
            if kind == "onset" and index not in used_onsets
            and abs(time_ms - start) <= tolerance_ms
        ]
        if onset_candidates:
            _, time_ms, index = min(onset_candidates)
            used_onsets.add(index)
            onset_delays.append(time_ms - start)
        else:
            missing_onsets += 1
        offset_candidates = [
            (abs(time_ms - end), time_ms, index)
            for index, (kind, time_ms) in enumerate(transitions)
            if kind == "offset" and index not in used_offsets
            and abs(time_ms - end) <= tolerance_ms
        ]
        if offset_candidates:
            _, time_ms, index = min(offset_candidates)
            used_offsets.add(index)
            offset_delays.append(time_ms - end)
        else:
            missing_offsets += 1
    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": round(precision, 6), "recall": round(recall, 6),
        "fpr": round(fpr, 6), "fnr": round(fnr, 6),
        "f1": round(f1, 6), "false_positives_per_nonspeech_minute": round(fp_per_minute, 3),
        "onset_delay_ms_median": round(statistics.median(onset_delays), 2) if onset_delays else None,
        "offset_delay_ms_median": round(statistics.median(offset_delays), 2) if offset_delays else None,
        "missing_onsets": missing_onsets, "missing_offsets": missing_offsets,
        "annotated_speech_intervals": len(intervals),
        "onset_transition_count": sum(kind == "onset" for kind, _ in transitions),
        "offset_transition_count": sum(kind == "offset" for kind, _ in transitions),
        "transition_tolerance_ms": tolerance_ms,
        "transition_time": "end_of_state-changing_window",
    }


def compare_pcm(
    pcm: bytes,
    sample_rate: int,
    speech_intervals_ms: list,
    *,
    extractor: Callable[[bytes, int], dict],
    temporal_class,
    backend,
    source_sha256: str,
    source_git_blob: str,
) -> dict:
    if type(pcm) is not bytes or not pcm or len(pcm) % 2:
        raise ValueError("input must be non-empty mono PCM16 bytes")
    if sample_rate not in SUPPORTED_RATES:
        raise ValueError("sample rate must be 8000, 16000, 32000 or 48000 Hz")
    frame_samples = sample_rate * FRAME_MS // 1000
    window_samples = sample_rate * WINDOW_MS // 1000
    hop_samples = sample_rate * HOP_MS // 1000
    total_samples = len(pcm) // 2
    duration_ms = total_samples * 1000 // sample_rate
    intervals = _validate_intervals(speech_intervals_ms, duration_ms)
    if total_samples < window_samples:
        raise ValueError("audio must contain at least one complete 40 ms window")
    usable_samples = total_samples - (total_samples % hop_samples)
    if usable_samples != total_samples:
        raise ValueError("audio sample count must align to the 20 ms hop")
    processed_duration_ms = usable_samples * 1000 // sample_rate
    starts = list(range(0, usable_samples - window_samples + 1, hop_samples))

    v3_state = temporal_class()
    v3_raw, v3_smooth = [], []
    started = time.perf_counter()
    cpu_started = time.process_time()
    for start in starts:
        start_ms = start * 1000 // sample_rate
        end_ms = (start + window_samples) * 1000 // sample_rate
        window = pcm[start * 2:(start + window_samples) * 2]
        cues = extractor(window, sample_rate)
        state = v3_state.update(
            source_id="vad-compare-local", generation_id="raw-ear-v3",
            start_ms=start_ms, end_ms=end_ms, cues=cues,
        )
        v3_raw.append({"start_ms": start_ms, "end_ms": end_ms,
                       "positive": cues["activity_hint"] == "VOICED"})
        v3_smooth.append({"start_ms": start_ms, "end_ms": end_ms,
                          "positive": bool(state["voice_active"])})
    v3_elapsed_ms = (time.perf_counter() - started) * 1000
    v3_cpu_ms = (time.process_time() - cpu_started) * 1000

    vad_state = temporal_class()
    web_raw, web_smooth = [], []
    started = time.perf_counter()
    cpu_started = time.process_time()
    decisions = []
    for start in range(0, usable_samples - frame_samples + 1, frame_samples):
        frame = pcm[start * 2:(start + frame_samples) * 2]
        decisions.append(bool(backend.is_speech(frame, sample_rate)))
    for start in starts:
        frame_index = start // frame_samples
        aligned_voice = any(decisions[frame_index:frame_index + 2])
        start_ms = start * 1000 // sample_rate
        end_ms = (start + window_samples) * 1000 // sample_rate
        cues = {"activity_hint": "VOICED" if aligned_voice else "SILENCE",
                "activity_score": 1.0 if aligned_voice else 0.0}
        state = vad_state.update(
            source_id="vad-compare-local", generation_id="webrtc-vad",
            start_ms=start_ms, end_ms=end_ms, cues=cues,
        )
        web_raw.append({"start_ms": start_ms, "end_ms": end_ms, "positive": aligned_voice})
        web_smooth.append({"start_ms": start_ms, "end_ms": end_ms,
                           "positive": bool(state["voice_active"])})
    web_elapsed_ms = (time.perf_counter() - started) * 1000
    web_cpu_ms = (time.process_time() - cpu_started) * 1000
    try:
        peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else None
        peak_rss_unit = ("KiB" if sys.platform.startswith("linux") else "platform_native") if peak_rss is not None else None
    except Exception:
        peak_rss, peak_rss_unit = None, None

    vad_baseline = {
        "name": backend.name, "version": backend.version,
        "raw": _metrics(web_raw, intervals, processed_duration_ms),
        "temporal_smoothed": _metrics(web_smooth, intervals, processed_duration_ms),
        "processing_wall_ms": round(web_elapsed_ms, 3),
        "processing_cpu_ms": round(web_cpu_ms, 3),
        "real_time_factor": round(web_elapsed_ms / max(processed_duration_ms, 1), 6),
    }
    result = {
        "schema": "v14.raw-ear-vad-comparison/1",
        "environment": "LOCAL_LINUX_SYNTHETIC_OR_USER_SUPPLIED_WAV",
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "process_peak_rss": peak_rss,
        "process_peak_rss_unit": peak_rss_unit,
        "rss_scope": "whole benchmark process peak; not incremental per backend",
        "sample_rate_hz": sample_rate,
        "frame_ms": FRAME_MS,
        "aligned_window_ms": WINDOW_MS,
        "hop_ms": HOP_MS,
        "duration_ms": duration_ms,
        "processed_duration_ms": processed_duration_ms,
        "source": {"audio_sha256_not_emitted": True, "v3_source_sha256": source_sha256,
                   "v3_source_git_blob": source_git_blob},
        "alignment": "20ms VAD decisions OR-combined into the same 40ms windows; both detectors use identical TemporalVoiceEvidence V1 smoothing. Onset/offset time is the end of the state-changing 40ms window.",
        "raw_ear_v3": {
            "raw": _metrics(v3_raw, intervals, processed_duration_ms),
            "temporal_smoothed": _metrics(v3_smooth, intervals, processed_duration_ms),
            "processing_wall_ms": round(v3_elapsed_ms, 3),
            "processing_cpu_ms": round(v3_cpu_ms, 3),
            "real_time_factor": round(v3_elapsed_ms / max(processed_duration_ms, 1), 6),
        },
        "vad_baseline": vad_baseline,
        "limitations": [
            "The 40ms overlap-window OR is an explicit alignment adapter, not native WebRTC/libfvad postprocessing.",
            "Synthetic fixtures are software smoke tests, not speech-corpus accuracy evidence.",
            "No microphone, Android ABI, Redmi CPU/RSS/PSS, battery, or user audio is measured by default.",
            "The V3 activity hint is a deterministic acoustic heuristic, not a calibrated speech probability.",
            "Reference labels use any-overlap 40ms windows; boundary metrics use unique state transitions within +/-500ms.",
        ],
    }
    if backend.name == "WEBRTCVAD_PYTHON_WHEELS":
        result["webrtc_baseline"] = vad_baseline
    return result


def load_wav(path: Path) -> tuple[bytes, int]:
    with wave.open(str(path), "rb") as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2 or wav.getcomptype() != "NONE":
            raise ValueError("WAV must be uncompressed mono PCM16")
        sample_rate = wav.getframerate()
        pcm = wav.readframes(wav.getnframes())
    if sample_rate not in SUPPORTED_RATES:
        raise ValueError("WAV sample rate must be 8/16/32/48 kHz")
    return pcm, sample_rate


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav", type=Path)
    parser.add_argument("annotations", type=Path, help="JSON: {\"speech_intervals_ms\":[[start,end],...]}")
    parser.add_argument("--v3-source", type=Path, default=None)
    parser.add_argument("--temporal-source", type=Path, default=None)
    parser.add_argument("--backend", choices=("auto", "libfvad", "webrtcvad"), default="auto")
    parser.add_argument("--libfvad-path", default=None)
    parser.add_argument("--mode", type=int, choices=(0, 1, 2, 3), default=2)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    v3_path = args.v3_source or root / "v13" / "code" / "v13" / "audio_voice_cues.py"
    temporal_path = args.temporal_source or root / "v13" / "code" / "v13" / "audio_temporal_evidence.py"
    extractor, source_sha256, source_blob = _load_v3_extractor(v3_path)
    temporal_class = _load_temporal_class(temporal_path)
    annotations = json.loads(args.annotations.read_text(encoding="utf-8"))
    if set(annotations) != {"speech_intervals_ms"}:
        raise ValueError("annotation JSON must contain only speech_intervals_ms")
    if args.backend == "libfvad" or (args.backend == "auto" and args.libfvad_path):
        library = args.libfvad_path or ctypes.util.find_library("fvad")
        if not library:
            raise RuntimeError("libfvad shared library not found; pass --libfvad-path")
        backend = LibFvadBackend(
            library, args.mode, 16000,
            version=os.getenv("V14_LIBFVAD_VERSION", "library-path-pinned-by-caller"),
        )
    else:
        backend = WebRtcVadBackend(args.mode)
    pcm, sample_rate = load_wav(args.wav)
    if sample_rate != 16000 and isinstance(backend, LibFvadBackend):
        backend.close()
        raise ValueError("this libfvad adapter currently pins 16 kHz; use a 16 kHz WAV")
    try:
        result = compare_pcm(
            pcm, sample_rate, annotations["speech_intervals_ms"],
            extractor=extractor, temporal_class=temporal_class, backend=backend,
            source_sha256=source_sha256, source_git_blob=source_blob,
        )
    finally:
        if isinstance(backend, LibFvadBackend):
            backend.close()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
