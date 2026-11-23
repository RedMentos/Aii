"""Run117AX optional JEF/C2 route binding to persisted C5/C6 operator CLI."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.run63_jef_c3_native import cohort
from scripts import jef_c3_c5_c6_operator_cli as cli
from v13.runtime import Runtime

class JefRouteOperatorCli(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.rows=cohort()

    def inp(self,row,name="input.json"):
        data={"project":row["id"],"domain":row["domain"],
              "policy_source":row["b2_source"],
              "sheet_source":row["b1_source"],"current":row["current"]}
        path=self.root/name
        path.write_text(json.dumps(data),encoding="utf-8")
        return path,data

    def safe(self,result):
        self.assertEqual(result["delivery_authority"],0)
        self.assertEqual(result["learning_authority"],0)
        self.assertEqual(result["tool_dispatches"],0)
        self.assertFalse(result["output_committed"])
        self.assertFalse(result["native_proof"])
        self.assertFalse(result["real_tty_approved"])
        self.assertEqual(result["age0"],"RECORD_ONLY")
        for key in ("policy_source","sheet_source","current","native_output"):
            self.assertNotIn(key,result)

    def test_six_optin_route_bound_drafts_and_restart(self):
        for i,row in enumerate(self.rows):
            for mode in ("synthetic_exact","synthetic_wrong"):
                with self.subTest(id=row["id"],mode=mode):
                    p,data=self.inp(row,f"case_{i}_{mode}.json")
                    home=self.root/f"home_{i}_{mode}"
                    result=cli.run(home,p,mode,operator_opt_in=True,
                                   callback_opt_in=True,route_shadow=True)
                    self.assertEqual(result["status"],
                                     "SHADOW_DRAFT_PREFLIGHT_READY",result)
                    self.assertEqual(result["route_shadow_status"],
                                     cli.JEF_C2_ROUTE_READY)
                    self.assertFalse(result["route_applied"])
                    self.assertEqual(result["c2_advisory_status"],"NOT_SUPPLIED")
                    self.assertEqual(result["c6_status"],"NEEDS_REAL_TTY_APPROVAL")
                    self.assertTrue(result["preflight_only"])
                    self.assertTrue(result["no_live_output"])
                    self.assertFalse(result["native_model_called"])
                    self.assertIsNone(result["native_process_reaped"])
                    self.assertEqual(result["source_only_fallback"],
                                     mode=="synthetic_wrong")
                    self.assertRegex(result["route_prompt_sha256"],r"^[a-f0-9]{64}$")
                    self.safe(result)
                    raw=json.dumps(result)
                    for source in (data["policy_source"],data["sheet_source"],
                                   data["current"]):
                        self.assertNotIn(source,raw)
                    runtime=Runtime(home)
                    try:
                        messages=runtime.store.rows(
                            "SELECT text,status FROM messages WHERE role='assistant'")
                        self.assertEqual(len(messages),1)
                        self.assertEqual(messages[0]["text"],row["oracle_action"])
                        self.assertEqual(messages[0]["status"],"INTERRUPTED")
                        self.assertEqual(runtime.store.one(
                            "SELECT COUNT(*) AS n FROM messages "
                            "WHERE role='assistant' AND status='FINAL'")["n"],0)
                    finally:
                        runtime.close()

    def test_route_flag_alone_never_opens_input_or_runtime(self):
        home=self.root/"not-created"
        missing=self.root/"missing.json"
        for kwargs in ({"route_shadow":True},
                       {"route_shadow":True,"operator_opt_in":True},
                       {"route_shadow":True,"callback_opt_in":True}):
            out=cli.run(home,missing,"synthetic_exact",**kwargs)
            self.assertEqual(out["status"],"OFF")
            self.assertFalse(out["input_read"])
            self.assertFalse(out["runtime_opened"])
            self.safe(out)
        self.assertFalse(home.exists())

    def test_invalid_route_flag_rejected_before_read(self):
        home=self.root/"not-created";missing=self.root/"missing.json"
        out=cli.run(home,missing,"synthetic_exact",
                    operator_opt_in=True,callback_opt_in=True,route_shadow=1)
        self.assertEqual(out["status"],"ROUTE_FLAG_RED")
        self.assertFalse(out["input_read"])
        self.assertFalse(out["runtime_opened"])
        self.assertFalse(home.exists())
        self.safe(out)

    def test_forged_route_prompt_refused_before_c5_draft(self):
        row=self.rows[0];p,_=self.inp(row)
        home=self.root/"forged"
        with patch.object(cli,"propose_jef_c2_route",return_value={
            "status":cli.JEF_C2_ROUTE_READY,
            "formatter_route":"JEF_TYPED_C3_FORMATTER_ONLY",
            "route_applied":False,
            "messages_sha256":"0"*64,
            "source_ref_sha256":[],
            "typed_jef_action":row["oracle_action"],
            "source_rechecked":True,
            "delivery_authority":0,"learning_authority":0,"tool_dispatches":0,
        }):
            out=cli.run(home,p,"synthetic_exact",
                        operator_opt_in=True,callback_opt_in=True,
                        route_shadow=True)
        self.assertEqual(out["status"],"ROUTE_SOURCE_RED",out)
        self.assertNotIn("draft_message_id",out)
        self.safe(out)
        r=Runtime(home)
        try:
            self.assertEqual(r.store.one(
                "SELECT COUNT(*) AS n FROM actions")["n"],0)
            self.assertEqual(r.store.one(
                "SELECT COUNT(*) AS n FROM messages WHERE role='assistant'")["n"],0)
        finally:
            r.close()

    def test_native_missing_model_refuses_without_route(self):
        row=self.rows[0];p,_=self.inp(row)
        home=self.root/"no-model"
        out=cli.run(home,p,"native",operator_opt_in=True,
                    callback_opt_in=True,route_shadow=True)
        self.assertEqual(out["status"],"NATIVE_BINDING_RED",out)
        self.assertNotIn("route_shadow_status",out)
        self.assertFalse(out["native_model_called"])
        self.safe(out)

    def test_command_line_route_flag_is_explicit(self):
        row=self.rows[0];p,_=self.inp(row)
        home=self.root/"cli-home"
        script=Path(cli.__file__).resolve()
        command=[sys.executable,str(script),"--home",str(home),
                 "--input-file",str(p),"--mode","synthetic_exact",
                 "--operator-opt-in","--callback-opt-in","--route-shadow"]
        completed=subprocess.run(command,capture_output=True,text=True,
                                 timeout=30,check=False)
        self.assertEqual(completed.returncode,0,completed.stderr)
        out=json.loads(completed.stdout)
        self.assertEqual(out["status"],"SHADOW_DRAFT_PREFLIGHT_READY",out)
        self.assertEqual(out["route_shadow_status"],cli.JEF_C2_ROUTE_READY)
        self.safe(out)

if __name__=="__main__":
    unittest.main()
