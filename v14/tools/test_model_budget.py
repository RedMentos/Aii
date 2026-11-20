import unittest
from model_budget import audit

class ModelBudgetTest(unittest.TestCase):
    def setUp(self):
        self.registry = {'models': {'language': {'model_id': 'test', 'revision': 'sha', 'license_id': 'Apache-2.0', 'files': [{'size': 100}]}, 'optional': {'files': []}}}

    def test_budget_and_provenance(self):
        result = audit(self.registry, 100)
        self.assertTrue(result['fits_disk_only'])
        self.assertEqual(result['models'][0]['license_id'], 'Apache-2.0')
        self.assertEqual(result['combined_disk_bytes'], 100)

    def test_insufficient_budget(self):
        self.assertFalse(audit(self.registry, 99)['fits_disk_only'])

    def test_negative_and_bool_rejected(self):
        for size in (-1, True):
            self.registry['models']['language']['files'][0]['size'] = size
            with self.assertRaises(ValueError): audit(self.registry, 100)

    def test_negative_capacity_rejected(self):
        with self.assertRaises(ValueError): audit(self.registry, -1)

if __name__ == '__main__': unittest.main()
