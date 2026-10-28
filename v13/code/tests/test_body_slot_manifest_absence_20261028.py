"""WP-N11/AG0: removed body manifests cannot resurrect stale ACTIVE/RAMP slots."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v13.common import Unavailable
from v13.runtime import Runtime


class BodySlotManifestAbsence(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.home=Path(self.temp.name)
        self.r=Runtime(self.home)
        self.fake=self.home/'candidate.gguf'
        self.fake.write_bytes(b'GGUF synthetic')
        self.slot={'stage':'ACTIVE',
                   'active':{'path':str(self.fake),'revision':'candidate-rev'}}

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def test_no_b_manifest_never_treats_old_active_as_committed_swap(self):
        fabric=self.r.bodies
        self.assertIsNone(fabric._committed('B1_DETAIL',self.slot))
        self.assertIsNone(fabric._committed('B2_GIST',self.slot))
        with patch.object(fabric.slots.box,'load',
                          return_value=({'slots':{'B1_DETAIL':self.slot}},0)):
            self.assertIsNone(fabric.path_override('B1_DETAIL'))
            with self.assertRaises(Unavailable):
                self.r.models.path_for('B1_DETAIL')

    def test_real_committed_swap_requires_installed_baseline_revision(self):
        fabric=self.r.bodies
        self.r.models.installed['body']={'exact_revision':'baseline-rev',
                                         'download_complete':True}
        self.assertEqual(fabric._committed('B1_DETAIL',self.slot),self.fake)
        self.slot['active']['revision']='baseline-rev'
        self.assertIsNone(fabric._committed('B1_DETAIL',self.slot))
        self.r.models.installed.pop('body')
        self.slot['active']['revision']='candidate-rev'
        self.assertIsNone(fabric._committed('B1_DETAIL',self.slot))

    def test_no_b_manifest_blocks_ramp_even_if_route_key_exists(self):
        fabric=self.r.bodies
        ramp={'stage':'RAMP',
              'active':{'path':str(self.fake),'revision':'old-rev'},
              'candidate':{'path':str(self.fake),'revision':'candidate-rev'}}
        fabric.route_key='synthetic-turn'
        with patch.object(fabric.slots.box,'load',
                          return_value=({'slots':{'B1_DETAIL':ramp}},0)):
            self.assertIsNone(fabric.path_override('B1_DETAIL'))
            with self.assertRaises(Unavailable):
                self.r.models.path_for('B1_DETAIL')


if __name__=='__main__':
    unittest.main()
