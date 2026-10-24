"""Run68: human RECORD labels block lower-authority JEF outcome training rows.

Full checkout integration test; fake Store only to stop before native optimizer.
"""
import json
import unittest
from unittest.mock import patch
from v13.learning import Learner


class FakeStore:
    def __init__(self, permission='record', revision='rev', include_decision=True):
        self.permission = permission
        self.revision = revision
        self.include_decision = include_decision

    def rows(self, query, args=()):
        if 'FROM feedback f' in query:
            return [{'event_id':'e1','source_id':'human1','kind':'wake','value':'detail',
                     'permission':self.permission,'created':1.,'hash':'sha-human'}]
        raise AssertionError(query)

    def one(self, query, args=()):
        if 'HumanDecision' in query:
            return {'payload':json.dumps({'decision_packet_id':'decision1'})} if self.include_decision else None
        if 'ExecutiveDecision' in query:
            if not args or args[0] is None:
                return None
            return {'payload':json.dumps({'component':'wake','context_revision':self.revision,
                    'context_ref':{'sha256':'ctx1'},'packet_id':'decision1'})}
        raise AssertionError(query)

    def log(self, *args):
        pass


class FakeRuntime:
    cfg = {'learning_mode':'SHADOW_UPDATE'}
    guard = type('Guard',(),{'update':lambda self, resources:'NORMAL'})()

    def resources(self):
        return {}


def capture_keys(permission='record', revision='rev', include_decision=True):
    learner = Learner.__new__(Learner)
    learner.r = FakeRuntime()
    learner.s = FakeStore(permission, revision, include_decision)
    learner.context_revision = lambda component:'rev'
    captured = []

    def outcome_rows(store, component, rev, keys):
        captured.append(set(keys))
        return []

    with patch('v13.jefoutcome.training_rows', side_effect=outcome_rows):
        with unittest.TestCase().assertRaises(ValueError):
            learner.shadow_readout('wake')  # min six per class; no optimizer runs
    return captured


class HumanPrecedence(unittest.TestCase):
    def test_record_permission_blocks_lower_authority(self):
        self.assertEqual(capture_keys('record'),[{'ctx1'}])

    def test_learn_permission_also_blocks_lower_authority(self):
        self.assertEqual(capture_keys('learn'),[{'ctx1'}])

    def test_no_human_decision_does_not_block(self):
        self.assertEqual(capture_keys('record',include_decision=False),[set()])

    def test_stale_revision_does_not_claim_same_context(self):
        self.assertEqual(capture_keys('record',revision='old'),[set()])


if __name__ == '__main__':
    unittest.main()
