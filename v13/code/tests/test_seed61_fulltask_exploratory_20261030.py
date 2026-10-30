"""Adversarial lexical checks for explicitly posthoc seed61 full-task diagnostic."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import seed61_fulltask_exploratory_20261030 as m

F={'a':'Maple','b':'Finch','a_days':6,'b_days':3}

class PosthocSoftware(unittest.TestCase):
    def test_explicit_named_sooner_correct(self):
        self.assertEqual(m.sooner_claim('Finch finishes sooner (3 days).',F),'CORRECT')
        self.assertEqual(m.sooner_claim('Finch will finish first.',F),'CORRECT')
        self.assertEqual(m.sooner_claim('Finch is faster.',F),'CORRECT')

    def test_explicit_named_sooner_wrong(self):
        self.assertEqual(m.sooner_claim('Maple finishes sooner.',F),'INCORRECT')

    def test_no_claim_does_not_infer_from_day_numbers(self):
        self.assertEqual(m.sooner_claim('Maple takes 6 days and Finch takes 3 days.',F),'NO_EXPLICIT_CLAIM')

    def test_contradiction_and_negation_fail_closed(self):
        self.assertEqual(m.sooner_claim('Maple finishes sooner. Finch finishes sooner.',F),'AMBIGUOUS')
        self.assertEqual(m.sooner_claim('Maple does not finish sooner.',F),'AMBIGUOUS')
        self.assertEqual(m.sooner_claim('Finch ist nicht schneller.',F),'NO_EXPLICIT_CLAIM')

    def test_wrong_original_digest_rejected(self):
        with self.assertRaisesRegex(ValueError,'ORIGINAL_ZIP_SHA256_CHANGED'):
            m.audit(Path(__file__), '0'*64)

if __name__=='__main__':unittest.main()