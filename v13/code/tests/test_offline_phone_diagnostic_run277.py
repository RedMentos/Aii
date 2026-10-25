"""Run277: real extracted source ZIP offline diagnostic, never a native proof."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from scripts.package_source import package
from scripts.verify_phone_zip_current_run268 import verify


class OfflinePhoneDiagnosticRun277(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.tmp.name)
        cls.source=Path(__file__).resolve().parents[1]
        cls.zip_path=cls.root/'V13-Phone.zip'
        cls.package_report=package(cls.source,cls.zip_path,phone_install=True)
        cls.report=verify(cls.zip_path,cls.source)
        with zipfile.ZipFile(cls.zip_path) as z:z.extractall(cls.root/'extract')
        cls.app=cls.root/'extract/V13-Phone'

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def diagnostic(self,home,app=None):
        env=os.environ.copy()
        # The subprocess must use the same pinned isolated interpreter that the
        # CI fixture provisioned; system python3 may have no NumPy.
        env.update(PATH=str(Path(sys.executable).parent)+os.pathsep+env.get('PATH',''),
                   V13_HOME=str(home),V13_NO_AUTOSTART='1',V13_SOURCE_ONLY_DIAGNOSTIC='1',
                   PIP_NO_INDEX='1',PIP_DISABLE_PIP_VERSION_CHECK='1',NEEDLE_TELEMETRY='0',DO_NOT_TRACK='1')
        return subprocess.run(['bash','setup.sh'],cwd=app or self.app,env=env,text=True,
                              stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)

    def test_current_phone_zip_source_hashes_and_all_organs_present(self):
        self.assertGreaterEqual(self.report['file_count'],980)
        self.assertEqual(self.report['all_member_hashes'],'PASS')
        self.assertEqual(self.report['checkout_byte_parity'],'PASS')
        self.assertFalse(self.report['native_model_inference'])
        self.assertFalse(self.report['redmi_measured'])
        for name in ('v13/memory.py','v13/context_os.py','v13/executive.py','v13/focal.py',
                     'v13/sleep.py','v13/operator.py','tests/test_operator_memory_authority_run276.py'):
            self.assertTrue((self.app/name).is_file(),name)

    def test_real_extracted_zip_offline_setup_runs_doctor_without_models(self):
        home=self.root/'home'
        p=self.diagnostic(home)
        self.assertEqual(p.returncode,0,p.stdout[-5000:])
        self.assertIn('SOURCE_ONLY_DIAGNOSTIC',p.stdout)
        self.assertIn('NO_NATIVE_MODEL / NO_REDMi / NO_JEPA_PROOF',p.stdout)
        self.assertIn('STEP2=UTILITY_FAIL B3_L1=FAIL',p.stdout)
        self.assertIn('Full selftest and model probe NOT RUN',p.stdout)
        self.assertNotIn('Download-Versuch',p.stdout)
        self.assertNotIn('Lade Cactus-Compute',p.stdout)
        self.assertTrue((home/'bin/v13').is_file())
        self.assertFalse((home/'bin/llama-server').exists())
        self.assertEqual(list(home.rglob('*.gguf')),[])
        self.assertEqual(list(home.rglob('*.cact')),[])
        self.assertEqual(self.report['gates']['V13'],'INCOMPLETE')

    def test_tampered_extracted_source_is_refused_before_setup(self):
        # Separate fresh extraction; never mutate the verified positive fixture.
        other=self.root/'tampered'
        with zipfile.ZipFile(self.zip_path) as z:z.extractall(other)
        app=other/'V13-Phone'
        with (app/'v13/memory.py').open('ab') as f:f.write(b'\n# adversarial tamper\n')
        home=self.root/'tampered_home'
        p=self.diagnostic(home,app)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('SOURCE_HASH_MISMATCH',p.stdout.upper())
        self.assertFalse((home/'bin/v13').exists())

    def test_default_installer_remains_native_and_full_selftest_path(self):
        script=(self.app/'setup.sh').read_text()
        self.assertIn('"$V13_PYTHON" -m v13.bootstrap --home "$V13_DATA_HOME"',script)
        self.assertIn('"$V13_DATA_HOME/bin/v13" selftest',script)
        self.assertIn('"$V13_DATA_HOME/bin/v13" probe',script)
        self.assertIn('V13_SOURCE_ONLY_DIAGNOSTIC:-0',script)
        self.assertEqual(subprocess.run(['bash','-n',str(self.app/'setup.sh')]).returncode,0)


if __name__=='__main__':unittest.main()
