"""Offline owner-consented, private relay / WebView control regressions."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from v13 import remote_observation as obs
from v13 import mobile_dashboard as ui


class FakePrivateGitHub:
    repository = "RedMentos/Aiiii"

    def __init__(self):
        self.calls = []
        self.private = True

    def check_private(self):
        if not self.private:
            raise ValueError("NOT_PRIVATE")

    def request(self, method, path, payload):
        self.calls.append((method,path,payload))
        return {"number":712} if method=="POST" else {"number":712}


class ObservationTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)/"private"
        self.root.mkdir(mode=0o700)
        for field,name in (("ROOT",self.root),
                           ("SETTINGS",self.root/"remote-observation-consent.json"),
                           ("STATE",self.root/"remote-observation-state.json")):
            patch=mock.patch.object(obs,field,name)
            patch.start()
            self.addCleanup(patch.stop)
        self.client=FakePrivateGitHub()
        self.cfg={"relay_repo":"RedMentos/Aiiii"}

    def test_no_silent_uploads_and_remote_tests_default_off(self):
        self.assertEqual(obs.consent(),{
            "observe":False,"remote_tests":False,"include_console":False})
        self.assertFalse(obs.permits("CHAT_SEND"))
        self.assertFalse(obs.permits("CHAT_RESULT"))
        self.assertFalse(obs.permits("CHAT_OPERATOR"))
        self.assertTrue(obs.permits("HEALTH"))
        self.assertEqual(obs.publish_once(self.client,self.cfg,now=2000),{"status":"DISABLED"})
        self.assertEqual(self.client.calls,[])

    def test_durable_consent_revocation_idempotent_and_private_file(self):
        for _ in range(3):
            obs.set_consent("remote_tests",True)
        self.assertTrue(obs.permits("CHAT_SEND"))
        self.assertEqual(obs.SETTINGS.stat().st_mode & 0o077,0)
        obs.set_consent("remote_tests",False)
        self.assertFalse(obs.permits("CHAT_SEND"))
        self.assertFalse(obs.consent()["observe"])
        with self.assertRaises(ValueError):
            obs.set_consent("arbitrary_shell",True)
        with self.assertRaises(ValueError):
            obs.set_consent("remote_tests",1)

    def test_one_status_issue_reused_at_15_min_intervals(self):
        obs.set_consent("observe",True)
        with mock.patch.object(obs,"report",return_value={"schema":obs.REPORT_SCHEMA,
                                                           "pipeline":{"last_result":"UP_TO_DATE"}}):
            first=obs.publish_once(self.client,self.cfg,now=4000)
            skip=obs.publish_once(self.client,self.cfg,now=4899)
            second=obs.publish_once(self.client,self.cfg,now=4900)
        self.assertEqual(first,{"status":"PUBLISHED","issue_number":712})
        self.assertEqual(skip,{"status":"NOT_DUE"})
        self.assertEqual(second,first)
        self.assertEqual([x[0] for x in self.client.calls],["POST","PATCH"])
        self.assertIn("/repos/RedMentos/Aiiii/issues/712",self.client.calls[-1][1])
        self.assertTrue(self.client.calls[0][2]["title"].startswith("V13OBS:"))
        self.assertEqual(obs.status(now=4900)["last_upload_utc"],4900)

    def test_revoked_observation_stops_network_before_poll(self):
        obs.set_consent("observe",True)
        obs.set_consent("observe",False)
        self.client.private=False
        self.assertEqual(obs.publish_once(self.client,self.cfg,now=4000),
                         {"status":"DISABLED"})
        self.assertEqual(self.client.calls,[])

    def test_relay_liveness_is_observed_not_claimed(self):
        self.assertFalse(obs.status(now=2000)["relay_recently_polled"])
        self.assertTrue(obs.heartbeat(now=2000))
        self.assertTrue(obs.status(now=2010)["relay_recently_polled"])
        self.assertFalse(obs.heartbeat(now=2010))
        self.assertFalse(obs.status(now=2401)["relay_recently_polled"])
        self.assertTrue(obs.heartbeat(now=2401))

    def test_fail_closed_on_corrupt_or_symlinked_consent(self):
        obs.SETTINGS.write_text(json.dumps({"schema":obs.SCHEMA,"observe":True}))
        obs.SETTINGS.chmod(0o600)  # valid filesystem ownership, invalid schema
        with self.assertRaises(ValueError):
            obs.consent()
        self.assertFalse(obs.permits("CHAT_SEND"))
        obs.SETTINGS.unlink()
        obs.SETTINGS.symlink_to(self.root/"private")
        with self.assertRaises(RuntimeError):
            obs.set_consent("observe",True)

    def test_webview_panel_is_real_and_exposes_granular_controls(self):
        before=ui.PRIVATE
        ui.PRIVATE=self.root
        self.addCleanup(setattr,ui,"PRIVATE",before)
        panel=ui._remote_observation_panel("/t/local/action")
        self.assertIn("remote_observe_on",panel)
        self.assertIn("remote_tests_on",panel)
        self.assertIn("remote_console_on",panel)
        self.assertIn("Nicht nachgewiesen",panel)
        obs.set_consent("observe",True)
        self.assertIn("remote_observe_off",ui._remote_observation_panel("/t/local/action"))


if __name__=="__main__":
    unittest.main()
