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
    def test_command_changes_real_next_turn_effort_not_official_age(self):
        with tempfile.TemporaryDirectory() as dirname:
            home = Path(dirname)
            cfg = initialize(home)
            store = Store(home)
            try:
                fake = SimpleNamespace(home=home, cfg=cfg, store=store)
                operator = Operator(fake)
                # A bare level is an explicit request to test this level,
                # not silently "shadow", even following a prior shadow choice.
                shadow = json.loads(operator.run(":labage 8 shadow"))
                self.assertEqual(shadow["stage"], 8)
                self.assertEqual(shadow["mode"], "shadow")
                self.assertEqual(effort.age_limits(fake.age)["focal_depth"], 1)
                changed = json.loads(operator.run(":labage 8"))
                self.assertTrue(changed["config_persisted"])
                self.assertEqual(changed["stage"], 8)
                self.assertEqual(changed["mode"], "active")
                limits = effort.age_limits(fake.age, "GREEN")
                self.assertTrue(limits["lab_compute_active"])
                self.assertEqual(limits["lab_stage"], 8)
                self.assertEqual(limits["focal_depth"], 3)
                self.assertEqual(limits["lab_compute_gate"], "APPLIED")
                self.assertEqual(limits["stage"], 0)
                self.assertFalse(fake.age.may("simple_tool_choice"))
                self.assertEqual(cfg["learning_mode"], "RECORD_ONLY")
                snapshot = json.loads(operator.run(":age"))
                self.assertEqual(snapshot["official"]["system_stage"], 0)
                self.assertEqual(snapshot["laboratory"]["stage"], 8)
                self.assertEqual(snapshot["laboratory"]["mode"], "active")
                with self.assertRaises(ValueError):
                    operator.run(":labage 11")
                self.assertEqual(lab_age.read(home)["stage"], 8)
            finally:
                store.close()


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
