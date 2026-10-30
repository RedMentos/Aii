"""Run12N real fresh_turn lifecycle integration with fake native runner.

No model download, no native claim. Exercises real initialize/Store-facing
call contract, isolated home, persisted preclose and postclose evidence.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import c2_body_observer_off_run12n as m
from scripts import c2_body_disjoint_paired181_run11v as frozen
from v13.config import initialize

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/c2_body_observer_off_run12n_20261030.json")


class FakeModels:
    b2_control = "two_body"

    def __init__(self):
        self.installed = {"body": object(), "gist": object()}
        self.saved = False

    def save(self):
        self.saved = True


class FakePool:
    def __init__(self):
        self.release_history = []


class FakeNeedle:
    proc = None


class FakeRuntime:
    instances = []

    def __init__(self, home):
        self.home = Path(home)
        self.models = FakeModels()
        self.pool = FakePool()
        self.needle = FakeNeedle()
        self.store = object()
        self.cfg = {"deadline_seconds": 1.0, "observer_seconds": 1.0}
        self.session = "test-session"
        self.closed = False
        self.submitted = []
        FakeRuntime.instances.append(self)

    def submit(self, text):
        self.submitted.append(text)
        return "test-event"

    def idle(self):
        return True

    def close(self):
        self.closed = True
        self.pool.release_history.append({
            "role": "C3_LANGUAGE", "process_reaped": True})


def fake_audit(store, event_id):
    assert event_id == "test-event"
    return {
        "event_id": event_id, "checks": {"source": True},
        "source_errors": [], "offers": [],
        "output": "Elm leaves 162 Euro. Vale leaves 47 Euro. Vale is sooner.",
        "output_metadata": {
            "model_generated": True,
            "route": {"source": "OPERATOR_ROUTE_OVERRIDE"},
            "c2_packet": {"route": "simple"},
            "runner": {
                "role": "C3_LANGUAGE",
                "actual_model": frozen.LANGUAGE_MODEL,
            },
        },
    }


class Run12NRealLifecycleTests(unittest.TestCase):
    def test_real_temp_home_submit_event_audit_preclose_postclose(self):
        FakeRuntime.instances.clear()
        case = m.load_fixture(FIXTURE)["cases"][0]
        with TemporaryDirectory() as td:
            root = Path(td)
            home = root / "installed"
            cfg = initialize(home)
            (home / "config/models.json").write_text("{}")
            out = root / "result"
            (out / "raw").mkdir(parents=True)
            (out / "preclose").mkdir()
            with patch.object(m, "Runtime", FakeRuntime), patch.object(
                    m, "audit_event", fake_audit):
                row = m.fresh_turn(
                    home, cfg, case, "A_C3_ONLY", 0, out)
            self.assertEqual(len(FakeRuntime.instances), 1)
            runtime = FakeRuntime.instances[0]
            self.assertTrue(runtime.closed)
            self.assertEqual(runtime.submitted, [frozen.prompt(case)])
            self.assertTrue(runtime.models.saved)
            self.assertEqual(row["flags"]["runner_role"], "C3_LANGUAGE")
            self.assertTrue(row["flags"]["valid_native"])
            self.assertEqual(row["flags"]["body_offer_roles"], [])
            self.assertEqual(row["flags"]["observer_mode"], "off")
            self.assertFalse(row["native_c2_process_reaped"])
            pre = json.loads(
                (out / "preclose/00_A_C3_ONLY.json").read_text())
            raw = json.loads(
                (out / "raw/00_A_C3_ONLY.json").read_text())
            self.assertEqual(pre["event_id"], "test-event")
            self.assertEqual(pre["body_process_releases_before_close"], [])
            self.assertEqual(raw["body_process_releases"], [
                {"role": "C3_LANGUAGE", "process_reaped": True}])
            self.assertEqual(raw["release_capture_phase"], "after_close")
            self.assertEqual(raw["raw_audit"]["event_id"], "test-event")
            self.assertEqual(raw["learning_mode"], "RECORD_ONLY")
            self.assertEqual(raw["jepa_weight"], 0)
            self.assertFalse(raw["step2_gate_promoted"])
            self.assertFalse(raw["b3_promoted"])
            self.assertFalse(raw["whole_system_complete"])

    def test_missing_final_release_cannot_validate(self):
        flags = {
            "route": "simple", "runner_role": "C3_LANGUAGE",
            "body_offer_roles": [], "native_c2_invocation": False,
            "route_valid": True, "output_valid": True,
            "source_exact": True,
        }
        with patch.object(frozen, "row_evidence", return_value=flags):
            result = m.zero_offer_witness(
                {}, "A_C3_ONLY", [],
                release_capture_phase="after_close")
        self.assertFalse(result["valid_native"])
        self.assertFalse(result["process_release_valid"])


if __name__ == "__main__":
    unittest.main()
