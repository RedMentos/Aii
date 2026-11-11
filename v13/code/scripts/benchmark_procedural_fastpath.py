#!/usr/bin/env python3
"""Bounded zero-LLM V13 fast-procedure throughput proof for Linux or Termux.

Run from v13/code:
    python scripts/benchmark_procedural_fastpath.py --rows 100000

Produces only a synthetic numbered text fixture in a disposable private home.
Measures writer+checkpoint overhead and single-check streamed readback.
DOES NOT measure model tokens/sec, native GGUF inference or learning quality.
No network, no model downloads, no changes to the user's main V13 Store.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import resource
import tempfile
import time

# Allow the documented `python scripts/benchmark_procedural_fastpath.py`
# from a clean Termux checkout without assuming an external PYTHONPATH.
if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from v13.procedural_batch import (
    MAX_OUTPUT_BYTES, MAX_ROWS, ProceduralBatch,
)

REVISION = "v13-procedural-fastpath-benchmark-v1"
SYNTHETIC_TEMPLATE = "task {i}: fixed local sample"


def _peak_rss_bytes():
    # Linux/Android ru_maxrss is KiB; this is process RSS peak, not PSS and
    # cannot establish thermal/battery fitness on a phone by itself.
    if platform.system() != "Linux":
        return None
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def run_benchmark(rows=100000, batch_rows=32768, chunk_bytes=65536,
                  max_seconds_per_call=12.0):
    if type(rows) is not int or not 1 <= rows <= MAX_ROWS:
        raise ValueError("rows must be 1..1000000")
    if type(batch_rows) is not int or not 1 <= batch_rows <= MAX_ROWS:
        raise ValueError("batch rows must be 1..1000000")
    if type(chunk_bytes) is not int or not 4 <= chunk_bytes <= 65536:
        raise ValueError("chunk bytes must be 4..65536")
    if (type(max_seconds_per_call) not in (int, float)
            or not 0 < max_seconds_per_call <= 120):
        raise ValueError("seconds per call must be in (0,120]")
    with tempfile.TemporaryDirectory(prefix="v13-fastbench-") as folder:
        home = Path(folder)
        runner = ProceduralBatch(home)
        proposal = runner.propose("benchmark", SYNTHETIC_TEMPLATE)
        runner.activate("benchmark", proposal["sha256"])
        start = time.monotonic()
        calls = 0
        while True:
            # Each call can run at most one bounded slice, always publishing
            # a complete hash-bound checkpoint (or recovering after a stop).
            result = runner.run("benchmark", rows, max_rows=batch_rows,
                                max_seconds=max_seconds_per_call)
            calls += 1
            if result["status"] == "DONE":
                break
            if calls > rows + 2:
                raise RuntimeError("benchmark did not make progress")
            if not result["rows_this_call"]:
                raise RuntimeError("benchmark stalled without progress")
        write_elapsed = max(time.monotonic() - start, 1e-9)
        started_stream = time.monotonic()
        digest = hashlib.sha256()
        consumed_bytes = 0
        consumed_rows = 0
        chunks = 0
        max_chunk_bytes = 0
        for text in runner.iter_output("benchmark", rows,
                                       chunk_bytes=chunk_bytes):
            data = text.encode("utf-8")
            chunks += 1
            consumed_bytes += len(data)
            consumed_rows += text.count("\n")
            max_chunk_bytes = max(max_chunk_bytes, len(data))
            digest.update(data)
        read_elapsed = max(time.monotonic() - started_stream, 1e-9)
        if (result["model_calls"] != 0
                or consumed_rows != rows
                or consumed_bytes != result["bytes"]
                or consumed_bytes > MAX_OUTPUT_BYTES
                or digest.hexdigest() != result["sha256"]):
            raise ValueError("benchmark replay output did not match checkpoint")
        return {
            "revision": REVISION,
            "evidence_level": "LOCAL_HOST_SYNTHETIC_PYTHON",
            "environment": {
                "system": platform.system(),
                "machine": platform.machine(),
                "python": platform.python_version(),
                "cpu_count": os.cpu_count(),
                "peak_process_rss_bytes": _peak_rss_bytes(),
                "is_redmi_measurement": False,
            },
            "fixture": {
                "kind": "SYNTHETIC_PURE_TEXT_REPEAT",
                "template_sha256": hashlib.sha256(
                    SYNTHETIC_TEMPLATE.encode("utf-8")).hexdigest(),
                "rows": rows, "bytes": consumed_bytes,
                "sha256": result["sha256"], "model_calls": 0,
            },
            "writer": {
                "elapsed_seconds": round(write_elapsed, 6),
                "calls": calls, "batch_rows": batch_rows,
                "rows_per_second": round(rows / write_elapsed, 1),
                "bytes_per_second": round(consumed_bytes / write_elapsed, 1),
            },
            "stream": {
                "elapsed_seconds": round(read_elapsed, 6),
                "chunks": chunks, "max_chunk_bytes": max_chunk_bytes,
                "requested_chunk_bytes": chunk_bytes,
                "bytes_per_second": round(consumed_bytes / read_elapsed, 1),
                "verified_same_sha256": True,
            },
            "claim_limit": (
                "These are host rows/bytes per second for precompiled synthetic "
                "text, NOT LLM tokens/sec, pretrained-model learning, native "
                "inference or Android battery/thermal data."
            ),
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=100000)
    parser.add_argument("--batch-rows", type=int, default=32768)
    parser.add_argument("--chunk-bytes", type=int, default=65536)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args(argv)
    report = run_benchmark(rows=args.rows, batch_rows=args.batch_rows,
                           chunk_bytes=args.chunk_bytes)
    data = (json.dumps(report, sort_keys=True, ensure_ascii=False,
                       indent=2) + "\n").encode("utf-8")
    if args.report is not None:
        parent = args.report.parent
        if parent.is_symlink() or not parent.is_dir() or args.report.is_symlink():
            raise ValueError("report destination must be an existing safe folder")
        # A user-selected report is never overwritten, even on a repeated run.
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(args.report, flags, 0o600)
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
    print(data.decode("utf-8"), end="")


if __name__ == "__main__":
    main()
