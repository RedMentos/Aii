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

    def test_native_system_report_is_failure_and_never_recovery(self):
        github=PrivateGitHub()
        with mock.patch("v13.chat_service.call",return_value={"running":True}):
            owner.monitor_and_alert(github,now=1900)
            with self.path.open("a",encoding="utf8") as log:
                log.write("[du> private question]\n"
                          "assistant> [SOURCE_SYSTEM_REPORT; Systemdiagnose; keine Modellantwort]\n"
                          "Zeitbudget erreicht: /private/model-path\n"
                          "Angenommene Eingabe (exakte Quelle): private question\n"
                          "Status: DEADLINE. Eine inhaltliche Modellantwort ist nicht belegt.\n")
            report=monitor.check()
            self.assertEqual(report["chat"],"CHAT_ERROR")
            self.assertEqual(report["error"],"MODEL_TIMEOUT")
            self.assertEqual(owner.monitor_and_alert(github,now=1910)["status"],"PUBLISHED")
        serialized=json.dumps(github.created)
        self.assertNotIn("V13RECOVERED",serialized)
        self.assertNotIn("private question",serialized)
        self.assertNotIn("/private/model-path",serialized)

    def test_pending_request_and_empty_response_do_not_recover_failure(self):
        github=PrivateGitHub()
        with mock.patch("v13.chat_service.call",return_value={"running":True}):
            owner.monitor_and_alert(github,now=1900)
            for chunk in ("[du> retry]\ndu>\n", "assistant> \n"):
                with self.path.open("a",encoding="utf8") as log:
                    log.write(chunk)
                self.assertEqual(owner.monitor_and_alert(github,now=1910)["status"],
                                 "AWAITING_ANSWER")
                self.assertEqual(len(github.created),1)
            with self.path.open("a",encoding="utf8") as log:
                log.write("Actual nonempty answer.\n")
            self.assertEqual(owner.monitor_and_alert(github,now=1920)["status"],"PUBLISHED")
        self.assertIn("V13RECOVERED",github.created[1]["title"])

    def test_system_report_header_split_during_capture_never_counts_as_answer(self):
        self.path.write_text("[du> retry]\nassistant> [SOURCE_SYS",encoding="utf8")
        with mock.patch("v13.chat_service.call",return_value={"running":True}):
            self.assertEqual(monitor.check()["chat"],"CHAT_PENDING")
            with self.path.open("a",encoding="utf8") as log:
                log.write("TEM_REPORT; Systemdiagnose; keine Modellantwort]\nMemoryError\n")
            self.assertEqual(monitor.check()["chat"],"CHAT_ERROR")
            self.assertEqual(monitor.check()["error"],"OUT_OF_MEMORY")

    def test_diagnostic_operator_output_does_not_hide_failed_chat(self):
        with self.path.open("a",encoding="utf8") as log:
            log.write("[du> :doctor]\n[V13] doctor OK\n")
        with mock.patch("v13.chat_service.call",return_value={"running":True}):
            self.assertEqual(monitor.check()["chat"],"CHAT_ERROR")

    def test_no_chat_history_does_not_publish_recovery(self):
        github=PrivateGitHub()
        with mock.patch("v13.chat_service.call",return_value={"running":True}):
            owner.monitor_and_alert(github,now=1900)
            self.path.unlink()
            self.assertEqual(owner.monitor_and_alert(github,now=1910)["status"],
                             "AWAITING_ANSWER")
        self.assertEqual(len(github.created),1)

    def test_error_with_later_partial_output_in_same_turn_stays_failed(self):
        with self.path.open("a",encoding="utf8") as log:
            log.write("assistant> partial output after an error\n")
        with mock.patch("v13.chat_service.call",return_value={"running":True}):
            self.assertEqual(monitor.check()["chat"],"CHAT_ERROR")

    def test_service_reconnect_with_only_old_answer_is_not_recovery(self):
        github=PrivateGitHub()
        self.path.write_text("[du> earlier question]\nassistant> Earlier answer.\n",encoding="utf8")
        with mock.patch("v13.chat_service.call",side_effect=ConnectionRefusedError):
            self.assertEqual(owner.monitor_and_alert(github,now=1900)["status"],"PUBLISHED")
        with mock.patch("v13.chat_service.call",return_value={"running":True}):
            self.assertEqual(owner.monitor_and_alert(github,now=1910)["status"],
                             "AWAITING_ANSWER")
            # An unrelated diagnostic line cannot make old evidence fresh.
            with self.path.open("a",encoding="utf8") as log:
                log.write("[V13] still running\n")
            self.assertEqual(owner.monitor_and_alert(github,now=1911)["status"],
                             "AWAITING_ANSWER")
            with self.path.open("a",encoding="utf8") as log:
                log.write("[du> new question]\nassistant> A new answer.\n")
            self.assertEqual(owner.monitor_and_alert(github,now=1920)["status"],"PUBLISHED")
        self.assertEqual(len(github.created),2)
        self.assertIn("V13RECOVERED",github.created[1]["title"])

    def test_safe_incident_cannot_export_unrecognized_error_text(self):
        body=monitor.safe_incident({"chat":"CHAT_ERROR","ai":"/private/runtime",
                                    "error":"secret prompt /private/model-path"})
        self.assertEqual(body["code"],"OTHER_EXCEPTION")
        self.assertEqual(body["ai"],"AI_OFFLINE")
        self.assertNotIn("private",json.dumps(body))

    def test_current_session_wins_over_lexically_newer_old_success(self):
        self.path.write_text("[du> old question]\nassistant> old answer\n",encoding="utf8")
        current=self.path.parent/"v13-session-20261112-100000-abcdef.log"
        current.write_text("[du> pending question]\ndu>\n",encoding="utf8")
        with mock.patch("v13.chat_service.call",return_value={
                "running":True,"last_session":current.name}):
            self.assertEqual(monitor.check()["chat"],"CHAT_PENDING")

    def test_empty_answer_and_runtime_notice_still_need_actual_answer(self):
        self.path.write_text("[du> pending]\nassistant> \n[V13] background status OK\ndu>\n",
                             encoding="utf8")
        with mock.patch("v13.chat_service.call",return_value={"running":True}):
            self.assertEqual(monitor.check()["chat"],"CHAT_PENDING")

    def test_diagnostic_after_other_output_still_wins_and_quoted_input_cannot_choose_error(self):
        self.path.write_text("[du> TimeoutError]\nassistant> earlier visible text\n"
                             "assistant> [SOURCE_SYSTEM_REPORT; Systemdiagnose; keine Modellantwort]\n"
                             "Permission denied: /private/file\n"
                             "Angenommene Eingabe (exakte Quelle): TimeoutError\n",encoding="utf8")
        with mock.patch("v13.chat_service.call",return_value={"running":True}):
            report=monitor.check()
        self.assertEqual(report["chat"],"CHAT_ERROR")
        self.assertEqual(report["error"],"PERMISSION")

    def test_offline_ai_also_triggers_critical_report(self):
        github=PrivateGitHub()
        self.path.unlink()
        with mock.patch("v13.chat_service.call",side_effect=ConnectionRefusedError):
            self.assertEqual(owner.monitor_and_alert(github,now=2000)["status"],"PUBLISHED")
        self.assertIn("SERVICE_OFFLINE",github.created[0]["title"])


if __name__=="__main__":
    unittest.main()
