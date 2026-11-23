"""Offline candidate probes with owned tiny processes, never native models."""
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from types import ModuleType, SimpleNamespace
import unittest

from v13.common import Cancelled, Limits
from v13.runners import check, kill_process


CODE = Path(__file__).resolve().parents[1]


def builder():
    path = CODE / "scripts/termux_probe_recovery_candidate_20261112.py"
    spec = importlib.util.spec_from_file_location("probe_recovery_builder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def candidate():
    data = builder().build_sources(CODE)["v13/verification.py"]
    module = ModuleType("v13._probe_recovery_test")
    module.__package__ = "v13"
    module.__file__ = str(CODE / "v13/verification.py")
    exec(compile(data, module.__file__, "exec"), module.__dict__)
    return module


class FakeStore:
    def __init__(self):
        self.metadata = {"last_session": "original-persisted-chat"}

    def meta(self, key):
        return self.metadata.get(key)

    def set_meta(self, key, value):
        self.metadata[key] = value

    def new_session(self, title):
        self.metadata["last_session"] = "probe-chat"
        return "probe-chat"

    def event(self, session, text):
        return {"event_id": "synthetic-probe-event"}


class FakeRunner:
    def __init__(self, role, mode, cancel):
        self.role, self.mode, self.cancel = role, mode, cancel
        self.proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"])
        self.last_metrics = {}

    def generate(self, messages, cancel, deadline, tokens):
        # Deliberately reuse the same dict to expose accidental phase aliases.
        self.last_metrics.clear()
        self.last_metrics.update(status="ERROR", last_phase="prefill", requested_tokens=tokens,
                                 generated_tokens=0, stage_durations_s={"load_s": 0.0})
        check(cancel, deadline)
        if self.role == "B1_DETAIL" and self.mode == "native_fail" and tokens == 48:
            raise Limits("synthetic native deadline")
        if self.role == "B1_DETAIL" and tokens != 48:
            if self.mode == "offer_cancel":
                cancel.set()
                self.last_metrics["status"] = "CANCELLED"
                check(cancel, deadline)
            if self.mode == "offer_fail":
                self.last_metrics["generated_tokens"] = 7
                self.last_metrics["status"] = "DEADLINE"
                while True:
                    check(cancel, deadline)
                    time.sleep(.002)
        self.last_metrics.update(status="FINAL", last_phase="stream", generated_tokens=3)
        yield "synthetic hello" if tokens == 48 else "{}"


class FakePool:
    def __init__(self, mode, cancel):
        self.mode, self.cancel = mode, cancel
        self.current = None
        self.runners = []

    def get(self, role):
        if self.current is None or self.current.role != role:
            self.current = FakeRunner(role, self.mode, self.cancel)
            self.runners.append(self.current)
        return self.current

    def unload(self):
        if self.current is not None:
            kill_process(self.current.proc)
        self.current = None
        return {"process_reaped": True}


class ProbeRecoveryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.home = Path(directory.name)
        (self.home / "exports").mkdir()
        self.module = candidate()

    def runtime(self, mode="success"):
        cancel = threading.Event()
        pool = FakePool(mode, cancel)
        self.addCleanup(pool.unload)
        runtime = SimpleNamespace(
            home=self.home, session="original-selected-chat", store=FakeStore(), pool=pool,
            cancel_event=cancel, cfg={"deadline_seconds": .15, "observer_seconds": .025,
                                      "observer_tokens": 160},
            revisions=lambda: {role: "synthetic-revision" for role in
                               ("C3_LANGUAGE", "B1_DETAIL", "B2_GIST", "C2_CONTROL")},
        )

        def offer(role, event, version, deadline):
            runner = pool.get(role)
            "".join(runner.generate([], cancel, deadline, runtime.cfg["observer_tokens"]))
            return {"evidence_refs": [], "rejected_quotes": 0,
                    "offer": {"summary": "synthetic", "quotes": []}}

        runtime.cognition = SimpleNamespace(percept=lambda event: None, offer=offer)

        def embed(*args):
            check(cancel, time.monotonic() + 1)
            return [1.0]

        runtime.needle = SimpleNamespace(embed=embed, control=lambda *args: {},
                                         last_metrics={}, unload=lambda: None)
        return runtime

    def assert_clean(self, runtime):
        self.assertEqual(runtime.session, "original-selected-chat")
        self.assertEqual(runtime.store.meta("last_session"), "original-persisted-chat")
        self.assertTrue(all(runner.proc.poll() is not None for runner in runtime.pool.runners))
        self.assertIsNone(runtime.pool.current)

    def test_builder_is_pinned_and_does_not_modify_frozen_source(self):
        module = builder()
        source = CODE / "v13/verification.py"
        before = source.read_bytes()
        replacement = module.build_sources(CODE)
        self.assertEqual(set(replacement), {"v13/verification.py"})
        self.assertNotEqual(replacement["v13/verification.py"], before)
        self.assertEqual(hashlib.sha256(before).hexdigest(), module.PINS["v13/verification.py"])
        self.assertEqual(source.read_bytes(), before)

    def test_builder_rejects_changed_source(self):
        code = self.home / "altered-code"
        (code / "v13").mkdir(parents=True)
        (code / "v13/verification.py").write_bytes((CODE / "v13/verification.py").read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "probe recovery source changed"):
            builder().build_sources(code)

    def test_offer_deadline_retains_successful_native_smoke_and_failure_metrics(self):
        runtime = self.runtime("offer_fail")
        result = self.module.probe(runtime)
        role = result["roles"]["B1_DETAIL"]
        self.assertFalse(role["ok"])
        self.assertEqual(role["phase"], "STRUCTURED_OFFER")
        self.assertEqual(role["actual_output"], "synthetic hello")
        self.assertEqual(role["metrics"]["status"], "FINAL")
        smoke = role["phases"]["NATIVE_SMOKE"]
        offer = role["phases"]["STRUCTURED_OFFER"]
        self.assertTrue(smoke["ok"])
        self.assertEqual(smoke["budget_seconds"], .15)
        self.assertEqual(smoke["requested_tokens"], 48)
        self.assertEqual(smoke["metrics"]["requested_tokens"], 48)
        self.assertFalse(offer["ok"])
        self.assertEqual(offer["error_type"], "Limits")
        self.assertEqual(offer["budget_seconds"], .025)
        self.assertEqual(offer["metrics"]["status"], "DEADLINE")
        self.assertEqual(offer["metrics"]["last_phase"], "prefill")
        self.assertEqual(offer["metrics"]["generated_tokens"], 7)
        self.assertGreaterEqual(offer["duration_s"], .025)
        self.assertGreaterEqual(role["duration_s"], offer["duration_s"])
        self.assertEqual(result["status"], "SMOKE_PARTIAL")
        self.assertFalse(result["full_runner_proof"])
        self.assert_clean(runtime)

    def test_native_failure_is_distinct_and_does_not_claim_an_offer(self):
        runtime = self.runtime("native_fail")
        result = self.module.probe(runtime)
        role = result["roles"]["B1_DETAIL"]
        self.assertFalse(role["ok"])
        self.assertEqual(role["phase"], "NATIVE_SMOKE")
        self.assertEqual(role["error_type"], "Limits")
        self.assertEqual(set(role["phases"]), {"NATIVE_SMOKE"})
        self.assertFalse(role["phases"]["NATIVE_SMOKE"]["ok"])
        self.assertNotIn("actual_output", role)
        self.assertNotIn("structured_offer", role)
        self.assert_clean(runtime)

    def test_success_keeps_both_phases_and_independent_metrics(self):
        runtime = self.runtime()
        result = self.module.probe(runtime)
        self.assertEqual(result["status"], "SMOKE_PASS")
        role = result["roles"]["B1_DETAIL"]
        self.assertTrue(role["ok"])
        self.assertEqual(role["phase"], "COMPLETE")
        self.assertTrue(all(phase["ok"] for phase in role["phases"].values()))
        self.assertEqual(role["phases"]["NATIVE_SMOKE"]["metrics"]["requested_tokens"], 48)
        self.assertEqual(role["phases"]["STRUCTURED_OFFER"]["metrics"]["requested_tokens"], 160)
        self.assertEqual(role["metrics"]["requested_tokens"], 48)
        self.assertIn("structured_offer", role)
        self.assertEqual(set(result["roles"]["C3_LANGUAGE"]["phases"]), {"NATIVE_SMOKE"})
        self.assertFalse(result["full_runner_proof"])
        self.assert_clean(runtime)

    def test_cancellation_records_failed_offer_and_reaps_owned_processes(self):
        runtime = self.runtime("offer_cancel")
        result = self.module.probe(runtime)
        role = result["roles"]["B1_DETAIL"]
        self.assertEqual(role["phase"], "STRUCTURED_OFFER")
        self.assertFalse(role["ok"])
        self.assertEqual(role["error_type"], "Cancelled")
        self.assertEqual(role["phases"]["STRUCTURED_OFFER"]["metrics"]["status"], "CANCELLED")
        self.assertTrue(role["phases"]["NATIVE_SMOKE"]["ok"])
        self.assertEqual(result["status"], "SMOKE_PARTIAL")
        self.assert_clean(runtime)

    def test_unexpected_perception_failure_restores_session(self):
        runtime = self.runtime()

        def fail(event):
            raise RuntimeError("synthetic perception failure")

        runtime.cognition.percept = fail
        with self.assertRaisesRegex(RuntimeError, "synthetic perception failure"):
            self.module.probe(runtime)
        self.assert_clean(runtime)

    def test_missing_or_unsnapshotable_metrics_are_unavailable(self):
        class Unsnapshotable:
            def __deepcopy__(self, memo):
                raise RuntimeError("synthetic unsupported metric")

        self.assertEqual(self.module._probe_metrics_snapshot(None), {})
        self.assertEqual(self.module._probe_metrics_snapshot(SimpleNamespace(last_metrics=[])), {})
        self.assertEqual(self.module._probe_metrics_snapshot(
            SimpleNamespace(last_metrics={"unsupported": Unsnapshotable()})), {})


if __name__ == "__main__":
    unittest.main()
