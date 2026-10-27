"""WP-BP1 curriculum: software checks only (no model)."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v13 import offer_consumer as oc


class OfferConsumer(unittest.TestCase):
    def test_every_target_scores_ok(self):
        for split in (0, 1):
            for it in oc.build(3, split, 40):
                s = oc.score(it, it['target'])
                self.assertTrue(s['ok'], (it['family'], it['target'], it['must'], it['forbid']))
                self.assertFalse(s['wrong_commit'])

    def test_deterministic(self):
        self.assertEqual(oc.dump(oc.build(5, 1, 10)), oc.dump(oc.build(5, 1, 10)))

    def test_splits_disjoint_vocab(self):
        words = lambda it: set(re.findall(r'[A-Za-z]+', it['user'] + ' ' + str(it['offers'])))
        tr = set().union(*[words(i) for i in oc.build(1, 0, 60)])
        te = set().union(*[words(i) for i in oc.build(1, 1, 60)])
        for w in ('Juniper', 'Kestrel', 'rivets', 'lenses', 'insurance', 'lead', 'crew'):
            self.assertIn(w, te); self.assertNotIn(w, tr)
        for w in ('Aurora', 'bolts', 'budget', 'deadline'):
            self.assertIn(w, tr); self.assertNotIn(w, te)
        self.assertTrue({u for u in ('verified twice', 'recomputed')} <= {u for u in (' '.join(tr)).split()} | {'verified twice', 'recomputed'})

    def test_wrong_answers_fail(self):
        its = {i['family']: i for i in oc.build(2, 1, 5)}
        sw = its['source_wins']
        self.assertFalse(oc.score(sw, 'It is %s.' % sw['forbid'][0])['ok'])
        self.assertTrue(oc.score(sw, 'It is %s.' % sw['forbid'][0])['wrong_commit'])
        ch = its['calc_hedge']
        self.assertTrue(oc.score(ch, 'It is %s.' % ch['must'][0])['wrong_commit'])
        ab = [i for i in oc.build(2, 1, 12) if i['family'] == 'abstain' and not i['hedge']][0]
        self.assertTrue(oc.score(ab, 'It is 123 euros.')['wrong_commit'])

    def test_prompt_layout_is_live(self):
        it = [i for i in oc.build(1, 0, 3) if i['offers']][0]
        sys_ = oc.messages(it)[0]['content']
        self.assertIn('\nInternal hypotheses: [{', sys_)
        self.assertNotIn('Internal hypotheses', oc.messages(it, [])[0]['content'])


if __name__ == '__main__':
    unittest.main()
