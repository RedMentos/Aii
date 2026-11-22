"""Independent software regressions for bounded CLI input and finalizer.

No native model, TTY, visible output, tool or learning authority.
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import jef_c3_c5_c6_operator_cli as cli
from scripts.run63_jef_c3_native import cohort
from v13.runtime import Runtime


class JefOperatorIoFinalizerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_sparse_oversize_is_bounded_before_runtime(self):
        path = self.root / "large.json"
        with path.open("wb") as file:
            file.truncate(32 * 1024 * 1024)
        home = self.root / "never_opened"
        with patch.object(Path, "read_bytes",
                          side_effect=AssertionError("unbounded read")):
            result = cli.run(home, path, "synthetic_exact",
                             operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(result["status"], "INPUT_RED")
        self.assertFalse(result["runtime_opened"])
        self.assertFalse(home.exists())

    def test_exact_input_bound_reaches_parser(self):
        path = self.root / "boundary.json"
        path.write_bytes(b" " * cli.MAX_INPUT_BYTES)
        with self.assertRaises(json.JSONDecodeError):
            cli._read_input(path)
        with path.open("ab") as file:
            file.write(b" ")
        with self.assertRaisesRegex(ValueError, "INPUT_SIZE_RED"):
            cli._read_input(path)

    def test_pool_unload_failure_still_attempts_store_close(self):
        row = cohort()[0]
        path = self.root / "human.json"
        path.write_text(json.dumps({
            "project": row["id"], "domain": row["domain"],
            "policy_source": row["b2_source"],
            "sheet_source": row["b1_source"],
            "current": row["current"],
        }), encoding="utf-8")
        closed = []
        unload_calls = []
        def factory(home):
            runtime = Runtime(home)
            original_unload = runtime.pool.unload
            original_close = runtime.close
            def unload_once():
                unload_calls.append(True)
                if len(unload_calls) == 1:
                    raise RuntimeError("injected unload failure")
                return original_unload()
            def close():
                closed.append(True)
                return original_close()
            runtime.pool.unload = unload_once
            runtime.close = close
            return runtime
        with patch.object(cli, "Runtime", side_effect=factory):
            result = cli.run(self.root / "home", path, "synthetic_exact",
                             operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(result["status"], "CLI_CLOSE_RED")
        self.assertEqual(result["pool_release_status"], "UNLOAD_RED")
        self.assertTrue(closed)
        self.assertFalse(result["output_committed"])
        self.assertEqual(result["delivery_authority"], 0)

    def test_native_release_receipts_fail_closed(self):
        cases = (
            ([], False),
            ([{"before": None, "process_reaped": True}], False),
            ([{"before": {"pid": 123}, "process_reaped": False}], False),
            ([{"before": {"pid": 123}, "process_reaped": True}], True),
            ([{"before": {"pid": 123}, "process_reaped": True},
              {"before": {"pid": 124}, "process_reaped": False}], False),
        )
        for releases, expected in cases:
            with self.subTest(releases=releases):
                report = {"status": "SHADOW_DRAFT_PREFLIGHT_READY",
                          "native_model_called": True}
                cli._finalize_native_release(report, releases)
                self.assertEqual(report["native_process_reaped"], expected)
                self.assertEqual(report["status"],
                                 "SHADOW_DRAFT_PREFLIGHT_READY" if expected
                                 else "NATIVE_RELEASE_RED")
        never_called = {"status": "NATIVE_BINDING_RED",
                        "native_model_called": False}
        cli._finalize_native_release(never_called, [])
        self.assertEqual(never_called["status"], "NATIVE_BINDING_RED")
        self.assertFalse(never_called["native_process_reaped"])


if __name__ == "__main__":
    unittest.main()
