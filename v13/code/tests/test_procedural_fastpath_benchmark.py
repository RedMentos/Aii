"""Benchmark must report measured, reproducible, non-model evidence honestly."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.benchmark_procedural_fastpath import run_benchmark, run_values_benchmark


def test_host_synthetic_benchmark_correct_rows_and_snapshot_sha():
    report = run_benchmark(rows=2500, batch_rows=128, chunk_bytes=7)
    assert report["fixture"]["rows"] == 2500
    assert report["fixture"]["model_calls"] == 0
    assert report["stream"]["verified_same_sha256"] is True
    assert report["writer"]["calls"] >= 20
    assert report["writer"]["rows_per_second"] > 0
    assert report["stream"]["bytes_per_second"] > 0
    assert report["stream"]["max_chunk_bytes"] <= 10
    assert report["environment"]["is_redmi_measurement"] is False
    assert "NOT LLM tokens/sec" in report["claim_limit"]


@pytest.mark.parametrize("kwargs", [
    {"rows": 0}, {"rows": True}, {"rows": 1000001},
    {"batch_rows": 0}, {"batch_rows": False}, {"batch_rows": -1},
    {"chunk_bytes": 3}, {"chunk_bytes": 65537},
    {"max_seconds_per_call": 0},
])
def test_benchmark_rejects_unbounded_inputs(kwargs):
    with pytest.raises(ValueError):
        run_benchmark(**kwargs)


def test_cli_optional_report_is_persisted_without_leaking_path(tmp_path):
    out = tmp_path / "bench.json"
    script = Path(__file__).resolve().parents[1] / "scripts" / "benchmark_procedural_fastpath.py"
    result = subprocess.run(
        [sys.executable, str(script), "--rows", "512",
         "--batch-rows", "128", "--report", str(out)],
        capture_output=True, text=True, check=True,
        cwd=str(script.parents[1])
    )
    a = json.loads(result.stdout)
    b = json.loads(out.read_text(encoding="utf-8"))
    assert a == b
    assert b["fixture"]["rows"] == 512
    assert "PRIVATE" not in json.dumps(b)
    assert out.stat().st_mode & 0o077 == 0
    # A second run must fail closed rather than destroy a previous report.
    second = subprocess.run(
        [sys.executable, str(script), "--rows", "128", "--report", str(out)],
        capture_output=True, text=True, cwd=str(script.parents[1])
    )
    assert second.returncode != 0
    assert json.loads(out.read_text())["fixture"]["rows"] == 512



def test_distinct_value_benchmark_is_not_a_constant_repeat():
    proof = run_values_benchmark(rows=3000, batch_rows=256, chunk_bytes=11)
    assert proof["fixture"]["kind"] == "SYNTHETIC_IMPORTED_VALUES"
    assert proof["fixture"]["rows"] == 3000
    assert proof["fixture"]["model_calls"] == 0
    assert len(proof["fixture"]["input_sha256"]) == 64
    assert proof["stream"]["verified_same_sha256"] is True
    assert proof["writer"]["rows_per_second"] > 0
    assert proof["environment"]["is_redmi_measurement"] is False
    assert "NOT general reasoning" in proof["claim_limit"]


def test_distinct_value_benchmark_rejects_invalid_limits():
    for kwargs in ({"rows": 0}, {"rows": True}, {"rows": 1000001},
                   {"batch_rows": -1}, {"chunk_bytes": 0}):
        with pytest.raises(ValueError):
            run_values_benchmark(**kwargs)
