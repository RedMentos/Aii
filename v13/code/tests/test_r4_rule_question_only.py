"""R4 part 9 script: question part extraction and frozen rule variants. No models."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import r4_rule_question_only as Q

class Rule(unittest.TestCase):
    def test_question_part_skips_data_with_total_line(self):
        t='Expense report. Items: cables 12 euros, postage 30 euros. Summary line at the bottom: "Total: 52 euros." Which item is the smallest?'
        self.assertEqual(Q.question_part(t),'Which item is the smallest?');self.assertEqual(Q.r0(t),'total');self.assertIsNone(Q.r1(t))
        self.assertEqual(Q.question_part('a 1, b 2. Is that right? Give the correct total.'),'Is that right? Give the correct total.')
    def test_r2_extra_wording(self):
        self.assertEqual(Q.r2('Rainfall: Lyon 600, Brno 200. By how much does the biggest exceed the smallest?'),'difference_max_min')
        self.assertEqual(Q.r2('Points: Mira 4, Omar 9. Add them all up.'),'total');self.assertIsNone(Q.r2('Points: Mira 4, Omar 9. Name the second item.'))
    def test_family_d_disjoint_from_part8(self):
        import r4_tool_choice_head as H
        old={r['question'] for r in H.corpus()};d=Q.family_d();self.assertEqual(len(d),228)
        self.assertFalse(old&{r['question'] for r in d})

if __name__=='__main__':unittest.main()
