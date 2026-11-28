"""Measured prefill-rate adaptation bound to one native runner lifecycle.

This tests the estimator and Runtime wiring without claiming a real GGUF or
Redmi benchmark. The rate is an effective prompt-token / time-to-first-token
measurement, not a kernel throughput assertion.
"""
import json
import math
import threading
import time

from v13.native_prefill_rate import PrefillRateEstimator
from v13.runners import LlamaRunner


def _runner(binding=("model-a", "threads=4", "batch=128")):
    runner = LlamaRunner.__new__(LlamaRunner)
    runner._prefill_rate_estimator = PrefillRateEstimator()
    runner._lifecycle_stamp = lambda: binding
    runner.last_metrics = {
        "prompt_tokens": 100,
        "generated_tokens": 10,
        "stage_durations_s": {"prefill_to_first_token_s": 2.0},
    }
    return runner


def test_estimator_uses_slowest_recent_success_and_bounded_window():
    estimator = PrefillRateEstimator(window_size=3)
    binding = ("model", "threads=4", "batch=128")
    for tokens, seconds in ((100, 2.0), (40, 2.0), (70, 2.0)):
        assert estimator.observe(binding, prompt_tokens=tokens,
                                 prefill_seconds=seconds, status="FINAL",
                                 generated_tokens=4)
    assert estimator.estimate(binding) == 20.0
    assert estimator.observe(binding, prompt_tokens=90, prefill_seconds=2.0,
                             status="FINAL", generated_tokens=4)
    assert estimator.estimate(binding) == 20.0
    assert estimator.observe(binding, prompt_tokens=80, prefill_seconds=2.0,
                             status="FINAL", generated_tokens=4)
    assert estimator.sample_count(binding) == 3
    assert estimator.estimate(binding) == 35.0


def test_estimator_rejects_deadline_empty_output_and_invalid_measurements():
    estimator = PrefillRateEstimator()
    binding = ("model", "threads=2", "batch=128")
    invalid = [
        ("DEADLINE", 100, 2.0, 5),
        ("FINAL", 100, 2.0, 0),
        ("FINAL", True, 2.0, 5),
        ("FINAL", 100, math.nan, 5),
        ("FINAL", 100, 0.0, 5),
    ]
    for status, tokens, seconds, generated in invalid:
        assert not estimator.observe(
            binding, prompt_tokens=tokens, prefill_seconds=seconds,
            status=status, generated_tokens=generated)
    assert estimator.estimate(binding) is None


def test_estimator_invalidates_samples_when_model_or_resource_binding_changes():
    estimator = PrefillRateEstimator()
    old = ("model-a", "threads=4", "batch=128")
    new = ("model-b", "threads=4", "batch=128")
    assert estimator.observe(old, prompt_tokens=200, prefill_seconds=2.0,
                             status="FINAL", generated_tokens=5)
    assert estimator.estimate(old) == 100.0
    assert estimator.estimate(new) is None
    assert estimator.sample_count(new) == 0


def test_runner_records_only_successful_effective_prefill_and_exports_aggregate():
    runner = _runner()
    assert runner._prefill_rate_estimate() is None
    runner._record_prefill_rate("FINAL")
    assert runner._prefill_rate_estimate() == 50.0
    assert runner.last_metrics["prefill_rate"] == {
        "revision": "v13.native-prefill-rate/1",
        "source": "MEASURED_CONSERVATIVE_MIN",
        "effective_tokens_per_second": 50.0,
        "sample_count": 1,
        "sample_added": True,
    }
    assert "model-a" not in json.dumps(runner.last_metrics["prefill_rate"])


def test_runner_does_not_learn_rate_from_deadline_or_zero_output():
    runner = _runner()
    runner._record_prefill_rate("DEADLINE")
    assert runner._prefill_rate_estimate() is None
    runner.last_metrics["generated_tokens"] = 0
    runner._prefill_rate_estimate()
    runner._record_prefill_rate("FINAL")
    assert runner._prefill_rate_estimate() is None


def test_runner_does_not_record_a_sample_if_lifecycle_changes_mid_turn():
    runner = _runner()
    assert runner._prefill_rate_estimate() is None
    runner._lifecycle_stamp = lambda: ("model-b", "threads=4", "batch=128")
    runner._record_prefill_rate("FINAL")
    assert runner._prefill_rate_estimate() is None


def test_runner_uses_measured_rate_in_the_actual_prompt_admission_path():
    runner = _runner()
    runner.role = "B1_DETAIL"
    runner.cfg = {"context_tokens": 2048}
    binding = runner._lifecycle_stamp()
    assert runner._prefill_rate_estimator.observe(
        binding, prompt_tokens=100, prefill_seconds=2.0,
        status="FINAL", generated_tokens=8)

    def request(method, path, payload, deadline):
        if path == "/apply-template":
            return {"prompt": "system: fixed rules\\nuser: exact source"}
        if path == "/tokenize":
            return {"tokens": list(range(50))}
        raise AssertionError("unexpected native request in admission test")

    runner._json = request
    messages = [
        {"role": "system", "content": "Internal B1 instructions."},
        {"role": "user", "content": json.dumps({
            "source_segments": [{"text": "Exact source"}],
        })},
    ]
    _, token_count, _ = runner._prompt(
        messages, threading.Event(), time.monotonic() + 12.0, 32)
    assert token_count == 50
    assert 80 <= runner._prompt_admission["target_tokens"] <= 83
    assert runner._prompt_admission["prefill_rate_source"] == "MEASURED_CONSERVATIVE_MIN"
    assert runner._prompt_admission["effective_prefill_tokens_per_second"] == 50.0
    assert runner._prompt_admission["source_text_rewritten"] is False
