import tempfile
import unittest
from pathlib import Path
import numpy as np
from test_output_adapter import fixture
from v13.output_adapter_worker import train,distribution,scores


class RetentionBoundaries(unittest.TestCase):
    def test_old_retention_reference_uses_actual_old_decoder_bias_cap(self):
        with tempfile.TemporaryDirectory() as d:
            inp=fixture();train(inp,d);old=Path(d)/'candidate.npz'
            with np.load(old,allow_pickle=False) as a:
                expected=scores(distribution(a['retention_base'],a['retention_x'],a['weights'],float(a['temperature']),float(a['max_bias']))[0],a['retention_y'])
            inp['active_checkpoint']=str(old);inp['config']['output_adapter_max_bias']=.1
            folder=Path(d)/'new';folder.mkdir();result=train(inp,folder)
            self.assertEqual(result['retained_test']['before'],expected)
            self.assertFalse(result['retention_pass'])
            self.assertFalse(result['commit_eligible'])

    def test_support_threshold_change_requires_independent_lineage(self):
        with tempfile.TemporaryDirectory() as d:
            inp=fixture();train(inp,d);inp['active_checkpoint']=str(Path(d)/'candidate.npz')
            inp['config']['output_adapter_support_cosine']=.96
            folder=Path(d)/'new';folder.mkdir()
            with self.assertRaisesRegex(ValueError,'support threshold is immutable'):train(inp,folder)
            self.assertFalse((folder/'candidate.npz').exists())


if __name__=='__main__':unittest.main()
