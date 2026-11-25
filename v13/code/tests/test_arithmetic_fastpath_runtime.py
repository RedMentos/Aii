import json
from pathlib import Path
import tempfile
import time
from unittest.mock import Mock

from v13.runtime import Runtime


def test_runtime_answers_exact_text_arithmetic_without_native_body_calls():
    with tempfile.TemporaryDirectory() as tmp:
        runtime = Runtime(Path(tmp))
        try:
            runtime.sleep.cycle.set_policy("enabled", "off")
            runtime.resources = lambda: {
                "wall_time": time.time(),
                "mem_available_bytes": 8 * 1024**3,
                "mem_total_bytes": 8 * 1024**3,
                "free_disk_bytes": 20 * 1024**3,
                "battery_temperature_c": 25.0,
                "battery_percent": 80.0,
                "charging": True,
                "processes": [],
                "own_peak_rss_bytes": 0,
            }
            runtime.guard.update(runtime.resources())
            runtime.pool.get = Mock(side_effect=AssertionError("C3 must not run for exact 2+2"))
            runtime.cognition.offer = Mock(side_effect=AssertionError("B1/B2 must not run for exact 2+2"))
            runtime.submit("2+2")
            until = time.monotonic() + 8
            while not runtime.idle() and time.monotonic() < until:
                time.sleep(0.005)
            assert runtime.idle()
            row = runtime.last_answer()
            assert row is not None
            assert row["status"] == "FINAL"
            assert row["text"].strip() == "4"
            meta = json.loads(row["metadata"])
            assert meta["arithmetic_fastpath"]["result"] == "4"
            assert meta["arithmetic_fastpath"]["native_models_invoked"] is False
            assert meta["output_policy"]["rule_id"] == "BUILTIN_ARITHMETIC_EXACT_V1"
            assert meta["output_authority"] == "APPROVED_FIXED_RULE"
            assert "B_OBSERVERS" in meta["skipped_native_stages"]
            assert "C3_DECODE" in meta["skipped_native_stages"]
            runtime.pool.get.assert_not_called()
            runtime.cognition.offer.assert_not_called()
        finally:
            runtime.close()
