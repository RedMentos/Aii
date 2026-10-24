"""Software-only control-flow proof; no native model, no HF assets, no Redmi."""
import contextlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import torch
import test_lp3_memory_key_candidate as existing

mod = existing.mod


class TestPostflightLifecycle(unittest.TestCase):
    def _run_fake(self, *, postflight_failure):
        with tempfile.TemporaryDirectory() as root:
            out = Path(root) / 'cohort'
            master = Path(root) / 'master'
            master.mkdir()
            snapshot = {'assets_sha256': {'model.safetensors': mod.PINNED_MASTER_SHA256},
                        'fixture_dependencies_sha256': {'lp2_assignment_objective.py': 'a' * 64}}

            class DummyModel:
                def eval(self):
                    return self

            fake = types.ModuleType('transformers')
            fake.AutoTokenizer = types.SimpleNamespace(from_pretrained=lambda *a, **kw: object())
            fake.AutoModelForCausalLM = types.SimpleNamespace(from_pretrained=lambda *a, **kw: DummyModel())

            def fake_eval(train, bank, holdout, expected, near, *, seed):
                outputs = {k: [None] * len(expected) for k in
                           ('raw', 'predicted', 'wrong_trained', 'value_shift', 'zero_intervention')}
                row = {k: mod.score(expected, v) for k, v in outputs.items()}
                row.update(seed=seed, expected=list(expected), outputs=outputs,
                           near_outputs={'raw': [None], 'predicted': [None]},
                           near_raw_nonabstain=0, near_pred_nonabstain=0,
                           good_loss={'steps': 30, 'initial_nce': 1.0, 'final_nce': 0.5},
                           wrong_loss={'steps': 30, 'initial_nce': 1.0, 'final_nce': 0.5})
                return row

            def check(*a, **kw):
                if postflight_failure:
                    raise ValueError('synthetic mutated tokenizer')
                return True

            argv = ['lp3_memory_key_candidate.py', '--master', str(master),
                    '--master-sha256', mod.PINNED_MASTER_SHA256, '--out', str(out)]
            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.dict(sys.modules, {'transformers': fake}))
                stack.enter_context(patch.object(sys, 'argv', argv))
                stack.enter_context(patch.object(mod, 'preflight_binding', return_value=snapshot))
                stack.enter_context(patch.object(mod, 'encode', side_effect=lambda m, t, s: torch.zeros(len(s), 16)))
                stack.enter_context(patch.object(mod, 'encode_answers', side_effect=lambda m, t, s: torch.zeros(len(s), 16)))
                stack.enter_context(patch.object(mod, 'evaluate', side_effect=fake_eval))
                stack.enter_context(patch.object(mod, 'verify_postflight_binding', side_effect=check))
                if postflight_failure:
                    with self.assertRaisesRegex(SystemExit, 'postflight source/snapshot binding failed'):
                        mod.main()
                else:
                    mod.main()
            self.assertEqual(len(list(out.glob('seed-*.json'))), 4)
            self.assertTrue((out / 'run_manifest.json').is_file())
            self.assertEqual((out / 'report.json').exists(), not postflight_failure)
            self.assertEqual((out / 'failed-input-binding.json').exists(), postflight_failure)
            if postflight_failure:
                marker = json.loads((out / 'failed-input-binding.json').read_text())
                self.assertEqual(marker['stage'], 'POSTFLIGHT_RECHECK')
                self.assertEqual(marker['error_type'], 'ValueError')
            else:
                report = json.loads((out / 'report.json').read_text())
                self.assertEqual(report['verdict'], 'LP3_MEMORY_KEY_NOT_SUPPORTED')

    def test_postflight_failure_keeps_seeds_but_never_closes_report(self):
        self._run_fake(postflight_failure=True)

    def test_postflight_success_publishes_report(self):
        self._run_fake(postflight_failure=False)


if __name__ == '__main__':
    unittest.main()
