"""Network-free one-click V13 private GitHub diagnostics; no real token or device."""
from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
