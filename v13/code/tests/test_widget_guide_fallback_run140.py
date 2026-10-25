"""Run140: fallback guide should ignore only EOF, not a failed pager."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

APP=Path(__file__).resolve().parents[1]

class GuideFallback(unittest.TestCase):
    def button(self, pager):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);home=root/'home';home.mkdir()
            src=root/"app's source";(src/'docs').mkdir(parents=True)
            shutil.copy2(APP/'KNOEPFE_EINRICHTEN.sh',src/'KNOEPFE_EINRICHTEN.sh')
            shutil.copy2(APP/'docs/BEFEHLE.md',src/'docs/BEFEHLE.md')
            env=dict(os.environ,HOME=str(home),PREFIX='/usr',V13_HOME=str(root/'model-home'))
            installed=subprocess.run(['/usr/bin/bash',str(src/'KNOEPFE_EINRICHTEN.sh')],env=env,capture_output=True,text=True)
            self.assertEqual(installed.returncode,0,installed.stderr)
            binpath=root/'bin';binpath.mkdir()
            more=binpath/'more';more.write_text('#!/bin/sh\n'+pager+'\n');more.chmod(0o700)
            result=subprocess.run(['/usr/bin/bash',str(home/'.shortcuts/V13 Befehle')],
                                  env=env|{'PATH':str(binpath)},stdin=subprocess.DEVNULL,
                                  capture_output=True,text=True,timeout=8)
            return result

    def test_successful_more_then_eof_is_success(self):
        row=self.button('exec /bin/cat "$2"')
        self.assertEqual(row.returncode,0,row.stderr)
        self.assertIn(':stillstand',row.stdout)

    def test_failed_more_remains_nonzero(self):
        row=self.button('exit 42')
        self.assertEqual(row.returncode,42,row.stderr)

if __name__=='__main__':unittest.main()
