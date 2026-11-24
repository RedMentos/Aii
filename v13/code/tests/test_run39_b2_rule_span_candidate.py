"""Run39 synthetic source-only regressions; no native or authority claims."""
import hashlib
import unittest

from scripts import run39_b2_rule_span_candidate as c

CURRENT = 'Project Aquila: decide from the earlier binding project rules, using the latest options.'
NOTE = ('Project Aquila background and approved procurement record. ' +
        'The opening section is administrative only. ' * 8 +
        'Binding rules: Budget 134 euros. Deadline 9 days. Local-only requirement: true.')
SHEET = 'Project Aquila supplier sheet. Option A costs 91 euros; option B costs 105 euros.'
ATLAS = 'Project Atlas archive index. Budget 100 euros. Deadline 5 days. Local-only requirement: false.'


def item(text, n, **override):
    ref = {'source_id': f'src{n}', 'sha256': hashlib.sha256(text.encode()).hexdigest(),
           'char_start': 0, 'char_end': len(text), 'modality': 'text'}
    return {'offer_id': f'p{n}', 'role': 'B2_GIST', 'event_id': f'e{n}',
            'session': 's', 'generation': 'g', 'model_revision': 'm',
            'source_ref': ref, **override}


def reader(items, texts):
    mapping = {i['source_ref']['source_id']: t for i, t in zip(items, texts)}
    def read(ref):
        text = mapping[ref['source_id']]
        if hashlib.sha256(text.encode()).hexdigest() != ref['sha256']:
            raise ValueError('tamper')
        return text[ref['char_start']:ref['char_end']]
    return read


def select(items, texts, current=CURRENT, **kwargs):
    return c.select_rule_span(current, 'current', 's', 'g', 'm',
                              items, reader(items, texts), **kwargs)


class RuleSpanTests(unittest.TestCase):
    def test_old_rule_beyond_240_survives_recent_sheet(self):
        items = [item(SHEET, 3), item(NOTE, 1)]
        x = select(items, [SHEET, NOTE])
        self.assertEqual(len(x['items']), 1)
        ref = x['items'][0]['source_ref']
        self.assertEqual(ref['source_id'], 'src1')
        self.assertGreater(ref['char_start'], 240)
        self.assertLessEqual(ref['char_end'] - ref['char_start'], 240)
        self.assertIn('Budget 134 euros', x['items'][0]['native_context']['exact_source_excerpt'])
        self.assertIn('Deadline 9 days', x['items'][0]['native_context']['exact_source_excerpt'])
        self.assertIn('Local-only requirement: true', x['items'][0]['native_context']['exact_source_excerpt'])
        self.assertFalse(x['canonical_gate_pass'])
        self.assertFalse(x['native_executed'])
        self.assertEqual(x['jepa_weight'], 0)

    def test_scans_beyond_output_slots(self):
        items = [item(SHEET, n) for n in (5, 4, 3, 2)] + [item(NOTE, 1)]
        x = select(items, [SHEET]*4 + [NOTE], slots=2, scan_limit=5)
        self.assertEqual(x['items'][0]['source_ref']['source_id'], 'src1')
        y = select(items, [SHEET]*4 + [NOTE], slots=2, scan_limit=4)
        self.assertEqual(y['items'], [])

    def test_unrelated_project_cannot_supply_rule(self):
        x = select([item(ATLAS, 1)], [ATLAS])
        self.assertEqual(x['items'], [])

    def test_mixed_project_rule_source_is_ambiguous(self):
        mixed = 'Project Aquila summary. ' + ATLAS
        x = select([item(mixed, 1)], [mixed])
        self.assertEqual(x['items'], [])

    def test_equal_quality_conflicting_rule_sources_refused(self):
        other = NOTE.replace('134 euros', '100 euros')
        x = select([item(NOTE, 1), item(other, 2)], [NOTE, other])
        self.assertEqual(x['items'], [])
        self.assertEqual(x['reasons']['AMBIGUOUS_RULE_SOURCES'], 1)

    def test_revoked_source_skipped(self):
        x = c.select_rule_span(CURRENT, 'current', 's', 'g', 'm',
                               [item(NOTE, 1)], lambda ref: (_ for _ in ()).throw(ValueError('deleted')))
        self.assertEqual(x['items'], [])
        self.assertEqual(x['reasons']['SOURCE_UNAVAILABLE'], 1)

    def test_midread_source_change_skipped(self):
        n = [0]
        def changed(ref):
            n[0] += 1
            return NOTE if n[0] == 1 else 'x' * (ref['char_end'] - ref['char_start'])
        x = c.select_rule_span(CURRENT, 'current', 's', 'g', 'm', [item(NOTE, 1)], changed)
        self.assertEqual(x['items'], [])
        self.assertEqual(x['reasons']['SOURCE_UNAVAILABLE'], 1)

    def test_wrong_session_generation_model_refused(self):
        for key, value in [('session', 'other'), ('generation', 'other'), ('model_revision', 'other')]:
            with self.subTest(key=key):
                x = select([item(NOTE, 1, **{key: value})], [NOTE])
                self.assertEqual(x['items'], [])

    def test_no_prior_rule_request_never_changes_default(self):
        x = select([item(NOTE, 1)], [NOTE], current='Project Aquila: choose an option.')
        self.assertEqual(x['items'], [])

    def test_malformed_ref_and_bool_bounds_refused(self):
        bad = item(NOTE, 1)
        bad['source_ref']['sha256'] = 'not-a-hash'
        self.assertEqual(select([bad], [NOTE])['items'], [])
        with self.assertRaisesRegex(ValueError, 'RUN39_BOUNDS'):
            select([], [], slots=True)

    def test_negative_superseded_note_refused(self):
        note = NOTE + ' These rules were superseded.'
        self.assertEqual(select([item(note, 1)], [note])['items'], [])

    def test_context_budget_refuses_oversized_payload(self):
        x = select([item(NOTE, 1)], [NOTE], cap=128)
        self.assertEqual(x['items'], [])
        self.assertEqual(x['reasons']['CAP'], 1)


if __name__ == '__main__':
    unittest.main()
