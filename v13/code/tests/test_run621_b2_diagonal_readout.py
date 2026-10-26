"""Run621 fixed exploratory B2 diagonal readout: synthetic and original-state gates."""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
import numpy as np

from scripts import run621_b2_diagonal_readout as R


class DiagonalReadoutTests(unittest.TestCase):
    def test_fixed_fit_is_finite_positive_deterministic_and_label_sensitive(self):
        rng=np.random.default_rng(621)
        a=rng.normal(size=(30,1024))
        b=a+rng.normal(scale=.1,size=(30,1024))
        w=R.fit(a,b)
        self.assertEqual(w.shape,(1024,))
        self.assertTrue(np.isfinite(w).all())
        self.assertTrue((w>0).all())
        self.assertTrue(np.array_equal(w,R.fit(a,b)))
        self.assertFalse(np.array_equal(w,R.fit(a,b[::-1])))

    def test_synthetic_heldout_source_disjoint_deterministic(self):
        rng=np.random.default_rng(622)
        facts=rng.normal(size=(40,1024))
        y=np.vstack([facts[i]+rng.normal(scale=.01,size=1024) for i in range(40) for _ in 'AB'])
        ids=[f'fact-{i}-{variant}' for i in range(40) for variant in 'AB']
        train=np.arange(60)
        test=np.arange(60,80)
        result,w=R.evaluate(y,ids,train,test)
        result2,w2=R.evaluate(y,ids,train,test)
        self.assertEqual(result,result2)
        self.assertTrue(np.array_equal(w,w2))
        self.assertEqual(result['controls'],200)
        self.assertEqual(result['test_prompts'],20)
        self.assertGreaterEqual(result['baseline']['raw']['top1'],.9)

    def test_invalid_shapes_nonfinite_and_missing_pairs_rejected(self):
        with self.assertRaises(ValueError):R.fit(np.zeros((3,1024)),np.zeros((3,1024)))
        with self.assertRaises(ValueError):R.unit(np.array([[float('nan'),0.]]))
        with self.assertRaises(ValueError):R.unit(np.zeros((2,1024)))
        with self.assertRaises(ValueError):R.paired_indices(['a-1-A']*60,list(range(60)))
        with self.assertRaises(ValueError):R.score(np.zeros((3,1024)),[1,0,2])

    def test_original_sha_closed_artifact_and_negative_gates(self):
        native=os.environ.get('RUN621_NATIVE')
        if not native:self.skipTest('RUN621_NATIVE original artifact not provided')
        with tempfile.TemporaryDirectory() as td:
            result=R.run(native,Path(td)/'report.json',Path(td)/'weights.npz')
            self.assertEqual(result['original_states_sha256'],R.PINS['614']['states'])
            self.assertEqual(result['gates']['STEP2'],'UTILITY_FAIL')
            self.assertEqual(result['gates']['Body_JEPA'],'UNAVAILABLE')
            self.assertEqual(result['jepa_weight'],0)
            self.assertFalse(result['native_inference_new'])
            self.assertFalse(result['native_body_training'])
            self.assertEqual(result['receiver_injection_authority'],0)
            self.assertEqual(result['head_activation_authority'],0)
            self.assertIn(result['status'],{'NO_B2_READOUT_GAIN','SCOPED_EXPLORATORY_B2_GAIN'})
            self.assertEqual(result['controls'],200)
            self.assertEqual(result['train_pairs'],30)
            self.assertEqual(result['test_prompts'],20)
            self.assertTrue((Path(td)/'weights.npz').exists())

    def test_tampered_original_artifact_fails_closed(self):
        native=os.environ.get('RUN621_NATIVE')
        if not native:self.skipTest('RUN621_NATIVE original artifact not provided')
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'native';source.mkdir()
            shutil.copy2(Path(native)/'RUN614_STATES.npz',source/'RUN614_STATES.npz')
            shutil.copy2(Path(native)/'RUN614_NATIVE_REPORT.json',source/'RUN614_NATIVE_REPORT.json')
            with (source/'RUN614_NATIVE_REPORT.json').open('ab') as f:f.write(b'\n')
            with self.assertRaises(ValueError):R.run(source,Path(td)/'error.json',Path(td)/'weights.npz')
            self.assertIn('"status": "ERROR"',(Path(td)/'error.json').read_text())
            self.assertFalse((Path(td)/'weights.npz').exists())

if __name__=='__main__':unittest.main()
