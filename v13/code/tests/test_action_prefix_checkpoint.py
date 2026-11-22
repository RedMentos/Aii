import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import checkpoint_action_jepa_prefix as closed
import capture_action_jepa_taps as cap


class PrefixTests(unittest.TestCase):
    def fixture(self,root):
        capture=root/'capture';capture.mkdir()
        texts=['one','two','three']
        for name in ('sentences','actions'):
            (root/name).write_text(name)
        reg={'expected_dim':1024,'expected_rows':3,'texts_sha256':cap.json_sha(texts)}
        reg.update({name:{'path':str(root/name),'sha256':cap.sha(root/name)} for name in ('sentences','actions')})
        cap.atomic_json(capture/'registration.json',reg)
        sha=cap.sha(capture/'registration.json')
        payload={'model':'alias','data':[{'index':i,'embedding':[float(i)]*1024} for i in range(2)]}
        batch={'registry_sha256':sha,'start':0,'end':2,'inputs':texts[:2],'response':payload,'model_alias':'alias'}
        cap.atomic_json(capture/'batch.json',batch)
        records=[{'path':'batch.json','sha256':cap.sha(capture/'batch.json')}]
        cap.write_checkpoint(capture,cap.validate_response(payload,2,'alias'),texts,sha,records)
        return capture,texts

    def test_closed_partial_archive_is_byte_exact_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);capture,texts=self.fixture(root);out=root/'closed.zip'
            with patch.object(closed,'corpus',return_value=(None,None,texts)):
                report=closed.checkpoint(capture,out)
                self.assertEqual(report['completed_rows'],2)
                self.assertFalse(report['complete_capture_claimed'])
                with self.assertRaisesRegex(ValueError,'never overwrite'):
                    closed.checkpoint(capture,out)
            with zipfile.ZipFile(out) as z:
                self.assertEqual(z.read('taps.npz'),(capture/'taps.npz').read_bytes())
                self.assertEqual(z.read('batch.json'),(capture/'batch.json').read_bytes())

    def test_changed_raw_batch_or_registered_corpus_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);capture,texts=self.fixture(root);out=root/'closed.zip'
            original=(capture/'batch.json').read_bytes()
            (capture/'batch.json').write_bytes(original+b' ')
            with patch.object(closed,'corpus',return_value=(None,None,texts)):
                with self.assertRaisesRegex(ValueError,'raw batch changed'):
                    closed.checkpoint(capture,out)
                self.assertFalse(out.exists())
                (capture/'batch.json').write_bytes(original)
                (root/'actions').write_text('altered')
                with self.assertRaisesRegex(ValueError,'source corpus binding changed'):
                    closed.checkpoint(capture,out)
                self.assertFalse(out.exists())

if __name__=='__main__':
    unittest.main()
