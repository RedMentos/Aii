"""A1/A5 offsets verified against real Store sources; no native-model claims."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from v13.cognition import segments
from v13.config import initialize
from v13.percept_subspan_candidate import source_segments
from v13.store import Store


class PerceptSubspanCandidate(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.home = Path(self.tmp.name)
        initialize(self.home)
        self.s = Store(self.home)

    def tearDown(self):
        self.s.close()
        self.tmp.cleanup()

    def check_tiling(self, ref, mode, width):
        before = deepcopy(ref)
        expected = self.s.read_source(ref)
        chunks = source_segments(self.s, ref, width, mode)
        self.assertEqual(ref, before)
        self.assertEqual(''.join(c['text'] for c in chunks), expected)
        pos = ref['char_start']
        for chunk in chunks:
            cr = chunk['source_ref']
            self.assertEqual(cr['source_id'], ref['source_id'])
            self.assertEqual(cr['sha256'], ref['sha256'])
            self.assertEqual(cr['modality'], 'text')
            self.assertEqual(cr['char_start'], pos)
            self.assertLess(cr['char_start'], cr['char_end'])
            self.assertLessEqual(cr['char_end'], ref['char_end'])
            self.assertEqual(self.s.read_source(cr), chunk['text'])
            pos = cr['char_end']
        self.assertEqual(pos, ref['char_end'])
        return chunks

    def test_offset_zero_preserves_existing_output_in_both_modes(self):
        text = 'Budget 120 €. Hallo, Welt!\n\nA longer English sentence. ' * 12
        ref = self.s.source(text)
        for mode in ('fixed', 'event'):
            with self.subTest(mode=mode):
                actual = self.check_tiling(ref, mode, 70)
                self.assertEqual(actual, segments(text, ref, 70, mode))

    def test_nonzero_source_slice_and_nested_reentry(self):
        text = 'PRELUDE Alpha Beta Gamma.\nThen exact 120 €! Final. SUFFIX'
        ref = self.s.source(text)
        start, end = text.index('Alpha'), text.index(' SUFFIX')
        ref.update(char_start=start, char_end=end)
        for mode in ('fixed', 'event'):
            chunks = self.check_tiling(ref, mode, 8)
            nested = chunks[len(chunks) // 2]['source_ref']
            self.check_tiling(nested, mode, 3)
        legacy = segments(self.s.read_source(ref), ref, 8, 'fixed')[0]
        self.assertNotEqual(self.s.read_source(legacy['source_ref']), legacy['text'])

    def test_empty_sources_and_nonzero_empty_spans(self):
        empty = self.s.source('')
        ref = self.s.source('abc')
        ref.update(char_start=2, char_end=2)
        for source in (empty, ref):
            for mode in ('fixed', 'event'):
                self.assertEqual(source_segments(self.s, source, 3, mode), [])

    def test_multilingual_unicode_offsets_are_codepoints_not_bytes(self):
        text = 'ignore 🚀 | Äpfel e\u0301, 汉字, عربى, emoji 👩\u200d💻!\nEnde | suffix'
        ref = self.s.source(text)
        ref.update(char_start=text.index('Äpfel'), char_end=text.index(' | suffix'))
        self.assertNotEqual(len(text[:ref['char_start']]), len(text[:ref['char_start']].encode('utf-8')))
        for mode in ('fixed', 'event'):
            self.check_tiling(ref, mode, 6)
            # Even a span slicing between a base character and a combining mark
            # has a well-defined Python-codepoint SourceRef, without a claim of
            # grapheme-aware boundaries.
            mark = text.index('\u0301')
            self.check_tiling(dict(ref, char_start=mark, char_end=mark+1), mode, 2)

    def test_long_whitespace_fallback_is_labeled_and_source_exact(self):
        text = 'prefix:' + ' ' * 400 + '\nActual text stays.' + ':suffix'
        ref = self.s.source(text)
        ref.update(char_start=len('prefix:'), char_end=len(text)-len(':suffix'))
        with self.assertRaises(IndexError):
            segments(self.s.read_source(ref), ref, 40, 'event')
        chunks = self.check_tiling(ref, 'event', 40)
        self.assertTrue(chunks)
        self.assertTrue(all(x['candidate_fallback'] == 'EVENT_LONG_WHITESPACE_FIXED' for x in chunks))

    def test_invalid_offsets_hash_mode_width_and_deleted_source_fail(self):
        ref = self.s.source('abcd')
        bad_refs = [None, {}, dict(ref, char_start=-1), dict(ref, char_start=True),
                    dict(ref, char_start=3, char_end=2), dict(ref, char_end=5),
                    dict(ref, sha256='0'*64), dict(ref, modality='audio'),
                    dict(ref, source_id='missing')]
        for bad in bad_refs:
            with self.subTest(ref=bad), self.assertRaises((ValueError, KeyError)):
                source_segments(self.s, bad)
        for width in (0, -1, True, 1.5, '10', None, 10**400):
            for mode in ('fixed', 'event'):
                with self.subTest(width=width, mode=mode), self.assertRaises(ValueError):
                    source_segments(self.s, ref, width, mode)
        with self.assertRaises(ValueError):
            source_segments(self.s, ref, 1, 'unknown')
        with self.s.tx() as c:
            c.execute('UPDATE sources SET deleted=1 WHERE id=?', (ref['source_id'],))
        with self.assertRaises(ValueError):
            source_segments(self.s, ref)

    def test_corrupted_source_blob_rejected(self):
        ref = self.s.source('do not change this')
        (self.home / 'data/blobs' / ref['sha256']).write_text('changed')
        with self.assertRaises(ValueError):
            source_segments(self.s, ref)


if __name__ == '__main__':
    unittest.main()
