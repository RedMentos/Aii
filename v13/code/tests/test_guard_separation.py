"""Entity-guard key separation (WP-T9 follow-up): distinct guard words, last-turn guard scope, native header field."""
import struct
import tempfile
import unittest
from pathlib import Path
from v13 import sparse_memory as sm

try:
    import torch
except ImportError:
    torch = None

QS = ['What is my favourite colour?', 'What is my favourite dish?', 'Which instrument do I play?',
      'Which board game do I play most?', 'What is the name of my cat?']

class GuardWords(unittest.TestCase):
    def test_default_keeps_all_content_words(self):
        self.assertEqual(sm.guard_words(QS[1]), ['favourite', 'dish'])

    def test_shared_frame_words_are_dropped(self):
        self.assertEqual(sm.guard_words(QS[1], QS), ['dish'])
        self.assertEqual(sm.guard_words(QS[0], QS), ['colour'])
        self.assertEqual(sm.guard_words(QS[2], QS), ['instrument'])
        self.assertEqual(sm.guard_words(QS[3], QS), ['board', 'game'])
        self.assertEqual(sm.guard_words(QS[4], QS), ['cat'])

    def test_duplicates_of_the_own_question_do_not_count(self):
        self.assertEqual(sm.guard_words(QS[1], [QS[1], QS[1]]), ['favourite', 'dish'])

    def test_all_shared_falls_back_to_all_words(self):
        self.assertEqual(sm.guard_words('What is my favourite?', ['My favourite song?']), ['favourite'])

class Scope(unittest.TestCase):
    def test_last_user_turn_from_second_to_last_marker(self):
        m = 7
        ids = [m, 1, 2, 3, 0, m, 4, 5, 0, m, 6]  # system, user, assistant header
        self.assertEqual(sm.scoped_context(ids, m), [m, 4, 5, 0, m, 6])
        self.assertEqual(sm.scoped_context(ids, None), ids)
        self.assertEqual(sm.scoped_context([1, m, 2], m), [1, m, 2])  # fewer than two markers: whole prompt

    def test_header_field(self):
        self.assertEqual(sm.guard_header({'entity_guard': False, 'guard_scope': 'last_user'}, 3), 0)
        self.assertEqual(sm.guard_header({'entity_guard': True}), 1)  # unchanged default
        self.assertEqual(sm.guard_header({'entity_guard': True, 'guard_scope': 'prompt'}, 9), 1)
        self.assertEqual(sm.guard_header({'entity_guard': True, 'guard_scope': 'last_user'}, 6), 8)
        with self.assertRaises(ValueError): sm.guard_header({'entity_guard': True, 'guard_scope': 'last_user'})

    def test_defaults_are_off(self):
        self.assertFalse(sm.DEFAULTS['guard_distinct']); self.assertIsNone(sm.DEFAULTS['guard_vocab'])
        self.assertEqual(sm.DEFAULTS['guard_scope'], 'prompt')

    def test_native_hook_reads_the_scope_field(self):
        h = (Path(__file__).resolve().parents[1]/'scripts/v13_memory_hook.h').read_text()
        self.assertIn('m.scope_mark = h[5] >= 2 ? h[5] - 2 : -1', h)
        self.assertIn('++seen == 2', h)
        self.assertIn('if (m.explicit_ctx && m.scope_mark >= 0 && n > 1) return true;', h)  # decoded prompt chunks must not re-open the scope

@unittest.skipIf(torch is None, 'torch not installed (model-free CI)')
class TorchGuard(unittest.TestCase):
    def model(self):
        nn = torch.nn
        class Block(nn.Module):
            def __init__(self): super().__init__(); self.feed_forward = nn.Linear(8, 8)
            def forward(self, x): return x+self.feed_forward(x)
        class Inner(nn.Module):
            def __init__(self): super().__init__(); self.layers = nn.ModuleList([Block() for _ in range(2)])
        class Model(nn.Module):
            def __init__(self):
                super().__init__(); self.model = Inner(); self.emb = nn.Embedding(20, 8); self.config = type('C', (), {'hidden_size': 8})()
            def forward(self, input_ids):
                x = self.emb(input_ids)
                for b in self.model.layers: x = b(x)
                return x
        return Model()

    def fire(self, scope_mark, ids):
        torch.manual_seed(3); m = self.model()
        mem, _ = sm.attach(torch, m, dict(sm.DEFAULTS, keyed_slots=4, topk=2, entity_guard=True, entity_width=2))
        mem.scope_mark = scope_mark; x = torch.tensor([ids])
        with torch.no_grad():
            base = m(x).clone(); mem.record_q = []; m(x); raw = mem.record_q[0]; mem.record_q = None
            mem.hkeys[0] = torch.nn.functional.normalize(raw[-1]-mem.mu, dim=-1); mem.theta[0] = .5; mem.written[0] = 1.; mem.values[0] = 5.
            mem.ent[0, 0] = 11  # the slot's entity token sits only in the system part of the prompt
            return float((m(x)-base).abs().sum())

    def test_entity_in_system_part_opens_the_guard_only_without_scope(self):
        ids = [7, 11, 2, 0, 7, 4, 5, 0, 7, 6]
        self.assertGreater(self.fire(None, ids), 1.)
        self.assertLess(self.fire(7, ids), 1e-6)

    def test_scoped_header_round_trip(self):
        torch.manual_seed(0); m = self.model()
        mem, layer = sm.attach(torch, m, dict(sm.DEFAULTS, keyed_slots=2, topk=1, entity_guard=True, entity_width=2))
        with torch.no_grad(): mem.written[0] = 1.
        cfg = dict(sm.DEFAULTS, keyed_slots=2, topk=1, entity_guard=True, entity_width=2, guard_scope='last_user', guard_mark=7)
        with tempfile.TemporaryDirectory() as t:
            pt = Path(t)/'m.pt'; torch.save({'revision': sm.REVISION, 'layer': layer, 'cfg': cfg, 'state': mem.state_dict(), 'slots': [0], 'slot_items': {0: 'a'}}, pt)
            sm.export_native(pt, Path(t)/'m.bin'); head = (Path(t)/'m.bin').read_bytes()[:32]
        self.assertEqual(head[:8], b'V13SMEM1'); self.assertEqual(struct.unpack('<6i', head[8:])[5], 9)

if __name__ == '__main__':
    unittest.main()
