"""R4 part 5: BOOT operation rule, recipe and number guard of scripts/r4_typed_recipe.py (no model)."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import r4_typed_recipe as T

V=lambda *p:[{'name':n,'number':x} for n,x in p]
class Recipe(unittest.TestCase):
    def test_operation_rule(self):
        self.assertEqual(T.operation('Which city had the most rain, and how many millimetres more than the city with the least?'),'difference_max_min')
        self.assertEqual(T.operation('Is the summary line correct? Give the correct total.'),'total')
        self.assertEqual(T.operation('Which number is the most recent one?'),'none')
    def test_recipe_names_extremes_and_sums(self):
        self.assertEqual(T.recipe('difference_max_min',V(('Lyon',644),('Brno',255),('Linz',300)),'Lyon 644, Brno 255, Linz 300.'),(389,'largest Lyon 644 - smallest Brno 255'))
        self.assertEqual(T.recipe('total',V(('pens',12),('ink',30)),'pens 12 euros, ink 30 euros.')[0],42)
    def test_number_guard(self):
        with self.assertRaises(ValueError):T.recipe('total',V(('a',12),('b',31)),'a 12, b 30.')
        with self.assertRaises(ValueError):T.recipe('total',V(('a',3),('b',5)),'cost 3.5 and 5')  # 3 only inside a decimal
        with self.assertRaises(ValueError):T.recipe('total',V(('a',3)),'a 3.')
        with self.assertRaises(ValueError):T.recipe('none',V(('a',3),('b',4)),'a 3, b 4.')

if __name__=='__main__':unittest.main()
