"""Read-only private GitHub owner-command tests (no network, no Android needed)."""
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from v13 import owner_read_bridge as o
from v13 import remote_maintenance_bridge as b


class FakeGitHub:
    def __init__(self, issues, private=True):
        self.queue = issues
        self.private = private
        self.comments_sent = []
        self.closed = []
        self.checks = 0
    def check_private(self):
        self.checks += 1
        if not self.private:
            raise b.Denied("relay MUST be private")
    def issues(self):
        return [i for i in self.queue if i["number"] not in self.closed]
    def comment(self, number, receipt):
        self.comments_sent.append((number, receipt))
    def close(self, number):
        self.closed.append(number)


class OwnerReadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        source = root / "source"
        source.mkdir()
        self.cfg = {
            "relay_repo": "RedMentos/Aiiii",
            "installed_root": str(source),
            "state_dir": str(root / "state"),
            "keys": {"agent-owner": "ab" * 32},
            "authors": {"agent-owner": ["RedMentos"]},
            "permissions": {"agent-owner": ["HEALTH", "LEARNING_STATUS"]},
            "remote_apply_enabled": False
        }
        self.now = 1900

    def issue(self, command="HEALTH", author="RedMentos", ident="d" * 32,
              number=1, expiry=None, created_at=None):
        body = {"schema": o.READ_SCHEMA, "id": ident, "command": command,
                "expires_at": self.now + 500 if expiry is None else expiry}
        return {"number": number, "title": "V13READ:" + ident,
                "body": json.dumps(body), "user": {"login": author},
                "created_at": created_at or datetime.fromtimestamp(
                    self.now, timezone.utc).isoformat()}

    def test_owner_capabilities_migrate_once_and_respect_future_revocation(self):
        root=Path(self.temp.name)/"private"
        root.mkdir(mode=0o700)
        conf=root/"remote.json"
        conf.write_text(json.dumps(self.cfg))
        conf.chmod(0o600)
        self.assertTrue(o.activate_owner_capabilities(conf))
        saved=json.loads(conf.read_text())
        self.assertEqual(saved["permissions"]["agent-owner"],list(o.OWNER_GRANTS))
        self.assertTrue((root/"owner-capabilities-v2.done").is_file())
        # Owner can later explicitly revoke remote chat. Never re-enable it
        # just because the relay restarted after another GitHub update.
        saved["permissions"]["agent-owner"].remove("CHAT_SEND")
        conf.write_text(json.dumps(saved))
        conf.chmod(0o600)
        self.assertFalse(o.activate_owner_capabilities(conf))
        again=json.loads(conf.read_text())
        self.assertNotIn("CHAT_SEND",again["permissions"]["agent-owner"])

    def test_owner_migration_refuses_untrusted_permissions_and_public_repo(self):
        root=Path(self.temp.name)/"unsafe"
        root.mkdir(mode=0o700)
        conf=root/"remote.json"
        for edit in ({"relay_repo":"RedMentos/Aii"},
                     {"authors":{"agent-owner":["Attacker"]}},
                     {"permissions":{"agent-owner":["SHELL"]}}):
            payload={**self.cfg,**edit}
            conf.write_text(json.dumps(payload))
            conf.chmod(0o600)
            with self.assertRaises(b.Denied):
                o.activate_owner_capabilities(conf)

    def test_owner_health_e2e_and_idempotent_restart(self):
        issue = self.issue()
        client = FakeGitHub([issue])
        self.assertEqual(o.poll_once(client, self.cfg, now=self.now)["processed"], 1)
        self.assertEqual(client.comments_sent[0][1]["device_status"]["status"], "OK")
        self.assertEqual(client.closed, [1])
        client.closed.clear()  # failed close/reopened issue
        self.assertEqual(o.poll_once(client, self.cfg, now=self.now)["processed"], 1)
        self.assertEqual(len(client.comments_sent), 1)

    def test_health_reports_effective_remote_chat_grants_without_exposing_keys(self):
        self.cfg["permissions"]["agent-owner"].extend(["CHAT_SEND", "CHAT_RESULT"])
        client=FakeGitHub([self.issue()])
        self.assertEqual(o.poll_once(client,self.cfg,now=self.now)["processed"],1)
        status=client.comments_sent[0][1]["device_status"]
        self.assertEqual(status["relay_protocol"],"v13-owner-chat-v2")
        self.assertTrue(status["owner_capabilities"]["chat_send"])
        self.assertTrue(status["owner_capabilities"]["chat_result"])
        self.assertFalse(status["owner_capabilities"]["chat_operator"])
        self.assertNotIn(self.cfg["keys"]["agent-owner"],json.dumps(status))

    def test_android_missing_getloadavg_does_not_break_health(self):
        from unittest import mock
        client = FakeGitHub([self.issue()])
        with mock.patch.object(b.os, "getloadavg", side_effect=AttributeError("Android API unavailable")):
            result = o.poll_once(client, self.cfg, now=self.now)
        self.assertEqual(result["processed"], 1)
        status = client.comments_sent[0][1]["device_status"]
        self.assertEqual(status["status"], "OK")
        self.assertEqual(status["load_average_state"], "UNAVAILABLE")

    def test_owner_learning_status_only(self):
        client = FakeGitHub([self.issue("LEARNING_STATUS")])
        self.assertEqual(o.poll_once(client, self.cfg, now=self.now)["processed"], 1)
        self.assertEqual(client.comments_sent[0][1]["device_status"]["learning"]["state"], "UNINSTRUMENTED")

    def test_owner_pipeline_status_read_is_authenticated_and_no_mutation(self):
        from unittest import mock
        self.cfg["permissions"]["agent-owner"].append("PIPELINE_STATUS")
        client = FakeGitHub([self.issue("PIPELINE_STATUS")])
        with mock.patch("v13.pipeline_agent.snapshot", return_value={
            "schema": "v13.pipeline-status/1", "auto_enabled": True,
            "last_result": "UP_TO_DATE", "runtime": "UP_TO_DATE",
            "dashboard": "UP_TO_DATE", "last_error": "NONE"}):
            result = o.poll_once(client, self.cfg, now=self.now)
        self.assertEqual(result["processed"], 1)
        status = client.comments_sent[0][1]["device_status"]
        self.assertEqual(status["pipeline"]["last_result"], "UP_TO_DATE")
        self.assertNotIn("cmd", str(status))
        self.assertEqual(client.closed, [1])
        self.cfg["permissions"]["agent-owner"].remove("PIPELINE_STATUS")
        with self.assertRaises(b.Denied):
            o.validate_owner_read(self.issue("PIPELINE_STATUS"), self.cfg, now=self.now)

    def test_log_page_requires_permission_explicit_indices_and_local_opt_in(self):
        from unittest import mock
        self.cfg["permissions"]["agent-owner"].append("LOG_PAGE")
        issue=self.issue("LOG_PAGE")
        body=json.loads(issue["body"])
        body["args"]={"session":0,"page":3}
        issue["body"]=json.dumps(body)
        client=FakeGitHub([issue])
        with mock.patch("v13.mobile_dashboard.remote_console_page",
                        return_value={"state":"USER_NOT_OPTED_IN"}) as reader:
            self.assertEqual(o.poll_once(client,self.cfg,now=self.now)["processed"],1)
        reader.assert_called_once_with(0,3)
        self.assertEqual(client.comments_sent[0][1]["device_status"]["console_page"]["state"],"USER_NOT_OPTED_IN")
        for bad in (
            {"session":-1,"page":0},
            {"session":0,"page":2048},
            {"session":True,"page":0},
            {"session":0,"page":0,"path":"/etc/passwd"},
            {"session":"../../","page":0},
        ):
            invalid=self.issue("LOG_PAGE")
            data=json.loads(invalid["body"])
            data["args"]=bad
            invalid["body"]=json.dumps(data)
            with self.subTest(bad=bad),self.assertRaises(b.Denied):
                o.validate_owner_read(invalid,self.cfg,now=self.now)
        self.cfg["permissions"]["agent-owner"].remove("LOG_PAGE")
        with self.assertRaises(b.Denied):
            o.validate_owner_read(issue,self.cfg,now=self.now)

    def test_wrong_author_expired_stale_or_invalid_denied(self):
        inputs = [
            self.issue(author="Impostor"),
            self.issue(expiry=self.now - 1),
            self.issue(expiry=self.now + 2000),
            self.issue(created_at="2020-01-01T00:00:00Z"),
            self.issue(command="PATCH_APPLY"),
            self.issue(command="SHELL"),
            self.issue(command="PATCH_STAGE"),
        ]
        for issue in inputs:
            with self.subTest(issue=issue):
                with self.assertRaises(b.Denied):
                    o.validate_owner_read(issue, self.cfg, now=self.now)

    def test_title_mismatch_and_injected_arguments(self):
        issue = self.issue()
        issue["title"] = "V13READ:" + "0" * 32
        with self.assertRaises(b.Denied):
            o.validate_owner_read(issue, self.cfg, now=self.now)
        issue = self.issue()
        obj = json.loads(issue["body"])
        obj["args"] = {"shell": "rm -rf /"}
        issue["body"] = json.dumps(obj)
        with self.assertRaises(b.Denied):
            o.validate_owner_read(issue, self.cfg, now=self.now)

    def test_private_repo_required(self):
        client = FakeGitHub([self.issue()], private=False)
        with self.assertRaises(b.Denied):
            o.poll_once(client, self.cfg, now=self.now)
        self.assertEqual(client.comments_sent, [])

    def test_stopped_ignores_commands(self):
        state = Path(self.cfg["state_dir"])
        state.mkdir(mode=0o700)
        (state / "STOP").touch()
        client = FakeGitHub([self.issue()])
        self.assertEqual(o.poll_once(client, self.cfg, now=self.now)["status"], "STOPPED_LOCALLY")
        self.assertFalse(client.comments_sent)

    def test_duplicate_nonce_in_second_issue_does_not_reexecute(self):
        one = self.issue(number=1)
        two = self.issue(number=2)
        client = FakeGitHub([one, two])
        self.assertEqual(o.poll_once(client, self.cfg, now=self.now)["processed"], 1)
        self.assertEqual(len(client.comments_sent), 1)

    def test_unsigned_legacy_command_still_rejected(self):
        issue = self.issue()
        issue["title"] = "V13CMD:" + "d" * 32
        client = FakeGitHub([issue])
        self.assertEqual(o.poll_once(client, self.cfg, now=self.now)["processed"], 0)
        self.assertFalse(client.comments_sent)

    def test_read_generator_no_patch(self):
        command = o.create_read_request("HEALTH", now=self.now)
        self.assertEqual(command["command"], "HEALTH")
        self.assertEqual(len(command["id"]), 32)
        with self.assertRaises(b.Denied):
            o.create_read_request("PATCH_APPLY", now=self.now)


if __name__ == "__main__":
    unittest.main()
