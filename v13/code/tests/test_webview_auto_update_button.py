"""Actual loopback HTTP regression for the native WebView auto-update toggle.

No JS execution, GitHub, Android, model download or live phone state: the
real Python UI GET / POST / 303 / GET and shared worker marker are exercised.
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
from urllib.error import HTTPError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


class AutoUpdateWebViewButton(unittest.TestCase):
    def test_native_button_can_enable_disable_reenable_and_refuses_bad_csrf(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            env = dict(os.environ, HOME=str(home), V13_UI_PORT="0",
                       V13_UI_NO_AUTO_OPEN="1")
            script = '''
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
'''
            proc = subprocess.Popen([sys.executable, "-c", script],
                cwd=str(Path(__file__).resolve().parents[1]), env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                self.assertTrue(select.select([proc.stdout], [], [], 12)[0],
                                "local dashboard must open an HTTP port")
                url = proc.stdout.readline().partition(": ")[2].strip()
                self.assertTrue(url.startswith("http://127.0.0.1:"))
                post_url = urljoin(url,"action")
                marker = home / ".v13-private" / "auto-source-update.enabled"

                def page():
                    with urlopen(url,timeout=8) as response:
                        self.assertEqual(response.status,200)
                        return response.read().decode("utf-8")

                def native_button(html, command):
                    forms=re.findall(
                        r'<form[^>]*data-native-submit="1"[^>]*>(.*?)</form>',
                        html,re.S)
                    found=[f for f in forms
                           if re.search(r'name="action" value="'+command+r'"',f)]
                    self.assertEqual(len(found),1,
                                     "the real button must be a native form")
                    self.assertRegex(found[0],r'name="csrf" value="[a-f0-9]{48}"')
                    csrf=re.search(r'name="csrf" value="([a-f0-9]{48})"',
                                   found[0]).group(1)
                    return csrf

                def toggle(command,csrf):
                    body=urlencode({"action":command,"csrf":csrf}).encode()
                    req=Request(post_url,body,
                                headers={"Content-Type":"application/x-www-form-urlencoded"})
                    with urlopen(req,timeout=10) as response:
                        self.assertEqual(response.status,200,
                                         "303 must finish at the rendered GET")
                        self.assertEqual(response.geturl(),url,
                                         "POST must not remain in browser history")
                        return response.read().decode("utf-8")

                initial=page()
                self.assertIn("Auto-Updates EIN",initial)
                csrf=native_button(initial,"auto_enable")
                enabled=toggle("auto_enable",csrf)
                self.assertEqual(marker.read_text(),"yes\\n".replace("\\\\n","\\n"))
                self.assertEqual(marker.stat().st_mode & 0o077,0)
                self.assertIn("Auto-Updates AUS",enabled)
                self.assertIn("Auto AN",enabled)
                self.assertIn("Auto AN",json.loads(
                    urlopen(urljoin(url,"state"),timeout=8).read())["pipeline_status"])

                csrf=native_button(enabled,"auto_disable")
                disabled=toggle("auto_disable",csrf)
                self.assertFalse(marker.exists())
                self.assertIn("Auto-Updates EIN",disabled)
                self.assertIn("Auto AUS",disabled)

                # Repeated toggles remain usable; no single-use browser state.
                csrf=native_button(disabled,"auto_enable")
                enabled_again=toggle("auto_enable",csrf)
                self.assertTrue(marker.is_file())
                self.assertIn("Auto-Updates AUS",enabled_again)

                bad=Request(post_url,urlencode({"action":"auto_disable","csrf":"0"*48}).encode(),
                            headers={"Content-Type":"application/x-www-form-urlencoded"})
                with self.assertRaises(HTTPError) as denied:
                    urlopen(bad,timeout=8)
                self.assertEqual(denied.exception.code,403)
                self.assertTrue(marker.is_file(),
                                "invalid token must not silently toggle consent")
            finally:
                proc.terminate()
                proc.wait(timeout=6)


if __name__=="__main__":
    unittest.main()
