"""R4 part 10 script: counting exclusion and family E disjointness. No models."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import r4_rule_r3 as R
import r4_rule_question_only as Q
import r4_tool_choice_head as H

class R3(unittest.TestCase):
    def test_counting_is_not_a_sum(self):
        self.assertIsNone(R.r3('Points: Mira 4, Omar 9. What is the total number of entries?'))
        self.assertEqual(R.r3('Points: Mira 4, Omar 9. What is the total?'),'total')
        self.assertEqual(R.r3('Points: Mira 4, Omar 9. How many more does the largest have than the smallest?'),'difference_max_min')
    def test_family_e_new(self):
        e={r['question'] for r in R.family_e()};self.assertEqual(len(R.family_e()),228)
        self.assertFalse(e&{r['question'] for r in H.corpus()});self.assertFalse(e&{r['question'] for r in Q.family_d()})

if __name__=='__main__':unittest.main()
