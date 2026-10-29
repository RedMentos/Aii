"""Run135 read-only Age/STEP2 software cross-chain; no runtime integration."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from scripts import age_evidence_finite_candidate as finite
from scripts import age_state_quarantine_candidate as quarantine
from scripts import step2_composed_source_repairs_candidate as composed
from scripts import step2_exact_rule_native_replay_preflight as frozen
from scripts import step2_option_quote_consistency_candidate as quotes
from v13 import age
from v13.common import dumps, file_hash
from v13.config import initialize
from v13.store import Store

GOOD = {"experience": 10000, "competence": .95, "stability": .95,
        "retention": .98, "calibration": .9, "memory_health": .97,
        "safe_self_control": .999, "regression_pass": True}


class Run135AgeStep2Crosschain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.cfg = initialize(self.home) | {"user_stage_cap": 5}
        self.store = Store(self.home)
        self.age = age.AgeControl(self.store, self.cfg)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_finite_evidence_then_persisted_state_diagnostic_no_age_promotion(self):
        before = self.age.state()[1]
        for i in range(3):
            finite.record(self.age, "system", GOOD, evidence_id="run135-" + str(i))
        report = quarantine.snapshot(self.age)
        self.assertEqual(report["status"], "VALID_DIAGNOSTIC_ONLY")
        self.assertEqual(report["effective_stage"], 0)
        self.assertFalse(report["runtime_enforced"])
        self.assertGreater(self.age.state()[1], before)
        self.assertEqual(self.age.system_stage(), 0)
        self.assertFalse(self.age.allowed("short_dream"))
        self.assertEqual(quarantine.guarded_view(self.age)["system_stage"], 0)

    def test_invalid_finite_evidence_does_not_mutate_age(self):
        before = self.age.state()
        bad = dict(GOOD, competence=True)
        with self.assertRaisesRegex(ValueError, "AGE_EVIDENCE_COMPETENCE_NOT_FINITE_UNIT"):
            finite.record(self.age, "system", bad, evidence_id="run135-invalid")
        self.assertEqual(self.age.state(), before)
        self.assertEqual(quarantine.snapshot(self.age)["status"], "VALID_DIAGNOSTIC_ONLY")

    def test_corrupt_persisted_state_is_diagnostic_only_no_repair(self):
        state, version = self.age.state()
        state["system"]["maturity"]["trust"] = 2.0
        self.store.set_state(age.STATE_KEY, state, expected=version)
        before = self.age.state()
        report = quarantine.snapshot(self.age)
        self.assertEqual(report["status"], "QUARANTINED_DIAGNOSTIC_ONLY")
        self.assertEqual(report["granted_rights"], [])
        self.assertIsNone(report["budgets"])
        self.assertFalse(report["runtime_enforced"])
        with self.assertRaises(quarantine.AgeStateIntegrityError):
            quarantine.guarded_view(self.age)
        self.assertEqual(self.age.state(), before)
        self.assertEqual(self.age.system_stage(), 0)

    def test_step2_original_replay_does_not_mutate_age_or_promote_gate(self):
        source_path = os.environ.get("V13_RUN116_SOURCE_REPORT")
        tool_path = os.environ.get("V13_RUN116_TOOL_REPORT")
        if not source_path or not tool_path:
            self.skipTest("original frozen native raw not supplied")
        self.assertEqual(file_hash(tool_path), quotes.TOOL_SHA256)
        source = frozen.load_original(Path(source_path))
        tool = json.loads(Path(tool_path).read_text(encoding="utf-8"))
        before_age = self.age.state()
        before_source, before_tool = dumps(source), dumps(tool)
        report = composed.replay(source, tool)
        self.assertEqual(self.age.state(), before_age)
        self.assertEqual((dumps(source), dumps(tool)), (before_source, before_tool))
        self.assertEqual(report["rows"], 42)
        self.assertEqual(report["native_calls"], 0)
        self.assertEqual(report["treatment_wrong_committed"], 0)
        self.assertFalse(report["canonical_gate_pass"])
        self.assertEqual(report["step2_status"], "UTILITY_FAIL")
        self.assertEqual(report["jepa_weight"], 0)
        self.assertEqual(quarantine.snapshot(self.age)["effective_stage"], 0)


if __name__ == "__main__":
    unittest.main()
