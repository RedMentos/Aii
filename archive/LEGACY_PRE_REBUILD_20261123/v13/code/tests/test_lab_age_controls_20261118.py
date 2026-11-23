"""Regression: owner-selected lab stage must persist, reach the actual runner,
and be visible in the real local WebView POST/GET without changing earned Age.

Temporary HOME and a loopback fake console only. No GGUF, phone or private
tokens. The UI test does not imply native compute improved on the Redmi.
"""
import json
import os
from pathlib import Path
import re
import select
import subprocess
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from v13 import lab_age, effort
from v13.config import initialize
from v13.operator import Operator
from v13.store import Store


class LabOperatorEndToEnd(unittest.TestCase):
    def test_x10_grants_actual_test_rights_but_not_earned_age_or_compute(self):
        from v13.lab_age_runtime import LaboratoryAgeControl
        from v13.age import AgeControl
        from v13.agi.tools import ToolRegistry
        with tempfile.TemporaryDirectory() as dirname:
            home = Path(dirname)
            cfg = initialize(home)
            store = Store(home)
            try:
                earned = AgeControl(store, cfg)
                lab = LaboratoryAgeControl(store, cfg)
                self.assertEqual(lab.system_stage(), 0)
                self.assertFalse(earned.may("simple_tool_choice"))
                self.assertTrue(lab.may("simple_tool_choice"))
                self.assertTrue(lab.may("tool_learning"))
                self.assertTrue(lab.may("active_info_search"))
                self.assertFalse(lab.may("body_swap"))  # structural lock
                self.assertFalse(lab.may("edit_hard_rules"))
                self.assertFalse(lab.may("simple_tool_choice", hard_rule_block=True))
                self.assertFalse(lab.may("simple_tool_choice", user_permissions=set()))
                self.assertFalse(lab.may("tool_learning", resource_mode="RED"))
                self.assertEqual(lab.budgets("system")["focal_depth"],
                                 earned.budgets("system")["focal_depth"])
                self.assertTrue(lab.view()["laboratory"]["feature_gates_live"])
                self.assertEqual(lab.view()["system_stage"], 0)
                registry = ToolRegistry(store, age=lab)
                registry.enable("calc")
                executed = registry.call("calc", {"expression": "2+3"}, origin="SYSTEM")
                self.assertEqual(executed["status"], "EXECUTED")
                self.assertEqual(executed["result"], 5)
                lab_age.save(home, stage=10, mode="shadow")
                self.assertFalse(lab.may("simple_tool_choice"))
                self.assertEqual(lab_age.effective_stage(home), None)
                lab_age.save(home, stage=10, mode="active")
                self.assertTrue(lab.may("simple_tool_choice"))
                lab_age.save(home, stage=0, mode="active")
                self.assertFalse(lab.may("simple_tool_choice"))
                self.assertEqual(lab.simulated_stage(), None)
            finally:
                store.close()

    def test_explicit_worker_shadow_training_never_mutates_persisted_learning(self):
        from v13.lab_age import LabConfig
        import threading
        with tempfile.TemporaryDirectory() as dirname:
            home = Path(dirname)
            cfg = initialize(home)
            live = LabConfig(cfg, home)
            self.assertEqual(live["learning_mode"], "RECORD_ONLY")
            seen = []
            with live.shadow_training():
                self.assertEqual(live["learning_mode"], "SHADOW_UPDATE")
                self.assertEqual(live.get("learning_mode"), "SHADOW_UPDATE")
                worker = threading.Thread(target=lambda: seen.append(live["learning_mode"]))
                worker.start()
                worker.join(2)
                self.assertEqual(seen, ["RECORD_ONLY"])
            self.assertEqual(live["learning_mode"], "RECORD_ONLY")
            self.assertEqual(live.get("learning_mode"), "RECORD_ONLY")
            self.assertEqual(json.loads((home/"config/settings.json").read_text())["learning_mode"],
                             "RECORD_ONLY")
            lab_age.save(home, stage=10, mode="off")
            with self.assertRaises(ValueError):
                with live.shadow_training():
                    pass
            lab_age.save(home, stage=1, mode="active")
            with self.assertRaises(ValueError):
                with live.shadow_training():
                    pass

    def test_source_pinned_integrated_stage_really_contains_age_and_learning_hooks(self):
        import importlib.util
        from v13.lab_age_runtime import LaboratoryAgeControl
        code = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "v13_lab_stage_test", code/"scripts/stage_integrated_candidate.py")
        stage_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stage_mod)
        with tempfile.TemporaryDirectory(prefix="v13-age-stage-") as tmp:
            staged = Path(tmp)/"staged"
            manifest = stage_mod.stage(code, staged)
            self.assertIn("v13/runtime.py", manifest["replaced_files"])
            self.assertIn("v13/operator.py", manifest["replaced_files"])
            text_runtime = (staged/"v13/runtime.py").read_text()
            text_operator = (staged/"v13/operator.py").read_text()
            text_age = (staged/"v13/age.py").read_text()
            self.assertIn("LabConfig(initialize(home),home)", text_runtime)
            self.assertIn("kind in ('shadow','lab_shadow')", text_runtime)
            self.assertIn("self.cfg.shadow_training()", text_runtime)
            self.assertIn("r.enqueue(job,args[0]", text_operator)
            self.assertIn("LaboratoryAgeControl", text_age)
            self.assertNotIn("lab_shadow", (code/"v13/runtime.py").read_text())
            self.assertNotIn("LabConfig(initialize", (code/"v13/runtime.py").read_text())
            for file in ("v13/age.py","v13/runtime.py","v13/operator.py","v13/ui.py"):
                compile((staged/file).read_bytes(), str(staged/file), "exec")
            # Execute the *real generated worker arm* with a tiny synthetic
            # Learner, rather than merely looking for string markers.
            import ast
            import queue
            import time
            from v13.lab_age import LabConfig
            syntax = ast.parse(text_runtime)
            cls = next(n for n in syntax.body if isinstance(n,ast.ClassDef)
                       and n.name == "Runtime")
            method = next(n for n in cls.body if isinstance(n,ast.FunctionDef)
                          and n.name == "_worker")
            unit = ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[]))
            namespace = {"time":time,"queue":queue}
            exec(compile(unit, str(staged/"v13/runtime.py"),"exec"),namespace)
            home = Path(tmp)/"owner"
            persisted = initialize(home)
            config = LabConfig(persisted,home)
            record = []
            stop = threading.Event()
            class MiniStore:
                def pending_turns(self,*_):return []
                def log(self,kind,_,meta):
                    record.append((kind,meta.get("error")))
                    stop.set()
            class MiniLearner:
                def shadow(self):
                    record.append(("LEARNER_EXECUTED",config["learning_mode"]))
                    stop.set()
                    return "SHADOW_CANDIDATE_ONLY"
            jobs = queue.Queue()
            jobs.put(("lab_shadow","route",0,time.monotonic()))
            fake = SimpleNamespace(stop=stop,paused=False,lock=threading.RLock(),
                jobs=jobs,queued_bytes=0,current=None,cancel_event=threading.Event(),
                store=MiniStore(),cfg=config,learner=MiniLearner(),
                _session_local=threading.local(),status="READY",
                notice=lambda note:record.append(("notice",note)))
            namespace["_worker"](fake)
            self.assertIn(("LEARNER_EXECUTED","SHADOW_UPDATE"),record)
            self.assertEqual(config["learning_mode"],"RECORD_ONLY")
            self.assertEqual(jobs.unfinished_tasks,0)
            # Revoking X10 before execution prevents any training attempt.
            record.clear()
            stop.clear()
            lab_age.save(home,mode="off")
            jobs.put(("lab_shadow","route",0,time.monotonic()))
            namespace["_worker"](fake)
            self.assertFalse(any(kind=="LEARNER_EXECUTED" for kind,_ in record))
            self.assertTrue(any(kind=="job_error" for kind,_ in record))
            self.assertEqual(config["learning_mode"],"RECORD_ONLY")
            self.assertEqual(jobs.unfinished_tasks,0)

class BrowserLabAgeEndToEnd(unittest.TestCase):
    def test_real_webview_stage_apply_readback_status_and_invalid_requests(self):
        with tempfile.TemporaryDirectory(prefix="v13-lab-webview-") as dirname:
            home = Path(dirname)
            env = dict(os.environ, HOME=str(home), V13_UI_PORT="0",
                       V13_UI_NO_AUTO_OPEN="1")
            script = """
from v13 import mobile_dashboard as ui
class FakeConsole:
    def state(self):
        return {"running":False,"exit_code":None,"daemon":"READY",
                "service":"READY","autostart":False}
    def output(self,limit=50000): return ""
    def saved_sessions(self): return []
    def transcript(self,*,all_sessions=True): return ""
ui.RemoteConsole = FakeConsole
ui.summary = lambda: {"native_probe":"NO_PROBE","roles":{}}
ui.serve(open_browser=False)
"""
            proc = subprocess.Popen([sys.executable, "-c", script],
                cwd=str(Path(__file__).resolve().parents[1]), env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                self.assertTrue(select.select([proc.stdout], [], [], 12)[0],
                                "local WebView server never opened")
                url=proc.stdout.readline().partition(": ")[2].strip()
                self.assertTrue(url.startswith("http://127.0.0.1:"))
                def get(segment=""):
                    with urlopen(urljoin(url, segment),timeout=8) as response:
                        self.assertEqual(response.status,200)
                        return response.read().decode("utf-8")
                page=get()
                self.assertIn('id="lab-age-stage"', page)
                self.assertIn('id="lab-age-live"', page)
                self.assertIn("Labor-Age",page)
                self.assertIn("AKTIV ANGEFORDERT",page)
                csrf=re.search(r'name="csrf" value="([a-f0-9]{48})"',page)
                self.assertIsNotNone(csrf)
                key=csrf.group(1)
                state=json.loads(get("state"))["lab_age"]
                self.assertEqual(state["official_stage"],0)
                self.assertEqual(state["stage"],10)
                self.assertEqual(state["mode"],"active")
                self.assertFalse(state["config_persisted"])
                def set_lab(stage,mode,csrf=key):
                    body=urlencode({"action":"lab_age_set", "lab_stage":str(stage),
                                    "lab_mode":mode,"csrf":csrf}).encode()
                    req=Request(urljoin(url,"action"),body,
                                headers={"Content-Type":"application/x-www-form-urlencoded",
                                         "Accept":"application/json"})
                    with urlopen(req,timeout=8) as response:
                        return response.status,json.loads(response.read())
                code,ack=set_lab(7,"active")
                self.assertEqual(code,200)
                self.assertTrue(ack["ok"])
                self.assertEqual(ack["lab_age"]["stage"],7)
                self.assertEqual(ack["lab_age"]["mode"],"active")
                self.assertTrue(ack["lab_age"]["config_persisted"])
                self.assertEqual(json.loads(get("state"))["lab_age"]["stage"],7)
                saved=home/"v13/config/lab-age.json"
                self.assertTrue(saved.is_file())
                self.assertEqual(saved.stat().st_mode&0o077,0)
                self.assertEqual(json.loads(saved.read_text())["stage"],7)
                rendered=get()
                self.assertIn("Labor-Age <strong>7</strong>",rendered)
                self.assertIn("AKTIV ANGEFORDERT",rendered)
                code,ack=set_lab(9,"shadow")
                self.assertEqual(code,200)
                self.assertEqual(ack["lab_age"]["mode"],"shadow")
                self.assertFalse(ack["lab_age"]["compute_requested"])
                self.assertEqual(json.loads(get("state"))["lab_age"]["stage"],9)
                for invalid_stage,invalid_mode in ((11,"active"),(7,"not-a-mode")):
                    with self.subTest(stage=invalid_stage,mode=invalid_mode):
                        with self.assertRaises(HTTPError) as denied:
                            set_lab(invalid_stage,invalid_mode)
                        self.assertEqual(denied.exception.code,400)
                self.assertEqual(lab_age.read(home/"v13"),{
                    "schema":"v13.lab-age/1","stage":9,"mode":"shadow"})
                with self.assertRaises(HTTPError) as denied:
                    set_lab(8,"active",csrf="0"*48)
                self.assertEqual(denied.exception.code,403)
                self.assertEqual(lab_age.read(home/"v13")["mode"],"shadow")
            finally:
                proc.terminate()
                proc.wait(timeout=8)
                proc.stdout.close()
                proc.stderr.close()


if __name__=="__main__":
    unittest.main()
