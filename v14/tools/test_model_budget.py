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
        with self.assertRaises(ValueError): audit(self.registry, True)
        with self.assertRaises(ValueError): audit(self.registry, 1.0)

    def test_optional_models_not_baseline(self):
        self.registry['models']['vision'] = {'model_id': 'eye', 'revision': 'sha2', 'files': [{'size': 900}]}
        result = audit(self.registry, 100)
        self.assertTrue(result['baseline_fits_disk_only'])
        self.assertFalse(result['fits_disk_only'])
        self.assertEqual(result['baseline_disk_bytes'], 100)
        self.assertEqual(result['optional_disk_bytes'], 900)

if __name__ == '__main__': unittest.main()
