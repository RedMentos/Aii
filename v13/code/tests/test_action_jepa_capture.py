"""Atomic/resume/ownership guards only; no native server is started by these tests."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import capture_action_jepa_taps as cap
import tests.test_action_jepa_export as export_tests


class CaptureTests(unittest.TestCase):
    def payload(self, n, alias='owned-model'):
        return {'model': alias, 'data': [{'index': i, 'embedding': [float(i)] * 1024} for i in range(n)]}

    def test_response_requires_owned_alias_exact_indices_and_finite_shape(self):
        self.assertEqual(cap.validate_response(self.payload(2), 2, 'owned-model').shape, (2, 1024))
        with self.assertRaisesRegex(ValueError, 'owned unique'):
            cap.validate_response(self.payload(2), 2, 'other-model')
        body = self.payload(2)
        body['data'][1]['index'] = 0
        with self.assertRaisesRegex(ValueError, 'indices'):
            cap.validate_response(body, 2, 'owned-model')
        body = self.payload(1)
        body['data'][0]['embedding'][0] = float('nan')
        with self.assertRaisesRegex(ValueError, 'finite'):
            cap.validate_response(body, 1, 'owned-model')

    def test_atomic_checkpoint_replays_raw_native_response_and_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            texts = ['one', 'two', 'three']
            body = self.payload(2)
            batch = {'registry_sha256': 'registered', 'start': 0, 'end': 2,
                     'inputs': texts[:2], 'response': body, 'model_alias': 'owned-model'}
            cap.atomic_json(root/'batch.json', batch)
            records = [{'path': 'batch.json', 'sha256': cap.sha(root/'batch.json')}]
            x = cap.validate_response(body, 2, 'owned-model')
            cap.write_checkpoint(root, x, texts, 'registered', records)
            loaded, observed = cap.load_checkpoint(root, texts, 'registered')
            np.testing.assert_array_equal(x, loaded)
            self.assertEqual(records, observed)
            with self.assertRaisesRegex(ValueError, 'input order'):
                cap.load_checkpoint(root, list(reversed(texts)), 'registered')
            batch['response']['data'][0]['embedding'][0] += 1
            cap.atomic_json(root/'batch.json', batch)
            with self.assertRaisesRegex(ValueError, 'batch bytes changed'):
                cap.load_checkpoint(root, texts, 'registered')

    def test_missing_terminal70_and_run_without_registration_never_start_native(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sp, ap, pp, _, _, _, _ = export_tests.ExportTests().fixture(root)
            args = argparse.Namespace(plan=pp, sentences=sp, actions=ap, model=root/'model.gguf',
                                      server=root/'bin/runner', out=root/'capture', threads=2, batch_size=16,
                                      register_only=False, run=True, check_frozen70=None)
            with patch.object(cap.subprocess, 'Popen') as start:
                with self.assertRaisesRegex(ValueError, 'prior separate'):
                    cap.capture(args)
                args.run, args.register_only = False, True
                out = cap.capture(args)
                self.assertFalse(out['native_model_started'])
                args.run, args.register_only = True, False
                with self.assertRaisesRegex(ValueError, 'check-frozen70'):
                    cap.capture(args)
                report = root/'report.json'
                report.write_text(json.dumps({'status': 'RUNNING', 'rows': [], 'proof_version': 3}))
                args.check_frozen70 = report
                with self.assertRaisesRegex(ValueError, 'terminal'):
                    cap.capture(args)
                start.assert_not_called()

    def test_changed_shared_library_prevents_resume_registration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sp, ap, pp, *_ = export_tests.ExportTests().fixture(root)
            args = argparse.Namespace(plan=pp, sentences=sp, actions=ap, model=root/'model.gguf',
                                      server=root/'bin/runner', out=root/'capture', threads=2, batch_size=16,
                                      register_only=True, run=False, check_frozen70=None)
            cap.capture(args)
            (root/'bin/libggml.so').write_bytes(b'changed executable library')
            with patch.object(cap.subprocess, 'Popen') as start:
                with self.assertRaisesRegex(ValueError, 'Resume registration differs'):
                    cap.capture(args)
                start.assert_not_called()


if __name__ == '__main__':
    unittest.main()
