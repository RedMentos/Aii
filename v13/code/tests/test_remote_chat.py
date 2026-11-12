"""End-to-end V13 private issue chat transmission and result lookup (offline)."""
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from v13 import owner_read_bridge as owner
from v13 import remote_chat
from v13 import remote_maintenance_bridge as bridge


class FakeGitHub:
    def __init__(self, issues):
        self.queue=issues
        self.comments_sent=[]
        self.closed=[]
    def check_private(self):return True
    def issues(self):return [i for i in self.queue if i["number"] not in self.closed]
    def comment(self,num,receipt):self.comments_sent.append((num,receipt))
    def close(self,num):self.closed.append(num)


class RemoteChatTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home=Path(tmp.name)
        root=self.home/".v13-private"
        root.mkdir(mode=0o700)
        logs=root/"console-logs"
        logs.mkdir(mode=0o700)
        jobs=root/"remote-chat-jobs"
        jobs.mkdir(mode=0o700)
        for name,value in [("ROOT",root),("LOGS",logs),("JOBS",jobs)]:
            p=mock.patch.object(remote_chat,name,value)
            p.start();self.addCleanup(p.stop)
        self.session="v13-session-20261112-121200-a1b2c3.log"
        self.path=logs/self.session
        self.path.write_text("V13 started\ndu>\n",encoding="utf8")
        self.path.chmod(0o600)
        self.id="a"*32
        self.cfg={"relay_repo":"RedMentos/Aiiii",
                  "installed_root":str(self.home),
                  "state_dir":str(self.home/"bridge-state"),
                  "keys":{"agent-owner":"ab"*32},
                  "permissions":{"agent-owner":["CHAT_SEND","CHAT_RESULT","UPDATE_REQUEST"]},
                  "authors":{"agent-owner":["RedMentos"]},
                  "remote_apply_enabled":False}
        self.now=1900

    def make_issue(self,command,args,number=4,ident=None):
        ident=ident or self.id
        body={"schema":owner.READ_SCHEMA,"id":ident,
              "command":command,"expires_at":self.now+500}
        if args is not None:body["args"]=args
        return {"number":number,"title":"V13READ:"+ident,
                "body":json.dumps(body),"user":{"login":"RedMentos"},
                "created_at":datetime.fromtimestamp(self.now,timezone.utc).isoformat()}

    def receipt(self, offset=None, session=None):
        return {"status":"SENT", "session":session or self.session,
                "offset":self.path.stat().st_size if offset is None else offset,
                "input_logged":True}

    def test_remote_send_issue_then_get_exact_response_from_running_ai(self):
        def rpc(method, **kw):
            if method=="state":return {"running":True,"last_session":self.session}
            if method=="send":
                receipt=self.receipt()
                self.assertEqual(kw["line"],"Hallo V13")
                with self.path.open("a",encoding="utf8") as out:
                    out.write("[du> Hallo V13]\nassistant> Hallo, ich bin V13.\n\ndu>\n")
                return receipt
            raise AssertionError("Unexpected RPC "+method)
        send=self.make_issue("CHAT_SEND",{"text":"Hallo V13"})
        client=FakeGitHub([send])
        with mock.patch("v13.chat_service.call",side_effect=rpc):
            self.assertEqual(owner.poll_once(client,self.cfg,now=self.now)["processed"],1)
        sent=client.comments_sent[0][1]["device_status"]
        self.assertEqual(sent["status"],"SENT")
        self.assertEqual(sent["request_id"],self.id)
        self.assertEqual(len(list(remote_chat.JOBS.iterdir())),1)
        # Same request ID cannot send twice even after an issue is reopened.
        client.closed.clear()
        with mock.patch("v13.chat_service.call",side_effect=AssertionError("replayed")):
            owner.poll_once(client,self.cfg,now=self.now)
        self.assertEqual(len(client.comments_sent),1)

        receive=self.make_issue("CHAT_RESULT",{"request_id":self.id},number=5,ident="b"*32)
        client=FakeGitHub([receive])
        self.assertEqual(owner.poll_once(client,self.cfg,now=self.now)["processed"],1)
        result=client.comments_sent[0][1]["device_status"]
        self.assertEqual(result["status"],"ANSWER_VISIBLE")
        self.assertFalse(result["complete"])
        self.assertEqual(result["correlation"],"ATOMIC_INPUT_WINDOW")
        self.assertIn("Hallo, ich bin V13",result["output"])
        self.assertNotIn("[du> Hallo V13]",result["output"])

    def test_early_terminal_prompt_does_not_hide_async_model_reply(self):
        # The native plain V13 UI redraws "du>" immediately after queueing
        # a question; an actual model answer arrives only later.
        def fake_rpc(method,**kw):
            if method=="state":return {"running":True,"last_session":self.session}
            return self.receipt()
        with mock.patch("v13.chat_service.call",side_effect=fake_rpc):
            remote_chat.send(self.id,"Is the model alive?")
        with self.path.open("a",encoding="utf8") as log:
            log.write("[du> Is the model alive?]\ndu>\n")
        self.assertEqual(remote_chat.result(self.id)["status"],"GENERATING")
        with self.path.open("a",encoding="utf8") as log:
            log.write("\nassistant> Yes, I can answer your question.\n")
        res=remote_chat.result(self.id)
        self.assertEqual(res["status"],"ANSWER_VISIBLE")
        self.assertIn("Yes, I can answer",res["output"])

    def test_real_phone_missing_path_error_is_visible_not_success(self):
        def rpc(method,**kw):
            if method=="state":return {"running":True,"last_session":self.session}
            if method=="send":
                receipt=self.receipt()
                with self.path.open("a",encoding="utf8") as out:
                    out.write("[du> Hi]\n[Fehler] [Errno 2] No such file or directory: 'abcdef123'\n\ndu>\n")
                return receipt
        with mock.patch("v13.chat_service.call",side_effect=rpc):
            self.assertEqual(remote_chat.send(self.id,"Hi")["status"],"SENT")
        result=remote_chat.result(self.id)
        self.assertEqual(result["status"],"MODEL_ERROR")
        self.assertIn("[Errno 2]",result["output"])

    def test_reject_fake_author_shell_operator_and_injected_schema(self):
        values=[
            ("CHAT_SEND",{"text":":shutdown"}),
            ("CHAT_SEND",{"text":"hi\n:shutdown"}),
            ("CHAT_SEND",{"text":"z"*1600}),
            ("CHAT_SEND",{"text":"Hi","shell":"rm -rf /"}),
            ("CHAT_RESULT",{"request_id":"../../secrets"}),
            ("UPDATE_REQUEST",{"shell":"bash"}),
        ]
        for cmd,args in values:
            issue=self.make_issue(cmd,args)
            with self.subTest(cmd=cmd,args=str(args)[:60]),self.assertRaises(bridge.Denied):
                owner.validate_owner_read(issue,self.cfg,now=self.now)
        imp=self.make_issue("CHAT_SEND",{"text":"Hi"})
        imp["user"]["login"]="Impostor"
        with self.assertRaises(bridge.Denied):
            owner.validate_owner_read(imp,self.cfg,now=self.now)
        with self.assertRaises(remote_chat.ChatDenied):
            remote_chat.send("c"*32,":shutdown")

    def test_result_redacts_token_and_is_bounded(self):
        with mock.patch("v13.chat_service.call",side_effect=lambda method,**kw:(
            {"running":True,"last_session":self.session} if method=="state"
            else self.receipt())):
            remote_chat.send(self.id,"Test")
        with self.path.open("a",encoding="utf8") as out:
            out.write("[du> Test]\nassistant> github_pat_abcdefghijklmnopqrstuvwxyz\n\ndu>\n")
        data=remote_chat.result(self.id)
        self.assertEqual(data["status"],"ANSWER_VISIBLE")
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz",str(data))
        self.assertIn("[TOKEN_REDACTED]",data["output"])

    def test_exact_remote_diagnostic_command_executes_and_arbitrary_operator_denied(self):
        self.cfg["permissions"]["agent-owner"].append("CHAT_OPERATOR")
        def rpc(method,**kw):
            if method=="state":return {"running":True,"last_session":self.session}
            if method=="send":
                receipt=self.receipt()
                self.assertEqual(kw["line"],":doctor")
                with self.path.open("a",encoding="utf8") as out:
                    out.write("[du> :doctor]\n[V13] doctor OK\n\ndu>\n")
                return receipt
            raise AssertionError(method)
        issue=self.make_issue("CHAT_OPERATOR",{"command":":doctor"})
        client=FakeGitHub([issue])
        with mock.patch("v13.chat_service.call",side_effect=rpc):
            self.assertEqual(owner.poll_once(client,self.cfg,now=self.now)["processed"],1)
        self.assertEqual(client.comments_sent[0][1]["device_status"]["status"],"SENT")
        self.assertIn("doctor OK",remote_chat.result(self.id)["output"])
        invalid=self.make_issue("CHAT_OPERATOR",{"command":":shutdown"},ident="b"*32)
        with self.assertRaises(bridge.Denied):
            owner.validate_owner_read(invalid,self.cfg,now=self.now)

    def test_owner_can_revoke_and_enable_explicit_private_log_diagnostics(self):
        from v13 import mobile_dashboard as ui
        self.cfg["permissions"]["agent-owner"].extend(["LOG_SHARING_ON","LOG_SHARING_OFF"])
        for command,enabled in (("LOG_SHARING_ON",True),("LOG_SHARING_OFF",False)):
            issue=self.make_issue(command,None,number=7 if enabled else 8,
                                  ident=("b" if enabled else "c")*32)
            client=FakeGitHub([issue])
            with mock.patch.object(ui,"set_remote_full_console") as full, \
                 mock.patch.object(ui,"set_remote_log_sharing") as errors:
                self.assertEqual(owner.poll_once(client,self.cfg,now=self.now)["processed"],1)
            full.assert_called_once_with(enabled)
            errors.assert_called_once_with(enabled)
            self.assertEqual(client.comments_sent[0][1]["device_status"]["status"],
                             "ENABLED" if enabled else "DISABLED")

    def test_no_running_ai_refuses_not_faked_accepted(self):
        with mock.patch("v13.chat_service.call",return_value={"running":False}):
            data=remote_chat.send(self.id,"Hi")
        self.assertEqual(data["status"],"NOT_RUNNING")
        self.assertEqual(list(remote_chat.JOBS.iterdir()),[])

    def test_native_system_report_never_returns_answer_or_quoted_user_source(self):
        def rpc(method,**kw):
            if method=="state":return {"running":True,"last_session":self.session}
            receipt=self.receipt()
            with self.path.open("a",encoding="utf8") as out:
                out.write("[du> Hi]\nassistant> [SOURCE_SYSTEM_REPORT; Systemdiagnose; keine Modellantwort]\n"
                          "Zeitbudget erreicht: /private/model-path\n"
                          "Angenommene Eingabe (exakte Quelle): private question\n")
            return receipt
        with mock.patch("v13.chat_service.call",side_effect=rpc):
            remote_chat.send(self.id,"Hi")
        data=remote_chat.result(self.id)
        self.assertEqual(data["status"],"MODEL_ERROR")
        self.assertEqual(data["error_code"],"MODEL_TIMEOUT")
        self.assertFalse(data["complete"])
        self.assertNotIn("private question",str(data))
        self.assertNotIn("/private/model-path",str(data))

    def test_rejected_send_cannot_claim_a_later_local_answer(self):
        def rpc(method,**kw):
            if method=="state":return {"running":True,"last_session":self.session}
            return {"status":"REJECTED"}
        with mock.patch("v13.chat_service.call",side_effect=rpc):
            self.assertEqual(remote_chat.send(self.id,"remote question")["status"],"REJECTED")
        with self.path.open("a",encoding="utf8") as out:
            out.write("[du> local question]\nassistant> local answer\n")
        data=remote_chat.result(self.id)
        self.assertEqual(data["status"],"REJECTED")
        self.assertNotIn("local answer",str(data))

    def test_interrupted_send_stays_uncertain_and_cannot_be_replayed(self):
        def rpc(method,**kw):
            if method=="state":return {"running":True,"last_session":self.session}
            with self.path.open("a",encoding="utf8") as out:
                out.write("[du> maybe accepted]\nassistant> maybe generated\n")
            raise TimeoutError("secret path /private/chat.sock")
        with mock.patch("v13.chat_service.call",side_effect=rpc):
            data=remote_chat.send(self.id,"maybe accepted")
        self.assertEqual(data["status"],"SEND_UNCONFIRMED")
        self.assertEqual(remote_chat.result(self.id)["status"],"SEND_UNCONFIRMED")
        with self.assertRaises(remote_chat.ChatDenied):
            remote_chat.send(self.id,"maybe accepted")
        self.assertNotIn("private",str(data))

    def test_old_service_without_atomic_receipt_never_uses_loose_snapshot(self):
        def rpc(method,**kw):
            if method=="state":return {"running":True,"last_session":self.session}
            with self.path.open("a",encoding="utf8") as out:
                out.write("[du> another client]\nassistant> another answer\n")
            return {"status":"SENT"}
        with mock.patch("v13.chat_service.call",side_effect=rpc):
            self.assertEqual(remote_chat.send(self.id,"remote question")["status"],
                             "CORRELATION_UNAVAILABLE")
        self.assertEqual(remote_chat.result(self.id)["status"],"CORRELATION_UNAVAILABLE")

    def test_atomic_receipt_wins_over_competing_send_and_session_restart(self):
        new_session="v13-session-20261112-121201-b1b2c3.log"
        new_path=remote_chat.LOGS/new_session
        def rpc(method,**kw):
            if method=="state":
                # A restart/concurrent client occurs after this snapshot.
                return {"running":True,"last_session":self.session}
            with self.path.open("a",encoding="utf8") as out:
                out.write("[du> competing old question]\nassistant> wrong old answer\n")
            new_path.write_text("[du> competing new question]\nassistant> wrong new answer\n")
            offset=new_path.stat().st_size
            with new_path.open("a",encoding="utf8") as out:
                out.write("[du> target question]\nassistant> target answer\n")
            return self.receipt(offset,new_session)
        with mock.patch("v13.chat_service.call",side_effect=rpc):
            self.assertEqual(remote_chat.send(self.id,"target question")["status"],"SENT")
        data=remote_chat.result(self.id)
        self.assertEqual(data["status"],"ANSWER_VISIBLE")
        self.assertIn("target answer",data["output"])
        self.assertNotIn("wrong",data["output"])
        self.assertNotIn("competing",data["output"])

    def test_next_input_never_proves_previous_answer_complete(self):
        def rpc(method,**kw):
            if method=="state":return {"running":True,"last_session":self.session}
            receipt=self.receipt()
            with self.path.open("a",encoding="utf8") as out:
                out.write("[du> first question]\nassistant> partial first answer\n"
                          "[du> second question]\nassistant> uncertain output\n")
            return receipt
        with mock.patch("v13.chat_service.call",side_effect=rpc):
            remote_chat.send(self.id,"first question")
        data=remote_chat.result(self.id)
        self.assertEqual(data["status"],"AMBIGUOUS_TURN")
        self.assertFalse(data["complete"])
        self.assertNotIn("uncertain output",str(data))


if __name__=="__main__":
    unittest.main()
