"""Run42 disjoint synthetic Orion source-to-tool SHADOW; no native model."""
import unittest
from scripts import run42_b2_eligibility_source_shadow as study
from tests.test_run40_b2_store_history_readonly import Store

CURRENT = 'Project Orion. Decide using the earlier binding project rules and latest supplier sheet.'
RULE = ('Project Orion kickoff memo. ' + 'Administrative history only. '*12 +
        'Binding rules: Budget 160 euros. Deadline 8 days. Local-only requirement: true.')
SHEET = ('Project Orion supplier sheet. Option A: cost 115 euros, duration 6 days, local true. '
         'Option B: cost 90 euros, duration 5 days, local false.')
ALT = SHEET.replace('115 euros','110 euros')
ATLAS = SHEET.replace('Project Orion','Project Atlas')


class ExactSourceEligibility(unittest.TestCase):
    def setUp(self):
        self.s = Store()

    def offer(self, text, **kwargs):
        e = self.s.event(text, **kwargs)
        self.s.offer(e)
        return e

    def setup_positive(self):
        note = self.offer(RULE)
        for _ in range(5): self.offer(SHEET)
        cur = self.s.event(CURRENT)
        return note, cur

    def eval(self, cur):
        return study.evaluate(self.s, cur, 's', 'g', 'm')

    def test_exact_rule_beyond_four_slots_produces_shadow_action(self):
        note, cur = self.setup_positive()
        before = self.s.db.total_changes
        r = self.eval(cur)
        self.assertEqual(self.s.db.total_changes, before)
        self.assertEqual(r['status'], 'SHADOW_DETERMINISTIC_DECISION_NO_OUTPUT')
        self.assertEqual(r['decision']['action'], 'A')
        self.assertEqual([o['remaining'] for o in r['decision']['options']], [45,70])
        self.assertEqual([o['eligible'] for o in r['decision']['options']], [True,False])
        self.assertEqual(r['source_refs'][0]['source_id'], note['source_ref']['source_id'])
        self.assertGreater(r['source_refs'][0]['char_start'], 240)
        self.assertFalse(r['canonical_gate_pass'])
        self.assertEqual(r['authority'], 'SHADOW_NO_AUTHORITY')

    def test_revoked_rule_refuses(self):
        note, cur = self.setup_positive()
        self.s.db.execute('UPDATE sources SET deleted=1 WHERE id=?', (note['source_ref']['source_id'],))
        self.assertEqual(self.eval(cur)['status'], 'ABSTAIN_RULE_SOURCE')

    def test_conflicting_rule_sources_refuse(self):
        self.offer(RULE)
        self.offer(RULE.replace('160 euros','130 euros'))
        self.offer(SHEET)
        cur = self.s.event(CURRENT)
        self.assertEqual(self.eval(cur)['status'], 'ABSTAIN_RULE_SOURCE')

    def test_deleted_option_source_refuses(self):
        note = self.offer(RULE)
        sheet = self.offer(SHEET)
        cur = self.s.event(CURRENT)
        self.s.db.execute('UPDATE sources SET deleted=1 WHERE id=?',(sheet['source_ref']['source_id'],))
        self.assertEqual(self.eval(cur)['status'], 'ABSTAIN_OPTION_SOURCE')

    def test_conflicting_older_option_sheets_refuse(self):
        self.offer(RULE); self.offer(SHEET); self.offer(ALT)
        cur = self.s.event(CURRENT)
        self.assertEqual(self.eval(cur)['status'], 'ABSTAIN_CONFLICTING_OPTION_SOURCES')

    def test_current_rule_override_refuses_old_value(self):
        self.offer(RULE); self.offer(SHEET)
        cur = self.s.event(CURRENT + ' Current binding rule: Budget 100 euros.')
        r = self.eval(cur)
        self.assertEqual(r['status'], 'ABSTAIN_CONFLICT_OR_UNSUPPORTED')
        self.assertEqual(r['decision']['action'], 'UNKNOWN')

    def test_unrelated_atlas_option_sheet_excluded(self):
        self.offer(RULE); self.offer(ATLAS)
        cur = self.s.event(CURRENT)
        self.assertEqual(self.eval(cur)['status'], 'ABSTAIN_OPTION_SOURCE')

    def test_current_without_project_refuses(self):
        self.offer(RULE); self.offer(SHEET)
        cur = self.s.event('Decide using earlier rules.')
        self.assertEqual(self.eval(cur)['status'], 'ABSTAIN_PROJECT_IDENTITY')


if __name__ == '__main__': unittest.main()
