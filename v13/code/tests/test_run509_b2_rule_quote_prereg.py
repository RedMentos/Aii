"""Run509 fresh quote-focus prereg: source-only, no native or model calls."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run491_step2_heldout10 as old
import run509_b2_rule_quote_prereg as new


class FreshQuotePrereg(unittest.TestCase):
    def test_fresh_ten_episode_roles_and_original_oracles(self):
        rows = new.fixtures()
        self.assertEqual(len(rows), 10)
        self.assertEqual([f["type"] for f in rows],
                         ["SPLIT"] * 6 + ["RULE"] * 2 + ["DETAIL"] * 2)
        self.assertEqual(tuple(f["oracle"]["action"] for f in rows),
                         new.EXPECTED_ACTIONS)
        self.assertFalse({f["id"] for f in rows} & {s[0] for s in old.SPECS})
        self.assertEqual(new.digest(rows), new.digest(new.fixtures()))

    def test_focus_is_value_free_and_role_scoped(self):
        packet = new.focus_packet()
        self.assertEqual(packet["target_role"], "B2_GIST")
        self.assertEqual(packet["kind"], "FILL_GAP")
        self.assertEqual(packet["authority"], "EXECUTIVE_QUESTION_NOT_FACT")
        self.assertNotIn("Arbor", packet["question"])
        self.assertNotIn("117", packet["question"])
        self.assertNotIn("Option A:", packet["question"])
        self.assertIn("Do not infer values", packet["question"])
        self.assertNotIn("A", packet["reason"])

    def test_frozen_seed_scope_and_all_negative_gates(self):
        x = new.registration()
        self.assertEqual(x["seeds"], [41, 42, 43])
        self.assertEqual(x["arms"], ["BASE", "RULE_FOCUS"])
        self.assertEqual(x["planned_b2_offer_observations"], 60)
        self.assertTrue(x["fixture_hash_frozen"])
        self.assertEqual(x["fixture_sha256"], new.EXPECTED_FIXTURE_SHA256)
        self.assertEqual(x["status"], "SOURCE_ONLY_FROZEN_NO_NATIVE")
        self.assertEqual(x["model_sha256_expected_not_retrieved"],
                         old.MODEL_SHA256)
        self.assertEqual(x["runner_sha256_expected_not_retrieved"],
                         old.RUNNER_SHA256)
        for key, value in (("native_executed", False),
                           ("canonical_gate_pass", False),
                           ("step2_exit", "UTILITY_FAIL"),
                           ("b3_l1", "FAIL"),
                           ("body_jepa", "UNAVAILABLE"),
                           ("jepa_weight", 0),
                           ("redmi_measured", False)):
            self.assertEqual(x[key], value)

    def test_bad_oracle_and_id_collision_rejected(self):
        specs = list(new.SPECS)
        specs[0] = ("Vesper", *specs[0][1:])
        with patch.object(new, "SPECS", tuple(specs)):
            with self.assertRaisesRegex(ValueError, "FRESH_FIXTURE_ID_COLLISION"):
                new.fixtures()
        specs = list(new.SPECS)
        specs[0] = (specs[0][0], specs[0][1], specs[0][2],
                    (200, 4, True), specs[0][4])
        with patch.object(new, "SPECS", tuple(specs)):
            with self.assertRaisesRegex(ValueError, "FRESH_ORACLE_ACTION_DRIFT"):
                new.fixtures()

    def test_same_action_but_changed_fixture_fails_frozen_sha(self):
        specs = list(new.SPECS)
        name, kind, rules, a, b = specs[0]
        specs[0] = (name, kind, (rules[0] + 1, rules[1], rules[2]), a, b)
        with patch.object(new, "SPECS", tuple(specs)):
            with self.assertRaisesRegex(ValueError, "FRESH_FIXTURE_HASH_DRIFT"):
                new.fixtures()

    def test_source_only_cli_exclusive_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "registration.json"
            cmd = [sys.executable, str(ROOT / "scripts" /
                   "run509_b2_rule_quote_prereg.py"), "--output", str(output)]
            first = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            self.assertEqual(first.returncode, 0, first.stderr)
            data = json.loads(output.read_text())
            self.assertEqual(data["fixture_sha256"], new.digest(new.fixtures()))
            self.assertFalse(data["native_executed"])
            again = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            self.assertNotEqual(again.returncode, 0)
            self.assertIn("FileExistsError", again.stderr)
            native = subprocess.run(cmd + ["--execute"], capture_output=True,
                                    text=True, timeout=60)
            self.assertNotEqual(native.returncode, 0)
            self.assertIn("unrecognized arguments", native.stderr)


if __name__ == "__main__":
    unittest.main()
