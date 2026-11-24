#!/usr/bin/env python3
"""Synthetic-only RAW_EAR Python/NumPy benchmark with optional WebRTC VAD baseline.

No microphone, file capture, network, user audio, model weights or training.
This measures feature-extraction cost and output parity, not speech accuracy.
Run from v13/code:
  python experiments/benchmark_raw_ear_backends.py --iterations 20
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import random
import statistics
import struct
import sys
import time
import tracemalloc
from pathlib import Path

# Keep the documented direct-script invocation working: Python otherwise puts
# only this experiments/ directory at sys.path[0], not the v13/code package root.
CODE_ROOT = Path(__file__).resolve().parents[1]
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from v13.audio_voice_cues import extract_voice_cues
from v13.audio_speaker_evidence import SCHEMA, SpeakerChangeEvidenceRegistry


SAMPLE_RATE = 16000


def pcm16(samples):
    clipped = [max(-32768, min(32767, int(value))) for value in samples]
    return struct.pack("<" + "h" * len(clipped), *clipped)


def tone(frequency=140.0, seconds=1.0, amplitude=9000.0):
    count = int(SAMPLE_RATE * seconds)
    return pcm16(amplitude * math.sin(2.0 * math.pi * frequency * i / SAMPLE_RATE)
                 for i in range(count))


def harmonic_voice_like():
    samples = []
    for i in range(SAMPLE_RATE):
        t = i / SAMPLE_RATE
        f0 = 135.0 + 25.0 * math.sin(2.0 * math.pi * 2.5 * t)
        phase = 2.0 * math.pi * (
            135.0 * t
            + (25.0 / (2.0 * math.pi * 2.5))
            * (1.0 - math.cos(2.0 * math.pi * 2.5 * t))
        )
        envelope = 0.18 + 0.12 * (0.5 + 0.5 * math.sin(2.0 * math.pi * 3.0 * t))
        samples.append(32767.0 * envelope * (
            math.sin(phase) + 0.45 * math.sin(2.0 * phase) + 0.2 * math.sin(3.0 * phase)
        ))
    return pcm16(samples)


def white_noise(amplitude=5000.0):
    rng = random.Random(12345)
    return pcm16(rng.uniform(-amplitude, amplitude) for _ in range(SAMPLE_RATE))


def impulse_bursts():
    samples = [0] * SAMPLE_RATE
    for burst in range(10):
        start = 1000 + burst * 1500
        for offset in range(8):
            if start + offset < SAMPLE_RATE:
                samples[start + offset] = 30000 if offset % 2 == 0 else -30000
    return pcm16(samples)


def measure(function, iterations):
    timings = []
    for _ in range(iterations):
        started = time.perf_counter()
        function()
        timings.append((time.perf_counter() - started) * 1000.0)
    ordered = sorted(timings)
    return {
        "median_ms": round(statistics.median(ordered), 4),
        "p95_ms": round(ordered[min(len(ordered) - 1, int(0.95 * (len(ordered) - 1)))], 4),
        "max_ms": round(max(ordered), 4),
        "iterations": iterations,
    }


def web_rtc_fractions(pcm):
    try:
        import webrtcvad
    except ImportError:
        return None, None
    frame_bytes = int(SAMPLE_RATE * 0.020) * 2
    result = {"version": getattr(webrtcvad, "__version__", "unknown"), "frame_ms": 20}
    for mode in (0, 2, 3):
        vad = webrtcvad.Vad(mode)
        decisions = [
            vad.is_speech(pcm[offset:offset + frame_bytes], SAMPLE_RATE)
            for offset in range(0, len(pcm) - frame_bytes + 1, frame_bytes)
        ]
        result[f"mode_{mode}_speech_fraction"] = round(
            sum(decisions) / len(decisions), 4
        ) if decisions else 0.0
    return result, None


def benchmark_speaker_tracker(iterations):
    """Measure only the synthetic 192-D/80-ms embedding consumer, not model inference."""
    rng = random.Random(20261121)
    vectors = []
    for _ in range(12):
        vector = [rng.uniform(-1.0, 1.0) for _ in range(192)]
        vectors.append(vector)
    batches = []
    for index in range(iterations):
        start_ms = 1000 + index * 1000
        # Bind each synthetic embedding batch to an actual deterministic PCM16
        # fixture, matching the runtime registry's source-integrity contract.
        pcm = struct.pack(
            "<" + "h" * 16000,
            *(int(4000 * math.sin(2 * math.pi * 220 * sample / 16000 + index * 0.1))
              for sample in range(16000)),
        )
        current_chunk_sha256 = hashlib.sha256(pcm).hexdigest()
        frames = [
            {"end_ms": start_ms + offset * 80, "vector": vectors[offset % len(vectors)]}
            for offset in range(1, 13)
        ]
        batches.append({
            "schema": SCHEMA,
            "source_id": "benchmark:raw-ear",
            "generation_id": "benchmark:generation",
            "consent_receipt_ref": "benchmark:consent-epoch",
            "current_chunk_sha256": current_chunk_sha256,
            "model_id": "synthetic:192d",
            "model_revision": "fixture-v1",
            "model_sha256": "a" * 64,
            "model_license_id": "synthetic-only",
            "model_language": "synthetic",
            "encoder_id": "synthetic",
            "encoder_revision": "fixture-v1",
            "embedding_unit": "FRAME",
            "embedding_dim": 192,
            "frame_step_ms": 80,
            "lookback_frames": 10,
            "confidence_threshold": 0.8,
            "calibration_id": "synthetic-only",
            "frames": frames,
        })
    registry = SpeakerChangeEvidenceRegistry()
    index = 0

    def update():
        nonlocal index
        start_ms = 1000 + index * 1000
        result = registry.update(
            source_id="benchmark:raw-ear",
            generation_id="benchmark:generation",
            consent_receipt_ref="benchmark:consent-epoch",
            start_ms=start_ms,
            end_ms=start_ms + 1000,
            activity_hint="VOICED",
            current_chunk_sha256=batches[index]["current_chunk_sha256"],
            embeddings=batches[index],
        )
        index += 1
        return result

    return measure(update, iterations)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.iterations <= 500:
        parser.error("--iterations must be in 1..500")

    fixtures = {
        "silence": bytes(SAMPLE_RATE * 2),
        "pure_tone": tone(),
        "harmonic_voice_like": harmonic_voice_like(),
        "white_noise": white_noise(),
        "impulse_bursts": impulse_bursts(),
    }
    report = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "sample_rate_hz": SAMPLE_RATE,
        "synthetic_only": True,
        "real_speech_accuracy_claim": False,
        "device_benchmark": False,
        "speaker_embedding_consumer": {"embedding_dim": 192, "frame_step_ms": 80, "lookback_ms": 800, "model_inference_included": False, "synthetic_benchmark": True, "timing": benchmark_speaker_tracker(args.iterations)},
        "results": {},
    }
    try:
        import numpy
        report["numpy_version"] = numpy.__version__
    except ImportError:
        report["numpy_version"] = None
        raise SystemExit("NumPy is required for this opt-in benchmark")

    for name, pcm in fixtures.items():
        python_result = extract_voice_cues(pcm, SAMPLE_RATE, backend="python")
        numpy_result = extract_voice_cues(pcm, SAMPLE_RATE, backend="numpy")
        if python_result != numpy_result:
            raise SystemExit(f"backend parity failure for fixture: {name}")
        tracemalloc.start()
        extract_voice_cues(pcm, SAMPLE_RATE, backend="numpy")
        _, numpy_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        vad, _ = web_rtc_fractions(pcm)
        report["results"][name] = {
            "cues": python_result,
            "python_backend": measure(
                lambda: extract_voice_cues(pcm, SAMPLE_RATE, backend="python"),
                args.iterations,
            ),
            "numpy_backend": measure(
                lambda: extract_voice_cues(pcm, SAMPLE_RATE, backend="numpy"),
                args.iterations,
            ),
            "numpy_tracemalloc_peak_bytes": numpy_peak,
            "webrtc_vad": vad,
            "backend_outputs_equal": True,
        }

    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
