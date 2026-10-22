"""2026-10-22: native runner uses cfg['seed'] when a call gives no seed (chain link integrated_candidates.runner_seed)."""
import inspect,unittest
from pathlib import Path
from v13 import runners
from v13.config import DEFAULTS

class RunnerSeed(unittest.TestCase):
    def test_default_seed_comes_from_cfg(self):
        from scripts.integrated_candidates import INTEGRATED,integrated_sources
        self.assertIn('runner_seed',INTEGRATED);self.assertEqual(DEFAULTS['seed'],13)  # default turns unchanged
        live=(Path(__file__).resolve().parents[1]/'v13/runners.py').read_text();self.assertEqual(integrated_sources()['v13/runners.py'],live)
        self.assertIn('"seed":self.cfg.get("seed",13) if seed is None else seed,',live)
        gens=[c.generate for c in vars(runners).values() if inspect.isclass(c) and 'confidence_field' in getattr(getattr(c,'generate',None),'__code__',type('',(),{'co_varnames':()})).co_varnames]
        self.assertTrue(gens);self.assertTrue(all(inspect.signature(g).parameters['seed'].default is None for g in gens))

if __name__=='__main__':unittest.main()
