"""Run68 frozen source and schema parser tests, no native model."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import jef_c3_schema_fixture_727 as f

class Fixture(unittest.TestCase):
    def test_six_balanced(self):
        rows=f.fixtures()
        self.assertEqual([r['expected'] for r in rows],['A','B','NONE']*2)
        self.assertEqual(len({r['project'] for r in rows}),6)

    def test_registered_table_tamper(self):
        x=f.TABLE[0]
        try:
            f.TABLE[0]=x[:-1]+('B',)
            with self.assertRaisesRegex(ValueError,'TABLE_CHANGED'):f.fixtures()
        finally:f.TABLE[0]=x

    def test_oracle(self):
        for row in f.TABLE:self.assertEqual(f.oracle(row[6],row[7:9]),row[-1])

    def test_schema_frozen(self):
        self.assertEqual(f.SCHEMA,{'type':'object','properties':{'action':{'type':'string','enum':['A','B','NONE']}},'required':['action'],'additionalProperties':False})

    def test_exact_schema_copy(self):
        for a in ('A','B','NONE'):
            self.assertEqual(f.decode_schema('{"action":"'+a+'"}'),a)
            self.assertEqual(f.score('{"action":"'+a+'"}',a,'SCHEMA'),1)

    def test_duplicate_key_rejected(self):
        self.assertIsNone(f.decode_schema('{"action":"A","action":"B"}'))

    def test_extra_key_rejected(self):
        self.assertIsNone(f.decode_schema('{"action":"A","other":1}'))

    def test_wrong_type_rejected(self):
        self.assertIsNone(f.decode_schema('{"action":1}'))

    def test_wrong_action_rejected(self):
        self.assertIsNone(f.decode_schema('{"action":"C"}'))

    def test_nonjson_rejected(self):
        self.assertIsNone(f.decode_schema('Option A'))

    def test_strict_baseline_no_trim(self):
        self.assertEqual(f.score('A','A','BASELINE'),1)
        self.assertEqual(f.score(' A','A','BASELINE'),0)

    def test_invalid_arm_rejected(self):
        with self.assertRaisesRegex(ValueError,'ARM_RED'):f.score('A','A','PROMOTE')

if __name__=='__main__':unittest.main()
