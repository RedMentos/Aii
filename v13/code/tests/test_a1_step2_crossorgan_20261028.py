"""A1→STEP2 exact Store SourceRef path across long notes and revisions.

Software/SQLite only. No native model calls, authority or gate promotion.
"""
import tempfile
import unittest
from pathlib import Path

from scripts.a1_step2_verified_source_candidate import verified_segment
from scripts.step2_longnote_revision_fixtures import FIXTURES
from v13.agi.eligibility import stated
from v13.runtime import Runtime


class A1Step2CrossOrgan(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def source(self, text):
        prefix = '前置::'
        suffix = '::尾部'
        event = self.r.store.event(self.r.session, prefix + text + suffix)
        ref = dict(event['source_ref'],
                   char_start=len(prefix),
                   char_end=len(prefix) + len(text))
        self.assertEqual(self.r.store.read_source(ref), text)
        return ref

    def check(self, text, ref, mode):
        parts = verified_segment(self.r.store, text, ref, width=41, mode=mode)
        self.assertTrue(parts)
        self.assertEqual(''.join(p['text'] for p in parts), text)
        cursor = ref['char_start']
        for p in parts:
            child = p['source_ref']
            self.assertEqual(child['char_start'], cursor)
            self.assertEqual(child['source_id'], ref['source_id'])
            self.assertEqual(child['sha256'], ref['sha256'])
            self.assertEqual(self.r.store.read_source(child), p['text'])
            cursor = child['char_end']
        self.assertEqual(cursor, ref['char_end'])
        return parts

    def test_all_ten_longnote_fixture_lanes_have_exact_store_offsets(self):
        self.assertEqual(len(FIXTURES), 10)
        for f in FIXTURES:
            for label, text in (('old', f['history'][0]),
                                ('recent', f['history'][2]),
                                ('current', f['current'])):
                with self.subTest(fixture=f['id'], lane=label):
                    ref = self.source(text)
                    for mode in ('fixed', 'event'):
                        self.check(text, ref, mode)

    def test_revision_current_rule_is_distinct_from_obsolete_old_source(self):
        revised = [f for f in FIXTURES if f['type'] == 'REVISION']
        self.assertEqual(len(revised), 1)
        f = revised[0]
        self.assertEqual(f['temporal_mode'], 'REVISED_CURRENT_RULES')
        old, current = f['history'][0], f['current']
        old_ref, current_ref = self.source(old), self.source(current)
        self.assertNotEqual(old_ref['source_id'], current_ref['source_id'])
        self.assertNotEqual(f['old_rules'], f['rules'])
        self.assertTrue(all(stated(k, v, current) for k, v in f['rules'].items()))
        self.assertTrue(all(stated(k, v, old) for k, v in f['old_rules'].items()))
        self.check(current, current_ref, 'event')
        with self.assertRaises(ValueError):
            verified_segment(self.r.store, current, old_ref, 41)

    def test_store_restart_keeps_exact_excerpt_and_child_references(self):
        f = FIXTURES[0]
        text = f['history'][0]
        ref = self.source(text)
        parts = self.check(text, ref, 'fixed')
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.assertEqual(self.r.store.read_source(ref), text)
        for part in parts:
            self.assertEqual(self.r.store.read_source(part['source_ref']),
                             part['text'])
        self.check(text, ref, 'event')

    def test_shifted_and_tampered_source_refs_fail_closed(self):
        f = FIXTURES[0]
        text = f['history'][0]
        ref = self.source(text)
        bad_refs = (
            dict(ref, char_start=ref['char_start'] + 1,
                 char_end=ref['char_end'] + 1),
            dict(ref, sha256='0' * 64),
            dict(ref, source_id='not-an-event'),
        )
        for bad in bad_refs:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                verified_segment(self.r.store, text, bad, 41, 'event')
        with self.assertRaises(ValueError):
            verified_segment(self.r.store, text + ' forged', ref, 41)
        with self.assertRaises(ValueError):
            verified_segment(self.r.store, text, ref, True)


if __name__ == '__main__':
    unittest.main()
