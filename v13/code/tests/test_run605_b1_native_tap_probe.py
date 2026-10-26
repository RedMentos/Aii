"""Synthetic protocol-only checks for Run605, no model downloaded."""
import importlib.util
from pathlib import Path
import tempfile
import sys
import types
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/run605_b1_native_tap_probe.py'


class ProbeChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('run605_probe', SCRIPT)
        cls.module = importlib.util.module_from_spec(spec)
        fake = types.ModuleType('v13')
        config = types.ModuleType('v13.config'); config.DEFAULTS = {}
        runners = types.ModuleType('v13.runners'); runners.LlamaRunner = object
        runners.TAP_SPECS = {'body':('lfm2.result_norm.final.v1',2048)}
        with patch.dict(sys.modules, {'v13':fake,'v13.config':config,'v13.runners':runners}):
            spec.loader.exec_module(cls.module)

    def test_reject_wrong_model_before_runner_launch(self):
        with tempfile.TemporaryDirectory() as d:
            model = Path(d)/'wrong.gguf'; model.write_bytes(b'wrong')
            server = Path(d)/'server'; server.write_bytes(b'fake')
            with self.assertRaisesRegex(ValueError, 'model sha256 mismatch'):
                self.module.probe(model, server)

    def test_reject_wrong_archive_binding(self):
        with tempfile.TemporaryDirectory() as d:
            model = Path(d)/'fake.gguf'; model.write_bytes(b'x')
            server = Path(d)/'server'; server.write_bytes(b'fake')
            with patch.object(self.module, 'sha256', return_value=self.module.EXPECTED_MODEL_SHA):
                with self.assertRaisesRegex(ValueError, 'archive sha256 mismatch'):
                    self.module.probe(model, server, 'wrong')

    def test_locked_b2_spec_and_authority(self):
        self.assertEqual(self.module.EXPECTED_MODEL_SHA,
                         'bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1')
        self.assertEqual(self.module.PROMPTS[0], self.module.PROMPTS[1])
        self.assertNotEqual(self.module.PROMPTS[0], self.module.PROMPTS[2])
        source = SCRIPT.read_text()
        self.assertIn("'CAN_TRAIN_BODY') is not False", source)
        self.assertIn("'CAN_LATENT_INJECT') is not False", source)
        self.assertIn('runner.unload()', source)

    def test_fake_native_receipt_requires_dimension_authority_and_repeatability(self):
        module = self.module
        class FakeRunner:
            instances = []
            bad_dim = False
            bad_authority = False
            inconsistent = False
            def __init__(self, home, role, model, cfg, purpose):
                self.role = role
                self.calls = 0
                self.unloaded = False
                FakeRunner.instances.append(self)
                self.asserted_purpose = purpose
            def tap(self, prompt, cancel, deadline, max_tokens):
                self.calls += 1
                ids = [1, 2] if 'blue' in prompt else [3, 4]
                if self.inconsistent and self.calls == 2:
                    ids = [9, 9]
                dim = 1024 if self.bad_dim else 2048
                metrics = {'tap_id':'lfm2.result_norm.final.v1',
                           'embedding_dim':2048, 'role':'B1_DETAIL',
                           'CAN_LATENT_TAP':not self.bad_authority,
                           'CAN_LATENT_INJECT':False, 'CAN_TRAIN_BODY':False}
                return {'token_ids':ids, 'vectors':[[1.0]*dim for _ in ids],
                        'metrics':metrics}
            def unload(self):
                self.unloaded = True

        with tempfile.TemporaryDirectory() as d:
            model = Path(d)/'body.gguf'; model.write_bytes(b'synthetic')
            server = Path(d)/'server'; server.write_bytes(b'synthetic')
            with patch.object(module, 'sha256', return_value=module.EXPECTED_MODEL_SHA), \
                 patch.object(module, 'LlamaRunner', FakeRunner):
                good = module.probe(model, server, workdir=d)
                self.assertEqual(good['embedding_dim'], 2048)
                self.assertEqual(good['token_counts'], [2,2,2])
                self.assertEqual(good['max_repeat_abs_delta'], 0.0)
                self.assertTrue(FakeRunner.instances[-1].unloaded)
                for flag, error in (('bad_dim','dimension'),
                                    ('bad_authority','metrics/authority'),
                                    ('inconsistent','same prompt')):
                    with self.subTest(flag=flag):
                        setattr(FakeRunner, flag, True)
                        with self.assertRaisesRegex(ValueError, error):
                            module.probe(model, server, workdir=d)
                        self.assertTrue(FakeRunner.instances[-1].unloaded)
                        setattr(FakeRunner, flag, False)



if __name__ == '__main__':
    unittest.main()
