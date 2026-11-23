"""A1/B1/B2 exact SourceRef offsets for a nonzero-origin source excerpt.

Real Runtime/SQLite SourceRef round-trip; frozen production code unchanged.
"""
import tempfile
import unittest
from pathlib import Path

from scripts.a1_partial_source_ref_candidate import segment_excerpt as segments
from scripts.a1_partial_source_ref_candidate import event_segments_excerpt as text_segments
from v13.runtime import Runtime


class A1PartialSourceRefFrozenSafe(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.text = (
            'Project Orion has 120 credits. Keep the exact 120 value. '
            'Project Vega has 42 credits; never exchange these amounts. '
            'This paragraph contains αβγ and a precise final sentence.'
        )
        self.prefix = '前置::'
        self.suffix = '::尾部'
        self.full = self.prefix + self.text + self.suffix
        event = self.r.store.event(self.r.session, self.full)
        self.full_ref = event['source_ref']
        start = len(self.prefix)
        self.part_ref = dict(
            self.full_ref, char_start=start, char_end=start + len(self.text))
        self.assertEqual(self.r.store.read_source(self.part_ref), self.text)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def check(self, text, ref, pieces):
        self.assertTrue(pieces)
        self.assertEqual(''.join(p['text'] for p in pieces), text)
        cursor = ref['char_start']
        for p in pieces:
            child = p['source_ref']
            self.assertEqual(child['char_start'], cursor)
            self.assertGreater(child['char_end'], cursor)
            self.assertLessEqual(child['char_end'], ref['char_end'])
            for field in ('source_id', 'sha256', 'modality'):
                self.assertEqual(child[field], ref[field])
            self.assertEqual(self.r.store.read_source(child), p['text'])
            cursor = child['char_end']
        self.assertEqual(cursor, ref['char_end'])

    def test_fixed_and_event_modes_keep_nonzero_source_origin(self):
        for mode in ('fixed', 'event'):
            with self.subTest(mode=mode):
                self.check(self.text, self.part_ref,
                           segments(self.text, self.part_ref, 28, mode))

    def test_direct_event_segmenter_preserves_nonzero_origin(self):
        self.check(self.text, self.part_ref,
                   text_segments(self.text, self.part_ref, 28))

    def test_parent_ref_unchanged_and_invalid_spans_rejected(self):
        original = dict(self.part_ref)
        self.check(self.text, self.part_ref, segments(self.text, self.part_ref, 28, 'event'))
        self.assertEqual(self.part_ref, original)
        invalid = [
            dict(original, char_start=True),
            dict(original, char_end=original['char_end'] + 1),
            dict(original, char_start=-1),
            dict(original, source_id=''),
        ]
        for bad in invalid:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                segments(self.text, bad, 28, 'fixed')
        for width in (0, -1, True, 1.5):
            with self.subTest(width=width), self.assertRaises(ValueError):
                segments(self.text, original, width, 'fixed')
        with self.assertRaises(ValueError):
            segments(self.text, original, 28, 'unexpected')

    def test_base_zero_original_full_source_still_exact(self):
        for mode in ('fixed', 'event'):
            with self.subTest(mode=mode):
                self.check(self.full, self.full_ref,
                           segments(self.full, self.full_ref, 28, mode))


if __name__ == '__main__':
    unittest.main()
