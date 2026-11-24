import tempfile
import unittest
from pathlib import Path
from v13.runtime import Runtime
from v13.operator import Operator


class OutputSourceErasure(unittest.TestCase):
    def test_reference_erasure_invalidates_label_and_keeps_independent_shared_source(self):
        with tempfile.TemporaryDirectory() as d:
            r=Runtime(Path(d))
            try:
                e=r.store.event(r.session,'Frage');messages=[{'role':'user','content':'Frage'}]
                r.learner.output_delta(e,messages,999999999.)
                response=r.learner.output_feedback(e['event_id'],'Hallo','learn')
                sid=response.split('source=')[1].split()[0]
                label=r.learner.output_labels()[0][2]['source_ref']
                independent=r.store.source('Hallo','INDEPENDENT_TEST_SOURCE')
                self.assertEqual(len(r.learner.output_labels()),1)
                self.assertIn('Ausgabereferenz gelöscht',Operator(r).run(':forget-source '+sid+' --confirm'))
                with self.assertRaises(ValueError):r.store.read_source(label)
                self.assertEqual(r.store.read_source(independent),'Hallo')
                self.assertEqual(r.learner.output_labels(),[])
                self.assertEqual(r.store.rows('SELECT * FROM feedback WHERE source_id=?',(sid,)),[])
            finally:r.close()
    def test_arbitrary_query_source_requires_its_own_explicit_erasure_scope(self):
        with tempfile.TemporaryDirectory() as d:
            r=Runtime(Path(d))
            try:
                e=r.store.event(r.session,'Originalfrage')
                with self.assertRaises(ValueError):Operator(r).run(':forget-source '+e['source_ref']['source_id']+' --confirm')
                self.assertEqual(r.store.read_source(e['source_ref']),'Originalfrage')
            finally:r.close()


if __name__=='__main__':unittest.main()
