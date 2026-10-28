"""C5 model-manifest availability: synthetic no-B and shared-body controls."""
import json
from pathlib import Path
import tempfile
import unittest

from v13.focal import ActionGate, available_body_roles
from v13.runtime import Runtime


class C5ManifestAvailability(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.temp.name))
        self.e = {'event_id': 'evt_c5_manifest',
                  'brain_generation_id': self.r.store.generation_id,
                  'source_ref': self.r.store.source('Budget 120 Euro', 'USER')}
        self.gate = ActionGate(self.r.store)

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def choose(self, route, available):
        return self.gate.select(self.e, route=route, direct=False,
                                resource_state='NORMAL', available_roles=available)

    def test_no_b_manifest_suppresses_both_roles_and_c3_is_selected(self):
        for route in ('detail', 'gist', 'both', 'simple'):
            selected = self.choose(route, set())
            self.assertEqual(selected['role'], 'C3_LANGUAGE')
            reasons = {x['action_id']: x['reason'] for x in selected['suppressed']}
            self.assertEqual(reasons['B1_DETAIL'], 'MODEL_MANIFEST_ABSENT')
            self.assertEqual(reasons['B2_GIST'], 'MODEL_MANIFEST_ABSENT')
            packet = json.loads(self.r.store.one(
                "SELECT payload FROM packets WHERE kind='ActionSelection' ORDER BY rowid DESC LIMIT 1"
            )['payload'])
            self.assertEqual(packet['selected']['action_id'], 'C3_LANGUAGE')

    def test_installed_roles_and_legacy_callers_keep_route_table(self):
        self.assertEqual(self.choose('detail', {'B1_DETAIL','B2_GIST'})['role'],
                         'B1_DETAIL')
        self.assertEqual(self.choose('gist', {'B1_DETAIL','B2_GIST'})['role'],
                         'B2_GIST')
        self.assertEqual(self.choose('both', {'B1_DETAIL','B2_GIST'})['role'],
                         'B1_DETAIL')
        self.assertEqual(self.choose('gist', {'B1_DETAIL'})['role'], 'C3_LANGUAGE')
        self.assertEqual(self.choose('detail', {'B2_GIST'})['role'], 'C3_LANGUAGE')
        self.assertEqual(self.gate.select(self.e, route='both', direct=False,
                                         resource_state='NORMAL')['role'], 'B1_DETAIL')

    def test_shared_body_control_maps_b2_to_body_manifest(self):
        self.r.models.installed = {
            'body': {'download_complete': True},
            'gist': {'download_complete': False},
        }
        self.r.models.b2_control = 'two_body'
        self.assertEqual(available_body_roles(self.r.models), {'B1_DETAIL'})
        self.r.models.b2_control = 'shared_body_dual_state'
        self.assertEqual(available_body_roles(self.r.models),
                         {'B1_DETAIL', 'B2_GIST'})
        self.r.models.installed['body']['download_complete'] = False
        self.assertEqual(available_body_roles(self.r.models), set())


if __name__ == '__main__':
    unittest.main()
