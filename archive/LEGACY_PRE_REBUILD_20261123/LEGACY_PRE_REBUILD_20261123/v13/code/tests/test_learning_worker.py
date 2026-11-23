"""Local optimizer tests with numerical fixtures, not a hardware proof."""
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from v13.config import initialize
from v13.learning_worker import train

class Worker(unittest.TestCase):
    def test_training_result_is_reloadable_json_and_real_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);cfg=initialize(p)
            x=np.tile(np.eye(4),(4,1));y=list(range(4))*4
            metrics=train({'config':cfg,'embeddings':x.tolist(),'labels':y,'scaffold_labels':y,'active_checkpoint':None},p)
            saved=json.loads((p/'metrics.json').read_text())
            self.assertIs(saved['gradient_check'],True);self.assertIsInstance(saved['finite_difference_max_error'],float)
            with np.load(p/'candidate.npz',allow_pickle=False) as z:self.assertTrue(np.any(z['route_w']!=0))
            self.assertLess(metrics['loss_after'],metrics['loss_before'])
            self.assertTrue(saved['checkpoint_reload'])

if __name__=='__main__':unittest.main()
