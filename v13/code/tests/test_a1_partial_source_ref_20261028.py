"""A1/B1/B2 exact SourceRef offsets for a nonzero-origin source excerpt.

Real Runtime/SQLite SourceRef round-trip; software only, no native inference.
"""
import tempfile
import unittest
from pathlib import Path

from v13.cognition import segments
from v13.episodes import text_segments
from v13.runtime import Runtime


class A1PartialSourceRef(unittest.TestCase):
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

    def test_base_zero_original_full_source_still_exact(self):
        for mode in ('fixed', 'event'):
            with self.subTest(mode=mode):
                self.check(self.full, self.full_ref,
                           segments(self.full, self.full_ref, 28, mode))


if __name__ == '__main__':
    unittest.main()
