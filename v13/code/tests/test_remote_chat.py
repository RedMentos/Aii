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

    def test_remote_send_issue_then_get_exact_response_from_running_ai(self):
        def rpc(method, **kw):
            if method=="state":return {"running":True,"last_session":self.session}
            if method=="send":
                self.assertEqual(kw["line"],"Hallo V13")
                with self.path.open("a",encoding="utf8") as out:
                    out.write("[du> Hallo V13]\nassistant> Hallo, ich bin V13.\n\ndu>\n")
                return {"status":"SENT"}
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
        self.assertEqual(result["status"],"ANSWERED")
        self.assertIn("Hallo, ich bin V13",result["output"])
        self.assertNotIn("[du> Hallo V13]",result["output"])

    def test_real_phone_missing_path_error_is_visible_not_success(self):
        def rpc(method,**kw):
            if method=="state":return {"running":True,"last_session":self.session}
            if method=="send":
                with self.path.open("a",encoding="utf8") as out:
                    out.write("[du> Hi]\n[Fehler] [Errno 2] No such file or directory: 'abcdef123'\n\ndu>\n")
                return {"status":"SENT"}
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
            else {"status":"SENT"})):
            remote_chat.send(self.id,"Test")
        with self.path.open("a",encoding="utf8") as out:
            out.write("[du> Test]\nassistant> github_pat_abcdefghijklmnopqrstuvwxyz\n\ndu>\n")
        data=remote_chat.result(self.id)
        self.assertEqual(data["status"],"ANSWERED")
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz",str(data))
        self.assertIn("[TOKEN_REDACTED]",data["output"])

    def test_no_running_ai_refuses_not_faked_accepted(self):
        with mock.patch("v13.chat_service.call",return_value={"running":False}):
            data=remote_chat.send(self.id,"Hi")
        self.assertEqual(data["status"],"NOT_RUNNING")
        self.assertEqual(list(remote_chat.JOBS.iterdir()),[])


if __name__=="__main__":
    unittest.main()
