#!/usr/bin/env python3
"""Run392 read-only full-suite resource mode diagnostic; preserves all test verdicts."""
import json
import sys
import unittest

from v13 import config
from v13 import resource_modes as rm


def main():
    print("RUN392_DEFAULT_BEFORE", repr(config.DEFAULTS.get("minimum_free_mb")), flush=True)
    suite = unittest.defaultTestLoader.discover("tests", pattern="test_*.py")
    module = sys.modules.get("test_resource_modes")
    if module is None:
        raise RuntimeError("test_resource_modes not discovered")
    original = module.Wired.test_sleep_halves_replay_in_yellow

    def traced(self):
        guard = self.r.guard
        print("RUN392_DEFAULT_AT_TEST", repr(config.DEFAULTS.get("minimum_free_mb")), flush=True)
        print("RUN392_RUNTIME_CFG", repr(self.r.cfg.get("minimum_free_mb")), repr(self.r.cfg.get("thermal_limit_c")), flush=True)
        print("RUN392_PROFILE", json.dumps(guard.profile, sort_keys=True, default=str), flush=True)
        print("RUN392_CYCLE_RUNTIME_LINK", self.r.sleep.cycle.runtime is self.r, flush=True)
        previous = guard.update

        def trace_update(snapshot):
            state = previous(snapshot)
            print(
                "RUN392_GUARD_UPDATE",
                json.dumps({
                    "mem_available_bytes": snapshot.get("mem_available_bytes"),
                    "battery_temperature_c": snapshot.get("battery_temperature_c"),
                    "state": state,
                    "mode": guard.mode,
                    "reasons": list(guard.reasons),
                    "profile_mem_mb": guard.profile.get("mem_mb"),
                    "classify_direct": rm.classify(snapshot, guard.profile, guard.mode),
                }, sort_keys=True, default=str),
                flush=True,
            )
            return state

        guard.update = trace_update
        try:
            return original(self)
        finally:
            last, _ = self.r.store.state("SLEEP_LAST", None)
            print("RUN392_SLEEP_LAST", json.dumps(last, sort_keys=True, default=str)[:3000], flush=True)

    module.Wired.test_sleep_halves_replay_in_yellow = traced
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    print("RUN392_DEFAULT_AFTER", repr(config.DEFAULTS.get("minimum_free_mb")), flush=True)
    print("RUN392_TOTAL", result.testsRun, "FAIL", len(result.failures), "ERROR", len(result.errors), "SKIP", len(result.skipped), flush=True)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
