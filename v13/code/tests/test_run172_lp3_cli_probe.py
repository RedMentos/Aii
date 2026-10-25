import os
import pathlib
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from run172_lp3_cli_probe import probe

HELPER = pathlib.Path(os.environ.get('RUN172_HELPER', str(pathlib.Path(__file__).resolve().parents[1] / 'scripts/lp3_serial_cohort.py')))

class TestLP3CLI(unittest.TestCase):
    def test_exact_reconstructed_helper_refuses_native(self):
        if not HELPER.is_file():raise unittest.SkipTest('Run21 helper not staged')
        result=probe(HELPER)
        self.assertEqual(result['returncode'],2, result['stderr_excerpt'])
        self.assertTrue(result['expected_blocked_rc2'])
        self.assertFalse(result['native_executed'])
    def test_nonexact_helper_refused_before_launch(self):
        with self.assertRaisesRegex(ValueError,'helper_not_exact'):
            probe(pathlib.Path(__file__).resolve())
    def test_missing_sibling_is_distinct_import_failure(self):
        if not HELPER.is_file():raise unittest.SkipTest('Run21 helper not staged')
        with tempfile.TemporaryDirectory() as d:
            only=pathlib.Path(d)/'lp3_serial_cohort.py';shutil.copyfile(HELPER,only)
            env=os.environ.copy();env['PYTHONPATH']=''
            result=probe(only,env=env)
            self.assertEqual(result['returncode'],1)
            self.assertFalse(result['expected_blocked_rc2'])
            self.assertIn('ModuleNotFoundError',result['stderr_excerpt'])

if __name__=='__main__':unittest.main()
