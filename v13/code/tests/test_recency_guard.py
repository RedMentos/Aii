"""WP-Z2g recency guard in the eligibility recipe: a quoted rule superseded by a newer session source counts as unavailable."""
import unittest
from v13.agi import eligibility as E

OLD='Project Hadar kickoff notes. Budget 110 euros. Deadline 7 days. Local-only requirement: true.'
NEW='Project Hadar status note. The steering group revised one rule on Monday. New budget 60 euros. All other project rules are unchanged.'
SHEET='Option A: cost 95 euros, duration 4 days, local true. Option B: cost 70 euros, duration 6 days, local true.'
CUR='Project Hadar. Decide between Option A and Option B from the latest supplier data sheet.'
OPTS=[{'entity':'A','cost':95,'days':4,'local':True},{'entity':'B','cost':70,'days':6,'local':True}]

class Recency(unittest.TestCase):
    def test_off_is_previous_behaviour(self):
        d=E.decide({'budget':110,'deadline':7,'local_only':True},OPTS,CUR,[OLD,SHEET])
        self.assertEqual((d['action'],d['revision']),('B',E.REVISION))
    def test_stale_quote_becomes_unknown(self):
        d=E.decide({'budget':110,'deadline':7,'local_only':True},OPTS,CUR,[OLD,SHEET],history=[OLD,NEW,SHEET])
        self.assertEqual(d['action'],'UNKNOWN');self.assertIn('budget:superseded',d['rejected']);self.assertEqual(d['revision'],E.REVISION+'+recency')
    def test_current_value_and_unrevised_rules_pass(self):
        d=E.decide({'budget':60,'deadline':7,'local_only':True},OPTS,CUR,[OLD,NEW,SHEET],history=[OLD,NEW,SHEET])
        self.assertEqual(d['action'],'NONE');self.assertEqual(d['rejected'],[])
    def test_current_source_still_wins(self):
        cur=CUR+' Rules for this decision: budget 110 euros.'
        d=E.decide({'budget':110,'deadline':7,'local_only':True},OPTS,cur,[OLD,SHEET],history=[OLD,NEW,SHEET])
        self.assertNotIn('budget:superseded',d['rejected'])
    def test_newest_values(self):
        self.assertEqual(E.newest_values('budget',[OLD,NEW,SHEET]),{60});self.assertEqual(E.newest_values('deadline',[OLD,NEW]),{7});self.assertEqual(E.newest_values('budget',[]),set())

if __name__=='__main__':unittest.main()
