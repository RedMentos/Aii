"""Local operator CLI real-Store tests; synthetic callbacks, no native."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.run63_jef_c3_native import cohort
from scripts import jef_c3_c5_c6_operator_cli as cli
from v13.runtime import Runtime


class JefC3C5C6OperatorCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.fixtures = cohort()

    def tearDown(self):
        self.tmp.cleanup()

    def input(self, row, name="input.json"):
        data = {
            "project": row["id"], "domain": row["domain"],
            "policy_source": row["b2_source"],
            "sheet_source": row["b1_source"],
            "current": row["current"],
        }
        path = self.root/name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path, data

    def assert_safe(self, result):
        self.assertEqual(result["delivery_authority"], 0)
        self.assertFalse(result["output_committed"])
        self.assertEqual(result["tool_dispatches"], 0)
        self.assertEqual(result["learning_authority"], 0)
        self.assertFalse(result["native_proof"])
        self.assertFalse(result["real_tty_approved"])
        self.assertEqual(result["age0"], "RECORD_ONLY")
        self.assertNotIn("native_output", result)
        self.assertNotIn("policy_source", result)
        self.assertNotIn("sheet_source", result)
        self.assertNotIn("current", result)

    def test_off_does_not_read_file_or_open_runtime(self):
        home = self.root/"never-created"
        missing = self.root/"not-there.json"
        for opts in ({}, {"operator_opt_in": 1, "callback_opt_in": True},
                     {"operator_opt_in": True, "callback_opt_in": 1}):
            result = cli.run(home, missing, "synthetic_exact", **opts)
            self.assertEqual(result["status"], "OFF")
            self.assertFalse(result["input_read"])
            self.assertFalse(result["runtime_opened"])
            self.assert_safe(result)
        self.assertFalse(home.exists())

    def test_six_source_bound_local_drafts_survive_restart(self):
        for i, row in enumerate(self.fixtures):
            for mode in ("synthetic_exact", "synthetic_wrong"):
                with self.subTest(id=row["id"], mode=mode):
                    input_file, data = self.input(row, f"input_{i}_{mode}.json")
                    home = self.root/f"home_{i}_{mode}"
                    result = cli.run(
                        home, input_file, mode,
                        operator_opt_in=True, callback_opt_in=True)
                    self.assertEqual(result["status"],
                                     "SHADOW_DRAFT_PREFLIGHT_READY")
                    self.assertEqual(result["stage_status"],
                                     "JEF_C5_SOURCE_ONLY_DRAFT_STAGED_SHADOW")
                    self.assertEqual(result["c6_status"],
                                     "NEEDS_REAL_TTY_APPROVAL")
                    self.assertTrue(result["preflight_only"])
                    self.assertTrue(result["no_live_output"])
                    self.assertFalse(result["native_model_called"])
                    self.assertIsNone(result["native_process_reaped"])
                    self.assertEqual(result["source_only_fallback"],
                                     mode == "synthetic_wrong")
                    self.assertEqual(result["model_formatter_status"],
                                     ("FORMATTER_MATCH_SHADOW"
                                      if mode == "synthetic_exact"
                                      else "FORMATTER_MISMATCH_RED"))
                    self.assert_safe(result)
                    wire = json.dumps(result)
                    for source in (data["current"], data["policy_source"],
                                   data["sheet_source"]):
                        self.assertNotIn(source, wire)
                    r = Runtime(home)
                    try:
                        # Store._recover deliberately invalidates uncommitted
                        # DRAFT on restart. The row/evidence persists, but
                        # no DRAFT is eligible for a later output commit.
                        rows = r.store.rows(
                            "SELECT text,status FROM messages "
                            "WHERE role='assistant'")
                        self.assertEqual(len(rows), 1)
                        self.assertEqual(rows[0]["text"], row["oracle_action"])
                        self.assertEqual(rows[0]["status"], "INTERRUPTED")
                        self.assertEqual(r.store.one(
                            "SELECT COUNT(*) AS n FROM messages "
                            "WHERE role='assistant' AND status='DRAFT'")["n"], 0)
                        self.assertEqual(r.store.one(
                            "SELECT COUNT(*) AS n FROM actions "
                            "WHERE kind='TEXT_REPORT'")["n"], 1)
                        self.assertEqual(r.store.one(
                            "SELECT COUNT(*) AS n FROM messages "
                            "WHERE role='assistant' AND "
                            "status IN ('FINAL','OUTPUT_COMMITTED')")["n"], 0)
                    finally:
                        r.close()

    def test_input_rejections_before_store_write(self):
        row = self.fixtures[0]
        input_file, data = self.input(row)
        variants = {
            "duplicate": '{"project":"X","project":"Y"}',
            "missing": json.dumps({k:v for k,v in data.items()
                                   if k != "current"}),
            "extra": json.dumps(dict(data, oracle_action="A")),
            "type": json.dumps(dict(data, current=123)),
            "project": json.dumps(dict(data, project="../unsafe")),
            "leading_digit_project": json.dumps(dict(data, project="1Bad")),
            "long_domain": json.dumps(dict(data, domain="A" * 41)),
            "oversized_source": json.dumps(dict(
                data, policy_source=data["policy_source"] + "x" * 2048)),
            "identity": json.dumps(dict(data, policy_source="wrong")),
            "control": json.dumps(dict(data, current=data["current"]+"\n")),
            "oversize": "x" * 16385,
            "malformed": "{",
        }
        for name, text in variants.items():
            with self.subTest(name=name):
                path = self.root/(name+".json")
                path.write_text(text, encoding="utf-8")
                home = self.root/("home_"+name)
                result = cli.run(home, path, "synthetic_exact",
                                 operator_opt_in=True, callback_opt_in=True)
                self.assertEqual(result["status"], "INPUT_RED")
                self.assertFalse(result["runtime_opened"])
                self.assertFalse(home.exists())
                self.assert_safe(result)
        invalid = self.root/"invalid_utf8.json"
        invalid.write_bytes(b"\xff\xfe")
        result = cli.run(self.root/"invalid_utf8_home", invalid,
                         "synthetic_exact", operator_opt_in=True,
                         callback_opt_in=True)
        self.assertEqual(result["status"], "INPUT_RED")
        self.assertFalse((self.root/"invalid_utf8_home").exists())

    def test_wrong_grammar_denies_before_callback_and_no_draft(self):
        row = self.fixtures[0]
        path, data = self.input(row)
        data["policy_source"] = (
            f"Project {row['id']} archived {row['domain']} policy. garbage")
        path.write_text(json.dumps(data), encoding="utf-8")
        home = self.root/"grammar_home"
        result = cli.run(home, path, "synthetic_exact",
                         operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(result["status"], "SOURCE_ADMISSION_RED")
        self.assert_safe(result)
        r = Runtime(home)
        try:
            self.assertEqual(r.store.one(
                "SELECT COUNT(*) AS n FROM messages "
                "WHERE role='assistant' AND status='DRAFT'")["n"], 0)
        finally:
            r.close()

    def test_native_missing_pinned_model_refuses_before_human_records(self):
        path, _ = self.input(self.fixtures[0])
        home = self.root/"native_missing"
        result = cli.run(home, path, "native",
                         operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(result["status"], "NATIVE_BINDING_RED")
        self.assertFalse(result["native_model_called"])
        self.assert_safe(result)
        r = Runtime(home)
        try:
            self.assertEqual(r.store.one(
                "SELECT COUNT(*) AS n FROM memories")["n"], 0)
        finally:
            r.close()

    def test_invalid_mode_refuses_before_read(self):
        missing = self.root/"missing"
        home = self.root/"not-created"
        result = cli.run(home, missing, "unknown",
                         operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(result["status"], "INVALID_MODE")
        self.assertFalse(result["input_read"])
        self.assertFalse(home.exists())


if __name__ == "__main__":
    unittest.main()
