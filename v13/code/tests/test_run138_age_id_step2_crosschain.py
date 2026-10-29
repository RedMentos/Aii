"""Run138: exact donor Age evidence-ID guard coexists with frozen STEP2 replay."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from scripts import age_evidence_id_preflight_candidate as guard
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


class Run138AgeIdStep2Crosschain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.cfg = initialize(self.home) | {"user_stage_cap": 5}
        self.store = Store(self.home)
        self.controller = age.AgeControl(self.store, self.cfg)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_bad_id_then_valid_id_leave_frozen_step2_replay_identical(self):
        source_path = os.environ.get("V13_RUN116_SOURCE_REPORT")
        tool_path = os.environ.get("V13_RUN116_TOOL_REPORT")
        if not source_path or not tool_path:
            self.skipTest("original frozen Run116 native raw not supplied")
        self.assertEqual(file_hash(tool_path), quotes.TOOL_SHA256)
        source = frozen.load_original(Path(source_path))
        tool = json.loads(Path(tool_path).read_text(encoding="utf-8"))
        before_source, before_tool = dumps(source), dumps(tool)
        before_age = self.controller.state()
        before_telemetry = len(self.store.rows("SELECT * FROM telemetry"))
        with self.assertRaisesRegex(ValueError, "AGE_EVIDENCE_ID_INVALID"):
            guard.record(self.controller, "system", GOOD, evidence_id=True)
        self.assertEqual(self.controller.state(), before_age)
        self.assertEqual(len(self.store.rows("SELECT * FROM telemetry")),
                         before_telemetry)
        self.assertEqual(quarantine.snapshot(self.controller)["status"],
                         "VALID_DIAGNOSTIC_ONLY")
        before_replay = composed.replay(source, tool)
        self.assertEqual(self.controller.state(), before_age)
        guard.record(self.controller, "system", GOOD, evidence_id="run138-valid")
        after_record = self.controller.state()
        self.assertGreater(after_record[1], before_age[1])
        after_replay = composed.replay(source, tool)
        self.assertEqual(self.controller.state(), after_record)
        self.assertEqual(dumps(before_replay), dumps(after_replay))
        self.assertEqual((dumps(source), dumps(tool)), (before_source, before_tool))
        self.assertEqual(after_replay["rows"], 42)
        self.assertEqual(after_replay["native_calls"], 0)
        self.assertEqual(after_replay["treatment_wrong_committed"], 0)
        self.assertFalse(after_replay["canonical_gate_pass"])
        self.assertEqual(after_replay["step2_status"], "UTILITY_FAIL")
        self.assertEqual(after_replay["jepa_weight"], 0)
        self.assertEqual(quarantine.snapshot(self.controller)["effective_stage"], 0)
        self.assertFalse(self.controller.allowed("short_dream"))

    def test_invalid_id_and_metric_combination_still_never_writes(self):
        before = self.controller.state()
        with self.assertRaisesRegex(ValueError, "AGE_EVIDENCE_ID_INVALID"):
            guard.record(self.controller, "system",
                         dict(GOOD, competence=float("inf")), evidence_id=True)
        self.assertEqual(self.controller.state(), before)
        self.assertEqual(quarantine.snapshot(self.controller)["status"],
                         "VALID_DIAGNOSTIC_ONLY")


if __name__ == "__main__":
    unittest.main()
