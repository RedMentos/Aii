"""CPU-only synthetic persistence/rollback tests. Not native body learning proof."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import torch
from v13.body_jepa_checkpoint import save, restore

SHA = hashlib.sha256(b'frozen-body-model|train|source|config').hexdigest()

class EMA:
    def __init__(self, params):
        self.params = list(params)
        self.shadow = [p.detach().clone() for p in self.params]
        self.updates = 0
    def update(self):
        with torch.no_grad():
            for s, p in zip(self.shadow, self.params):
                s.mul_(.8).add_(p.detach(), alpha=.2)
        self.updates += 1


def setup():
    torch.manual_seed(110)
    model = torch.nn.Linear(3, 2)
    pred = torch.nn.Linear(2, 2)
    ema = EMA(model.parameters())
    opt = torch.optim.AdamW(list(model.parameters()) + list(pred.parameters()), lr=.01)
    gen = torch.Generator().manual_seed(991)
    return model, pred, opt, ema, gen


def run_step(components, step):
    model, pred, opt, ema, gen = components
    opt.zero_grad()
    idx = torch.randperm(5, generator=gen)
    x = torch.randn(5, 3)[idx]
    y = torch.randn(5, 2)[idx]
    loss = ((pred(model(x)) - y) ** 2).mean()
    loss.backward()
    opt.step()
    ema.update()
    return {'step': step, 'loss': float(loss.detach())}


class BodyJepaStepCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_exact_cpu_restart_with_optimizer_ema_and_two_rngs(self):
        uninterrupted = setup()
        expected = [run_step(uninterrupted, n) for n in range(1, 5)]
        fresh = setup()
        hist = [run_step(fresh, n) for n in range(1, 3)]
        ptr = save(self.root, SHA, 2, *fresh, hist)
        self.assertEqual(ptr['step'], 2)
        self.assertTrue((self.root / 'CURRENT.json').is_file())
        self.assertEqual(len(list(self.root.glob('step-*.pt'))), 1)
        resumed = setup()
        self.assertIsNone(restore(self.root / 'nonexistent', SHA, *resumed))
        loaded = restore(self.root, SHA, *resumed)
        self.assertEqual(loaded['step'], 2)
        self.assertEqual(loaded['history'], hist)
        for n in range(3, 5):
            hist.append(run_step(resumed, n))
        self.assertEqual(hist, expected)
        for x, y in zip(uninterrupted[0].parameters(), resumed[0].parameters()):
            self.assertTrue(torch.equal(x, y))
        for x, y in zip(uninterrupted[1].parameters(), resumed[1].parameters()):
            self.assertTrue(torch.equal(x, y))
        for x, y in zip(uninterrupted[3].shadow, resumed[3].shadow):
            self.assertTrue(torch.equal(x, y))
        self.assertEqual(uninterrupted[3].updates, resumed[3].updates)

    def test_cross_source_and_tamper_fail_before_state_mutation(self):
        source = setup()
        hist = [run_step(source, 1)]
        save(self.root, SHA, 1, *source, hist)
        target = setup()
        before = [p.detach().clone() for p in target[0].parameters()]
        with self.assertRaises(ValueError):
            restore(self.root, '0'*64, *target)
        self.assertTrue(all(torch.equal(a, b) for a, b in zip(before, target[0].parameters())))
        pointer = json.loads((self.root/'CURRENT.json').read_text())
        (self.root / pointer['file']).write_bytes(b'corrupted')
        with self.assertRaises(ValueError):
            restore(self.root, SHA, *target)
        self.assertTrue(all(torch.equal(a, b) for a, b in zip(before, target[0].parameters())))

    def test_crash_orphan_does_not_replace_committed_pointer(self):
        source = setup()
        hist = [run_step(source, 1)]
        one = save(self.root, SHA, 1, *source, hist)
        (self.root / 'step-000002-1111111111111111.pt').write_bytes(b'orphan')
        target = setup()
        self.assertEqual(restore(self.root, SHA, *target)['step'], 1)
        self.assertEqual(json.loads((self.root/'CURRENT.json').read_text()), one)

    def test_reject_nonfinite_or_unmatched_ema_before_file_creation(self):
        c = setup()
        h = [run_step(c, 1)]
        with self.assertRaises(ValueError):
            save(self.root, SHA, 1, *c, [{'step': 1, 'loss': float('nan')}])
        c[3].updates = 0
        with self.assertRaises(ValueError):
            save(self.root, SHA, 1, *c, h)
        self.assertFalse((self.root/'CURRENT.json').exists())

    def test_stale_step_cannot_replace_committed_pointer(self):
        c = setup()
        h = [run_step(c, 1)]
        first = save(self.root, SHA, 1, *c, h)
        with self.assertRaises(ValueError):
            save(self.root, SHA, 1, *c, h)
        self.assertEqual(json.loads((self.root/'CURRENT.json').read_text()), first)

    def test_rehashed_checkpoint_without_optimizer_moments_is_rejected(self):
        # A hash-consistent but incomplete optimizer cannot be an exact resume.
        c = setup()
        h = [run_step(c, 1)]
        pointer = save(self.root, SHA, 1, *c, h)
        state = torch.load(self.root / pointer['file'], weights_only=True)
        self.assertTrue(state['optimizer']['state'])
        state['optimizer']['state'].clear()
        candidate = self.root / 'incomplete.tmp'
        torch.save(state, candidate)
        sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
        name = 'step-000001-' + sha[:16] + '.pt'
        candidate.rename(self.root / name)
        pointer.update(file=name, size=(self.root / name).stat().st_size, sha256=sha)
        (self.root / 'CURRENT.json').write_text(json.dumps(pointer))
        target = setup()
        before = [p.detach().clone() for p in target[0].parameters()]
        with self.assertRaisesRegex(ValueError, 'optimizer state'):
            restore(self.root, SHA, *target)
        self.assertTrue(all(torch.equal(a, b) for a, b in zip(before, target[0].parameters())))

    def test_optimizer_order_mismatch_rejected_before_mutation(self):
        c = setup()
        h = [run_step(c, 1)]
        save(self.root, SHA, 1, *c, h)
        other = setup()
        model, pred, _, ema, gen = other
        wrong_order = torch.optim.AdamW(list(reversed(list(model.parameters())))
                                      + list(pred.parameters()), lr=.01)
        before = [p.detach().clone() for p in model.parameters()]
        with self.assertRaises(ValueError):
            restore(self.root, SHA, model, pred, wrong_order, ema, gen)
        self.assertTrue(all(torch.equal(a, b) for a, b in zip(before, model.parameters())))

    def test_orphan_only_root_refused_without_retraining(self):
        (self.root / 'step-000001-aaaaaaaaaaaaaaaa.pt').write_bytes(b'orphan')
        with self.assertRaisesRegex(ValueError, 'Untracked checkpoint'):
            restore(self.root, SHA, *setup())

    def test_pointer_symlink_refused(self):
        c = setup()
        h = [run_step(c, 1)]
        save(self.root, SHA, 1, *c, h)
        p = self.root/'CURRENT.json'
        original = self.root/'saved.json'
        p.rename(original)
        p.symlink_to(original)
        with self.assertRaises(ValueError):
            restore(self.root, SHA, *setup())

if __name__ == '__main__':
    unittest.main()
