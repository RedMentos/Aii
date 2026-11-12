"""Network-free one-click V13 private GitHub diagnostics; no real token or device."""
from pathlib import Path
import hashlib
import json
import tempfile
import unittest
from unittest import mock

from v13 import diagnostic_push as d


class PrivateGitHub:
    repository = "RedMentos/Aiiii"

    def __init__(self, private=True):
        self.private = private
        self.calls = []

    def check_private(self):
        return self.private

    def request(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if path.endswith("/issues"):
            return {"number": 17}
        return {"id": len(self.calls)}


class DiagnosticReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.private = self.root / "private"
        self.private.mkdir(mode=0o700)
        self.home = self.root / "home"
        self.home.mkdir()
        (self.private / "console-logs").mkdir()
        (self.private / "ui.log").write_text("normal UI line\n[Fehler] broken save 123\n", encoding="utf-8")
        (self.private / "console-logs/v13-session-1.log").write_text(
            "du> Secret private question\nassistant> Private answer\n"
            "Authorization: Bearer TESTPRIVATEGITCREDENTIAL123456789\n"
            "github_pat_TESTLONGSECRET123456789\n", encoding="utf-8")
        self.summary = mock.patch("v13.mobile_dashboard.summary", return_value={"status":"SMOKE_PARTIAL"})
        self.pipeline = mock.patch("v13.pipeline_agent.snapshot", return_value={"last_result":"ERROR"})
        self.summary.start()
        self.pipeline.start()
        self.addCleanup(self.summary.stop)
        self.addCleanup(self.pipeline.stop)

    def test_technical_optin_never_uploads_chat(self):
        report = d.collect(full=False, home=self.home, private=self.private)
        self.assertEqual(report["mode"], "TECHNICAL")
        self.assertNotIn("Secret private question", json.dumps(report))
        self.assertIn("[Fehler]", report["files"]["ui.log"])

    def test_explicit_full_report_chunks_complete_and_redacts_secrets(self):
        client = PrivateGitHub()
        result = d.publish(full=True, client=client, home=self.home, private=self.private)
        self.assertEqual(result["status"], "SENT")
        self.assertIn("/issues/17", result["url"])
        comments = [payload["body"] for method, path, payload in client.calls
                    if method == "POST" and path.endswith("/comments")]
        manifest = json.loads(client.calls[0][2]["body"])
        self.assertEqual(manifest["mode"], "FULL_WITH_CHAT")
        self.assertEqual(json.loads(comments[-1])["status"], "COMPLETE")
        source = "".join(json.loads(body)["data"] for body in comments[:-1])
        parsed = json.loads(source)
        self.assertIn("Secret private question", str(parsed["files"]))
        self.assertNotIn("TESTPRIVATEGITCREDENTIAL123456789", source)
        self.assertNotIn("github_pat_TESTLONGSECRET123456789", source)
        self.assertEqual(parsed["schema"], d.SCHEMA)
        self.assertFalse(parsed["truncated"])
        self.assertFalse(manifest["truncated"])
        self.assertFalse(result["truncated"])

    def test_refuses_nonprivate_repository_before_writing(self):
        client = PrivateGitHub(private=False)
        with self.assertRaises(ValueError):
            d.publish(full=True, client=client, home=self.home, private=self.private)
        self.assertEqual(client.calls, [])

    def test_full_report_never_reads_credentials_or_database(self):
        (self.private/"remote.json").write_text('{"keys":{"agent-owner":"SECRET_TOKEN"}}')
        (self.home/"brain.sqlite3").write_text("PRIVATE_DATABASE")
        report = d.collect(full=True, home=self.home, private=self.private)
        out = json.dumps(report)
        self.assertNotIn("SECRET_TOKEN", out)
        self.assertNotIn("PRIVATE_DATABASE", out)

    def test_native_probe_stays_valid_and_preserves_results_after_summarizing(self):
        probe = self.home / "exports/native-probe.json"
        probe.parent.mkdir()
        source = {
            "status": "SMOKE_PARTIAL", "full_runner_proof": False,
            "phone_measured": True, "effective_config": {
                "deadline_seconds": 90, "threads": 2, "prompts": "PRIVATE_PROMPT"},
            "roles": {
                "B1_DETAIL": {"ok": False, "error": "Zeitbudget erreicht", "duration_s": 44.8},
                "B2_GIST": {"ok": True, "actual_output": "PRIVATE_OUTPUT" * 10000,
                            "metrics": {"duration_s": 36.9, "status": "FINAL",
                                        "generated_tokens": 48, "ttft_s": 1.1,
                                        "resource_samples": [{"path": "/private/path"}] * 1000}},
                "C3_LANGUAGE": {"ok": True, "duration_s": 3.1},
                "C2_CONTROL": {"ok": False, "error": "No such file or directory: /private/path"}
            }, "access_token": "github_pat_TESTLONGSECRET123456789"
        }
        probe.write_text(json.dumps(source), encoding="utf8")
        report = d.collect(full=False, home=self.home, private=self.private)
        artifact = json.loads(report["files"]["native-probe.json"])
        self.assertEqual(artifact["source_status"], "PARSED")
        self.assertEqual(artifact["status"], "SMOKE_PARTIAL")
        self.assertFalse(artifact["full_runner_proof"])
        self.assertEqual(artifact["effective_config"]["deadline_seconds"], 90)
        self.assertEqual(artifact["roles"]["B1_DETAIL"], {
            "ok": False, "error_present": True, "error_kind": "TIME_BUDGET", "duration_s": 44.8})
        self.assertEqual(artifact["roles"]["B2_GIST"]["metrics"]["duration_s"], 36.9)
        self.assertTrue(artifact["roles"]["B2_GIST"]["ok"])
        self.assertEqual(artifact["roles"]["C2_CONTROL"]["error_kind"], "MISSING_FILE")
        self.assertEqual(report["file_metadata"]["native-probe.json"]["source_bytes"],
                         probe.stat().st_size)
        self.assertTrue(report["file_metadata"]["native-probe.json"]["truncated"])
        self.assertTrue(report["truncated"])
        for omitted in ("PRIVATE_PROMPT", "PRIVATE_OUTPUT", "/private/path", "github_pat_", "resource_samples"):
            self.assertNotIn(omitted, json.dumps(artifact))
        self.assertLessEqual(len(report["files"]["native-probe.json"]), d.MAX_FILE_CHARS)

    def test_oversized_and_invalid_probe_are_explicitly_unverified(self):
        probe = self.home / "exports/native-probe.json"
        probe.parent.mkdir()
        for content, expected in ((json.dumps({"status": "SMOKE_PASS", "large": "x" * 500}), "SIZE_LIMIT"),
                                  ('{"status": "SMOKE_PASS",', "INVALID_JSON")):
            with self.subTest(expected=expected), mock.patch.object(d, "MAX_PROBE_BYTES", 128):
                probe.write_text(content, encoding="utf8")
                report = d.collect(full=False, home=self.home, private=self.private)
                artifact = json.loads(report["files"]["native-probe.json"])
                self.assertEqual(artifact["source_status"], expected)
                self.assertEqual(artifact["status"], "UNVERIFIED")
                self.assertEqual(artifact["roles"], {})
                self.assertTrue(report["truncated"])

    def test_utf8_tail_discard_is_flagged_even_when_decoded_tail_fits(self):
        path = self.private / "ui.log"
        path.write_text("\U0001f680" * 257, encoding="utf8")
        with mock.patch.object(d, "MAX_FILE_CHARS", 256):
            report = d.collect(full=True, home=self.home, private=self.private)
        text = report["files"]["ui.log"]
        self.assertTrue(text.startswith(d.TRUNCATION_NOTICE))
        self.assertLessEqual(len(text), 256)
        self.assertNotIn("\ufffd", text)
        self.assertTrue(report["file_metadata"]["ui.log"]["truncated"])
        self.assertTrue(report["truncated"])

    def test_redaction_growth_and_notice_fit_within_file_bound(self):
        (self.private / "ui.log").write_text(("ghp_abcdefghijkl " * 7).strip(), encoding="utf8")
        with mock.patch.object(d, "MAX_FILE_CHARS", 128):
            report = d.collect(full=True, home=self.home, private=self.private)
        text = report["files"]["ui.log"]
        self.assertLessEqual(len(text), 128)
        self.assertNotIn("abcdefghijkl", text)
        self.assertTrue(report["truncated"])

    def test_aggregate_cap_marks_later_files_omitted_without_negative_zero_slice(self):
        for name in ("ui.log", "ai-service.log", "bridge.log"):
            (self.private / name).write_text("x" * 200, encoding="utf8")
        with mock.patch.object(d, "MAX_TOTAL_CHARS", 300):
            report = d.collect(full=True, home=self.home, private=self.private)
        self.assertLessEqual(sum(map(len, report["files"].values())), 300)
        self.assertEqual(report["total_transmitted_chars"], sum(map(len, report["files"].values())))
        self.assertTrue(report["file_metadata"]["bridge.log"]["omitted"])
        self.assertTrue(report["file_metadata"]["bridge.log"]["truncated"])
        self.assertNotIn("bridge.log", report["files"])
        self.assertTrue(report["truncated"])

    def test_non_bmp_logs_fit_complete_private_relay_and_hash(self):
        (self.private / "ui.log").write_text("\U0001f680" * d.MAX_FILE_CHARS, encoding="utf8")
        for name in ("ai-service.log", "bridge.log", "v13-ui-last.log"):
            (self.private / name).write_text("\U0001f680" * d.MAX_FILE_CHARS, encoding="utf8")
        report = d.collect(full=True, home=self.home, private=self.private)
        pages, digest = d._pages(report)
        self.assertLessEqual(len(pages), d.MAX_PAGES)
        self.assertTrue(all(len(page) <= d.PAGE_CHARS for page in pages))
        joined = "".join(pages)
        self.assertEqual(hashlib.sha256(joined.encode("ascii")).hexdigest(), digest)
        self.assertEqual(json.loads(joined), report)
        self.assertTrue(report["truncated"])
        self.assertTrue(all(len(text) <= d.MAX_FILE_CHARS for text in report["files"].values()))
        self.assertLessEqual(report["total_transmitted_chars"], d.MAX_TOTAL_CHARS)

    def test_error_line_limit_is_reported_as_truncation(self):
        (self.private / "ui.log").write_text("[Fehler] diagnostic\n" * 121, encoding="utf8")
        report = d.collect(full=False, home=self.home, private=self.private)
        self.assertEqual(len(report["files"]["ui.log"].splitlines()), 100)
        self.assertTrue(report["file_metadata"]["ui.log"]["truncated"])
        self.assertTrue(report["truncated"])

    def test_probe_never_promotes_unknown_or_nonfinite_measurements(self):
        probe = self.home / "exports/native-probe.json"
        probe.parent.mkdir()
        probe.write_text(json.dumps({
            "status": "NOT_A_SMOKE_RESULT", "full_runner_proof": "yes",
            "effective_config": {"deadline_seconds": float("inf"), "threads": True},
            "roles": {"B1_DETAIL": {"ok": "yes", "duration_s": float("nan"),
                                     "metrics": {"generated_tokens": 10**400,
                                                 "ttft_s": -1, "status": "ARBITRARY_TEXT"}}}
        }), encoding="utf8")
        report = d.collect(full=False, home=self.home, private=self.private)
        artifact = json.loads(report["files"]["native-probe.json"])
        self.assertEqual(artifact["status"], "UNVERIFIED")
        self.assertNotIn("full_runner_proof", artifact)
        self.assertEqual(artifact["effective_config"], {})
        self.assertEqual(artifact["roles"]["B1_DETAIL"], {"ok": None, "metrics": {}})


if __name__ == "__main__":
    unittest.main()
