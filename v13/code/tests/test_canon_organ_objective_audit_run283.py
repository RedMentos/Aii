"""Run283: prevent omission or silent promotion of any binding V13 organ/objective.

Read-only canonical manifest audit. Does not claim code presence = capability.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts import canon_organ_audit as A

ROOT = Path(__file__).resolve().parents[1]


class CanonOrganObjectiveAuditRun283(unittest.TestCase):
    def setUp(self):
        self.contracts = json.loads((ROOT/'specs/component-contracts.json').read_text())
        self.objectives = json.loads((ROOT/'specs/learning-objectives.json').read_text())

    def check(self, contracts=None, objectives=None):
        return A.audit(ROOT, contracts=contracts or self.contracts,
                       objectives=objectives or self.objectives)

    def test_current_manifest_is_consistent_but_explicitly_incomplete(self):
        report = self.check()
        self.assertEqual(report['errors'], [])
        self.assertEqual(report['component_count'], 30)
        self.assertEqual(report['objective_count'], 30)
        self.assertEqual(report['status'], 'CONSISTENT_BUT_INCOMPLETE')
        self.assertFalse(report['canonical_architecture_complete'])
        self.assertIn('B3', report['components_by_mode']['PARTIAL'])
        self.assertIn('A2', report['components_by_mode']['UNAVAILABLE'])

    def test_missing_or_duplicate_canonical_organ_is_rejected(self):
        altered = copy.deepcopy(self.contracts)
        altered['components'] = [x for x in altered['components'] if x['component_id'] != 'C3']
        self.assertIn('MISSING_COMPONENT:C3', self.check(contracts=altered)['errors'])
        altered = copy.deepcopy(self.contracts)
        altered['components'].append(copy.deepcopy(altered['components'][0]))
        self.assertIn('DUPLICATE_COMPONENT:A0', self.check(contracts=altered)['errors'])

    def test_unsupported_completion_claim_is_rejected(self):
        altered = copy.deepcopy(self.contracts)
        altered['canonical_architecture_complete'] = True
        self.assertIn('UNSUPPORTED_COMPLETION_CLAIM', self.check(contracts=altered)['errors'])

    def test_canon_hash_mismatch_is_rejected(self):
        altered = copy.deepcopy(self.contracts)
        altered['canon_sha256'] = '0'*64
        self.assertIn('CANON_HASH_MISMATCH', self.check(contracts=altered)['errors'])

    def test_missing_implementation_file_is_rejected(self):
        altered = copy.deepcopy(self.contracts)
        row = next(x for x in altered['components'] if x['component_id']=='C3')
        row['implementation_files'].append('v13/THIS_DOES_NOT_EXIST_RUN283.py')
        self.assertIn('MISSING_IMPLEMENTATION_FILE:C3:v13/THIS_DOES_NOT_EXIST_RUN283.py',
                      self.check(contracts=altered)['errors'])

    def test_unavailable_component_cannot_be_silently_marked_implemented(self):
        altered = copy.deepcopy(self.contracts)
        row = next(x for x in altered['components'] if x['component_id']=='A2')
        row['current_mode'] = 'IMPLEMENTED'
        self.assertIn('MISSING_IMPLEMENTATION_FILES:A2', self.check(contracts=altered)['errors'])

    def test_unavailable_objective_cannot_gain_learning_authority(self):
        altered = copy.deepcopy(self.objectives)
        row = next(x for x in altered['objectives'] if x['objective_id']=='B_local_JEPA')
        row['learn_gain'] = 0.01
        self.assertIn('UNAUTHORIZED_OBJECTIVE_GAIN:B_local_JEPA',
                      self.check(objectives=altered)['errors'])

    def test_objective_cannot_reference_nonexistent_organ(self):
        altered = copy.deepcopy(self.objectives)
        altered['objectives'][0]['applicable_components'].append('Z999')
        self.assertIn('UNKNOWN_OBJECTIVE_COMPONENT:Z999',
                      self.check(objectives=altered)['errors'])

    def test_duplicate_objective_id_is_rejected(self):
        altered = copy.deepcopy(self.objectives)
        altered['objectives'].append(copy.deepcopy(altered['objectives'][0]))
        self.assertIn('DUPLICATE_OBJECTIVE:'+altered['objectives'][0]['objective_id'],
                      self.check(objectives=altered)['errors'])


if __name__ == '__main__':
    unittest.main()
