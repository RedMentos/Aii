"""Run264: synthetic WorldModel ablation stays synthetic under strict source binding."""
import tempfile
from pathlib import Path
from unittest import mock
import unittest

from v13.ablation99 import _store
from v13 import world_model as W
from scripts import ablation_world_model_confidence as A


class SyntheticWorldScope(unittest.TestCase):
    def test_facade_cannot_expose_real_source_reader(self):
        with tempfile.TemporaryDirectory() as d:
            real, _ = _store(Path(d))
            try:
                self.assertTrue(callable(real.read_source))
                fake = A.SyntheticTransitionStore(real)
                self.assertFalse(hasattr(fake, 'read_source'))
                self.assertEqual(fake.evidence_scope, 'SYNTHETIC_TEST_ONLY')
            finally:
                real.close()

    def test_real_store_rejects_synthetic_action_ids_while_facade_allows_math(self):
        transitions, _ = A.world(13)
        with tempfile.TemporaryDirectory() as d:
            real, _ = _store(Path(d))
            try:
                fake = A.SyntheticTransitionStore(real)
                with mock.patch.object(W, 'transitions', lambda *a, **k: transitions):
                    rejected = W.fit(real, rng_seed=13)
                    self.assertEqual(rejected['status'], 'SOURCE_UNVERIFIED')
                    fitted = W.fit(fake, rng_seed=13)
                self.assertEqual(fitted['status'], 'FITTED')
                self.assertEqual(fitted['evidence_scope'], 'SYNTHETIC_TEST_ONLY')
                self.assertIsNotNone(W.load(fake))
                self.assertIsNone(W.load(real))
            finally:
                real.close()

    def test_original_preregistered_seed_is_fitted_and_scored(self):
        original = A.Q
        A.Q = 20
        try:
            r = A.run_seed(13)
        finally:
            A.Q = original
        self.assertEqual(r['fit_status'], 'FITTED')
        self.assertEqual(r['queries_n'], 20)
        self.assertEqual(r['evaluated_n'] + r['abstained_n'], 20)
        self.assertGreater(r['evaluated_n'], 0)


if __name__ == '__main__':
    unittest.main()
