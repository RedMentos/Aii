"""Run444: packaged Phone ZIP executes its real offline installer and doctor.

Software-only Linux acceptance; no Termux/Redmi/native/model proof.
"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Run444PhoneOfflineSetup(unittest.TestCase):
    def test_extracted_phone_source_integrity_and_offline_cli(self):
        if not (ROOT / 'WORKSPACE_FILES.json').is_file():
            self.skipTest('Packaged Phone source ZIP required; checkout is not an installer artifact')
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / 'data-home'
            env = os.environ.copy()
            env.update(V13_SOURCE_ONLY_DIAGNOSTIC='1', V13_HOME=str(home),
                       HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                       NO_MODEL_DOWNLOADS='1', NEEDLE_TELEMETRY='0',
                       V13_NO_AUTOSTART='1')
            env.pop('PREFIX', None)
            result = subprocess.run(['bash', str(ROOT / 'setup.sh')], cwd=ROOT,
                                    env=env, text=True, capture_output=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stdout[-600:] + result.stderr[-600:])
            self.assertIn('SOURCE_ONLY_DIAGNOSTIC: source integrity verified', result.stdout)
            self.assertIn('NO_NATIVE_MODEL / NO_REDMi / NO_JEPA_PROOF', result.stdout)
            self.assertIn('STEP2=UTILITY_FAIL B3_L1=FAIL Body-JEPA=UNAVAILABLE jepa_weight=0 V13=INCOMPLETE', result.stdout)
            launcher = home / 'bin/v13'
            self.assertTrue(launcher.is_file())
            self.assertTrue(os.access(launcher, os.X_OK))
            cli = subprocess.run([str(launcher), 'doctor'], cwd=ROOT, env=env,
                                 text=True, capture_output=True, timeout=30)
            self.assertEqual(cli.returncode, 0, cli.stderr)
            report = json.loads(cli.stdout)
            self.assertEqual(report['data_integrity_errors'], [])
            self.assertFalse(report['canonical_architecture_complete'])
            self.assertIn('language', report['missing_models'])
            self.assertEqual(report['learning_mode'], 'RECORD_ONLY')
            self.assertFalse(list(home.rglob('*.gguf')))
            self.assertFalse(list(home.rglob('*.safetensors')))
            self.assertFalse(list(home.rglob('native-probe.json')))


if __name__ == '__main__':
    unittest.main()
