"""Synthetic RAW EAR -> A5 -> B/C SHADOW microbenchmark.

No microphone, private samples, Android permission or model inference.
Run from v13/code: python scripts/bench_audio_shadow_route.py --iterations 1000
Numbers are HOST_ONLY unless executed locally on the actual Redmi.
"""
import argparse
import json
import statistics
import time
import tracemalloc

from v13.audio_percept_contract import audio_percept_packet
from v13.audio_shadow_consumer import audio_shadow_observation

SOURCE_SHA = "a" * 64


def run(iterations):
    if not 1 <= iterations <= 100000:
        raise ValueError("iterations outside 1..100000")
    source = {"sha256": SOURCE_SHA, "revoked": False, "modality": "audio"}
    lookups = 0

    def read_source(source_id):
        nonlocal lookups
        if source_id != "synthetic-source":
            raise PermissionError("unknown synthetic source")
        lookups += 1
        return source

    durations_ns = []
    tracemalloc.start()
    try:
        for i in range(iterations):
            start = time.perf_counter_ns()
            packet = audio_percept_packet(
                event_id=f"synthetic-{i}", generation_id="synthetic-generation",
                source_id="synthetic-source", source_sha256=SOURCE_SHA,
                start_ms=0, end_ms=20, rms=0.2, zcr=0.1,
                consent_receipt="synthetic-only-not-os-consent",
            )
            observation = audio_shadow_observation(packet, read_source)
            elapsed = time.perf_counter_ns() - start
            if observation["authority"] != "SHADOW_ONLY" or observation["learning_authority"]:
                raise AssertionError("unexpected authority")
            if observation["finality"] != "FINAL" or len(observation["windows"]) != 1:
                raise AssertionError("broken audio observation")
            durations_ns.append(elapsed)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    if lookups != iterations:
        raise AssertionError("source was not revalidated on every observation")
    durations_ns.sort()
    return {
        "schema": "v13.synthetic_audio_shadow_benchmark/1",
        "evidence": "SYNTHETIC_HOST_ONLY",
        "android_verified": False,
        "native_audio": False,
        "iterations": iterations,
        "source_rechecks": lookups,
        "median_ms": round(statistics.median(durations_ns) / 1e6, 6),
        "p95_ms": round(durations_ns[min(iterations - 1, (95 * iterations + 99) // 100 - 1)] / 1e6, 6),
        "tracemalloc_peak_bytes": peak,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1000)
    args = parser.parse_args()
    print(json.dumps(run(args.iterations), sort_keys=True))


if __name__ == "__main__":
    main()
