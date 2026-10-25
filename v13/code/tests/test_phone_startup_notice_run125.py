"""Run125: preworker phone stop notices must reach the human exactly once.

Linux software/SQLite, no Android widget or native model.
"""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13 import phone_halt as H, ui, standstill as S


class StartupNoticeRun125(unittest.TestCase):
    def test_preworker_stillstand_notice_visible_in_plain_chat(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d)
            (H.control_dir(home)/"STILLSTAND").touch()
            r=Runtime(home)
            try:
                self.assertTrue(S.status(r)["on"])
                self.assertTrue(r._startup_phone_halt)
                out=io.StringIO()
                with contextlib.redirect_stdout(out), patch.object(ui,"read_block",side_effect=EOFError):
                    ui.plain(r)
                self.assertIn("Knopf",out.getvalue())
                self.assertIn("STILLSTAND AN",out.getvalue())
                self.assertEqual(out.getvalue().count("STILLSTAND AN"),1)
            finally:r.close()

    def test_startup_notice_consumer_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d)
            (H.control_dir(home)/"NOTAUS").touch()
            r=Runtime(home)
            try:
                seen=[]
                ui.show_startup_stop(r,seen.append)
                ui.show_startup_stop(r,seen.append)
                self.assertEqual(len(seen),1)
                self.assertIn("NOTAUS AN",seen[0])
                self.assertEqual(r._startup_phone_halt,[])
            finally:r.close()


if __name__=="__main__":
    unittest.main()
