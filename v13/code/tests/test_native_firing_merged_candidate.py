"""Merged isolated source regressions. No native model is launched here."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import native_firing_candidate_smoke as smoke
from scripts import native_firing_runtime_candidate as firing
from tests import test_native_firing_runtime_candidate as candidate_tests
from v13.memory_server import _native_live_rows


class MergedPreparation(unittest.TestCase):
    def test_both_changes_survive_composition_and_live_sources_are_unchanged(self):
        original,changed=smoke.merged_sources()
        self.assertTrue(all((smoke.ROOT/name).read_text()==text for name,text in original.items()))
        for name,text in changed.items():compile(text,name,'exec')
        runners=changed['v13/runners.py']
        for marker in ('self._audit_lock=threading.Lock()','self._snapshot_assets(cmd,env)',
                       'self._verify_approval_mirror()','self._audit_finish_window(status)'):
            self.assertIn(marker,runners)
        self.assertIn('approval_store=self.store',changed['v13/runtime.py'])
        self.assertIn('observed_shadow_delivery',changed['v13/runtime.py'])

    def test_fixture_is_structurally_live_authored_nonzero_guard_disabled(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'diagnostic.bin';p.write_bytes(smoke.fixture_bytes())
            self.assertEqual(_native_live_rows(p),(1,{0}))

    def test_prepare_is_inference_free_and_hash_change_rejected_before_report(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);binary=root/'binary';model=root/'model';binary.write_bytes(b'b');model.write_bytes(b'm')
            out=root/'proof'
            with patch('subprocess.Popen',side_effect=AssertionError('No inference permitted')):
                registration=smoke.prepare(binary,model,out)
            self.assertEqual(json.loads((out/'registration.json').read_text()),registration)
            self.assertEqual(registration['memory_origin'],'SYNTHETIC_PROTOCOL_FIXTURE')
            self.assertFalse(registration['selective_omission_enabled'])
            model.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Registered diagnostic bytes/config changed'):
                smoke.run(binary,model,out)
            self.assertFalse((out/'report.json').exists())


def load_tests(loader,tests,pattern):
    suite=unittest.TestSuite([tests])
    merged=loader.loadTestsFromModule(candidate_tests)
    class IsolatedSuite(unittest.TestSuite):
        def run(self,result,debug=False):
            with patch.object(candidate_tests,'load_candidate',smoke.load_merged),\
                 patch.object(candidate_tests,'sources',smoke.merged_sources):
                return super().run(result,debug)
    suite.addTest(IsolatedSuite(merged))
    return suite


if __name__=='__main__':unittest.main()
