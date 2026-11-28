"""Conservative, in-memory effective prefill-rate estimator.

The estimate is bound to one LlamaRunner lifecycle stamp and is never persisted.
It measures prompt tokens divided by wall time to first generated token; this is
an operational envelope, not a claim about raw llama.cpp kernel throughput.
"""
from __future__ import annotations

import math


class PrefillRateEstimator:
    REVISION = "v13.native-prefill-rate/1"

    def __init__(self, window_size: int = 5) -> None:
        if type(window_size) is not int or not 1 <= window_size <= 16:
            raise ValueError("window_size must be an integer in 1..16")
        self.window_size = window_size
        self._binding = None
        self._samples: list[float] = []

    def _bind(self, binding) -> bool:
        if binding is None:
            return False
        if self._binding != binding:
            self._binding = binding
            self._samples = []
        return True

    def estimate(self, binding) -> float | None:
        if not self._bind(binding) or not self._samples:
            return None
        # The slowest of the recent successful samples is deliberately used,
        # so one warm/cache-heavy turn cannot inflate the next prompt budget.
        return min(self._samples)

    def sample_count(self, binding) -> int:
        if not self._bind(binding):
            return 0
        return len(self._samples)

    def observe(
        self,
        binding,
        *,
        prompt_tokens,
        prefill_seconds,
        status,
        generated_tokens,
    ) -> bool:
        if status != "FINAL":
            return False
        if type(prompt_tokens) is not int or prompt_tokens <= 0:
            return False
        if type(generated_tokens) is not int or generated_tokens <= 0:
            return False
        if (type(prefill_seconds) not in (int, float)
                or not math.isfinite(prefill_seconds) or prefill_seconds <= 0):
            return False
        rate = prompt_tokens / float(prefill_seconds)
        if not math.isfinite(rate) or rate <= 0:
            return False
        if not self._bind(binding):
            return False
        self._samples.append(min(1000.0, rate))
        if len(self._samples) > self.window_size:
            del self._samples[0]
        return True
