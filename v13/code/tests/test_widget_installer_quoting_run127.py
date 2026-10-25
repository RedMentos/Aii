"""Run127: Termux Widget installer must quote custom paths as Bash data.

Linux shell simulation only, no Android/Redmi widget execution.
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

APP=Path(__file__).resolve().parents[1]


class WidgetInstallerQuotingRun127(unittest.TestCase):
    def install(self,source,home,model_home):
        env=dict(os.environ,HOME=str(home),PREFIX="/usr",V13_HOME=str(model_home))
        result=subprocess.run(["bash",str(source)],cwd=home,env=env,
                              capture_output=True,text=True,timeout=8)
        self.assertEqual(result.returncode,0,result.stderr)
        return env

    def test_apostrophe_spaces_and_semicolon_are_literal_stop_path(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);user_home=root/"termux-home";user_home.mkdir()
            target=root/"it's a home; echo should-not-run"
            env=self.install(APP/"KNOEPFE_EINRICHTEN.sh",user_home,target)
            button=user_home/".shortcuts/tasks/V13 Stillstand"
            result=subprocess.run(["bash",str(button)],cwd=user_home,env=env,
                                  capture_output=True,text=True,timeout=8)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue((target/"control/STILLSTAND").is_file())
            self.assertFalse((user_home/"should-not-run").exists())

    def test_malicious_looking_path_is_data_not_shell_code(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);user_home=root/"home";user_home.mkdir()
            target=root/"it's; touch injected; #"
            env=self.install(APP/"KNOEPFE_EINRICHTEN.sh",user_home,target)
            result=subprocess.run(["bash",str(user_home/".shortcuts/tasks/V13 Notaus")],
                                  cwd=user_home,env=env,capture_output=True,text=True,timeout=8)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue((target/"control/NOTAUS").is_file())
            self.assertFalse((user_home/"injected").exists())

    def test_apostrophe_in_source_folder_does_not_break_guide_button(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);user_home=root/"home";user_home.mkdir()
            source=root/"app's source";(source/"docs").mkdir(parents=True)
            shutil.copy2(APP/"KNOEPFE_EINRICHTEN.sh",source/"KNOEPFE_EINRICHTEN.sh")
            shutil.copy2(APP/"docs/BEFEHLE.md",source/"docs/BEFEHLE.md")
            env=self.install(source/"KNOEPFE_EINRICHTEN.sh",user_home,root/"model-home")
            result=subprocess.run(["bash",str(user_home/".shortcuts/V13 Befehle")],
                                  cwd=user_home,env=env|{"PATH":"/usr/bin:/bin"},
                                  stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=8)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn(":stillstand",result.stdout)


if __name__=="__main__":
    unittest.main()
