"""Native rendering keeps explicit continuity and revalidates exact sources."""
import json
from pathlib import Path
import tempfile
import unittest
from v13.config import initialize
from v13.store import Store
from v13.executive import Executive
from v13.memory import Memory

class ExecutiveContext(unittest.TestCase):
    def test_task_and_correction_authority_survive_restart_without_prompt_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder);cfg=initialize(home);s=Store(home)
            try:
                sid=s.new_session();x=Executive(s);e=s.event(sid,'Projekt Aurora Budget?')
                x.begin(e,sid,cfg);x.task(sid,'Prüfe Aurora-Budget')
                m=Memory(s,cfg);m.feedback(e['event_id'],'fact','400 Euro')
                aid=s.start_action(e['event_id'],e['brain_generation_id'])
                x.update(e,sid,memories=m.recall('Projekt Aurora Budget?',sid),action_id=aid)
                view=x.report_context(sid);text=json.dumps(view,ensure_ascii=False)
                self.assertEqual(view['task_request']['exact_request'],'Prüfe Aurora-Budget')
                self.assertEqual(view['task_request']['authority'],'REQUEST_NOT_FACT')
                self.assertEqual(view['action_type'],'LOCAL_TEXT_REPORT')
                self.assertNotIn(e['source_ref']['source_id'],text);self.assertNotIn(aid,text)
                self.assertEqual(s.read_source(x.view(sid)['memory_refs'][0]['source_ref']),'400 Euro')
                s.close();s=Store(home);x=Executive(s);self.assertEqual(x.report_context(sid),view)
                x.task(sid,clear=True);self.assertIsNone(x.report_context(sid)['task_request'])
            finally:s.close()

    def test_tampered_task_never_enters_native_context(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder);cfg=initialize(home);s=Store(home)
            try:
                sid=s.new_session();x=Executive(s);e=s.event(sid,'Original request')
                x.begin(e,sid,cfg);ref=x.view(sid)['active_task']['source_ref']
                (home/'data/blobs'/ref['sha256']).write_text('tampered')
                self.assertIsNone(x.report_context(sid)['task_request'])
            finally:s.close()

if __name__=='__main__':unittest.main()
