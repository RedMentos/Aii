"""Cross-organ review: Age0 evidence, World-JEPA confidence and trusted-route C_fast.

Real Runtime/Store, synthetic WorldJEPA arrays and a stub C3 output; never
a native-model or learned-utility proof. No new source/age permissions.
"""
import json
from pathlib import Path
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np

from v13.age import AgeControl
from v13.agi import hub
from v13.operator import Operator
from v13.runtime import Runtime
from v13.world_jepa import WorldJEPA


class CrossOrganWorldAgeSkillIntegration(unittest.TestCase):
    def test_store_restart_and_full_c_fast_fallback_preserve_negative_gates(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            r = Runtime(home)
            try:
                Operator(r).run(":observers off")
                age = AgeControl(r.store, r.cfg)
                original = age.state()
                original_telemetry = r.store.rows("SELECT * FROM telemetry")
                with self.assertRaisesRegex(ValueError, "AGE_EVIDENCE"):
                    age.record("system", {"competence": float("nan")}, evidence_id="invalid")
                self.assertEqual(age.state(), original)
                self.assertEqual(r.store.rows("SELECT * FROM telemetry"), original_telemetry)
                result = age.record("system", {"competence": None}, evidence_id="unmeasured")
                self.assertEqual(result["stage"], 0)
                self.assertNotIn("proposal", result)

                # A single learned predictor has no epistemic ensemble spread.
                x = np.zeros((16, 2), dtype=float)
                a = np.eye(2)[np.arange(16) % 2]
                world = WorldJEPA(seed=7, ensemble=1).fit(
                    x, a, x + a, steps=1, log_every=1)
                confidence, labels = world.confidence(x[:2], a[:2])
                np.testing.assert_array_equal(confidence, np.zeros(2))
                self.assertEqual(labels, ["SIMULATION_UNCERTAIN"] * 2)

                # Conflicting TRUSTED skills must not skip the real Runtime
                # route dispatch; C3 itself is stubbed, so this is software.
                lib = hub(r).skills
                lib.propose("age_world_detail", [{"route": "detail"}],
                            trigger="review world age")
                lib.propose("age_world_gist", [{"route": "gist"}],
                            trigger="review world age")
                lib.set_stage("age_world_detail", "TRUSTED")
                lib.set_stage("age_world_gist", "TRUSTED")
                r.pool.get = Mock(return_value=SimpleNamespace(
                    role="C3_LANGUAGE", last_metrics={"test_seam": True},
                    generate=lambda *args, **kwargs: iter(["ok"])))
                r.learner.output_delta = Mock(return_value=None)
                r._route = Mock(return_value=(
                    "simple", {"source": "BOOT_SCAFFOLD"}))
                r.submit("Please review world age")
                deadline = time.monotonic() + 10
                while not r.idle() and time.monotonic() < deadline:
                    time.sleep(.005)
                answer = r.last_answer()
                self.assertIsNotNone(answer)
                meta = json.loads(answer["metadata"])
                self.assertEqual(meta["route"]["source"], "BOOT_SCAFFOLD")
                r._route.assert_called_once()
                self.assertFalse(meta.get("skill", {}).get("automatic", False))
                self.assertEqual(age.system_stage(), 0)
                self.assertFalse(age.allowed("short_dream"))
                self.assertEqual(r.cfg["learning_mode"], "RECORD_ONLY")
                self.assertEqual(r.cfg["jepa_weight"], 0)
            finally:
                r.close()
            r2 = Runtime(home)
            try:
                age2 = AgeControl(r2.store, r2.cfg)
                self.assertEqual(age2.system_stage(), 0)
                self.assertEqual(age2.state()[0]["system"]["evidence_count"], 1)
                self.assertFalse(age2.allowed("short_dream"))
            finally:
                r2.close()


if __name__ == "__main__":
    unittest.main()
