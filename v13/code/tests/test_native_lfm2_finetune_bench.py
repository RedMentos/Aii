"""WP-S6 rest: training-stream construction and strict scoring of the native LFM2 finetune bench (no model needed)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import native_lfm2_finetune_bench as B  # noqa: E402


class FakeLfmServer:
    """Mimics the LFM2.5 template as llama-server b10964 renders it (checked via /apply-template on 2026-10-12)."""

    def render(self, msgs):
        return '<|startoftext|>' + ''.join(f'<|im_start|>{m["role"]}\n{m["content"]}<|im_end|>\n' for m in msgs) + '<|im_start|>assistant\n'

    def post(self, path, body):
        assert path == '/apply-template' and not body['add_generation_prompt']
        return {'prompt': '<|startoftext|>' + ''.join(f'<|im_start|>{m["role"]}\n{m["content"]}<|im_end|>\n' for m in body['messages'])}


class StreamTests(unittest.TestCase):
    def test_turn_matches_inference_prompt(self):
        prompt, answer, sep = B.turn(FakeLfmServer(), 'Q?', 'A.')
        self.assertEqual(prompt, '<|im_start|>user\nQ?<|im_end|>\n<|im_start|>assistant\n')  # BOS added once by the tool
        self.assertEqual((answer, sep), ('A.<|im_end|>', '\n'))
        self.assertNotIn('<think>', answer)

    def test_answer_mode_marks_every_answer(self):
        text = B.train_text(FakeLfmServer(), reps=2, seed=1, mode='answer', anchors=[('Hi?', 'Hello.')])
        self.assertEqual(text.count('\x01'), text.count('\x02'))
        self.assertEqual(text.count('\x01'), 2 * (len(B.FACTS) + 1))
        self.assertEqual(text.count('\x01Your cat is called Mitzi.<|im_end|>\x02'), 2)
        self.assertNotIn('\x01', B.train_text(FakeLfmServer(), reps=1, seed=1, mode='all', anchors=[]))

    def test_anchor_rotation_covers_each_anchor(self):
        anchors = [(f'q{i}?', f'a{i}.') for i in range(8)]
        text = B.train_text(FakeLfmServer(), reps=12, seed=1, mode='answer', anchors=anchors)
        for q, _ in anchors:
            self.assertIn(f'user\n{q}<|im_end|>', text)

    def test_strict_scoring_needs_the_fact_up_front(self):
        self.assertTrue(B.hit(B.first_sentence('Your cat is called Mitzi. She is nice.'), ['mitzi']))
        hedge = 'It looks like you are asking about an instrument. Do you play the bandoneon?'
        self.assertTrue(B.hit(hedge, ['bandoneon']))
        self.assertFalse(B.hit(B.first_sentence(hedge), ['bandoneon']))

    def test_variants_are_bounded(self):
        for name, (keys, lr, epochs, mode, anchor) in B.VARIANTS.items():
            self.assertIn(mode, B.TOOLS, name)
            self.assertLessEqual(lr, 1e-3, name)
            self.assertTrue(keys, name)


if __name__ == '__main__':
    unittest.main()
