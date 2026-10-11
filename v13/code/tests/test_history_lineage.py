"""No quality claims: exercise retained chat versus erased inference lineage."""
import json
import tempfile
import unittest
from pathlib import Path
from v13.config import initialize
from v13.store import Store
from v13.history import native_history
from v13.common import dumps


class HistoryLineage(unittest.TestCase):
    def test_deleted_dependency_excludes_both_roles_after_restart_but_keeps_chat(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d);initialize(h);s=Store(h);sid=s.new_session()
            e=s.event(sid,'Alte Frage');dependency=s.source('Human correction','HUMAN_FACT')
            s.message(sid,e['event_id'],'assistant','Antwort mit Korrektur','FINAL',{'context_source_refs':[e['source_ref'],dependency]})
            new=s.event(sid,'Neue Frage');rows,refs=native_history(s,sid,new['event_id'],2)
            self.assertEqual([row['role'] for row in rows],['user','assistant']);self.assertIn(dependency,refs)
            with s.tx() as c:c.execute('UPDATE sources SET deleted=1 WHERE id=?',(dependency['source_id'],))
            s.close();s=Store(h)
            try:
                self.assertEqual(native_history(s,sid,new['event_id'],2),([],[]))
                self.assertTrue(any(row['text']=='Antwort mit Korrektur' for row in s.history(sid)))
            finally:s.close()

    def test_legacy_unbound_model_answer_and_incomplete_pair_cannot_be_reimported(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d);initialize(h);s=Store(h);sid=s.new_session()
            try:
                legacy=s.event(sid,'Alte native Frage');s.message(sid,legacy['event_id'],'assistant','Legacy native text','FINAL',{'model_generated':True})
                partial=s.event(sid,'Abgebrochen');s.message(sid,partial['event_id'],'assistant','Part','CANCELLED',{'context_source_refs':[partial['source_ref']]})
                exact=s.event(sid,'Kopiere exakt: Hallo');s.message(sid,exact['event_id'],'assistant','Hallo','FINAL',{'direct_source_copy':True})
                new=s.event(sid,'Neue Frage');rows,refs=native_history(s,sid,new['event_id'],4)
                self.assertEqual([row['event_id'] for row in rows],[exact['event_id'],exact['event_id']]);self.assertEqual(refs,[exact['source_ref']])
            finally:s.close()


if __name__=='__main__':unittest.main()
