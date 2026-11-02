import unittest
from v13 import behavior_probe as B
from v13 import dream_policy as D

class T(unittest.TestCase):
    def test_abstains(self):
        for t in ["I don't know that.", "You haven't told me.", "Please tell me your mother's name.", "Ich weiß ich nicht"]:
            self.assertTrue(B.abstains(t), t)
        for t in ["Your mother's maiden name is Schmidt.", "It is 12345.", ""]:
            self.assertFalse(B.abstains(t), t)
    def test_score(self):
        s = B.score(["I don't know.", "It is 42.", "Not sure."], ["Your cat is Mitzi.", "I don't know"], [["mitzi"], ["jonte"]])
        self.assertAlmostEqual(s['unknown_abstain'], 2 / 3); self.assertAlmostEqual(s['unknown_invented'], 1 / 3)
        self.assertEqual(s['known_answered'], .5); self.assertEqual(s['known_over_abstain'], .5)
    def test_items_policy_only(self):
        it = B.policy_items_en(20, 1); self.assertEqual(len(it), 20)
        self.assertTrue(all(abs(1) and B.abstains(i['target']) for i in it))
        text = ' '.join(i['prompt'].lower() for i in it)
        for q in B.UNKNOWN:  # no probe question appears in the training items
            self.assertNotIn(q.lower(), text)
        self.assertEqual(D.audit(it, ['Mitzi', 'Kranich bakery'])['leaking_items'], 0)
        self.assertEqual(B.policy_items_en(20, 1), it)
    def test_control_not_abstaining(self):
        it = B.policy_items_en(8, 1, other=True); self.assertTrue(all(not B.abstains(i['target']) for i in it))
if __name__ == '__main__': unittest.main()
