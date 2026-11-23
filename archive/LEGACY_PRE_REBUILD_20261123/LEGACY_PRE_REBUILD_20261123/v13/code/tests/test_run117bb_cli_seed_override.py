"""Run117BB native-only seed override cannot alter original default or synthetic authority."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from scripts import jef_c3_c5_c6_operator_cli as cli
from scripts.run63_jef_c3_native import cohort

class Run117BBSeedOverride(unittest.TestCase):
    def test_invalid_seed_fails_before_input_and_runtime(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for seed in (True,False,1.0,'13',-1,2147483648,{},[]):
                with self.subTest(seed=seed):
                    result=cli.run(root/'home',root/'missing.json','native',
                        operator_opt_in=True,callback_opt_in=True,seed_override=seed)
                    self.assertEqual(result['status'],'SEED_OVERRIDE_RED')
                    self.assertFalse(result['input_read'])
                    self.assertFalse(result['runtime_opened'])
                    self.assertFalse((root/'home').exists())

    def test_synthetic_override_refused_even_with_optin(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for mode in ('synthetic_exact','synthetic_schema_exact','synthetic_wrong'):
                result=cli.run(root/'home',root/'missing.json',mode,
                    operator_opt_in=True,callback_opt_in=True,seed_override=13)
                self.assertEqual(result['status'],'SEED_OVERRIDE_RED')
                self.assertFalse((root/'home').exists())

    def test_native_valid_seed_reaches_original_model_binding_guard(self):
        row=cohort()[0]
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);inp=root/'input.json'
            inp.write_text(json.dumps({'project':row['id'],'domain':row['domain'],
                'policy_source':row['b2_source'],'sheet_source':row['b1_source'],
                'current':row['current']}))
            for mode,seed in (('native',13),('native_schema',727),('native',0),
                              ('native_schema',2147483647)):
                result=cli.run(root/f'home_{mode}_{seed}',inp,mode,
                    operator_opt_in=True,callback_opt_in=True,
                    route_shadow=True,seed_override=seed)
                self.assertEqual(result['status'],'NATIVE_BINDING_RED')
                self.assertFalse(result['native_model_called'])
                self.assertFalse(result['output_committed'])

    def test_cli_rejects_bad_seed_before_file_or_store(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            command=[sys.executable,str(Path(cli.__file__).resolve()),
                     '--home',str(root/'home'),'--input-file',str(root/'missing.json'),
                     '--mode','native','--operator-opt-in','--callback-opt-in',
                     '--seed-override','-1']
            p=subprocess.run(command,capture_output=True,text=True,timeout=20)
            self.assertEqual(p.returncode,1)
            self.assertEqual(json.loads(p.stdout)['status'],'SEED_OVERRIDE_RED')
            self.assertFalse((root/'home').exists())

if __name__=='__main__':unittest.main()
