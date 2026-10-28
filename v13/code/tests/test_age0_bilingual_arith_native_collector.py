"""No-model software guards for the serial heldout native collector candidate."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts import age0_bilingual_arith_native_collector as C
from scripts import age0_bilingual_arith_scorer as S


class CollectorGuards(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        (self.home / "config").mkdir(parents=True)
        self.settings = {
            "learning_mode": "RECORD_ONLY", "system_stage": 0,
            "jepa_weight": 0, "latents_enabled": False, "b2_control": "two_body"
        }
        self.save_settings()

    def tearDown(self):
        self.tmp.cleanup()

    def save_settings(self):
        (self.home / "config/settings.json").write_text(json.dumps(self.settings))

    def test_persisted_final_metadata_is_not_synthesized(self):
        item = S.fixture()[0]
        meta = {"runner": {"role": "B1_DETAIL"}, "tool_call": None,
                "tool_shadow": {"tool": "calc", "reason": "AGE0"}}
        message = {"text": "37 Euro", "status": "FINAL", "metadata": json.dumps(meta)}
        row = C.row_from_message(item, message)
        self.assertEqual(row["runner_role"], "B1_DETAIL")
        self.assertEqual(row["runner_model_sha256"], S.ROLE_MODELS["B1_DETAIL"])
        self.assertIsNone(row["tool_call"])
        self.assertEqual(row["tool_shadow"]["tool"], "calc")
        self.assertEqual(row["answer"], "37 Euro")
        missing = C.row_from_message(item, None)
        self.assertEqual(missing["status"], "MISSING")
        self.assertIsNone(missing["runner_role"])
        self.assertEqual(missing["answer"], "")

    def test_wrong_runner_does_not_receive_a_valid_model_hash(self):
        item = S.fixture()[0]
        message = {"text": "37", "status": "FINAL",
                   "metadata": json.dumps({"runner": {"role": "EXTERNAL_TOOL"}})}
        row = C.row_from_message(item, message)
        self.assertIsNone(row["runner_model_sha256"])
        self.assertEqual(row["runner_role"], "EXTERNAL_TOOL")

    def test_fsync_raw_append_and_atomic_result(self):
        raw = self.root / "RAW_ROWS.jsonl"
        C._append_fsynced(raw, {"id": "a01", "status": "FINAL"})
        C._append_fsynced(raw, {"id": "a02", "status": "ERROR"})
        rows = [json.loads(line) for line in raw.read_text().splitlines()]
        self.assertEqual([r["id"] for r in rows], ["a01", "a02"])
        result = self.root / "CAPTURE_RESULT.json"
        C._atomic_json(result, {"native_completed": False})
        self.assertFalse(json.loads(result.read_text())["native_completed"])
        with self.assertRaises(FileExistsError):
            C._atomic_json(result, {"native_completed": True})

    def test_invalid_prompt_and_age_gates_refuse_before_native(self):
        with self.assertRaises(ValueError):
            C.preflight(self.home, "0"*40)
        for key, bad in (("learning_mode", "COMMIT"), ("system_stage", 1),
                         ("jepa_weight", .1), ("latents_enabled", True),
                         ("b2_control", "shared_body_dual_state")):
            self.settings[key] = bad
            self.save_settings()
            with self.subTest(key=key), self.assertRaises(ValueError):
                C.preflight(self.home, S.CANDIDATE_PROMPT)
            self.settings[key] = {"learning_mode": "RECORD_ONLY", "system_stage": 0,
                                  "jepa_weight": 0, "latents_enabled": False,
                                  "b2_control": "two_body"}[key]

    def test_existing_output_refused_without_native(self):
        out = self.root / "existing"
        out.mkdir()
        with self.assertRaises(FileExistsError):
            C.collect(self.home, out, S.CANDIDATE_PROMPT)
        with self.assertRaises(ValueError):
            C.collect(self.home, self.root / "new", S.CANDIDATE_PROMPT, seconds=1)


if __name__ == "__main__":
    unittest.main()
