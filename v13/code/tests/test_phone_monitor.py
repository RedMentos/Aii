"""Proactive private Redmi incident reporting: actual failed chat despite RUNNING UI."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from v13 import phone_monitor as monitor
from v13 import owner_read_bridge as owner


class PrivateGitHub:
    repository="RedMentos/Aiiii"
    def __init__(self):self.created=[]
    def request(self,method,path,payload,**kwargs):
        if method!="POST" or path!="/repos/RedMentos/Aiiii/issues":
            raise AssertionError("Unexpected private GitHub action")
        self.created.append(payload)
        return {"number":len(self.created)}


class MonitorTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        private=Path(tmp.name)/".v13-private"
        private.mkdir(mode=0o700)
        logdir=private/"console-logs"
        logdir.mkdir(mode=0o700)
        self.path=logdir/"v13-session-20261112-110600-123abc.log"
        self.path.write_text("du>\n[du> Hi]\n"
                             "[Fehler] [Errno 2] No such file or directory: 'abc-secret-hash'\n"
                             "du>\n",encoding="utf8")
        for field,value in (("PRIVATE",private),("LOGS",logdir),
                            ("REPORT",private/"ai-health-status.json")):
            p=mock.patch.object(monitor,field,value)
            p.start();self.addCleanup(p.stop)

    def test_real_model_error_alert_sent_proactively_without_user_screenshot(self):
        github=PrivateGitHub()
        with mock.patch("v13.chat_service.call",return_value={"running":True}):
            first=monitor.check()
            self.assertEqual(first["ai"],"MODEL_RUNNING")
            self.assertEqual(first["chat"],"CHAT_ERROR")
            self.assertEqual(first["error"],"MISSING_FILE")
            response=owner.monitor_and_alert(github,now=1900)
            self.assertEqual(response["status"],"PUBLISHED")
            self.assertEqual(len(github.created),1)
            body=github.created[0]
            self.assertIn("V13ALERT:CHAT:MISSING_FILE",body["title"])
            self.assertNotIn("Hi",json.dumps(body))
            self.assertNotIn("abc-secret-hash",json.dumps(body))
            # No repeated issues every minute while still broken.
            again=owner.monitor_and_alert(github,now=1901)
            self.assertEqual(again["status"],"UNCHANGED")
            self.assertEqual(len(github.created),1)
        self.assertEqual(oct(monitor.REPORT.stat().st_mode & 0o777),"0o600")

    def test_recovery_after_verified_answer_produces_single_notice(self):
        github=PrivateGitHub()
        with mock.patch("v13.chat_service.call",return_value={"running":True}):
            owner.monitor_and_alert(github,now=1900)
            with self.path.open("a",encoding="utf8") as log:
                log.write("[du> Again]\nassistant> V13 answer OK\n\ndu>\n")
            recovered=owner.monitor_and_alert(github,now=1910)
            self.assertEqual(recovered["status"],"PUBLISHED")
            self.assertIn("V13RECOVERED:",github.created[1]["title"])
            self.assertEqual(owner.monitor_and_alert(github,now=1911)["status"],"UNCHANGED")

    def test_offline_ai_also_triggers_critical_report(self):
        github=PrivateGitHub()
        self.path.unlink()
        with mock.patch("v13.chat_service.call",side_effect=ConnectionRefusedError):
            self.assertEqual(owner.monitor_and_alert(github,now=2000)["status"],"PUBLISHED")
        self.assertIn("SERVICE_OFFLINE",github.created[0]["title"])


if __name__=="__main__":
    unittest.main()
