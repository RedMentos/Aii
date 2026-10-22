"""Interrupted real-training cohorts keep complete controls and reject drift."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1]/'scripts/dream_ablation_bench.py'
spec = importlib.util.spec_from_file_location('dream_checkpoint_bench', SCRIPT)
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


class FakeDream:
    fits = 0
    interrupt = None

    def __init__(self, master, threads):
        self.base_eval = {'probe_retention': .5}

    def reference(self):
        return self.base_eval

    def lora(self, seed):
        return object()

    def fit(self, model, items, max_steps=60, **kw):
        FakeDream.fits += 1
        if FakeDream.interrupt == FakeDream.fits:
            raise RuntimeError('simulated training interruption')
        self.progress_callback({'steps': max_steps, 'final_ce': .1, 'items': len(items)})
        return {'steps': max_steps, 'final_ce': .1, 'items': len(items)}

    def gen(self, model, prompt, n=24):
        self.generation_trace.append({'prompt': prompt, 'answer': 'hypothesis', 'max_new_tokens': n})
        return 'hypothesis'

    def split_eval(self, model):
        self.gen(model, 'raw recorded question')
        return {'A': {'recall': .5, 'paraphrase': .5}, 'B': {'recall': .5, 'paraphrase': .5},
                'near_miss_leak': .2, 'probe_retention': .5, 'kl_to_base': .1, 'forgotten': []}


class DreamCheckpoint(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.master = self.root/'master'; self.master.mkdir()
        (self.master/'model.safetensors').write_bytes(b'fixture master, no native claim')
        (self.master/'tokenizer.json').write_text('{}')
        self.dreams = self.root/'dreams.json'
        self.dreams.write_text(json.dumps({bench.A[0][0]: ['What do I call my cat?', 'What do I call that animal?']}))
        self.out = self.root/'out'
        self.path = self.out/'dream_ablation_b40.json'
        FakeDream.fits = 0; FakeDream.interrupt = None

    def run_main(self, resume=False):
        argv = [str(SCRIPT), '--master', str(self.master), '--dreams', str(self.dreams),
                '--out', str(self.out), '--seeds', '13', '--threads', '1', '--b-steps', '40']
        if resume: argv.append('--resume')
        with patch.object(sys, 'argv', argv), patch.object(bench, 'Dream', FakeDream), patch.object(bench, 'package_version', return_value='test-only'):
            return bench.main()

    def test_interruption_preserves_arm_and_resume_skips_it(self):
        FakeDream.interrupt = 3
        with self.assertRaisesRegex(RuntimeError, 'interruption'): self.run_main()
        partial = json.loads(self.path.read_text())
        first = copy.deepcopy(partial['runs'][0])
        self.assertEqual(len(partial['runs']), 1)
        self.assertEqual(partial['status'], 'RUNNING')
        self.assertEqual(partial['active_arm']['arm'], 'replay_exact')
        FakeDream.interrupt = None
        self.assertEqual(self.run_main(resume=True), 0)
        complete = json.loads(self.path.read_text())
        self.assertEqual(complete['runs'][0], first)
        self.assertEqual(len(complete['runs']), 5)
        self.assertEqual(FakeDream.fits, 11)  # 3 first attempt + 8 resumed fits
        self.assertEqual(complete['status'], 'COMPLETE')
        self.assertFalse(complete['canonical_gate_pass'])
        self.assertFalse(complete['phone_measured'])
        fits = FakeDream.fits
        self.run_main(resume=True)
        self.assertEqual(FakeDream.fits, fits)

    def test_model_or_dream_drift_rejects_before_training(self):
        self.run_main(); count = FakeDream.fits
        (self.master/'model.safetensors').write_bytes(b'changed master')
        with self.assertRaisesRegex(ValueError, 'changed'): self.run_main(resume=True)
        self.assertEqual(FakeDream.fits, count)

    def test_completed_raw_evidence_tamper_rejected(self):
        self.run_main()
        doc = json.loads(self.path.read_text())
        doc['runs'][0]['raw_generations'][0]['answer'] = 'edited'
        self.path.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, 'bytes changed'): self.run_main(resume=True)

    def test_external_chat_template_drift_rejects_before_training(self):
        template = self.master/'additional_chat_templates'; template.mkdir()
        path = template/'alternate.jinja'; path.write_text('{{ messages }}')
        self.run_main(); count = FakeDream.fits
        path.write_text('{{ changed_template }}')
        with self.assertRaisesRegex(ValueError, 'changed'): self.run_main(resume=True)
        self.assertEqual(FakeDream.fits, count)

    def test_duplicate_control_rejected_even_if_digest_updated(self):
        self.run_main()
        doc = json.loads(self.path.read_text())
        doc['runs'].append(doc['runs'][0]); doc['row_sha256'].append(doc['row_sha256'][0])
        with self.assertRaisesRegex(ValueError, 'duplicate'): bench.completed_pairs(doc, doc['run_binding'])

    def test_existing_cohort_never_overwritten_without_resume(self):
        self.run_main(); raw = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Existing cohort'): self.run_main()
        self.assertEqual(self.path.read_bytes(), raw)


if __name__ == '__main__': unittest.main()
